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
import yfinance as yf
from dotenv import load_dotenv

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

from src.strategy_v7_2 import add_indicators_v7_2
from src.brokerage_interface import get_brokerage_interface
from src.email_notifier import EmailNotifier

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
HARD_STOP_PCT     = 0.05          # 5% hard stop loss
MIN_PRICE         = 5.0           # no penny stocks
MIN_LIQUIDITY     = 500_000       # $500k daily dollar volume
STOCH_LOW         = 32.0
STOCH_HIGH        = 80.0
OVERBOUGHT_EXIT   = 70.0
CAGR_FILTER       = 0.15
VOLUME_SURGE      = 1.5
ORDER_CONFIRM_SEC = 90            # seconds to wait for order fill confirmation

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

def reconcile_with_ibkr(portfolio: dict) -> Tuple[dict, Optional[object]]:
    """
    Connect to IBKR, sync local portfolio with actual positions.
    Returns (updated_portfolio, ibkr_interface).
    ibkr_interface=None means IBKR unavailable — run in PAPER mode.
    """
    logger.info("--- Step 1: Reconciling with IBKR ---")
    try:
        ibkr = get_brokerage_interface(IBKR_CONFIG)
        if not ibkr.connect():
            logger.warning("IBKR not available - running in PAPER mode")
            return portfolio, None

        account = ibkr.get_account_info()
        ibkr_positions = ibkr.get_positions()

        if account:
            ibkr_cash = account.get('cash', 0)
            ibkr_equity = account.get('equity', 0)
            logger.info(f"IBKR account: cash=${ibkr_cash:,.2f}, equity=${ibkr_equity:,.2f}")

            # Reconcile cash
            local_cash = portfolio.get('cash', 0)
            if abs(ibkr_cash - local_cash) > 100:
                logger.warning(f"Cash mismatch: local=${local_cash:,.2f} vs IBKR=${ibkr_cash:,.2f} - using IBKR")
                portfolio['cash'] = ibkr_cash

        if ibkr_positions:
            ibkr_tickers = {p['symbol'] for p in ibkr_positions}
            local_tickers = set(portfolio.get('positions', {}).keys())

            # Positions in IBKR but not local -> add them
            for pos in ibkr_positions:
                sym = pos['symbol']
                if sym not in portfolio['positions']:
                    logger.warning(f"IBKR has {sym} not in local portfolio - adding")
                    portfolio['positions'][sym] = {
                        'shares':      int(pos['quantity']),
                        'entry_price': pos.get('entry_price', pos.get('current_price', 0)),
                        'entry_date':  today_str,
                        'ticker':      sym,
                        'execution_mode': 'LIVE',
                        'is_power_stock': False,
                        'highest_price':  pos.get('current_price', 0),
                        'quality_score':  0,
                        'stop_loss_price': pos.get('entry_price', 0) * (1 - HARD_STOP_PCT)
                    }

            # Positions local but not in IBKR -> remove them
            for sym in list(local_tickers):
                if sym not in ibkr_tickers:
                    logger.warning(f"Local has {sym} not in IBKR - removing from local")
                    portfolio['positions'].pop(sym, None)

        logger.info(f"Reconciliation complete: {len(portfolio['positions'])} positions")
        return portfolio, ibkr

    except Exception as e:
        logger.error(f"Reconciliation error: {e}")
        logger.error(traceback.format_exc())
        return portfolio, None


# ── Step 2: Fetch today's data ────────────────────────────────────────────────

def fetch_latest_prices(tickers: List[str]) -> Dict[str, float]:
    """Fetch today's close for a list of tickers from Yahoo Finance."""
    logger.info(f"Fetching latest prices for {len(tickers)} tickers...")
    prices = {}
    try:
        # Batch download — much faster than per-ticker
        batch_size = 100
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i + batch_size]
            try:
                data = yf.download(
                    batch,
                    period='2d',
                    auto_adjust=True,
                    progress=False,
                    threads=True
                )
                if 'Close' in data:
                    close = data['Close'].iloc[-1]
                    for t in batch:
                        if t in close.index and not pd.isna(close[t]):
                            prices[t] = float(close[t])
            except Exception as e:
                logger.warning(f"Batch price fetch error (tickers {i}-{i+batch_size}): {e}")
    except Exception as e:
        logger.error(f"fetch_latest_prices error: {e}")
        logger.error(traceback.format_exc())
    logger.info(f"Fetched prices for {len(prices)}/{len(tickers)} tickers")
    return prices


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


