"""
backtest_v8_1_vs_v8_3.py
========================
Compare v8.1 (baseline) vs v8.3 (trend-quality entry filters).
v8.3 improvements:
  1. ADX filter: adx_14 >= 20 (sideways regime rejection)
  2. SMA200 proximity guard: no entries within 1.5% of the 200-SMA
  3. Breakout requirement: close > max(high, 20) prior bars
  4. Stop-distance cap: min(low, ema_8, sma_20) must be within 5% below entry

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

from src.strategy_v8_1 import backtest_ticker_v8_1
from src.strategy_v8_3 import backtest_ticker_v8_3
from src.strategy_v7_2 import add_indicators_v7_2

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backtest_v81_v83')

DATA_DIR   = ROOT / 'data'
OUTPUT_DIR = ROOT / 'logs'
OUTPUT_DIR.mkdir(exist_ok=True)

INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_ROWS          = 300

SECTOR_MAX        = 3
REGIME_MAX_POS    = 3

# Variant configs map to PARAMS keys in strategy_engine.py.
# v8.3b disables breakout + stop-distance (audit: they reject 72.7%/52.9% of base bars).
VARIANTS = {
    'v8.3':  dict(adx_min=20.0, sma200_prox=0.015, breakout_lookback=20, max_stop_pct=0.05),
    'v8.3b': dict(adx_min=20.0, sma200_prox=0.015, breakout_lookback=None, max_stop_pct=None),
    'v8.3c': dict(adx_min=15.0, sma200_prox=0.015, breakout_lookback=None, max_stop_pct=None),
    'v8.4':  dict(adx_min=None, sma200_prox=None, breakout_lookback=None, max_stop_pct=None,
                  rsi_min=50.0),
}


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


def build_equity_curve_v8_1(all_trades: List[dict],
                              spy_regime: pd.Series) -> pd.Series:
    """v8.1 equity curve with regime-aware max positions and sector cap."""
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    trades = sorted(all_trades, key=lambda t: t['entry_date'])
    equity = INITIAL_CAPITAL
    curve  = [(trades[0]['entry_date'], equity)]
    active = []
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

        if open_count >= max_pos_now:
            continue
        if sector_count >= SECTOR_MAX:
            continue

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


def print_comparison(m81: dict, m83: dict, variant: str):
    def delta(v83, v81, higher_is_better=True):
        d = v83 - v81
        sign = '+' if d >= 0 else ''
        if higher_is_better:
            marker = ' [+]' if d > 0 else (' [-]' if d < 0 else '')
        else:
            marker = ' [+]' if d < 0 else (' [-]' if d > 0 else '')
        return f"{sign}{d:.2f}{marker}"

    print()
    print("=" * 72)
    print(f"STRATEGY COMPARISON: v8.1 (baseline)  vs  {variant} (trend-quality filters)")
    print("v8.3 adds: ADX>=20 + SMA200 proximity + 20d breakout + stop-distance cap")
    print("v8.3b:     ADX>=20 + SMA200 proximity only")
    print("=" * 72)
    print(f"{'Metric':<28} {'v8.1':>10} {variant:>10} {'Delta':>14}")
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
        v81v = m81.get(key,  0)
        v83v = m83.get(key, 0)
        if key == 'final_equity':
            print(f"  {label:<26} {v81v/1000:>10.1f} {v83v/1000:>10.1f} {delta(v83v/1000, v81v/1000, hib):>14}")
        elif key == 'total_trades':
            print(f"  {label:<26} {int(v81v):>10} {int(v83v):>10}")
        else:
            print(f"  {label:<26} {v81v:>10.2f} {v83v:>10.2f} {delta(v83v, v81v, hib):>14}")
    print("=" * 72)
    print()
    dd_d   = m83.get('max_drawdown', 0) - m81.get('max_drawdown', 0)
    cagr_d = m83.get('cagr', 0) - m81.get('cagr', 0)
    if dd_d < 0 and cagr_d >= 0:
        verdict = f"{variant} WINS  (lower DD, CAGR improved or preserved)"
    elif dd_d < 0 and cagr_d >= -1.0:
        verdict = f"{variant} MIXED (lower DD but CAGR cost < 1%)"
    elif cagr_d > 0 and dd_d <= 0:
        verdict = f"{variant} WINS  (higher CAGR, DD improved or same)"
    else:
        verdict = "v8.1 STILL BETTER"
    print(f"VERDICT: {verdict}")
    print(f"  CAGR delta: {cagr_d:+.2f}%  |  Drawdown delta: {dd_d:+.2f}%")
    print()


def get_sector(ticker: str) -> str:
    """Simple sector bucket by ticker initial. Replace with GICS CSV for production."""
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


def main():
    t0 = time.time()
    variant = sys.argv[1] if len(sys.argv) > 1 else 'v8.3'
    if variant not in VARIANTS:
        print(f"ERROR: unknown variant '{variant}'. Choose from {list(VARIANTS)}")
        return 1
    vkwargs = VARIANTS[variant]
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print("=" * 72)
    print(f"VOLATILITYHUNTER BACKTEST: v8.1 vs {variant} (TREND-QUALITY FILTERS)")
    print(f"Universe: {len(parquet_files)} tickers | Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"{variant} config: {vkwargs}")
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

    v81_trades = []
    v83_trades = []
    loaded = skipped = 0

    print(f"\nRunning per-ticker backtests ({len(parquet_files)} tickers)...")
    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(parquet_files)} | v8.1:{len(v81_trades)} v8.3:{len(v83_trades)} trades")

        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        if get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue

        sector = get_sector(ticker)
        v81_trades.extend(backtest_ticker_v8_1(ticker, df,
                                                spy_sma200=spy_regime,
                                                sector=sector))
        v83_trades.extend(backtest_ticker_v8_3(ticker, df,
                                                spy_sma200=spy_regime,
                                                sector=sector, **vkwargs))
        loaded += 1

    print(f"  Done: {loaded} tickers | {skipped} skipped")
    print(f"  v8.1 trades: {len(v81_trades)} | v8.3 trades: {len(v83_trades)}")

    if not v81_trades or not v83_trades:
        print("ERROR: No trades generated.")
        return 1

    print("\nBuilding equity curves...")
    ec81 = build_equity_curve_v8_1(v81_trades, spy_regime)
    ec83 = build_equity_curve_v8_1(v83_trades, spy_regime)  # Use same equity curve logic

    m81 = calc_metrics(ec81, v81_trades)
    m83 = calc_metrics(ec83, v83_trades)

    print_comparison(m81, m83, variant)

    # Trade count guardrail check (v8.2 reference: -78% = failure)
    trade_ratio = len(v83_trades) / len(v81_trades) if v81_trades else 0
    print(f"v8.3 trade retention: {trade_ratio:.1%} of v8.1 "
          f"({'PASS' if trade_ratio >= 0.70 else 'FAIL - exceeds 30% reduction'})")

    # Save results
    out = {
        'generated':       pd.Timestamp.now().isoformat(),
        'variant':         variant,
        'variant_config':  vkwargs,
        'v8_1':            m81,
        variant.replace('.', '_'): m83,
        'delta_cagr':      m83.get('cagr', 0)         - m81.get('cagr', 0),
        'delta_drawdown':  m83.get('max_drawdown', 0)  - m81.get('max_drawdown', 0),
        'delta_sharpe':    m83.get('sharpe', 0)        - m81.get('sharpe', 0),
        'trade_retention': trade_ratio,
    }
    ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    out_path = OUTPUT_DIR / f"backtest_v8_1_vs_{variant.replace('.', '_')}_{ts}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved: {out_path}")
    print(f"Total time: {time.time() - t0:.0f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
