"""
strategy_engine.py
==================
Single source of truth for all VolatilityHunter pipeline logic.
Imported by: daily_trading_loop.py, simulate_monday.py, full_universe_backtest.py

All 4 modes (backtest, simulation, paper, live) use the same functions from here.
No strategy logic lives in the caller scripts — only orchestration.

Strategy versions:
  V7  = original (HARD_STOP=5%, OVERBOUGHT_EXIT=70)
  V8  = optimized (HARD_STOP=8%, OVERBOUGHT_EXIT=78, 20-day momentum, re-entry)
"""

import logging
import traceback
from typing import Dict, List, Optional, Tuple

import numpy as np
import pandas as pd

from src.strategy_v7_2 import add_indicators_v7_2

logger = logging.getLogger('strategy_engine')

# ── Shared constants (both versions) ──────────────────────────────────────────
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_PRICE         = 5.0
MIN_LIQUIDITY     = 500_000
VOLUME_SURGE      = 1.5
CAGR_FILTER       = 0.15
STOCH_LOW         = 32.0
STOCH_HIGH        = 80.0

# ── Version-specific parameters ───────────────────────────────────────────────
PARAMS = {
    'v7': {
        'HARD_STOP_PCT':    0.05,
        'OVERBOUGHT_EXIT':  70.0,
        'MOMENTUM_DAYS':    None,   # disabled
        'MOMENTUM_MIN':     None,
        'REENTRY':          False,
    },
    'v8': {
        'HARD_STOP_PCT':    0.08,
        'OVERBOUGHT_EXIT':  78.0,
        'MOMENTUM_DAYS':    20,     # 20-day return filter
        'MOMENTUM_MIN':     0.05,   # must be +5% over 20 days
        'REENTRY':          True,   # re-enter if conditions re-qualify after exit
    },
}

DEFAULT_VERSION = 'v7'


def get_params(version: str = DEFAULT_VERSION) -> dict:
    return PARAMS[version]


# ── Indicator helpers ──────────────────────────────────────────────────────────

def get_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_and_prepare(path_or_df, min_rows: int = 300,
                     cutoff_date=None) -> Optional[pd.DataFrame]:
    """
    Load a parquet file (or accept an already-loaded df), clean index,
    optionally slice to cutoff_date, compute indicators.
    Returns None if insufficient data.
    """
    try:
        if isinstance(path_or_df, pd.DataFrame):
            df = path_or_df.copy()
        else:
            df = pd.read_parquet(path_or_df)

        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)

        if cutoff_date is not None:
            df = df[df.index <= pd.Timestamp(cutoff_date)]

        if len(df) < min_rows:
            return None

        df = add_indicators_v7_2(df)
        return df
    except Exception as e:
        logger.debug(f"load_and_prepare error: {e}")
        return None


# ── Drawdown scaling (Bug 3 fix) ───────────────────────────────────────────────

def get_dd_scale(portfolio: dict) -> float:
    """
    Reduce position size during drawdown — matches backtest behaviour.
    -10% DD -> 50% of normal size
    -20% DD -> 25% of normal size
    """
    hwm = portfolio.get('high_water_mark', portfolio.get('total_value',
          portfolio.get('cash', 0)))
    equity = _portfolio_equity(portfolio, {})
    if hwm <= 0:
        return 1.0
    dd = (equity - hwm) / hwm
    if dd < -0.20:
        return 0.25
    if dd < -0.10:
        return 0.50
    return 1.0


def update_high_water_mark(portfolio: dict, prices: Dict[str, float]) -> None:
    """Call once per day after prices are fetched."""
    equity = _portfolio_equity(portfolio, prices)
    current_hwm = portfolio.get('high_water_mark', 0)
    if equity > current_hwm:
        portfolio['high_water_mark'] = equity


def _portfolio_equity(portfolio: dict, prices: Dict[str, float]) -> float:
    pos_value = sum(
        p.get('shares', 0) * prices.get(t, p.get('entry_price', 0))
        for t, p in portfolio.get('positions', {}).items()
    )
    return portfolio.get('cash', 0) + pos_value


# ── Power stock promotion (Bug 1 fix) ─────────────────────────────────────────