# ── Step 3: Exit check ────────────────────────────────────────────────────────

def check_exits(portfolio: dict, latest_prices: Dict[str, float]) -> List[dict]:
    """
    Check all open positions for exit conditions.
    Returns list of exit decisions: [{ticker, price, reason}]
    """
    exits = []
    positions = portfolio.get('positions', {})

    for ticker, pos in positions.items():
        price = latest_prices.get(ticker)
        if not price:
            logger.warning(f"No price for open position {ticker} - skipping exit check")
            continue

        entry = pos.get('entry_price', price)
        pnl_pct = (price - entry) / entry if entry > 0 else 0

        # Hard stop
        if pnl_pct <= -HARD_STOP_PCT:
            exits.append({'ticker': ticker, 'price': price,
                          'reason': f'Hard stop ({pnl_pct:.1%})'})
            continue

        # Load indicators for signal-based exit
        df = load_ticker_with_latest(ticker, latest_prices)
        if df is None or df.empty:
            continue

        last = df.iloc[-1]
        k    = last.get('stoch_k', np.nan)
        d    = last.get('stoch_d', np.nan)
        sma200 = last.get('sma_200', np.nan)
        sma25  = last.get('sma_25', np.nan)
        atr    = last.get('atr', np.nan)

        # Standard exit: overbought rollover OR SMA200 break
        is_power = pos.get('is_power_stock', False)
        if not is_power:
            if (not np.isnan(k) and not np.isnan(d) and k < d and k > OVERBOUGHT_EXIT):
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Overbought rollover K={k:.1f}'})
            elif not np.isnan(sma200) and price < sma200:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'SMA200 break (price={price:.2f} < SMA200={sma200:.2f})'})
        else:
            # Power stock: SMA25 break or 3xATR trailing stop
            if not np.isnan(sma25) and price < sma25:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Power stock SMA25 break'})
            elif not np.isnan(atr) and price < atr * 3.0:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Power stock ATR trailing stop'})

    return exits


# ── Step 4: Signal scan ───────────────────────────────────────────────────────

def scan_universe(all_tickers: List[str],
                  open_tickers: set,
                  latest_prices: Dict[str, float]) -> List[dict]:
    """
    Scan all tickers, generate signals, return ranked list of buy candidates.
    Each candidate: {ticker, price, score, stoch_k, annual_return, reason}
    """
    candidates = []
    scanned = 0

    for ticker in all_tickers:
        if ticker in open_tickers:
            continue
        price = latest_prices.get(ticker)
        if not price or price < MIN_PRICE:
            continue

        df = load_ticker_with_latest(ticker, latest_prices)
        if df is None or df.empty:
            continue

        last = df.iloc[-1]
        k       = last.get('stoch_k',    np.nan)
        d       = last.get('stoch_d',    np.nan)
        sma200  = last.get('sma_200',    np.nan)
        vsma    = last.get('volume_sma', np.nan)
        volume  = last.get('volume',     np.nan)

        # 252-day annual return
        close_col = next((c for c in ['adjClose', 'Close', 'close'] if c in df.columns), None)
        if close_col and len(df) >= 253:
            annual_ret = (df[close_col].iloc[-1] / df[close_col].iloc[-253]) - 1
        else:
            annual_ret = np.nan

        # All conditions must be valid
        if any(np.isnan(v) for v in [k, d, sma200, vsma, volume, annual_ret]):
            scanned += 1
            continue

        buy = (
            STOCH_LOW <= k <= STOCH_HIGH and
            price > sma200 and
            volume >= vsma * VOLUME_SURGE and
            annual_ret >= CAGR_FILTER and
            (price * volume) >= MIN_LIQUIDITY
        )

        if buy:
            # Score: weight annual_return 60%, stoch position 40%
            stoch_score = 1.0 - abs(k - 56) / 24   # peak score at K=56 (center of 32-80)
            score = 0.6 * annual_ret + 0.4 * stoch_score
            candidates.append({
                'ticker':       ticker,
                'price':        price,
                'score':        score,
                'stoch_k':      k,
                'annual_return': annual_ret,
                'reason':       (f"Stoch_K={k:.1f} | SMA200 ok | "
                                 f"Vol surge | 1yr={annual_ret:.1%}")
            })

        scanned += 1
        if scanned % 500 == 0:
            logger.info(f"  Scanned {scanned}/{len(all_tickers)} | "
                        f"{len(candidates)} candidates so far")

    # Sort by score descending — best quality first
    candidates.sort(key=lambda x: x['score'], reverse=True)
    logger.info(f"Scan complete: {len(candidates)} buy candidates from {scanned} tickers")
    return candidates


