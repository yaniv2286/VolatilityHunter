"""
VolatilityHunter Daily Trading Loop
=====================================
Fully autonomous scan -> rank -> execute cycle.
Called once per day by Windows Task Scheduler at market open.

Pipeline:
  1. Reconcile local portfolio.json with actual IBKR positions
  2. Fetch today's prices (Yahoo Finance, last 5 days appended to parquet history)
  3. Check exits on all open positions
  4. Scan all 2,147 tickers -> generate signals -> rank by score
  5. Open new positions up to MAX_POSITIONS cap (Ironclad Guardrails)
  6. Verify orders filled after 60s
  7. Send email summary
  8. Save updated portfolio.json

ASCII output only. Task Scheduler compatible.
Exit code 0 = success, 1 = fatal error.
"""

import os
import sys
import json
import time
import logging
import traceback
from datetime import datetime, date
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np
import requests
from dotenv import load_dotenv

# Fix Python pathing - ensure ROOT is correctly set
import os, sys, pathlib
ROOT = pathlib.Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.strategy_v7_2 import add_indicators_v7_2
from src.brokerage_interface import get_brokerage_interface
from src.email_notifier import EmailNotifier
from src.strategy_engine import (
    promote_power_stocks,
    update_highest_prices,
    update_high_water_mark,
    get_dd_scale,
    get_params,
    check_exits       as engine_check_exits,
    scan_universe     as engine_scan_universe,
    calc_position_size,
    can_enter,
    get_spy_regime,
    get_regime_max_positions,
    get_params        as engine_get_params,
    DEFAULT_VERSION,
)

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)
today_str = datetime.now().strftime('%Y-%m-%d')

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / f"trading_{today_str}.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('daily_loop')

# ── Constants ─────────────────────────────────────────────────────────────────
DATA_DIR          = ROOT / "data"
PORTFOLIO_FILE    = DATA_DIR / "portfolio.json"
TICKERS_FILE      = ROOT / "tickers.txt"

INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20          # 20% per position (Ironclad Guardrail)
# Strategy parameters are in src/strategy_engine.py PARAMS[DEFAULT_VERSION]
# Change DEFAULT_VERSION there to switch all modes at once.
SPY_PARQUET       = DATA_DIR / "SPY.parquet"
ORDER_CONFIRM_SEC = 90

IBKR_CONFIG = {
    'BROKERAGE_TYPE': 'ibkr',
    'IBKR_HOST':      '127.0.0.1',
    'IBKR_PORT':      7497,
    'IBKR_CLIENT_ID': 42
}


# ── Portfolio state ───────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    try:
        with open(PORTFOLIO_FILE, 'r') as f:
            p = json.load(f)
        logger.info(f"Portfolio loaded: {len(p.get('positions', {}))} positions, "
                    f"${p.get('cash', 0):,.2f} cash")
        return p
    except Exception as e:
        logger.error(f"Failed to load portfolio: {e}")
        logger.error(traceback.format_exc())
        return {'cash': INITIAL_CAPITAL, 'positions': {}, 'trade_history': [], 'total_value': INITIAL_CAPITAL}


def save_portfolio(portfolio: dict):
    try:
        backup = PORTFOLIO_FILE.with_suffix('.backup.json')
        if PORTFOLIO_FILE.exists():
            import shutil
            shutil.copy2(PORTFOLIO_FILE, backup)
        with open(PORTFOLIO_FILE, 'w') as f:
            json.dump(portfolio, f, indent=2, default=str)
        logger.info("Portfolio saved.")
    except Exception as e:
        logger.error(f"Failed to save portfolio: {e}")
        logger.error(traceback.format_exc())


# ── Step 1: IBKR reconciliation ───────────────────────────────────────────────