def promote_power_stocks(portfolio: dict,
                         prices: Dict[str, float],
                         load_fn) -> List[str]:
    """
    Step 3b: Check every open non-power position for power stock promotion.
    Calls load_fn(ticker) -> Optional[pd.DataFrame] (caller provides loader).
    Returns list of promoted tickers.
    Matches backtest: K>80 + above all SMAs + vol surge for 2 consecutive days.
    """
    promoted = []
    for ticker, pos in portfolio.get('positions', {}).items():
        if pos.get('is_power_stock', False):
            continue
        df = load_fn(ticker)
        if df is None or len(df) < 2:
            continue
        try:
            if _qualifies_for_power(df):
                pos['is_power_stock'] = True
                pos['power_promoted_date'] = str(df.index[-1].date())
                promoted.append(ticker)
                logger.info(f"[POWER PROMOTED] {ticker} -> Power Stock mode")
        except Exception as e:
            logger.error(f"promote_power_stocks {ticker}: {e}\n{traceback.format_exc()}")
    return promoted


def _qualifies_for_power(df: pd.DataFrame) -> bool:
    """2-consecutive-day power criteria — matches backtest state machine."""
    close_col = get_col(df, ['adjClose', 'Close', 'close'])
    vol_col   = get_col(df, ['Volume', 'volume', 'adjVolume'])
    if close_col is None or vol_col is None:
        return False

    for row in [df.iloc[-1], df.iloc[-2]]:
        k      = row.get('stoch_k', np.nan)
        price  = row[close_col]
        sma25  = row.get('sma_25',    np.nan)
        sma50  = row.get('sma_50',    np.nan)
        sma100 = row.get('sma_100',   np.nan)
        sma200 = row.get('sma_200',   np.nan)
        vsma   = row.get('volume_sma', np.nan)
        vol    = row[vol_col]

        if any(np.isnan(v) for v in [k, sma25, sma50, sma100, sma200, vsma]):
            return False
        if not (k > 80 and price > sma25 and price > sma50
                and price > sma100 and price > sma200
                and vol > vsma * VOLUME_SURGE):
            return False
    return True


# ── Highest price tracking (Bug 2 fix) ────────────────────────────────────────

def update_highest_prices(portfolio: dict, prices: Dict[str, float]) -> None:
    """
    Call once per day after prices fetched.
    Keeps highest_price current for ATR trailing stop calculation.
    """
    for ticker, pos in portfolio.get('positions', {}).items():
        current = prices.get(ticker)
        if current and current > pos.get('highest_price', 0):
            pos['highest_price'] = current


# ── Exit logic ────────────────────────────────────────────────────────────────

def check_exits(portfolio: dict,
                prices: Dict[str, float],
                load_fn,
                version: str = DEFAULT_VERSION) -> List[dict]:
    """
    Check all open positions for exit conditions.
    Returns list of exit dicts: {ticker, price, reason}
    Shared by daily_loop, simulate_monday.
    """
    p = get_params(version)
    HARD_STOP_PCT   = p['HARD_STOP_PCT']
    OVERBOUGHT_EXIT = p['OVERBOUGHT_EXIT']

    exits = []
    for ticker, pos in portfolio.get('positions', {}).items():
        price = prices.get(ticker)
        if not price:
            logger.warning(f"No price for {ticker} - skipping exit check")
            continue

        entry   = pos.get('entry_price', price)
        pnl_pct = (price - entry) / entry if entry > 0 else 0

        # Hard stop
        if pnl_pct <= -HARD_STOP_PCT:
            exits.append({'ticker': ticker, 'price': price,
                          'reason': f'Hard stop ({pnl_pct:.1%})'})
            continue

        df = load_fn(ticker)
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
            # Standard exit: overbought rollover OR SMA200 break
            if not np.isnan(k) and not np.isnan(d) and k < d and k > OVERBOUGHT_EXIT:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Overbought rollover K={k:.1f} (threshold={OVERBOUGHT_EXIT})'})
            elif not np.isnan(sma200) and price < sma200:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'SMA200 break ({price:.2f} < {sma200:.2f})'})
        else:
            # Power stock: SMA25 break or ATR trailing stop from highest_price
            highest = pos.get('highest_price', entry)
            trailing_stop = highest - 3.0 * atr if not np.isnan(atr) else np.nan

            if not np.isnan(sma25) and price < sma25:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Power SMA25 break ({price:.2f} < {sma25:.2f})'})
            elif not np.isnan(trailing_stop) and price < trailing_stop:
                exits.append({'ticker': ticker, 'price': price,
                              'reason': f'Power ATR trailing stop (stop={trailing_stop:.2f})'})

    return exits


# ── Entry scan logic ──────────────────────────────────────────────────────────