# ── Step 5: Execute orders ────────────────────────────────────────────────────

def execute_exits(exits: List[dict], portfolio: dict,
                  ibkr, paper_mode: bool) -> List[dict]:
    executed = []
    for ex in exits:
        ticker = ex['ticker']
        price  = ex['price']
        pos    = portfolio['positions'].get(ticker)
        if not pos:
            continue

        shares = pos.get('shares', 0)
        if shares <= 0:
            continue

        logger.info(f"EXIT {ticker}: {shares} shares @ ${price:.2f} | {ex['reason']}")

        success = True
        if not paper_mode and ibkr:
            result = ibkr.place_market_order(ticker, shares, 'sell')
            success = result.get('success', False)
            if not success:
                logger.error(f"IBKR sell order FAILED for {ticker}: {result.get('reason')}")

        if success:
            proceeds = shares * price
            entry    = pos.get('entry_price', price)
            pnl      = proceeds - (shares * entry)
            pnl_pct  = pnl / (shares * entry) * 100 if entry > 0 else 0

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
                'execution_mode': 'PAPER' if paper_mode else 'LIVE',
                'reason':   ex['reason']
            }
            portfolio.setdefault('trade_history', []).append(trade_record)
            executed.append(trade_record)
            logger.info(f"  Exited {ticker}: P&L=${pnl:+.2f} ({pnl_pct:+.1f}%)")

    return executed


