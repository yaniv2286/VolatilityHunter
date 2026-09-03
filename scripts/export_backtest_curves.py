#!/usr/bin/env python3
"""
export_backtest_curves.py
=========================
Generates a backtest JSON that includes the full v8 and v8.1 equity curves
in addition to the standard summary metrics.  This is a thin wrapper around
the reference backtest functions in scripts/backtest_v8_vs_v8_1.py so the
reference script itself is not modified.

Output: logs/backtest_v8_vs_v8_1_curves_YYYYMMDD_HHMM.json
"""

import os
import sys
import time
import json
from pathlib import Path

import pandas as pd
import numpy as np

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

# Re-use the reference backtest engine without changing it.
import scripts.backtest_v8_vs_v8_1 as bt

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

DATA_DIR = ROOT / 'data'
LOGS_DIR = ROOT / 'logs'
LOGS_DIR.mkdir(exist_ok=True)


def get_sector(ticker: str) -> str:
    """Same first-letter bucketing used by scripts/backtest_v8_vs_v8_1.py."""
    buckets = {
        'ABCDE': 'Technology', 'FGHIJ': 'Healthcare',
        'KLMNO': 'Financials', 'PQRST': 'Energy',
        'UVWXYZ': 'Industrials'
    }
    t = ticker[0].upper()
    for letters, sector in buckets.items():
        if t in letters:
            return sector
    return 'Consumer'


def print_comparison(m8: dict, m81: dict):
    """Print v8 vs v8.1 comparison with a correct verdict (positive dd delta = shallower drawdown)."""
    def delta(v81, v8, higher_is_better=True):
        d = v81 - v8
        sign = '+' if d >= 0 else ''
        if higher_is_better:
            marker = ' [+]' if d > 0 else (' [-]' if d < 0 else '')
        else:
            marker = ' [+]' if d < 0 else (' [-]' if d > 0 else '')
        return f"{sign}{d:.2f}{marker}"

    print()
    print('=' * 72)
    print('STRATEGY COMPARISON: v8 (production)  vs  v8.1 (DD-reduction)')
    print('v8.1 adds: regime filter + sector cap(3) + time stop(10d) + vol sizing')
    print('=' * 72)
    print(f"{'Metric':<28} {'v8':>10} {'v8.1':>10} {'Delta':>14}")
    print('-' * 72)
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
        v8v  = m8.get(key, 0)
        v81v = m81.get(key, 0)
        if key == 'final_equity':
            print(f"  {label:<26} {v8v/1000:>10.1f} {v81v/1000:>10.1f} {delta(v81v/1000, v8v/1000, hib):>14}")
        elif key == 'total_trades':
            print(f"  {label:<26} {int(v8v):>10} {int(v81v):>10}")
        else:
            print(f"  {label:<26} {v8v:>10.2f} {v81v:>10.2f} {delta(v81v, v8v, hib):>14}")
    print('=' * 72)
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
    print(f'VERDICT: {verdict}')
    print(f'  CAGR delta: {cagr_d:+.2f}%  |  Drawdown delta: {dd_d:+.2f}%')
    print()


def main() -> int:
    t0 = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print('=' * 72)
    print('BACKTEST CURVE EXPORT: v8 vs v8.1')
    print(f'Universe: {len(parquet_files)} tickers | Capital: ${bt.INITIAL_CAPITAL:,.0f}')
    print('v8.1: regime filter + sector cap(3) + time stop(10d) + vol sizing')
    print('=' * 72)

    spy_regime = pd.Series(dtype=bool)
    spy_path = DATA_DIR / 'SPY.parquet'
    if spy_path.exists():
        spy_df = bt.load_ticker(spy_path)
        if spy_df is not None:
            spy_regime = bt.build_spy_regime(spy_df)
            bull_days = int(spy_regime.sum())
            bear_days = int((~spy_regime).sum())
            print(f'\nSPY regime loaded: {bull_days} bull days / {bear_days} bear days')
    else:
        print('\nWARN: SPY.parquet not found -- regime filter disabled (all bull)')

    v8_trades = []
    v81_trades = []
    loaded = skipped = 0

    print(f'\nRunning per-ticker backtests ({len(parquet_files)} tickers)...')
    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 300 == 0:
            print(f'  {i+1}/{len(parquet_files)} | v8:{len(v8_trades)} v8.1:{len(v81_trades)} trades')

        df = bt.load_ticker(fpath)
        if df is None or len(df) < bt.MIN_ROWS:
            skipped += 1
            continue
        if bt.get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue

        sector = get_sector(ticker)
        v8_trades.extend(bt.backtest_ticker_v8(ticker, df))
        v81_trades.extend(bt.backtest_ticker_v8_1(ticker, df, spy_sma200=spy_regime, sector=sector))
        loaded += 1

    print(f'  Done: {loaded} tickers | {skipped} skipped')
    print(f'  v8 trades: {len(v8_trades)} | v8.1 trades: {len(v81_trades)}')

    if not v8_trades or not v81_trades:
        print('ERROR: No trades generated.')
        return 1

    print('\nBuilding equity curves...')
    ec8 = bt.build_equity_curve_v8(v8_trades)
    ec81 = bt.build_equity_curve_v8_1(v81_trades, spy_regime)

    m8 = bt.calc_metrics(ec8, v8_trades)
    m81 = bt.calc_metrics(ec81, v81_trades)

    print_comparison(m8, m81)

    bear_trades = [t for t in v81_trades if not t.get('bull_regime', True)]
    bull_trades = [t for t in v81_trades if t.get('bull_regime', True)]
    print(f'v8.1 regime breakdown:')
    print(f'  Bull entries: {len(bull_trades)} | Bear entries: {len(bear_trades)}')

    time_stops = [t for t in v81_trades if t.get('reason') == 'Time stop']
    if time_stops:
        ts_avg = float(np.mean([t['pnl_pct'] for t in time_stops]))
        print(f'\nTime stop trades: {len(time_stops)} | avg P&L: {ts_avg:.2f}%')

    def _series_to_list(ec: pd.Series):
        return [[str(d.date()), float(v)] for d, v in ec.items()]

    out = {
        'generated': pd.Timestamp.now().isoformat(),
        'v8': m8,
        'v8_1': m81,
        'delta_cagr': m81.get('cagr', 0) - m8.get('cagr', 0),
        'delta_drawdown': m81.get('max_drawdown', 0) - m8.get('max_drawdown', 0),
        'delta_sharpe': m81.get('sharpe', 0) - m8.get('sharpe', 0),
        'time_stop_count': len(time_stops),
        'bear_trade_count': len(bear_trades),
        'equity_curve_v8': _series_to_list(ec8),
        'equity_curve_v8_1': _series_to_list(ec81),
    }
    ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    out_path = LOGS_DIR / f'backtest_v8_vs_v8_1_curves_{ts}.json'
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f'\nResults saved: {out_path}')
    print(f'Total time: {time.time() - t0:.0f}s')
    return 0


if __name__ == '__main__':
    sys.exit(main())
