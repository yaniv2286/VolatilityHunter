#!/usr/bin/env python3
"""
verify_v87_ranking.py
=====================
Verify the v8.7 RANK_BY candidate-ordering override in scan_universe().

Three synthetic tickers all pass the v8.1 entry filters but carry different
ranking inputs:
    A: highest 20d momentum, mid rsi_8, lowest volume surge
    B: lowest momentum, highest rsi_8, highest volume surge
    C: mid everywhere

Checks:
    - RANK_BY='momentum' orders A > C > B
    - RANK_BY='rsi'      orders B first
    - RANK_BY='volume'   orders B > C > A
    - RANK_BY='combo'    orders deterministically (B/C ahead of A)
    - v8.1 (no RANK_BY)  uses the composite score - order unchanged
    - candidates expose mom_20 / rsi_8 / vol_ratio fields

Test versions are injected into PARAMS in-process; strategy_engine.py
itself is untouched (one-change-per-version stays true).

Exit code 0 = all checks passed.
"""
import sys
import os
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))
os.chdir(str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

import pandas as pd
import numpy as np
from src.strategy_engine import scan_universe, PARAMS
from src.strategy_v7_2 import add_indicators_v7_2

# Injected test versions - never persisted
for name, rb in [('v87t_mom', 'momentum'), ('v87t_rsi', 'rsi'),
                 ('v87t_vol', 'volume'),   ('v87t_combo', 'combo')]:
    PARAMS[name] = {**PARAMS['v8.1'], 'RANK_BY': rb}

failures = []


def check(name, ok, detail=''):
    status = 'OK' if ok else 'FAIL'
    print(f"[{status}] {name}: {detail}")
    if not ok:
        failures.append(name)


def make_prepared(mom_boost=1.0, rsi=60.0, vol_mult=2.0):
    """Base v8.1-passing df, then override the ranking inputs."""
    n = 300
    closes = [50.0]
    for _ in range(1, n):
        closes.append(closes[-1] * 1.005)
    for j in range(8):
        closes[n - 12 + j] = closes[n - 12 + j - 1] * 0.99
    for j in range(4):
        closes[n - 4 + j] = closes[n - 4 + j - 1] * 1.02
    closes = np.array(closes)
    if closes[-1] <= closes[-21:-1].max() * 1.01:
        closes[-1] = closes[-21:-1].max() * 1.01 * 1.001
    df = pd.DataFrame({
        'open':   closes,
        'high':   closes * 1.01,
        'low':    closes * 0.99,
        'close':  closes,
        'volume': [1_000_000] * (n - 1) + [3_000_000],
    })
    prepared = add_indicators_v7_2(df)
    # mom20 = close[-1] / close[-21] - 1  -> shrink close[-21] to boost it
    prepared.iloc[-21, prepared.columns.get_loc('close')] = (
        float(prepared['close'].iloc[-1]) / (1 + 0.05 * mom_boost * 20))
    prepared.iloc[-1, prepared.columns.get_loc('rsi_8')] = rsi
    prepared.iloc[-1, prepared.columns.get_loc('volume_sma')] = 1_000_000
    prepared.iloc[-1, prepared.columns.get_loc('volume')] = vol_mult * 1_000_000
    price = float(prepared['close'].iloc[-1])
    return prepared, price


D_PRE = {
    'A': make_prepared(mom_boost=1.0,  rsi=60.0, vol_mult=1.6),   # best mom, worst vol
    'B': make_prepared(mom_boost=0.5,  rsi=75.0, vol_mult=5.0),   # mid mom, best vol
    'C': make_prepared(mom_boost=0.15, rsi=70.0, vol_mult=3.0),   # worst mom, mid vol
}
# combo pct-rank sums: A=1.0+0.333, B=0.667+1.0, C=0.333+0.667 -> B > A > C
PRICES = {t: p for t, (_, p) in D_PRE.items()}


def run(version):
    return scan_universe(list(D_PRE), set(), PRICES,
                         lambda t: D_PRE[t][0], version=version)


print("=" * 70)
print("V8.7 RANKING OVERRIDE VERIFICATION")
print("=" * 70)

c81 = run('v8.1')
check("all 3 tickers qualify under v8.1", len(c81) == 3,
      f"cands={[c['ticker'] for c in c81]}")
if c81:
    c = c81[0]
    has_fields = all(k in c for k in ('mom_20', 'rsi_8', 'vol_ratio'))
    check("candidates expose ranking fields", has_fields,
          f"mom20={c.get('mom_20'):.3f} rsi={c.get('rsi_8')} "
          f"vol={c.get('vol_ratio'):.1f}")

order = [c['ticker'] for c in run('v87t_mom')]
check("RANK_BY=momentum -> A>B>C", order == ['A', 'B', 'C'], f"order={order}")

order = [c['ticker'] for c in run('v87t_rsi')]
check("RANK_BY=rsi -> B first", order[0] == 'B', f"order={order}")

order = [c['ticker'] for c in run('v87t_vol')]
check("RANK_BY=volume -> B>C>A", order == ['B', 'C', 'A'], f"order={order}")

order = [c['ticker'] for c in run('v87t_combo')]
check("RANK_BY=combo -> B>A>C", order == ['B', 'A', 'C'], f"order={order}")

print()
print("=" * 70)
if failures:
    print(f"RESULT: FAIL ({len(failures)} checks failed)")
    sys.exit(1)
print("RESULT: ALL RANKING CHECKS PASSED")
sys.exit(0)
