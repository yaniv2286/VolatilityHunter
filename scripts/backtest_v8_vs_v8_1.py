"""
backtest_v8_vs_v8_1.py
======================
Side-by-side comparison: v8 (production) vs v8.1 (DD-reduction).
v8.1 changes vs v8:
  1. Market regime filter: SPY < SMA200 -> max 3 positions (bear guard)
  2. Sector cap: max 3 positions per sector simultaneously
  3. Time stop: exit losing position after 10 trading days
  4. Volatility-adjusted sizing: size scaled by ATR% vs median ATR%

Exit code 0 = completed successfully.
"""

import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from src.strategy_v8   import backtest_ticker_v8
from src.strategy_v8_1 import backtest_ticker_v8_1
from src.strategy_v7_2 import add_indicators_v7_2

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backtest_v8_v81')

DATA_DIR   = ROOT / 'data'
OUTPUT_DIR = ROOT / 'logs'
OUTPUT_DIR.mkdir(exist_ok=True)

INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_ROWS          = 300

# Sector cap for v8.1
SECTOR_MAX        = 3
REGIME_MAX_POS    = 3


def get_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_ticker(path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_parquet(path)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)
        return df
    except Exception:
        return None


def build_spy_regime(spy_df: pd.DataFrame) -> pd.Series:
    """Returns a boolean Series: True = SPY above its 200-day SMA (bull regime)."""
    close_col = get_col(spy_df, ['adjClose', 'Close', 'close'])
    if close_col is None:
        return pd.Series(dtype=bool)
    spy_df = add_indicators_v7_2(spy_df.copy())
    if 'sma_200' not in spy_df.columns:
        return pd.Series(dtype=bool)
    bull = spy_df[close_col] > spy_df['sma_200']
    return bull


def build_equity_curve_v8(all_trades: List[dict],
                           max_pos: int = MAX_POSITIONS) -> pd.Series:
    """Standard equity curve — same as backtest_v7_vs_v8.py."""
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    trades = sorted(all_trades, key=lambda t: t['entry_date'])
    equity = INITIAL_CAPITAL
    slots  = max_pos
    curve  = [(trades[0]['entry_date'], equity)]
    active = []
    hwm    = equity

    def close_expired(cur_date):
        nonlocal equity, slots
        still_open = []
        for pos in active:
            if pos['exit_date'] <= cur_date:
                gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
                equity = equity - pos['allocated'] + gain
                slots += 1
                curve.append((pos['exit_date'], equity))
            else:
                still_open.append(pos)
        active.clear()
        active.extend(still_open)

    for t in trades:
        close_expired(t['entry_date'])
        if equity > hwm:
            hwm = equity
        dd = (equity - hwm) / hwm if hwm > 0 else 0
        dd_scale = 0.25 if dd < -0.20 else 0.50 if dd < -0.10 else 1.0

        if slots > 0:
            allocated = equity * POSITION_SIZE_PCT * dd_scale
            if allocated > 0:
                active.append({'exit_date': t['exit_date'],
                               'pnl_pct':   t['pnl_pct'],
                               'allocated': allocated})
                slots -= 1
                curve.append((t['entry_date'], equity))

    for pos in sorted(active, key=lambda x: x['exit_date']):
        gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
        equity = equity - pos['allocated'] + gain
        curve.append((pos['exit_date'], equity))

    ec = pd.Series(
        [v for _, v in curve],
        index=pd.to_datetime([d for d, _ in curve])
    ).sort_index()
    return ec