def reconcile_with_ibkr(portfolio: dict) -> Tuple[dict, object]:
    """
    Connect to IBKR, sync local portfolio with actual positions.
    IBKR-FIRST: IBKR is the golden reference - always overwrites local data.
    Returns (updated_portfolio, ibkr_interface).
    CRITICAL: IBKR connection is MANDATORY - system fails if unavailable.
    """
    logger.info("--- Step 1: Reconciling with IBKR ---")
    try:
        ibkr = get_brokerage_interface(IBKR_CONFIG)
        if not ibkr.connect():
            logger.error("CRITICAL: IBKR connection FAILED - cannot proceed")
            logger.error("System requires IBKR Paper account connection for all trades")
            logger.error("Check: 1) IB Gateway running, 2) Port 7497 open, 3) Network connectivity")
            sys.exit(1)

        account = ibkr.get_account_info()
        ibkr_positions = ibkr.get_positions()

        # IBKR-FIRST: Overwrite cash with IBKR value (golden reference)
        if account:
            ibkr_cash = account.get('cash', 0)
            ibkr_equity = account.get('equity', 0)
            logger.info(f"IBKR account: cash=${ibkr_cash:,.2f}, equity=${ibkr_equity:,.2f}")
            
            # CRITICAL SANITY CHECK: Prevent margin bug from inflated IBKR cash
            # IBKR Paper account can accumulate liquidation proceeds, causing
            # cash balance to be 5-6x larger than it should be. This leads to
            # massive position sizes and margin usage.
            old_cash = portfolio.get('cash', 0)
            
            # ABSOLUTE THRESHOLD: Reject IBKR cash if it's suspiciously high
            # For a $100k account, anything >$150k is clearly wrong
            ABSOLUTE_MAX_CASH = 150000
            
            # RELATIVE THRESHOLD: Reject if IBKR is >2x portfolio (when portfolio is positive)
            reject_ibkr = False
            reason = ""
            
            if ibkr_cash > ABSOLUTE_MAX_CASH:
                reject_ibkr = True
                reason = f"IBKR cash ${ibkr_cash:,.2f} exceeds absolute max ${ABSOLUTE_MAX_CASH:,.2f}"
            elif old_cash > 0 and ibkr_cash > old_cash * 2.0:
                reject_ibkr = True
                reason = f"IBKR cash ${ibkr_cash:,.2f} is {ibkr_cash/old_cash:.1f}x portfolio ${old_cash:,.2f}"
            
            if reject_ibkr:
                logger.error("=" * 68)
                logger.error("CRITICAL: IBKR CASH SANITY CHECK FAILED")
                logger.error(f"Reason: {reason}")
                logger.error(f"IBKR reports: ${ibkr_cash:,.2f}")
                logger.error(f"Portfolio.json: ${old_cash:,.2f}")
                logger.error("")
                logger.error("This indicates IBKR Paper account has accumulated")
                logger.error("liquidation proceeds and is reporting inflated cash.")
                logger.error("ABORTING TRADING - Portfolio cash is unreliable.")
                logger.error("Manual intervention required to reset account.")
                logger.error("=" * 68)
                # ABORT - don't trade with corrupted data
                logger.error("TRADING ABORTED - Portfolio state corrupted")
                sys.exit(1)
            else:
                # IBKR cash is reasonable, use it
                portfolio['cash'] = ibkr_cash
                if abs(ibkr_cash - old_cash) > 100:
                    logger.warning(f"Cash reset: local=${old_cash:,.2f} -> IBKR=${ibkr_cash:,.2f}")

        # IBKR-FIRST: Replace all positions with IBKR positions
        old_positions = portfolio.get('positions', {})
        portfolio['positions'] = {}
        
        params = get_params(DEFAULT_VERSION)
        hard_stop_pct = params['HARD_STOP_PCT']
        
        for pos in ibkr_positions:
            sym = pos['symbol']
            portfolio['positions'][sym] = {
                'shares':      int(pos['quantity']),
                'entry_price': pos.get('entry_price', pos.get('current_price', 0)),
                'entry_date':  today_str,
                'ticker':      sym,
                'execution_mode': 'LIVE',
                'is_power_stock': False,
                'highest_price':  pos.get('current_price', 0),
                'quality_score':  0,
                'stop_loss_price': pos.get('entry_price', 0) * (1 - hard_stop_pct)
            }
        
        # Log discarded PAPER positions (if any)
        paper_positions = {k: v for k, v in old_positions.items() 
                          if v.get('execution_mode') == 'PAPER'}
        if paper_positions:
            logger.warning(f"Discarded {len(paper_positions)} PAPER positions (IBKR is master):")
            for sym in paper_positions:
                logger.warning(f"  - {sym}: {paper_positions[sym]['shares']} shares")
        
        # Update sync timestamp
        portfolio['last_ibkr_sync'] = datetime.now().isoformat()
        portfolio['ibkr_available'] = True
        
        logger.info(f"IBKR sync complete: {len(portfolio['positions'])} LIVE positions")
        return portfolio, ibkr

    except Exception as e:
        logger.error(f"CRITICAL: IBKR connection error: {e}")
        logger.error(traceback.format_exc())
        logger.error("System cannot proceed without IBKR connection")
        sys.exit(1)


# ── Step 2: Fetch today's data ────────────────────────────────────────────────

def fetch_latest_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch today's close for a list of tickers using Tiingo Professional API only."""
    logger.info(f"Production: Fetching latest prices for {len(tickers)} tickers via Tiingo Professional API")
    
    try:
        # Use the professional data loader (Tiingo only)
        from src.smart_data_loader_factory import get_data_loader
        loader = get_data_loader()
        
        # Call Tiingo bulk API - this handles 1000 tickers per request
        result = loader.update_all_stocks(tickers, full_refresh=False, batch_size=1000)
        
        if result['success']:
            prices = result.get('prices', {})
            logger.info(f"Production: Successfully fetched {len(prices)}/{len(tickers)} ticker prices via Tiingo bulk API")
            
            # Log first few prices for verification
            for i, (ticker, price) in enumerate(prices.items()):
                if i < 5:  # Log first 5 for verification
                    logger.info(f"Production: Got price for {ticker}: ${price:.2f}")
                else:
                    break
                    
            return prices
        else:
            logger.error(f"Production: Tiingo API failed - {result.get('error', 'Unknown error')}")
            return {}
            
    except Exception as e:
        logger.error(f"Production: Critical error in fetch_latest_prices: {e}")
        logger.error(traceback.format_exc())
        return {}