def execute_entries(candidates: List[dict], portfolio: dict,
                    ibkr, paper_mode: bool) -> List[dict]:
    executed = []
    open_count = len(portfolio.get('positions', {}))

    for cand in candidates:
        if open_count >= MAX_POSITIONS:
            break

        ticker = cand['ticker']
        price  = cand['price']
        if ticker in portfolio.get('positions', {}):
            continue

        # Ironclad position sizing: 20% of current total equity
        total_equity = portfolio.get('cash', 0) + sum(
            p.get('shares', 0) * latest_prices_ref.get(p.get('ticker', t), p.get('entry_price', 0))
            for t, p in portfolio.get('positions', {}).items()
        )
        alloc  = total_equity * POSITION_SIZE_PCT
        shares = int(alloc / price)
        cost   = shares * price

        if shares <= 0:
            logger.warning(f"Skipping {ticker}: shares=0 (price=${price:.2f}, alloc=${alloc:.2f})")
            continue
        if cost > portfolio.get('cash', 0):
            logger.warning(f"Skipping {ticker}: cost=${cost:.2f} > cash=${portfolio['cash']:.2f}")
            continue

        logger.info(f"ENTRY {ticker}: {shares} shares @ ${price:.2f} "
                    f"(cost=${cost:,.2f}, score={cand['score']:.3f})")

        success = True
        if not paper_mode and ibkr:
            result = ibkr.place_market_order(ticker, shares, 'buy')
            success = result.get('success', False)
            if not success:
                logger.error(f"IBKR buy order FAILED for {ticker}: {result.get('reason')}")

        if success:
            portfolio['cash'] = portfolio.get('cash', 0) - cost
            stop_loss = price * (1 - HARD_STOP_PCT)
            portfolio.setdefault('positions', {})[ticker] = {
                'shares':        shares,
                'entry_price':   price,
                'stop_loss_price': stop_loss,
                'entry_date':    today_str,
                'quality_score': cand['score'],
                'execution_mode': 'PAPER' if paper_mode else 'LIVE',
                'is_power_stock': False,
                'highest_price': price,
                'ticker':        ticker
            }

            trade_record = {
                'type':     'BUY',
                'ticker':   ticker,
                'shares':   shares,
                'price':    price,
                'cost':     cost,
                'timestamp': datetime.now().isoformat(),
                'execution_mode': 'PAPER' if paper_mode else 'LIVE',
                'quality_score': cand['score'],
                'reason':   cand['reason'],
                'stop_loss_price': stop_loss
            }
            portfolio.setdefault('trade_history', []).append(trade_record)
            executed.append(trade_record)
            open_count += 1
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
    CANCEL_TIMEOUT = 180   # cancel order after this many seconds unfilled

    def __init__(self, ibkr, paper_mode: bool):
        self.ibkr       = ibkr
        self.paper_mode = paper_mode

    def monitor(self, executed_entries: List[dict], executed_exits: List[dict],
                portfolio: dict) -> List[str]:
        """
        Poll IBKR open trades until all fill or timeout.
        Returns list of tickers where orders failed (for portfolio cleanup).
        """
        if self.paper_mode or not self.ibkr:
            logger.info("OrderMonitor: PAPER mode - skipping fill verification")
            return []
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
                 portfolio: dict, paper_mode: bool) -> List[str]:
    """Wrapper — uses OrderMonitor to poll fills and handle failures."""
    monitor = OrderMonitor(ibkr, paper_mode)
    return monitor.monitor(executed_entries, executed_exits, portfolio)


# ── Step 7: Email summary ─────────────────────────────────────────────────────

def send_summary(portfolio: dict, exits: List[dict], entries: List[dict],
                 scan_count: int, paper_mode: bool):
    try:
        mode = "PAPER" if paper_mode else "LIVE"
        total_value = portfolio.get('cash', 0) + sum(
            p.get('shares', 0) * p.get('entry_price', 0)
            for p in portfolio.get('positions', {}).values()
        )
        pnl_total = total_value - INITIAL_CAPITAL

        lines = [
            f"VolatilityHunter Daily Trading Report - {today_str}",
            f"Mode: {mode}",
            f"",
            f"ACCOUNT SUMMARY",
            f"  Cash          : ${portfolio.get('cash', 0):>12,.2f}",
            f"  Open positions: {len(portfolio.get('positions', {})):>12}",
            f"  Total equity  : ${total_value:>12,.2f}",
            f"  vs $100k base : ${pnl_total:>+12,.2f}",
            f"",
            f"TODAY'S ACTIVITY",
            f"  Universe scanned: {scan_count} tickers",
            f"  Exits executed  : {len(exits)}",
            f"  Entries executed: {len(entries)}",
            f"",
        ]

        if exits:
            lines.append("EXITS:")
            for e in exits:
                lines.append(f"  SELL {e['ticker']:8s} {e.get('shares',0):4d} @ ${e.get('price',0):.2f} "
                              f"P&L={e.get('pnl_pct',0):+.1f}% | {e.get('reason','')}")
            lines.append("")

        if entries:
            lines.append("ENTRIES:")
            for e in entries:
                lines.append(f"  BUY  {e['ticker']:8s} {e.get('shares',0):4d} @ ${e.get('price',0):.2f} "
                              f"score={e.get('quality_score',0):.3f} | {e.get('reason','')[:60]}")
            lines.append("")

        lines.append("OPEN POSITIONS:")
        for ticker, pos in portfolio.get('positions', {}).items():
            lines.append(f"  {ticker:8s} {pos.get('shares',0):4d} shares  "
                         f"entry=${pos.get('entry_price',0):.2f}  "
                         f"stop=${pos.get('stop_loss_price',0):.2f}")

        body = "\n".join(lines)

        notifier = EmailNotifier()
        subject = f"VH {mode} | {len(exits)} exits {len(entries)} entries | ${total_value:,.0f}"
        if notifier.send_email(subject, body):
            logger.info("Summary email sent.")
        else:
            logger.warning("Email send failed - check EmailNotifier config.")

    except Exception as e:
        logger.error(f"send_summary error: {e}")
        logger.error(traceback.format_exc())


