#!/usr/bin/env python3
"""
verify_earnings_guard.py
========================
Verify the v8.6 earnings guard (param-gated in strategy_engine):

  scan_universe:
    - ticker reporting within EARNINGS_BLOCK_DAYS (14)  -> rejected
    - ticker reporting beyond the window               -> accepted
    - ticker absent from map / empty map (fail-open)   -> accepted
    - past-dated earnings                              -> accepted
    - v8.1 ignores the map entirely                    -> accepted

  check_exits:
    - position reporting within EARNINGS_FORCE_EXIT_DAYS (1) -> full exit
    - position reporting later                             -> no earnings exit
    - v8.1 ignores the map                                 -> no exit

  src/earnings_calendar.py:
    - days_to_earnings() correctness on a mock map

All earnings maps are mocked inline - this script never hits the network.

Exit code 0 = all checks passed.
"""
import sys
import os
from pathlib import Path
from datetime import date, timedelta

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

import pandas as pd
import numpy as np
from src.strategy_engine import scan_universe, check_exits
from src.strategy_v7_2 import add_indicators_v7_2
from src.earnings_calendar import days_to_earnings

TODAY = date(2026, 10, 19)

failures = []


def check(name, ok, detail=''):
    status = 'OK' if ok else 'FAIL'
    print(f"[{status}] {name}: {detail}")
    if not ok:
        failures.append(name)


def make_base_df():
    """Synthetic uptrend that passes all v8.1 entry filters
    (same construction as verify_v83_filters.py)."""
    n = 300
    closes = [50.0]
    for _ in range(1, n):
        closes.append(closes[-1] * 1.005)
    for j in range(8):
        idx = n - 12 + j
        closes[idx] = closes[idx - 1] * 0.99
    for j in range(4):
        idx = n - 4 + j
        closes[idx] = closes[idx - 1] * 1.02
    closes = np.array(closes)
    if closes[-1] <= closes[-21:-1].max() * 1.01:
        closes[-1] = closes[-21:-1].max() * 1.01 * 1.001
    return pd.DataFrame({
        'open':   closes,
        'high':   closes * 1.01,
        'low':    closes * 0.99,
        'close':  closes,
        'volume': [1_000_000] * (n - 1) + [3_000_000],
    })


def run_scan(version, earnings_map):
    df = make_base_df()
    prepared = add_indicators_v7_2(df)
    price = float(df['close'].iloc[-1])
    return scan_universe(['TEST'], set(), {'TEST': price},
                         lambda t: prepared, version=version,
                         today=TODAY, earnings_map=earnings_map)


def run_exits(version, earnings_map, days_ago=3):
    """Position with no other exit signal active: fresh entry, +5% pnl,
    benign indicators (k<d but below OB, price > sma200)."""
    df = make_base_df()
    prepared = add_indicators_v7_2(df)
    price = float(df['close'].iloc[-1])
    port = {'positions': {'TEST': {
        'entry_price': price / 1.05,
        'entry_date': (TODAY - timedelta(days=days_ago)).isoformat(),
        'shares': 10,
    }}}
    return check_exits(port, {'TEST': price}, lambda t: prepared,
                       version=version, today=TODAY,
                       earnings_map=earnings_map)


def emap(days):
    return {'TEST': (TODAY + timedelta(days=days)).isoformat()}


print("=" * 70)
print("V8.6 EARNINGS GUARD VERIFICATION")
print("=" * 70)

# ── days_to_earnings helper ─────────────────────────────────────────────────
check("days_to_earnings +5d", days_to_earnings('TEST', TODAY, emap(5)) == 5)
check("days_to_earnings absent", days_to_earnings('OTHER', TODAY, emap(5)) is None)
check("days_to_earnings past", days_to_earnings('TEST', TODAY, emap(-1)) == -1)

# ── Entry block ─────────────────────────────────────────────────────────────
c = run_scan('v8.6', emap(5))
check("v8.6 blocks entry 5d before earnings", len(c) == 0, f"cands={len(c)}")

c = run_scan('v8.6', emap(14))
check("v8.6 blocks entry exactly at 14d boundary", len(c) == 0, f"cands={len(c)}")

c = run_scan('v8.6', emap(15))
check("v8.6 allows entry 15d before earnings", len(c) == 1, f"cands={len(c)}")

c = run_scan('v8.6', {'OTHER': (TODAY + timedelta(days=3)).isoformat()})
check("v8.6 allows ticker absent from map", len(c) == 1, f"cands={len(c)}")

c = run_scan('v8.6', {})
check("v8.6 fail-open on empty map", len(c) == 1, f"cands={len(c)}")

c = run_scan('v8.6', emap(-1))
check("v8.6 allows past-dated earnings", len(c) == 1, f"cands={len(c)}")

c = run_scan('v8.1', emap(5))
check("v8.1 ignores earnings map", len(c) == 1, f"cands={len(c)}")

# ── Force exit ──────────────────────────────────────────────────────────────
ex = run_exits('v8.6', emap(1))
check("v8.6 force-exits day before earnings",
      len(ex) == 1 and 'Earnings guard' in ex[0]['reason'],
      f"exits={ex}")

ex = run_exits('v8.6', emap(0))
check("v8.6 force-exits on report day",
      len(ex) == 1 and 'Earnings guard' in ex[0]['reason'], f"exits={ex}")

ex = run_exits('v8.6', emap(3))
check("v8.6 holds position 3d before earnings", len(ex) == 0, f"exits={ex}")

ex = run_exits('v8.6', emap(-2))
check("v8.6 ignores already-reported earnings", len(ex) == 0, f"exits={ex}")

ex = run_exits('v8.6', {})
check("v8.6 exits fail-open on empty map", len(ex) == 0, f"exits={ex}")

ex = run_exits('v8.1', emap(1))
check("v8.1 ignores earnings exit", len(ex) == 0, f"exits={ex}")

print()
print("=" * 70)
if failures:
    print(f"RESULT: FAIL ({len(failures)} checks failed)")
    sys.exit(1)
print("RESULT: ALL EARNINGS-GUARD CHECKS PASSED")
sys.exit(0)