def build_equity_curve_v8_1(all_trades: List[dict],
                              spy_regime: pd.Series) -> pd.Series:
    """
    v8.1 equity curve with:
    - Regime-aware max positions (10 bull / 3 bear)
    - Sector cap (max 3 per sector simultaneously)
    - Volatility-adjusted position sizing (vol_scale from trade dict)
    - Drawdown scaling (same as v8)
    """
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    trades = sorted(all_trades, key=lambda t: t['entry_date'])
    equity = INITIAL_CAPITAL
    curve  = [(trades[0]['entry_date'], equity)]
    active = []   # list of active position dicts
    hwm    = equity

    def close_expired(cur_date):
        nonlocal equity
        still_open = []
        for pos in active:
            if pos['exit_date'] <= cur_date:
                gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
                equity = equity - pos['allocated'] + gain
                curve.append((pos['exit_date'], equity))
            else:
                still_open.append(pos)
        active.clear()
        active.extend(still_open)

    for t in trades:
        close_expired(t['entry_date'])
        if equity > hwm:
            hwm = equity
        dd = (equity - hwm) / hwm if hwm > 0 else 0
        dd_scale = 0.25 if dd < -0.20 else 0.50 if dd < -0.10 else 1.0

        # Regime-aware max positions
        entry_dt = pd.Timestamp(t['entry_date'])
        if spy_regime.empty or entry_dt not in spy_regime.index:
            is_bull = True
        else:
            is_bull = bool(spy_regime.loc[entry_dt])
        max_pos_now = MAX_POSITIONS if is_bull else REGIME_MAX_POS

        open_count  = len(active)
        sector      = t.get('sector', 'Unknown')
        sector_count = sum(1 for p in active if p.get('sector') == sector)

        # Apply all caps
        if open_count >= max_pos_now:
            continue
        if sector_count >= SECTOR_MAX:
            continue

        # Volatility-adjusted sizing
        vol_scale = t.get('vol_scale', 1.0)
        allocated = equity * POSITION_SIZE_PCT * dd_scale * vol_scale
        if allocated > 0:
            active.append({
                'exit_date': t['exit_date'],
                'pnl_pct':   t['pnl_pct'],
                'allocated': allocated,
                'sector':    sector,
            })
            curve.append((t['entry_date'], equity))

    for pos in sorted(active, key=lambda x: x['exit_date']):
        gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
        equity = equity - pos['allocated'] + gain
        curve.append((pos['exit_date'], equity))

    ec = pd.Series(
        [v for _, v in curve],
        index=pd.to_datetime([d for d, _ in curve])
    ).sort_index()
    return ec


def calc_metrics(ec: pd.Series, trades: List[dict]) -> dict:
    if ec.empty or not trades:
        return {}
    final  = float(ec.iloc[-1])
    years  = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
    cagr   = ((final / INITIAL_CAPITAL) ** (1 / years)) - 1

    daily  = ec.resample('B').last().ffill().dropna()
    dd     = float(((daily - daily.cummax()) / daily.cummax()).min())
    ret    = daily.pct_change().dropna()
    sharpe = float((ret.mean() / ret.std()) * 252 ** 0.5) if ret.std() > 0 else 0.0

    winners  = [t for t in trades if t['pnl_pct'] > 0]
    losers   = [t for t in trades if t['pnl_pct'] <= 0]
    win_rate = len(winners) / len(trades) * 100 if trades else 0
    avg_win  = float(np.mean([t['pnl_pct'] for t in winners])) if winners else 0
    avg_loss = float(np.mean([t['pnl_pct'] for t in losers]))  if losers  else 0
    pf_denom = abs(sum(t['pnl_pct'] for t in losers)) or 1
    pf       = sum(t['pnl_pct'] for t in winners) / pf_denom

    cutoff5     = ec.index[-1] - pd.DateOffset(years=5)
    ec5         = ec[ec.index >= cutoff5]
    cutoff5_str = str(cutoff5.date())
    tr5         = [t for t in trades if t['entry_date'] >= cutoff5_str]
    cagr5       = 0.0
    if len(ec5) > 1:
        yrs5  = max((ec5.index[-1] - ec5.index[0]).days / 365.25, 0.01)
        cagr5 = ((float(ec5.iloc[-1]) / float(ec5.iloc[0])) ** (1 / yrs5)) - 1

    return {
        'final_equity':  final,
        'cagr':          cagr * 100,
        'cagr_5yr':      cagr5 * 100,
        'max_drawdown':  dd * 100,
        'sharpe':        sharpe,
        'win_rate':      win_rate,
        'avg_win':       avg_win,
        'avg_loss':      avg_loss,
        'profit_factor': pf,
        'total_trades':  len(trades),
        'years':         years,
    }


