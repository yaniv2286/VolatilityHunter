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
HARD_STOP_PCT     = 0.05
MIN_PRICE         = 5.0
MIN_LIQUIDITY     = 500_000
STOCH_LOW         = 32.0
STOCH_HIGH        = 80.0
OVERBOUGHT_EXIT   = 70.0
CAGR_FILTER       = 0.15
VOLUME_SURGE      = 1.5

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
    exits = []
    for ticker, pos in portfolio.get('positions', {}).items():
        price = prices.get(ticker)
        if not price:
            logger.warning(f"No sim price for {ticker} - skipping exit check")
            continue
        entry = pos.get('entry_price', price)
        pnl_pct = (price - entry) / entry if entry > 0 else 0

        if pnl_pct <= -HARD_STOP_PCT:
            exits.append({'ticker': ticker, 'price': price,
                          'reason': f'Hard stop ({pnl_pct:.1%})'})
            continue

        df = load_ticker_sim(ticker, sim_date, prices)
        if df is None or df.empty:
            continue
        last   = df.iloc[-1]
        k      = last.get('stoch_k', np.nan)
        d      = last.get('stoch_d', np.nan)
        sma200 = last.get('sma_200', np.nan)
        sma25  = last.get('sma_25',  np.nan)
        atr    = last.get('atr',     np.nan)

        is_power = pos.get('is_power_stock', False)
        if not is_power:
            if not np.isnan(k) and not np.isnan(d) and k < d and k > OVERBOUGHT_EXIT:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Overbought rollover K={k:.1f}'})
            elif not np.isnan(sma200) and price < sma200:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'SMA200 break'})
        else:
            highest = pos.get('highest_price', entry)
            trailing_stop = highest - 3.0 * atr if not np.isnan(atr) else np.nan
            if not np.isnan(sma25) and price < sma25:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Power SMA25 break ({price:.2f} < {sma25:.2f})'})
            elif not np.isnan(trailing_stop) and price < trailing_stop:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Power ATR trailing stop (stop={trailing_stop:.2f})'})
    return exits


def scan_universe(all_tickers: List[str], open_tickers: set,
                  prices: Dict[str, float], sim_date: date) -> List[dict]:
    candidates = []
    scanned = 0
    for ticker in all_tickers:
        if ticker in open_tickers:
            continue
        price = prices.get(ticker)
        if not price or price < MIN_PRICE:
            continue

        df = load_ticker_sim(ticker, sim_date, prices)
        if df is None or df.empty:
            continue

        last   = df.iloc[-1]
        k      = last.get('stoch_k',    np.nan)
        d      = last.get('stoch_d',    np.nan)
        sma200 = last.get('sma_200',    np.nan)
        vsma   = last.get('volume_sma', np.nan)
        volume = last.get('volume',     np.nan)

        close_col = next((c for c in ['adjClose', 'Close', 'close'] if c in df.columns), None)
        annual_ret = (df[close_col].iloc[-1] / df[close_col].iloc[-253]) - 1 \
                     if close_col and len(df) >= 253 else np.nan

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
            stoch_score = 1.0 - abs(k - 56) / 24
            score = 0.6 * annual_ret + 0.4 * stoch_score
            candidates.append({
                'ticker': ticker, 'price': price, 'score': score,
                'stoch_k': k, 'annual_return': annual_ret,
                'reason': f'K={k:.1f} | 1yr={annual_ret:.1%} | SMA200 ok | Vol surge'
            })
        scanned += 1
        if scanned % 500 == 0:
            logger.info(f"  Scanned {scanned}/{len(all_tickers)} | {len(candidates)} candidates")

    candidates.sort(key=lambda x: x['score'], reverse=True)
    logger.info(f"Scan complete: {len(candidates)} candidates from {scanned} tickers")
    return candidates


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
                     prices: Dict[str, float]) -> List[dict]:
    executed = []
    for cand in candidates:
        if len(portfolio.get('positions', {})) >= MAX_POSITIONS:
            break
        ticker = cand['ticker']
        price  = cand['price']
        if ticker in portfolio.get('positions', {}):
            continue
        pos_value = sum(
            p.get('shares', 0) * prices.get(t, p.get('entry_price', 0))
            for t, p in portfolio.get('positions', {}).items()
        )
        total_equity = portfolio.get('cash', 0) + pos_value
        dd_scale = get_dd_scale(portfolio)
        alloc  = total_equity * POSITION_SIZE_PCT * dd_scale
        shares = int(alloc / price)
        cost   = shares * price
        if shares <= 0 or cost > portfolio.get('cash', 0):
            continue
        portfolio['cash'] -= cost
        portfolio.setdefault('positions', {})[ticker] = {
            'shares': shares, 'entry_price': price,
            'entry_date': str(SIM_DATE), 'ticker': ticker,
            'execution_mode': 'PAPER_SIM', 'is_power_stock': False,
            'stop_loss_price': price * (1 - HARD_STOP_PCT)
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
    entries = simulate_entries(candidates[:20], portfolio, prices)

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
