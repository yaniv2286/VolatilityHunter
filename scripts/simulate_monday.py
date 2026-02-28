"""
simulate_monday.py
==================
Simulates a full Monday trading run using real prices from last Monday (2026-02-24).
Uses PAPER mode (no IBKR connection needed).
Runs the full pipeline:
  1. Load current portfolio.json
  2. Fetch real prices for 2026-02-24 from Yahoo Finance
  3. Check exits on all open positions
  4. Scan 2,147 tickers for buy signals
  5. Execute entries (paper)
  6. Print full summary

Does NOT modify portfolio.json — read-only simulation.
Exit code 0 = pipeline ran end-to-end cleanly.
"""

import os
import sys
import json
import copy
import logging
import traceback
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import numpy as np
import yfinance as yf
from dotenv import load_dotenv

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

from src.strategy_v7_2 import add_indicators_v7_2
from src.strategy_engine import (
    promote_power_stocks,
    update_highest_prices,
    update_high_water_mark,
    get_dd_scale,
    check_exits       as engine_check_exits,
    scan_universe     as engine_scan_universe,
    calc_position_size,
    can_enter,
    get_spy_regime,
    get_params        as engine_get_params,
    DEFAULT_VERSION,
)

# ── Config ─────────────────────────────────────────────────────────────────────
SIM_DATE        = date(2026, 2, 24)   # last Monday
DATA_DIR        = ROOT / 'data'
PORTFOLIO_FILE  = DATA_DIR / 'portfolio.json'
TICKERS_FILE    = ROOT / 'tickers.txt'
LOG_DIR         = ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)

INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_PRICE         = 5.0
# Strategy parameters are in src/strategy_engine.py PARAMS[DEFAULT_VERSION]
# Change DEFAULT_VERSION there to switch all modes at once.
SPY_PARQUET       = DATA_DIR / 'SPY.parquet'

# ── Logging ────────────────────────────────────────────────────────────────────
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / f'simulate_monday_{SIM_DATE}.log'), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('sim_monday')

# Global ref used inside execute_entries
latest_prices_ref: Dict[str, float] = {}


# ── Helpers ────────────────────────────────────────────────────────────────────

def load_portfolio() -> dict:
    try:
        with open(PORTFOLIO_FILE) as f:
            p = json.load(f)
        logger.info(f"Portfolio: {len(p.get('positions', {}))} positions, ${p.get('cash', 0):,.2f} cash")
        return copy.deepcopy(p)   # deep copy — we never write back
    except Exception as e:
        logger.error(f"Portfolio load failed: {e}")
        logger.error(traceback.format_exc())
        return {'cash': INITIAL_CAPITAL, 'positions': {}, 'trade_history': []}


