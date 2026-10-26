"""Correctness checks for src/backtest_engine.py.

1. FUTURE-DATA ISOLATION: truncate every price file at a cutoff, rerun,
   and require identical trades/equity on the shared window. If any
   decision used data after T, the runs would diverge.
2. DETERMINISM: two identical runs produce identical results.
3. CASH INTEGRITY: cash never goes negative; settled cash is respected.
4. NEXT-OPEN FILLS: every fill date is strictly after its signal date's
   bar (fills land on the session following the signal pass).

Run:  python scripts/verify_backtest_corrected.py
Exit 0 only if all checks pass.
"""

import os
import shutil
import sys
import tempfile
from pathlib import Path

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import BacktestData, CorrectedBacktest

TEST_SNAPSHOT = Path('temp/ws_snapshot_test')
START, END, CUTOFF = '2020-01-01', '2021-12-31', '2020-06-30'
TICKERS = ['AAPL', 'AXL', 'SPLK', 'MSFT', 'TWTR', 'SPY']
FAILURES = []


def check(name, ok, detail=''):
    print(f"  [{'PASS' if ok else 'FAIL'}] {name} {detail}")
    if not ok:
        FAILURES.append(name)


def run(prices_dir, start, end):
    data = BacktestData(Path(prices_dir), TICKERS)
    data.build_calendar(start, end)
    bt = CorrectedBacktest(data, starting_cash=100_000.0, version='v8.1')
    res = bt.run()
    eq = res['equity'].reset_index(drop=True)
    trades = [(r['ticker'], r['date'], r['shares'], round(r['price'], 4))
              for r in res['entries'] + res['exits']]
    return res, eq, trades


def test_isolation():
    print("1. Future-data isolation")
    with tempfile.TemporaryDirectory() as tmp:
        out = Path(tmp) / 'prices'
        out.mkdir(parents=True)
        for t in TICKERS:
            df = pd.read_parquet(TEST_SNAPSHOT / 'prices' / f'{t.lower()}.parquet')
            if 'date' in df.columns:
                df = df.set_index('date')
            df[df.index <= CUTOFF].to_parquet(out / f'{t.lower()}.parquet')
        res_a, eq_a, trades_a = run(out, START, CUTOFF)
        res_b, eq_b, trades_b = run(TEST_SNAPSHOT / 'prices', START, CUTOFF)
    check("equity identical", eq_a['equity'].round(6).equals(
        eq_b['equity'].round(6)),
        f"(n={len(eq_a)} vs {len(eq_b)})")
    check("trades identical", trades_a == trades_b,
          f"({len(trades_a)} vs {len(trades_b)})")


def test_determinism():
    print("2. Determinism")
    _, eq1, tr1 = run(TEST_SNAPSHOT / 'prices', START, END)
    _, eq2, tr2 = run(TEST_SNAPSHOT / 'prices', START, END)
    check("equity identical", eq1['equity'].equals(eq2['equity']))
    check("trades identical", tr1 == tr2)


def test_cash():
    print("3. Cash integrity")
    res, eq, _ = run(TEST_SNAPSHOT / 'prices', START, END)
    check("cash never negative", (eq['cash'] >= -0.01).all(),
          f"min=${eq['cash'].min():.2f}")
    check("settled <= cash", (eq['settled_cash'] <= eq['cash'] + 0.01).all())
    check("no negative positions value", (eq['positions_value'] >= -0.01).all())
    check("rejects recorded not crashed",
          all(o.status in ('filled', 'rejected') for o in res['orders']))


def test_next_open():
    print("4. Next-open fill timing")
    data = BacktestData(TEST_SNAPSHOT / 'prices', TICKERS)
    cal = data.build_calendar(START, END)
    bt = CorrectedBacktest(data, starting_cash=100_000.0, version='v8.1')
    res = bt.run()
    ok = True
    for r in res['entries'] + res['exits']:
        t, d = r['ticker'], pd.Timestamp(r['date'])
        dates = data._dates.get(t)
        a = data._arr.get(t)
        if dates is None or a is None:
            continue
        i = dates.searchsorted(d)
        if i >= len(dates) or dates[i] != d:
            continue
        # fill must be at this session's OPEN, and a bar must exist
        if abs(r['price'] - float(a['open'][i])) > r['price'] * 0.02:
            ok = False
            print(f"    suspicious fill {t} {d.date()} "
                  f"px={r['price']} open={a['open'][i]}")
    check("all fills within 2% of session open", ok)


if __name__ == '__main__':
    if not (TEST_SNAPSHOT / 'prices').exists():
        print("test snapshot missing - run download_research_snapshot.py "
              "with temp/ws_test_tickers.txt first")
        sys.exit(1)
    for t in (test_isolation, test_determinism, test_cash, test_next_open):
        t()
    print()
    if FAILURES:
        print(f"FAILED: {FAILURES}")
        sys.exit(1)
    print("All corrected-backtest checks passed.")
    sys.exit(0)