def load_ticker_with_latest(ticker: str, latest_prices: Dict[str, float]) -> Optional[pd.DataFrame]:
    """
    Load parquet history + append today's row from Yahoo Finance.
    Returns df with indicators calculated, or None on failure.
    """
    try:
        parquet = DATA_DIR / f"{ticker.lower()}.parquet"
        if not parquet.exists():
            return None

        df = pd.read_parquet(parquet)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)

        # Append today's data via Yahoo if not already present
        today = pd.Timestamp(date.today())
        if today not in df.index and ticker in latest_prices:
            try:
                yf_data = yf.download(
                    ticker, period='5d', auto_adjust=True,
                    progress=False, threads=False
                )
                if not yf_data.empty:
                    yf_data.index = yf_data.index.tz_localize(None) if hasattr(yf_data.index, 'tz') and yf_data.index.tz else yf_data.index
                    # Only append rows newer than last parquet date
                    new_rows = yf_data[yf_data.index > df.index[-1]]
                    if not new_rows.empty:
                        # Align columns
                        col_map = {}
                        for c in new_rows.columns:
                            c_lower = c.lower()
                            if 'close' in c_lower:
                                col_map[c] = 'adjClose'
                            elif 'open' in c_lower:
                                col_map[c] = 'adjOpen'
                            elif 'high' in c_lower:
                                col_map[c] = 'adjHigh'
                            elif 'low' in c_lower:
                                col_map[c] = 'adjLow'
                            elif 'volume' in c_lower:
                                col_map[c] = 'volume'
                        new_rows = new_rows.rename(columns=col_map)
                        df = pd.concat([df, new_rows[list(col_map.values())]])
                        df = df[~df.index.duplicated(keep='last')]
            except Exception:
                pass  # use parquet-only data if Yahoo fetch fails

        if len(df) < 300:
            return None

        df = add_indicators_v7_2(df)
        return df

    except Exception as e:
        logger.debug(f"load_ticker_with_latest {ticker}: {e}")
        return None


# ── Step 3: Exit check ────────────────────────────────────────────────────────────────

def check_exits(portfolio: dict, latest_prices: Dict[str, float]) -> List[dict]:
    def _load(ticker):
        return load_ticker_with_latest(ticker, latest_prices)
    return engine_check_exits(portfolio, latest_prices, _load,
                              version=DEFAULT_VERSION,
                              today=datetime.now().date())


# ── Step 4: Signal scan ──────────────────────────────────────────────────────────────

def scan_universe(all_tickers: List[str],
                  open_tickers: set,
                  latest_prices: Dict[str, float]) -> List[dict]:
    def _load(ticker):
        return load_ticker_with_latest(ticker, latest_prices)
    return engine_scan_universe(all_tickers, open_tickers, latest_prices,
                                _load, version=DEFAULT_VERSION)


# ── Step 5: Execute orders ────────────────────────────────────────────────────

def execute_exits(exits: List[dict], portfolio: dict, ibkr) -> List[dict]:
    """
    Execute exit orders on IBKR Paper account.
    All orders are real market orders placed via IBKR API.
    """
    executed = []
    for ex in exits:
        ticker = ex['ticker']
        if ticker not in portfolio.get('positions', {}):
            logger.warning(f"EXIT {ticker}: not in portfolio - skipping")
            continue

        pos      = portfolio['positions'][ticker]
        shares   = pos.get('shares', 0)
        price    = ex.get('price', 0)
        entry_px = pos.get('entry_price', 0)
        pnl      = (price - entry_px) * shares
        pnl_pct  = ((price - entry_px) / entry_px * 100) if entry_px > 0 else 0

        logger.info(f"EXIT {ticker}: {shares} shares @ ${price:.2f} | {ex['reason']}")

        # Place real market order on IBKR Paper account
        result = ibkr.place_market_order(ticker, shares, 'sell', price)
        success = result.get('success', False)
        if not success:
            logger.error(f"IBKR sell order FAILED for {ticker}: {result.get('reason')}")

        if success:
            proceeds = shares * price
            portfolio['cash'] = portfolio.get('cash', 0) + proceeds
            del portfolio['positions'][ticker]

            trade_record = {
                'type':     'SELL',
                'ticker':   ticker,
                'shares':   shares,
                'price':    price,
                'proceeds': proceeds,
                'pnl':      pnl,
                'pnl_pct':  pnl_pct,
                'timestamp': datetime.now().isoformat(),
                'execution_mode': 'IBKR_PAPER',
                'reason':   ex['reason']
            }
            portfolio.setdefault('trade_history', []).append(trade_record)
            executed.append(trade_record)
            logger.info(f"  Exited {ticker}: P&L=${pnl:+.2f} ({pnl_pct:+.1f}%)")

    return executed


