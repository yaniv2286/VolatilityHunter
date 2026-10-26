"""Parity check: prefiltered scan must equal full-universe scan.

For sampled sessions, run engine_scan_universe twice - once over every
ticker, once over data.prefilter_candidates() output - and require the
returned candidate lists (ticker, score, all fields) to be IDENTICAL.

Any divergence means the prefilter diverges from the shared engine and
the speed optimization is invalid.

Run:  python scripts/verify_prefilter.py
Exit 0 only if all sampled days match exactly.
"""

import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import BacktestData
from src.strategy_engine import scan_universe as engine_scan_universe, get_params

TEST_SNAPSHOT = Path('temp/ws_snapshot_test')
TICKERS = ['AAPL', 'AXL', 'SPLK', 'MSFT', 'TWTR', 'SPY']
VERSION = 'v8.1'
FAILURES = []


def norm(c):
    out = dict(c)
    for k, v in out.items():
        if isinstance(v, float):
            out[k] = round(v, 10)
    return out


def main():
    data = BacktestData(TEST_SNAPSHOT / 'prices', TICKERS)
    cal = data.build_calendar('2020-01-01', '2021-12-31')
    p = get_params(VERSION)
    rng = np.random.RandomState(7)
    sample = sorted(rng.choice(len(cal), size=min(30, len(cal)),
                               replace=False))
    checked = 0
    for i in sample:
        date = cal[i]
        data.advance(date)
        prices = data.session_prices(date)
        load_fn = lambda t, d=date: data.asof(t, d)
        full = engine_scan_universe(
            data.tickers, set(), prices, load_fn, version=VERSION,
            today=pd.Timestamp(date).date(), earnings_map={})
        filt_list = data.prefilter_candidates(
            date, p.get('MOMENTUM_DAYS'), p.get('MOMENTUM_MIN'))
        filt = engine_scan_universe(
            filt_list, set(), prices, load_fn, version=VERSION,
            today=pd.Timestamp(date).date(), earnings_map={})
        same = [norm(c) for c in full] == [norm(c) for c in filt]
        status = 'PASS' if same else 'FAIL'
        print(f"  [{status}] {date.date()}: full={len(full)} "
              f"prefilter={len(filt_list)} survivors -> {len(filt)}")
        if not same:
            FAILURES.append(str(date.date()))
            fset = {c['ticker'] for c in full}
            lset = {c['ticker'] for c in filt}
            print(f"    missing: {fset - lset} extra: {lset - fset}")
        checked += 1
    print()
    if FAILURES:
        print(f"FAILED on {FAILURES}")
        sys.exit(1)
    print(f"All {checked} sampled days identical. Prefilter is exact.")
    sys.exit(0)


if __name__ == '__main__':
    main()