def print_comparison(m8: dict, m81: dict):
    def delta(v81, v8, higher_is_better=True):
        d = v81 - v8
        sign = '+' if d >= 0 else ''
        if higher_is_better:
            marker = ' [+]' if d > 0 else (' [-]' if d < 0 else '')
        else:
            marker = ' [+]' if d < 0 else (' [-]' if d > 0 else '')
        return f"{sign}{d:.2f}{marker}"

    print()
    print("=" * 72)
    print("STRATEGY COMPARISON: v8 (production)  vs  v8.1 (DD-reduction)")
    print("v8.1 adds: regime filter + sector cap + time stop + vol sizing")
    print("=" * 72)
    print(f"{'Metric':<28} {'v8':>10} {'v8.1':>10} {'Delta':>14}")
    print("-" * 72)
    rows = [
        ('26yr CAGR %',     'cagr',          True),
        ('5yr CAGR %',      'cagr_5yr',      True),
        ('Max Drawdown %',  'max_drawdown',   False),
        ('Sharpe Ratio',    'sharpe',         True),
        ('Win Rate %',      'win_rate',       True),
        ('Avg Win %',       'avg_win',        True),
        ('Avg Loss %',      'avg_loss',       False),
        ('Profit Factor',   'profit_factor',  True),
        ('Total Trades',    'total_trades',   True),
        ('Final Equity $k', 'final_equity',   True),
    ]
    for label, key, hib in rows:
        v8v  = m8.get(key,  0)
        v81v = m81.get(key, 0)
        if key == 'final_equity':
            print(f"  {label:<26} {v8v/1000:>10.1f} {v81v/1000:>10.1f} {delta(v81v/1000, v8v/1000, hib):>14}")
        elif key == 'total_trades':
            print(f"  {label:<26} {int(v8v):>10} {int(v81v):>10}")
        else:
            print(f"  {label:<26} {v8v:>10.2f} {v81v:>10.2f} {delta(v81v, v8v, hib):>14}")
    print("=" * 72)
    print()
    dd_d   = m81.get('max_drawdown', 0) - m8.get('max_drawdown', 0)
    cagr_d = m81.get('cagr', 0) - m8.get('cagr', 0)
    # dd_d > 0 means v8.1 had a shallower (less negative) max drawdown.
    if dd_d > 0 and cagr_d >= -1.0:
        verdict = "v8.1 WINS  (lower DD, CAGR preserved)"
    elif dd_d > 0 and cagr_d < -1.0:
        verdict = "v8.1 MIXED (lower DD but CAGR cost > 1%)"
    elif cagr_d > 0:
        verdict = "v8.1 BETTER (higher CAGR, watch DD)"
    else:
        verdict = "v8 STILL BETTER"
    print(f"VERDICT: {verdict}")
    print(f"  CAGR delta: {cagr_d:+.2f}%  |  Drawdown delta: {dd_d:+.2f}%")
    print()