def execute_entries(candidates: List[dict], portfolio: dict, ibkr) -> List[dict]:
    """
    Execute entry orders on IBKR Paper account.
    All orders are real market orders placed via IBKR API.
    
    CRITICAL FIX: Track available cash separately to prevent margin usage.
    Portfolio cash is updated in memory after each order to ensure subsequent
    position size calculations use the correct remaining cash balance.
    """
    executed = []
    is_bull  = get_spy_regime(SPY_PARQUET)
    if not is_bull:
        max_pos = get_regime_max_positions(is_bull, DEFAULT_VERSION)
        logger.warning(f"BEAR REGIME (SPY < SMA200): max positions -> {max_pos}")

    def _load(ticker):
        return load_ticker_with_latest(ticker, latest_prices_ref)

    p = engine_get_params(DEFAULT_VERSION)

    for cand in candidates:
        ticker = cand['ticker']
        price  = cand['price']
        if ticker in portfolio.get('positions', {}):
            continue

        allowed, reason = can_enter(ticker, portfolio, is_bull, DEFAULT_VERSION)
        if not allowed:
            logger.info(f"Skipping {ticker}: {reason}")
            continue

        # CRITICAL: Use current portfolio cash (updated after each order)
        # This prevents margin usage by ensuring each position size calculation
        # uses the remaining cash after previous orders
        shares, cost = calc_position_size(portfolio, price, latest_prices_ref,
                                          ticker=ticker, load_fn=_load,
                                          version=DEFAULT_VERSION)
        if shares <= 0:
            logger.warning(f"Skipping {ticker}: shares=0 (price=${price:.2f})")
            continue
        if cost > portfolio.get('cash', 0):
            logger.warning(f"Skipping {ticker}: cost=${cost:.2f} > cash=${portfolio['cash']:.2f}")
            continue

        logger.info(f"ENTRY {ticker}: {shares} shares @ ${price:.2f} "
                    f"(cost=${cost:,.2f}, score={cand['score']:.3f})")

        # Place real market order on IBKR Paper account
        result = ibkr.place_market_order(ticker, shares, 'buy', price)
        success = result.get('success', False)
        if not success:
            logger.error(f"IBKR buy order FAILED for {ticker}: {result.get('reason')}")

        if success:
            stop_loss = price * (1 - p['HARD_STOP_PCT'])
            portfolio['cash'] = portfolio.get('cash', 0) - cost
            portfolio.setdefault('positions', {})[ticker] = {
                'shares':          shares,
                'entry_price':     price,
                'stop_loss_price': stop_loss,
                'entry_date':      today_str,
                'quality_score':   cand['score'],
                'execution_mode':  'IBKR_PAPER',
                'is_power_stock':  False,
                'highest_price':   price,
                'ticker':          ticker,
            }
            trade_record = {
                'type':            'BUY',
                'ticker':          ticker,
                'shares':          shares,
                'price':           price,
                'cost':            cost,
                'timestamp':       datetime.now().isoformat(),
                'execution_mode':  'IBKR_PAPER',
                'quality_score':   cand['score'],
                'reason':          cand['reason'],
                'stop_loss_price': stop_loss,
            }
            portfolio.setdefault('trade_history', []).append(trade_record)
            executed.append(trade_record)
            logger.info(f"  Entered {ticker}: stop=${stop_loss:.2f}")

    return executed


# ── Step 6: OrderMonitor (R5) ────────────────────────────────────────────────

class OrderMonitor:
    """
    R5: Monitors every placed order, polls every POLL_INTERVAL seconds.
    Alerts via email if an order is not filled within FILL_TIMEOUT seconds.
    Cancels and removes from portfolio if still unfilled after CANCEL_TIMEOUT.
    """
    POLL_INTERVAL  = 10    # seconds between polls
    FILL_TIMEOUT   = 90    # alert after this many seconds unfilled
    CANCEL_TIMEOUT = 300   # cancel order after this many seconds unfilled (5 minutes - limit orders should fill faster)

    def __init__(self, ibkr):
        self.ibkr = ibkr

    def monitor(self, executed_entries: List[dict], executed_exits: List[dict],
                portfolio: dict) -> List[str]:
        """
        Poll IBKR open trades until all fill or timeout.
        Returns list of tickers where orders failed (for portfolio cleanup).
        All orders are real trades on IBKR Paper account.
        """
        if not executed_entries and not executed_exits:
            return []

        all_symbols = (
            {e['ticker'] for e in executed_entries} |
            {e['ticker'] for e in executed_exits}
        )
        if not all_symbols:
            return []

        logger.info(f"OrderMonitor: watching {len(all_symbols)} orders...")
        t0          = time.time()
        alerted     = set()
        failed      = []

        while True:
            elapsed = time.time() - t0
            try:
                open_trades = self.ibkr.ib.openTrades() if hasattr(self.ibkr, 'ib') and self.ibkr.ib else []
                pending = {
                    t.contract.symbol
                    for t in open_trades
                    if t.contract.symbol in all_symbols
                    and t.orderStatus.status not in ('Filled', 'Cancelled', 'Inactive')
                }
            except Exception as e:
                logger.warning(f"OrderMonitor poll error: {e}")
                break

            if not pending:
                logger.info(f"OrderMonitor: all orders filled in {elapsed:.0f}s")
                break

            # Alert threshold
            if elapsed >= self.FILL_TIMEOUT:
                for sym in pending - alerted:
                    logger.warning(f"ORDER ALERT: {sym} still unfilled after {elapsed:.0f}s")
                    self._send_alert(sym, elapsed)
                    alerted.add(sym)

            # Cancel threshold
            if elapsed >= self.CANCEL_TIMEOUT:
                for sym in pending:
                    logger.error(f"ORDER CANCEL: {sym} unfilled after {elapsed:.0f}s - cancelling")
                    try:
                        for t in open_trades:
                            if t.contract.symbol == sym:
                                self.ibkr.ib.cancelOrder(t.order)
                    except Exception as ce:
                        logger.error(f"Cancel error for {sym}: {ce}")
                    failed.append(sym)
                    # Remove from portfolio if it was an entry
                    if sym in portfolio.get('positions', {}):
                        pos = portfolio['positions'].pop(sym)
                        # Refund cash
                        refund = pos.get('shares', 0) * pos.get('entry_price', 0)
                        portfolio['cash'] = portfolio.get('cash', 0) + refund
                        logger.error(f"Removed {sym} from portfolio, refunded ${refund:,.2f}")
                break

            time.sleep(self.POLL_INTERVAL)

        return failed

    def _send_alert(self, symbol: str, elapsed: float):
        """Send email alert for unfilled order."""
        try:
            notifier = EmailNotifier()
            notifier.send_email(
                subject=f"VH ORDER ALERT: {symbol} unfilled after {elapsed:.0f}s",
                body=(f"ORDER NOT FILLED\n"
                      f"Ticker : {symbol}\n"
                      f"Elapsed: {elapsed:.0f}s\n"
                      f"Action : Check TWS immediately.\n")
            )
        except Exception as e:
            logger.error(f"Alert email failed for {symbol}: {e}")