# ── Main ──────────────────────────────────────────────────────────────────────

latest_prices_ref: Dict[str, float] = {}   # module-level ref for execute_entries closure


def main():
    global latest_prices_ref

    t_start = time.time()
    logger.info("=" * 68)
    logger.info("VOLATILITYHUNTER DAILY TRADING LOOP")
    logger.info(f"Date: {today_str}  |  Capital: ${INITIAL_CAPITAL:,.0f}")
    logger.info("=" * 68)

    # ── Load tickers ──────────────────────────────────────────────────────
    all_tickers = [t.strip().upper() for t in
                   TICKERS_FILE.read_text().splitlines() if t.strip()]
    logger.info(f"Universe: {len(all_tickers)} tickers")

    # ── Step 1: Portfolio + IBKR reconciliation ───────────────────────────
    portfolio = load_portfolio()
    portfolio, ibkr = reconcile_with_ibkr(portfolio)
    paper_mode = (ibkr is None)
    if paper_mode:
        logger.warning("Running in PAPER mode (IBKR not connected)")

    # ── Step 2: Fetch today's prices (batch via Yahoo Finance) ───────────
    logger.info("--- Step 2: Fetching latest prices ---")
    open_tickers = list(portfolio.get('positions', {}).keys())
    fetch_tickers = list(set(all_tickers) | set(open_tickers))
    latest_prices = fetch_latest_prices(fetch_tickers)
    latest_prices_ref = latest_prices   # make available to execute_entries

    if not latest_prices:
        logger.error("No prices fetched - aborting. Check Yahoo Finance connectivity.")
        sys.exit(1)

    # ── Step 3: Check exits ───────────────────────────────────────────────
    logger.info("--- Step 3: Checking exits ---")
    exit_decisions = check_exits(portfolio, latest_prices)
    logger.info(f"Exit signals: {len(exit_decisions)}")

    executed_exits = execute_exits(exit_decisions, portfolio, ibkr, paper_mode)

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
    logger.info("--- Step 5: Executing entries ---")
    executed_entries = execute_entries(candidates[:MAX_POSITIONS], portfolio, ibkr, paper_mode)

    # ── Step 6: Verify fills (OrderMonitor R5) ───────────────────────────
    logger.info("--- Step 6: OrderMonitor: verifying fills ---")
    failed_orders = verify_fills(ibkr, executed_entries, executed_exits, portfolio, paper_mode)
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
    logger.info("--- Step 7: Sending summary ---")
    send_summary(portfolio, executed_exits, executed_entries,
                 len(all_tickers), paper_mode)

    # ── Disconnect IBKR ───────────────────────────────────────────────────
    if ibkr:
        try:
            ibkr.disconnect()
        except Exception:
            pass

    elapsed = time.time() - t_start
    logger.info("=" * 68)
    logger.info(f"Daily loop complete in {elapsed:.1f}s")
    logger.info(f"Positions: {len(portfolio['positions'])} | "
                f"Cash: ${portfolio['cash']:,.2f} | "
                f"Total: ${total_value:,.2f}")
    logger.info(f"Exits: {len(executed_exits)} | Entries: {len(executed_entries)}")
    logger.info("=" * 68)

    return 0


if __name__ == '__main__':
    try:
        sys.exit(main())
    except Exception as e:
        logger.error(f"FATAL: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