def scan_universe(all_tickers: List[str],
                  open_tickers: set,
                  prices: Dict[str, float],
                  load_fn,
                  version: str = DEFAULT_VERSION,
                  recently_exited: Optional[set] = None) -> List[dict]:
    """
    Scan all tickers for buy signals. Returns ranked list of candidates.
    load_fn(ticker) -> Optional[pd.DataFrame]
    recently_exited: set of tickers exited today — skip unless version=v8 with REENTRY=True
    """
    p = get_params(version)
    CAGR_MIN        = CAGR_FILTER
    MOMENTUM_DAYS   = p['MOMENTUM_DAYS']
    MOMENTUM_MIN    = p['MOMENTUM_MIN']
    REENTRY         = p['REENTRY']

    if recently_exited is None:
        recently_exited = set()

    candidates = []
    scanned    = 0

    for ticker in all_tickers:
        if ticker in open_tickers:
            continue
        # Re-entry: v7 skips stocks exited today; v8 allows re-entry if conditions re-qualify
        if ticker in recently_exited and not REENTRY:
            continue

        price = prices.get(ticker)
        if not price or price < MIN_PRICE:
            continue

        df = load_fn(ticker)
        if df is None or df.empty:
            continue

        close_col = get_col(df, ['adjClose', 'Close', 'close'])
        vol_col   = get_col(df, ['Volume', 'volume', 'adjVolume'])
        if close_col is None or vol_col is None:
            scanned += 1
            continue

        last   = df.iloc[-1]
        k      = last.get('stoch_k',    np.nan)
        d      = last.get('stoch_d',    np.nan)
        sma200 = last.get('sma_200',    np.nan)
        vsma   = last.get('volume_sma', np.nan)
        volume = last.get('volume',     np.nan)

        if any(np.isnan(v) for v in [k, d, sma200, vsma, volume]):
            scanned += 1
            continue

        # 252-day annual return
        annual_ret = np.nan
        if len(df) >= 253:
            p252 = df[close_col].iloc[-253]
            if p252 > 0:
                annual_ret = (df[close_col].iloc[-1] / p252) - 1

        if np.isnan(annual_ret):
            scanned += 1
            continue

        # 20-day momentum filter (v8 only)
        if MOMENTUM_DAYS and MOMENTUM_MIN is not None:
            if len(df) >= MOMENTUM_DAYS + 1:
                p20 = df[close_col].iloc[-(MOMENTUM_DAYS + 1)]
                mom20 = (df[close_col].iloc[-1] / p20) - 1 if p20 > 0 else np.nan
            else:
                mom20 = np.nan
            if np.isnan(mom20) or mom20 < MOMENTUM_MIN:
                scanned += 1
                continue

        buy = (
            STOCH_LOW <= k <= STOCH_HIGH and
            price > sma200 and
            volume >= vsma * VOLUME_SURGE and
            annual_ret >= CAGR_MIN and
            (price * volume) >= MIN_LIQUIDITY
        )

        if buy:
            stoch_score = 1.0 - abs(k - 56) / 24
            score = 0.6 * annual_ret + 0.4 * stoch_score
            reason_parts = [f'K={k:.1f}', f'1yr={annual_ret:.1%}', 'SMA200 ok', 'Vol surge']
            if MOMENTUM_DAYS:
                reason_parts.append(f'20d={mom20:.1%}')
            candidates.append({
                'ticker':        ticker,
                'price':         price,
                'score':         score,
                'stoch_k':       k,
                'annual_return': annual_ret,
                'reason':        ' | '.join(reason_parts),
            })

        scanned += 1
        if scanned % 500 == 0:
            logger.info(f"  Scanned {scanned}/{len(all_tickers)} | {len(candidates)} candidates")

    candidates.sort(key=lambda x: x['score'], reverse=True)
    logger.info(f"Scan complete ({version}): {len(candidates)} candidates from {scanned} tickers")
    return candidates


# ── Position sizing ───────────────────────────────────────────────────────────

def calc_position_size(portfolio: dict,
                       price: float,
                       prices: Dict[str, float],
                       version: str = DEFAULT_VERSION) -> Tuple[int, float]:
    """
    Returns (shares, cost) using 20% of equity with drawdown scaling.
    Returns (0, 0) if position not viable.
    """
    dd_scale     = get_dd_scale(portfolio)
    total_equity = _portfolio_equity(portfolio, prices)
    alloc        = total_equity * POSITION_SIZE_PCT * dd_scale
    shares       = int(alloc / price)
    cost         = shares * price

    if shares <= 0 or cost > portfolio.get('cash', 0):
        return 0, 0.0
    return shares, cost