def verify_fills(ibkr, executed_entries: List[dict], executed_exits: List[dict],
                 portfolio: dict) -> List[str]:
    """Wrapper — uses OrderMonitor to poll fills and handle failures."""
    monitor = OrderMonitor(ibkr)
    return monitor.monitor(executed_entries, executed_exits, portfolio)


# ── Step 7: Email summary ─────────────────────────────────────────────────────

def send_summary(portfolio: dict, exits: List[dict], entries: List[dict],
                 scan_count: int):
    """
    Send email summary of daily trading activity.
    System always runs on IBKR Paper account - no simulation mode.
    Uses HTML format for proper Gmail display.
    """
    try:
        from datetime import datetime
        
        # Status based on activity
        status = "OK" if len(exits) + len(entries) == 0 else "ACTIVE"
        status_color = "#28a745" if status == "OK" else "#ffc107"
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        # Calculate portfolio metrics
        cash = portfolio.get('cash', 0)
        positions = portfolio.get('positions', {})
        total_value = cash + sum(
            p.get('shares', 0) * latest_prices_ref.get(ticker, p.get('entry_price', 0))
            for ticker, p in positions.items()
        )
        pnl_total = total_value - INITIAL_CAPITAL
        pnl_color = "#28a745" if pnl_total >= 0 else "#dc3545"
        
        # Build HTML email body
        html_body = f"""
        <html>
        <head>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; background-color: #f5f5f5; }}
                .container {{ max-width: 800px; margin: 0 auto; background-color: white; padding: 20px; border-radius: 8px; }}
                .header {{ background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }}
                .status-badge {{ display: inline-block; padding: 5px 15px; background-color: {status_color}; color: white; border-radius: 20px; font-weight: bold; }}
                .section {{ margin-bottom: 25px; }}
                .section-title {{ color: #333; border-bottom: 2px solid #667eea; padding-bottom: 5px; margin-bottom: 15px; }}
                .metric-grid {{ display: grid; grid-template-columns: repeat(2, 1fr); gap: 15px; margin: 15px 0; }}
                .metric {{ background-color: #f8f9fa; padding: 15px; border-radius: 5px; border-left: 4px solid #667eea; }}
                .metric-label {{ font-size: 12px; color: #666; text-transform: uppercase; }}
                .metric-value {{ font-size: 24px; font-weight: bold; color: #333; margin-top: 5px; }}
                table {{ border-collapse: collapse; width: 100%; margin: 10px 0; }}
                th {{ background-color: #667eea; color: white; padding: 12px; text-align: left; }}
                td {{ border: 1px solid #ddd; padding: 10px; }}
                tr:nth-child(even) {{ background-color: #f8f9fa; }}
                .positive {{ color: #28a745; font-weight: bold; }}
                .negative {{ color: #dc3545; font-weight: bold; }}
                .info-row {{ display: flex; justify-content: space-between; margin: 8px 0; }}
                .info-label {{ color: #666; }}
                .info-value {{ font-weight: bold; }}
            </style>
        </head>
        <body>
            <div class="container">
                <div class="header">
                    <h2 style="margin: 0;">VolatilityHunter — IBKR Paper Account</h2>
                    <p style="margin: 10px 0 0 0;">{timestamp} IST | <span class="status-badge">{status}</span></p>
                </div>
                
                <div class="section">
                    <h3 class="section-title">Execution Summary</h3>
                    <div class="info-row">
                        <span class="info-label">Mode:</span>
                        <span class="info-value">IBKR_PAPER</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Result:</span>
                        <span class="info-value" style="color: {status_color};">SUCCESS</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Paper Trading:</span>
                        <span class="info-value">YES (Real orders, fake money)</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Log File:</span>
                        <span class="info-value" style="font-size: 11px;">{LOG_DIR / f'trading_{today_str}.log'}</span>
                    </div>
                </div>
                
                <div class="section">
                    <h3 class="section-title">💰 Portfolio Summary</h3>
                    <div class="metric-grid">
                        <div class="metric">
                            <div class="metric-label">Portfolio Value</div>
                            <div class="metric-value">${total_value:,.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Available Cash</div>
                            <div class="metric-value">${cash:,.2f}</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Total P&L</div>
                            <div class="metric-value" style="color: {pnl_color};">${pnl_total:+,.2f} ({(pnl_total/INITIAL_CAPITAL)*100:+.2f}%)</div>
                        </div>
                        <div class="metric">
                            <div class="metric-label">Active Positions</div>
                            <div class="metric-value">{len(positions)}</div>
                        </div>
                    </div>
                </div>
        """

        # Current positions with P&L
        if positions:
            html_body += """
                <div class="section">
                    <h3 class="section-title">📊 Current Positions</h3>
                    <table>
                        <tr>
                            <th>Ticker</th>
                            <th>Quantity</th>
                            <th>Entry Price</th>
                            <th>Current Price</th>
                            <th>P&L</th>
                            <th>Stop Loss</th>
                            <th>Days Held</th>
                        </tr>
            """
            
            for ticker, pos in sorted(positions.items()):
                shares = pos.get('shares', 0)
                entry_price = pos.get('entry_price', 0)
                current_price = latest_prices_ref.get(ticker, entry_price)
                pnl = (current_price - entry_price) * shares
                pnl_pct = ((current_price - entry_price) / entry_price * 100) if entry_price > 0 else 0
                entry_date = pos.get('entry_date', '')
                days_held = (datetime.now() - datetime.fromisoformat(entry_date)).days if entry_date else 0
                stop_loss = pos.get('stop_loss_price', 0)
                pnl_class = "positive" if pnl >= 0 else "negative"
                
                html_body += f"""
                        <tr>
                            <td><strong>{ticker}</strong></td>
                            <td>{shares}</td>
                            <td>${entry_price:.2f}</td>
                            <td>${current_price:.2f}</td>
                            <td class="{pnl_class}">${pnl:+,.2f} ({pnl_pct:+.2f}%)</td>
                            <td>${stop_loss:.2f}</td>
                            <td>{days_held}</td>
                        </tr>
                """
            
            html_body += """
                    </table>
                </div>
            """
        else:
            html_body += """
                <div class="section">
                    <h3 class="section-title">📊 Current Positions</h3>
                    <p><em>No open positions</em></p>
                </div>
            """

        # Exit signals executed today
        html_body += """
                <div class="section">
                    <h3 class="section-title">🔴 Exit Signals Today</h3>
        """
        
        if exits:
            html_body += "<table><tr><th>Ticker</th><th>Price</th><th>P&L</th><th>Reason</th></tr>"
            for e in exits:
                ticker = e.get('ticker', '')
                price = e.get('price', 0)
                pnl_pct = e.get('pnl_pct', 0)
                reason = e.get('reason', '')
                pnl_class = "positive" if pnl_pct >= 0 else "negative"
                html_body += f"""
                    <tr>
                        <td><strong>{ticker}</strong></td>
                        <td>${price:.2f}</td>
                        <td class="{pnl_class}">{pnl_pct:+.2f}%</td>
                        <td>{reason}</td>
                    </tr>
                """
            html_body += "</table>"
        else:
            html_body += "<p><em>No exit signals today</em></p>"
        
        html_body += "</div>"

        # Entry signals executed today
        html_body += """
                <div class="section">
                    <h3 class="section-title">🔵 Entry Signals Today</h3>
        """
        
        if entries:
            html_body += "<table><tr><th>Ticker</th><th>Price</th><th>Score</th><th>Reason</th></tr>"
            for e in entries:
                ticker = e.get('ticker', '')
                price = e.get('price', 0)
                score = e.get('quality_score', 0)
                reason = e.get('reason', '')
                html_body += f"""
                    <tr>
                        <td><strong>{ticker}</strong></td>
                        <td>${price:.2f}</td>
                        <td>{score:.3f}</td>
                        <td>{reason}</td>
                    </tr>
                """
            html_body += "</table>"
        else:
            html_body += "<p><em>No entry signals today</em></p>"
        
        html_body += "</div>"

        # System status
        html_body += f"""
                <div class="section">
                    <h3 class="section-title">⚙️ System Status</h3>
                    <div class="info-row">
                        <span class="info-label">Strategy Version:</span>
                        <span class="info-value">v8.1 (Lean Pipeline)</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Universe Scanned:</span>
                        <span class="info-value">{scan_count} tickers</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Max Positions:</span>
                        <span class="info-value">{MAX_POSITIONS} concurrent</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Position Size:</span>
                        <span class="info-value">{POSITION_SIZE_PCT*100:.0f}% per position</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Hard Stop:</span>
                        <span class="info-value">8% maximum loss</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">SPY Regime Filter:</span>
                        <span class="info-value">ACTIVE (200-day SMA)</span>
                    </div>
                    <div class="info-row">
                        <span class="info-label">Sector Cap:</span>
                        <span class="info-value">3 positions per sector</span>
                    </div>
                </div>
            </div>
        </body>
        </html>
        """

        body = html_body

        notifier = EmailNotifier()
        subject = f"{status} VolatilityHunter IBKR_PAPER completed - {today_str} {datetime.now().strftime('%H:%M:%S')}"
        
        # Attach log file to email (ALWAYS - per user requirement)
        log_file = LOG_DIR / f"trading_{today_str}.log"
        if log_file.exists():
            if notifier.send_email(subject, body, str(log_file)):
                logger.info("Summary email sent successfully with log attachment (HTML format).")
            else:
                logger.warning("Email send failed - check EmailNotifier config.")
        else:
            # No log file yet, send without attachment
            if notifier.send_email(subject, body):
                logger.info("Summary email sent successfully (HTML format, no log file found).")
            else:
                logger.warning("Email send failed - check EmailNotifier config.")

    except Exception as e:
        logger.error(f"send_summary error: {e}")
        logger.error(traceback.format_exc())