def main():
    t0 = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print("=" * 72)
    print("VOLATILITYHUNTER BACKTEST: v8 vs v8.1 (DD-REDUCTION)")
    print(f"Universe: {len(parquet_files)} tickers | Capital: ${INITIAL_CAPITAL:,.0f}")
    print("v8.1: regime filter + sector cap(3) + time stop(10d) + vol sizing")
    print("=" * 72)

    # Load SPY for regime filter
    spy_regime = pd.Series(dtype=bool)
    spy_path = DATA_DIR / 'SPY.parquet'
    if spy_path.exists():
        spy_df = load_ticker(spy_path)
        if spy_df is not None:
            spy_regime = build_spy_regime(spy_df)
            bull_days = int(spy_regime.sum())
            bear_days = int((~spy_regime).sum())
            print(f"\nSPY regime loaded: {bull_days} bull days / {bear_days} bear days")
    else:
        print("\nWARN: SPY.parquet not found — regime filter disabled (all bull)")

    # Simple sector map — assign by ticker initial for realistic simulation
    # In production this would use a real GICS lookup. For backtest we use
    # first-letter bucketing to create 8 pseudo-sectors (enough to test cap logic).
    def get_sector(ticker: str) -> str:
        buckets = {
            'ABCDE': 'Technology', 'FGHIJ': 'Healthcare',
            'KLMNO': 'Financials',  'PQRST': 'Energy',
            'UVWXYZ': 'Industrials'
        }
        t = ticker[0].upper()
        for letters, sector in buckets.items():
            if t in letters:
                return sector
        return 'Consumer'

    v8_trades  = []
    v81_trades = []
    loaded = skipped = 0

    print(f"\nRunning per-ticker backtests ({len(parquet_files)} tickers)...")
    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(parquet_files)} | v8:{len(v8_trades)} v8.1:{len(v81_trades)} trades")

        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        if get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue

        sector = get_sector(ticker)
        v8_trades.extend(backtest_ticker_v8(ticker, df))
        v81_trades.extend(backtest_ticker_v8_1(ticker, df,
                                                spy_sma200=spy_regime,
                                                sector=sector))
        loaded += 1

    print(f"  Done: {loaded} tickers | {skipped} skipped")
    print(f"  v8 trades: {len(v8_trades)} | v8.1 trades: {len(v81_trades)}")

    if not v8_trades or not v81_trades:
        print("ERROR: No trades generated.")
        return 1

    print("\nBuilding equity curves...")
    ec8  = build_equity_curve_v8(v8_trades)
    ec81 = build_equity_curve_v8_1(v81_trades, spy_regime)

    m8  = calc_metrics(ec8,  v8_trades)
    m81 = calc_metrics(ec81, v81_trades)

    print_comparison(m8, m81)

    # Breakdown by regime for v8.1
    bear_trades = [t for t in v81_trades if not t.get('bull_regime', True)]
    bull_trades = [t for t in v81_trades if t.get('bull_regime', True)]
    print(f"v8.1 regime breakdown:")
    print(f"  Bull entries: {len(bull_trades)} | Bear entries: {len(bear_trades)}")
    if bear_trades:
        bear_wr = sum(1 for t in bear_trades if t['pnl_pct'] > 0) / len(bear_trades) * 100
        bull_wr = sum(1 for t in bull_trades if t['pnl_pct'] > 0) / len(bull_trades) * 100 if bull_trades else 0
        print(f"  Bull win rate: {bull_wr:.1f}% | Bear win rate: {bear_wr:.1f}%")

    # Time stop analysis
    time_stops = [t for t in v81_trades if t.get('reason') == 'Time stop']
    if time_stops:
        ts_avg = float(np.mean([t['pnl_pct'] for t in time_stops]))
        print(f"\nTime stop trades: {len(time_stops)} | avg P&L: {ts_avg:.2f}%")

    # Save results
    out = {
        'generated':       pd.Timestamp.now().isoformat(),
        'v8':              m8,
        'v8_1':            m81,
        'delta_cagr':      m81.get('cagr', 0)         - m8.get('cagr', 0),
        'delta_drawdown':  m81.get('max_drawdown', 0)  - m8.get('max_drawdown', 0),
        'delta_sharpe':    m81.get('sharpe', 0)        - m8.get('sharpe', 0),
        'time_stop_count': len(time_stops),
        'bear_trade_count': len(bear_trades),
    }
    ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    out_path = OUTPUT_DIR / f"backtest_v8_vs_v8_1_{ts}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved: {out_path}")
    print(f"Total time: {time.time() - t0:.0f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