def fetch_prices_for_date(tickers: List[str], sim_date: date) -> Dict[str, float]:
    """Fetch real closing prices for sim_date from Yahoo Finance."""
    logger.info(f"Fetching real prices for {sim_date} ({len(tickers)} tickers)...")
    prices = {}
    # Download a window around sim_date
    start = pd.Timestamp(sim_date) - pd.Timedelta(days=5)
    end   = pd.Timestamp(sim_date) + pd.Timedelta(days=2)
    batch_size = 200

    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        try:
            data = yf.download(batch, start=start.strftime('%Y-%m-%d'),
                               end=end.strftime('%Y-%m-%d'),
                               auto_adjust=True, progress=False, threads=True)
            if 'Close' in data:
                close = data['Close']
                # Find the row closest to sim_date
                target = pd.Timestamp(sim_date)
                available = close.index[close.index <= target]
                if len(available) == 0:
                    continue
                row = close.loc[available[-1]]
                for t in batch:
                    if t in row.index and not pd.isna(row[t]):
                        prices[t] = float(row[t])
        except Exception as e:
            logger.warning(f"Batch {i}-{i+batch_size} price error: {e}")

        if (i // batch_size) % 5 == 0:
            logger.info(f"  Price fetch progress: {min(i+batch_size, len(tickers))}/{len(tickers)}")

    logger.info(f"Fetched prices for {len(prices)}/{len(tickers)} tickers")
    return prices


def load_ticker_sim(ticker: str, sim_date: date,
                    latest_prices: Dict[str, float]) -> Optional[pd.DataFrame]:
    """Load parquet history up to sim_date and compute indicators."""
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

        # Slice up to sim_date
        df = df[df.index <= pd.Timestamp(sim_date)]
        if len(df) < 300:
            return None

        df = add_indicators_v7_2(df)
        return df
    except Exception as e:
        logger.debug(f"load_ticker_sim {ticker}: {e}")
        return None


def check_exits(portfolio: dict, prices: Dict[str, float],
                sim_date: date) -> List[dict]:
    def _load(ticker):
        return load_ticker_sim(ticker, sim_date, prices)
    return engine_check_exits(portfolio, prices, _load,
                              version=DEFAULT_VERSION, today=sim_date)


def scan_universe(all_tickers: List[str], open_tickers: set,
                  prices: Dict[str, float], sim_date: date) -> List[dict]:
    def _load(ticker):
        return load_ticker_sim(ticker, sim_date, prices)
    return engine_scan_universe(all_tickers, open_tickers, prices,
                                _load, version=DEFAULT_VERSION)


def simulate_exits(exits: List[dict], portfolio: dict) -> List[dict]:
    executed = []
    for ex in exits:
        ticker = ex['ticker']
        price  = ex['price']
        pos    = portfolio['positions'].get(ticker)
        if not pos:
            continue
        shares   = pos.get('shares', 0)
        entry    = pos.get('entry_price', price)
        proceeds = shares * price
        pnl      = proceeds - shares * entry
        pnl_pct  = pnl / (shares * entry) * 100 if entry > 0 else 0
        portfolio['cash'] += proceeds
        del portfolio['positions'][ticker]
        executed.append({'ticker': ticker, 'shares': shares, 'price': price,
                         'pnl': pnl, 'pnl_pct': pnl_pct, 'reason': ex['reason']})
        logger.info(f"[SIM EXIT]  {ticker}: {shares}sh @ ${price:.2f} | P&L ${pnl:+.2f} ({pnl_pct:+.1f}%) | {ex['reason']}")
    return executed


def simulate_entries(candidates: List[dict], portfolio: dict,
                     prices: Dict[str, float], sim_date: date) -> List[dict]:
    executed = []
    p        = engine_get_params(DEFAULT_VERSION)
    is_bull  = get_spy_regime(SPY_PARQUET, cutoff_date=sim_date)
    if not is_bull:
        logger.warning(f"BEAR REGIME on {sim_date}: max positions -> {p['REGIME_MAX_POS']}")

    def _load(ticker):
        return load_ticker_sim(ticker, sim_date, prices)

    for cand in candidates:
        ticker = cand['ticker']
        price  = cand['price']
        if ticker in portfolio.get('positions', {}):
            continue

        allowed, reason = can_enter(ticker, portfolio, is_bull, DEFAULT_VERSION)
        if not allowed:
            logger.info(f"Skipping {ticker}: {reason}")
            continue

        shares, cost = calc_position_size(portfolio, price, prices,
                                          ticker=ticker, load_fn=_load,
                                          version=DEFAULT_VERSION)
        if shares <= 0 or cost > portfolio.get('cash', 0):
            continue

        portfolio['cash'] -= cost
        portfolio.setdefault('positions', {})[ticker] = {
            'shares':          shares,
            'entry_price':     price,
            'entry_date':      str(SIM_DATE),
            'ticker':          ticker,
            'execution_mode':  'PAPER_SIM',
            'is_power_stock':  False,
            'stop_loss_price': price * (1 - p['HARD_STOP_PCT']),
            'highest_price':   price,
        }
        executed.append({'ticker': ticker, 'shares': shares, 'price': price,
                         'cost': cost, 'reason': cand['reason']})
        logger.info(f"[SIM ENTRY] {ticker}: {shares}sh @ ${price:.2f} = ${cost:,.2f} | {cand['reason']}")
    return executed


# ── Main ───────────────────────────────────────────────────────────────────────

def main():
    logger.info("=" * 65)
    logger.info(f"SIMULATION: Monday {SIM_DATE} (PAPER mode - portfolio.json NOT modified)")
    logger.info("=" * 65)

    # Load tickers
    tickers = [t.strip() for t in TICKERS_FILE.read_text().splitlines() if t.strip()]
    logger.info(f"Universe: {len(tickers)} tickers")

    # Step 1: Load portfolio (read-only copy)
    portfolio = load_portfolio()
    open_tickers = set(portfolio.get('positions', {}).keys())
    logger.info(f"Open positions: {sorted(open_tickers)}")

    # Step 2: Fetch real prices for sim date
    all_relevant = list(set(tickers) | open_tickers)
    prices = fetch_prices_for_date(all_relevant, SIM_DATE)
    global latest_prices_ref
    latest_prices_ref = prices

    # Step 2b: Update highest_price + high-water mark
    update_highest_prices(portfolio, prices)
    update_high_water_mark(portfolio, prices)

    # Print current position values
    logger.info("--- Current portfolio as of sim date ---")
    total_pos_value = 0.0
    for ticker, pos in portfolio.get('positions', {}).items():
        p = prices.get(ticker, pos.get('entry_price', 0))
        entry = pos.get('entry_price', p)
        shares = pos.get('shares', 0)
        val = shares * p
        pnl_pct = (p - entry) / entry * 100 if entry > 0 else 0
        total_pos_value += val
        logger.info(f"  {ticker:6s}: {shares}sh | entry ${entry:.2f} | sim ${p:.2f} | P&L {pnl_pct:+.1f}% | value ${val:,.2f}")
    total_equity = portfolio.get('cash', 0) + total_pos_value
    logger.info(f"  Cash: ${portfolio['cash']:,.2f} | Positions: ${total_pos_value:,.2f} | Total: ${total_equity:,.2f}")

    # Step 3: Check exits
    logger.info("--- Step 3: Exit check ---")
    exits = check_exits(portfolio, prices, SIM_DATE)
    exit_trades = simulate_exits(exits, portfolio)
    logger.info(f"Exits triggered: {len(exit_trades)}")

    # Step 3b: Power stock promotion
    logger.info("--- Step 3b: Power stock promotion check ---")
    def _load_sim(ticker):
        return load_ticker_sim(ticker, SIM_DATE, prices)
    promoted = promote_power_stocks(portfolio, prices, _load_sim)
    if promoted:
        logger.info(f"Power promoted: {promoted}")

    # Step 4: Scan universe
    logger.info("--- Step 4: Universe scan ---")
    open_after_exits = set(portfolio.get('positions', {}).keys())
    candidates = scan_universe(tickers, open_after_exits, prices, SIM_DATE)

    # Step 5: Execute entries
    logger.info("--- Step 5: Entry execution ---")
    slot_available = MAX_POSITIONS - len(portfolio.get('positions', {}))
    logger.info(f"Slots available: {slot_available} | Top candidates: {len(candidates)}")
    entries = simulate_entries(candidates[:20], portfolio, prices, SIM_DATE)

    # ── Summary ────────────────────────────────────────────────────────────────
    logger.info("")
    logger.info("=" * 65)
    logger.info(f"SIMULATION SUMMARY — {SIM_DATE}")
    logger.info("=" * 65)
    logger.info(f"Starting portfolio:  ${total_equity:,.2f}")
    logger.info(f"Exits:               {len(exit_trades)}")
    for t in exit_trades:
        logger.info(f"  SOLD  {t['ticker']:6s} | P&L ${t['pnl']:+.2f} ({t['pnl_pct']:+.1f}%) | {t['reason']}")
    logger.info(f"Entries:             {len(entries)}")
    for t in entries:
        logger.info(f"  BOUGHT {t['ticker']:6s} | {t['shares']}sh @ ${t['price']:.2f} = ${t['cost']:,.2f}")
    logger.info(f"Final positions:     {len(portfolio.get('positions', {}))}")
    final_pos_val = sum(
        p.get('shares', 0) * prices.get(t, p.get('entry_price', 0))
        for t, p in portfolio.get('positions', {}).items()
    )
    final_equity = portfolio.get('cash', 0) + final_pos_val
    logger.info(f"Final cash:          ${portfolio['cash']:,.2f}")
    logger.info(f"Final equity:        ${final_equity:,.2f}")
    logger.info(f"Delta:               ${final_equity - total_equity:+,.2f}")
    logger.info("")
    logger.info("Top 10 buy candidates (not necessarily executed):")
    for c in candidates[:10]:
        logger.info(f"  {c['ticker']:6s} | score={c['score']:.3f} | ${c['price']:.2f} | {c['reason']}")
    logger.info("=" * 65)
    logger.info("SIMULATION COMPLETE — portfolio.json was NOT modified")
    logger.info("=" * 65)
    return 0


if __name__ == '__main__':
    sys.exit(main())