# ── Main ──────────────────────────────────────────────────────────────────────

latest_prices_ref: Dict[str, float] = {}   # module-level ref for execute_entries closure


def send_failure_email(error_message, step_failed, traceback_str=""):
    """
    Send failure notification email when system encounters critical error.
    ALWAYS includes log file attachment.
    """
    try:
        from datetime import datetime
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        body_lines = [
            f"VolatilityHunter — CRITICAL FAILURE",
            f"{timestamp} IST  |  Status: [FAILED]",
            f"",
            f"Execution Summary",
            f"Mode\tIBKR_PAPER",
            f"Result\tFAILURE",
            f"Failed Step\t{step_failed}",
            f"Timestamp\t{timestamp}",
            f"",
            f"🚨 Error Details",
            f"Error Message:\t{error_message}",
            f"",
        ]
        
        if traceback_str:
            body_lines.extend([
                f"Traceback:",
                f"{traceback_str}",
                f""
            ])
        
        body_lines.extend([
            f"⚙️ Action Required",
            f"1. Check IBKR Gateway is running on port 7497",
            f"2. Verify Tiingo API key is valid",
            f"3. Review attached log file for details",
            f"4. Check network connectivity",
            f"5. Restart system if necessary",
        ])
        
        body = "\n".join(body_lines)
        subject = f"[FAILED] VolatilityHunter IBKR_PAPER - {step_failed} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
        
        notifier = EmailNotifier()
        
        # ALWAYS attach log file for failure emails
        log_file = LOG_DIR / f"trading_{today_str}.log"
        if log_file.exists():
            if notifier.send_email(subject, body, str(log_file)):
                logger.info("Failure notification email sent with log attachment.")
            else:
                logger.error("Failed to send failure notification email.")
        else:
            # Send without attachment if log doesn't exist yet
            if notifier.send_email(subject, body):
                logger.info("Failure notification email sent (no log file).")
            else:
                logger.error("Failed to send failure notification email.")
    
    except Exception as e:
        logger.error(f"Failed to send failure email: {e}")


def main():
    global latest_prices_ref

    t_start = time.time()
    logger.info("=" * 68)
    logger.info("VOLATILITYHUNTER DAILY TRADING LOOP")
    logger.info(f"Date: {today_str}  |  Capital: ${INITIAL_CAPITAL:,.0f}")
    logger.info("=" * 68)
    
    # CRITICAL: Prevent multiple executions on same day (causes margin usage bug)
    lock_file = DATA_DIR / f"trading_lock_{today_str}.lock"
    if lock_file.exists():
        logger.error("=" * 68)
        logger.error("🚨 EXECUTION LOCK DETECTED")
        logger.error(f"Trading loop already ran today ({today_str})")
        logger.error("Multiple executions cause IBKR reconciliation to reset cash,")
        logger.error("leading to margin usage bugs. Aborting to prevent margin trades.")
        logger.error("=" * 68)
        logger.error(f"Lock file: {lock_file}")
        logger.error("To override: Delete the lock file and re-run")
        logger.error("=" * 68)
        sys.exit(1)
    
    # Create lock file
    lock_file.write_text(f"Locked at {datetime.now().isoformat()}")
    logger.info(f"✅ Execution lock created: {lock_file}")
    
    ibkr = None  # Initialize for cleanup in except block
    
    try:
        # ── Load tickers ──────────────────────────────────────────────────────
        all_tickers = [t.strip().upper() for t in
                       TICKERS_FILE.read_text().splitlines() if t.strip()]
        logger.info(f"Universe: {len(all_tickers)} tickers")

        # ── Step 1: Portfolio + IBKR reconciliation ───────────────────────────
        portfolio = load_portfolio()
        portfolio, ibkr = reconcile_with_ibkr(portfolio)
        logger.info("Connected to IBKR Paper account - ready for trading")

        # ── Step 2: Fetch today's prices ───────────────────────────────────────
        logger.info("--- Step 2: Fetching latest prices ---")
        open_tickers = list(portfolio.get('positions', {}).keys())
        fetch_tickers = list(set(all_tickers) | set(open_tickers))
        latest_prices = fetch_latest_prices(fetch_tickers)
        latest_prices_ref = latest_prices   # make available to execute_entries

        if not latest_prices:
            error_msg = "No prices fetched - Tiingo API connectivity issue"
            logger.error(error_msg)
            send_failure_email(error_msg, "Price Fetching")
            sys.exit(1)

        # ── Step 2b: Update highest_price + high-water mark (Bug 2 + 3 fix) ──
        update_highest_prices(portfolio, latest_prices)
        update_high_water_mark(portfolio, latest_prices)

        # ── Step 3: Check exits ───────────────────────────────────────────────
        logger.info("--- Step 3: Checking exits ---")
        exit_decisions = check_exits(portfolio, latest_prices)
        logger.info(f"Exit signals: {len(exit_decisions)}")

        executed_exits = execute_exits(exit_decisions, portfolio, ibkr)

        # ── Step 3b: Power stock promotion (Bug 1 fix) ────────────────────────
        logger.info("--- Step 3b: Power stock promotion check ---")
        def _load_for_promotion(ticker):
            return load_ticker_with_latest(ticker, latest_prices)
        promoted = promote_power_stocks(portfolio, latest_prices, _load_for_promotion)
        if promoted:
            logger.info(f"Power promoted: {promoted}")

        # ── Step 4: Scan universe for new entries ─────────────────────────────
        logger.info("--- Step 4: Scanning universe ---")
        open_set  = set(portfolio.get('positions', {}).keys())
        slots_available = MAX_POSITIONS - len(open_set)

        if slots_available > 0:
            candidates = scan_universe(all_tickers, open_set, latest_prices)
            logger.info(f"Available slots: {slots_available} | Candidates: {len(candidates)}")
        else:
            candidates = []
            logger.info(f"No slots available ({len(open_set)}/{MAX_POSITIONS} positions full)")

        # ── Step 5: Execute entries ───────────────────────────────────────────
        logger.info("--- Step 5: Market hours validation ---")
        
        # Check market hours before placing orders
        try:
            from src.market_hours import validate_before_trading
            if not validate_before_trading():
                logger.error("🚨 MARKET CLOSED - Skipping order execution")
                executed_entries = []
            else:
                logger.info("--- Step 5: Executing entries ---")
                executed_entries = execute_entries(candidates[:MAX_POSITIONS], portfolio, ibkr)
        except Exception as e:
            logger.error(f"Market hours check failed: {e}")
            logger.info("--- Step 5: Executing entries (fallback) ---")
            executed_entries = execute_entries(candidates[:MAX_POSITIONS], portfolio, ibkr)

        # ── Step 6: Verify fills (OrderMonitor R5) ───────────────────────────
        logger.info("--- Step 6: OrderMonitor: verifying fills ---")
        failed_orders = verify_fills(ibkr, executed_entries, executed_exits, portfolio)
        if failed_orders:
            logger.error(f"Orders failed/cancelled: {failed_orders}")

        # ── Save portfolio ────────────────────────────────────────────────────
        total_value = portfolio.get('cash', 0) + sum(
            p.get('shares', 0) * latest_prices.get(t, p.get('entry_price', 0))
            for t, p in portfolio.get('positions', {}).items()
        )
        portfolio['total_value'] = total_value
        save_portfolio(portfolio)

        # ── Step 7: Email summary ─────────────────────────────────────────────
        logger.info("--- Step 7: Sending summary email ---")
        send_summary(portfolio, executed_exits, executed_entries, len(all_tickers))

        # ── Disconnect IBKR ───────────────────────────────────────────────────
        if ibkr:
            try:
                ibkr.disconnect()
            except Exception:
                pass
    
    except Exception as e:
        # CRITICAL ERROR - Send failure notification email
        error_msg = str(e)
        tb_str = traceback.format_exc()
        logger.error(f"CRITICAL ERROR in main trading loop: {error_msg}")
        logger.error(tb_str)
        
        # Determine which step failed based on error context
        step_failed = "Unknown Step"
        if "IBKR" in error_msg or "connect" in error_msg.lower():
            step_failed = "IBKR Connection"
        elif "price" in error_msg.lower() or "tiingo" in error_msg.lower():
            step_failed = "Price Fetching"
        elif "order" in error_msg.lower():
            step_failed = "Order Execution"
        elif "portfolio" in error_msg.lower():
            step_failed = "Portfolio Management"
        
        send_failure_email(error_msg, step_failed, tb_str)
        
        # Cleanup IBKR connection
        if ibkr:
            try:
                ibkr.disconnect()
            except Exception:
                pass
        
        # Re-raise to ensure exit code is non-zero
        raise

    elapsed = time.time() - t_start
    logger.info("=" * 68)
    logger.info(f"Daily loop complete in {elapsed:.1f}s")
    logger.info(f"Positions: {len(portfolio['positions'])} | "
                f"Cash: ${portfolio['cash']:,.2f} | "
                f"Total: ${total_value:,.2f}")
    logger.info(f"Exits: {len(executed_exits)} | Entries: {len(executed_entries)}")
    logger.info("=" * 68)
    
    # Clean up Gateway after trading completes
    try:
        import psutil
        logger.info("🔄 Cleaning up IB Gateway...")
        for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info.get('cmdline') or []).lower()
                if 'ibgateway' in name or 'ibgateway' in cmdline:
                    proc.terminate()
                    logger.info(f"✅ Terminated Gateway process (PID {proc.pid})")
                elif name == 'javaw.exe' and ('ibgateway' in cmdline or 'ibcgateway' in cmdline):
                    proc.terminate()
                    logger.info(f"✅ Terminated Gateway Java process (PID {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied, PermissionError):
                continue
        logger.info("🧹 Gateway cleanup complete")
    except Exception as e:
        logger.warning(f"⚠️ Gateway cleanup failed: {e}")

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        logger.error(f"FATAL: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
