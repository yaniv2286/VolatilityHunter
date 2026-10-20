#!/usr/bin/env python3
"""
verify_v83_filters.py
=====================
Verify each v8.3 trend-quality filter fires correctly in scan_universe():
  - ADX_MIN:        low-ADX setup rejected
  - SMA200_PROXIMITY: entry hugging the 200-SMA rejected
  - BREAKOUT_LOOKBACK: no 20-day breakout rejected
  - MAX_STOP_PCT:   stop legs >5% below entry rejected
  - valid setup accepted under v8.3
  - v8.1 remains unaffected (same setup still accepted)

Uses a synthetic 300-bar uptrend with a dip-then-breakout final bar,
tuned so the base case passes ALL v8.1 + v8.3 filters.

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
from src.strategy_engine import scan_universe
from src.strategy_v7_2 import add_indicators_v7_2

failures = []


def check(name, ok, detail=''):
    status = 'OK' if ok else 'FAIL'
    print(f"[{status}] {name}: {detail}")
    if not ok:
        failures.append(name)


def make_base_df():
    """Synthetic uptrend + 8-day dip + 4-day rally ending at a new 20d high.
    Passes every v8.1 filter and every v8.3 filter (verified numerically)."""
    n = 300
    g, dip_days, dip_pct, rally_pct = 0.005, 8, 0.01, 0.02
    closes = [50.0]
    for _ in range(1, n):
        closes.append(closes[-1] * (1 + g))
    for j in range(dip_days):
        idx = n - dip_days - 4 + j
        closes[idx] = closes[idx - 1] * (1 - dip_pct)
    for j in range(4):
        idx = n - 4 + j
        closes[idx] = closes[idx - 1] * (1 + rally_pct)
    closes = np.array(closes)
    prior_max = closes[-21:-1].max() * 1.01
    if closes[-1] <= prior_max:
        closes[-1] = prior_max * 1.001
    return pd.DataFrame({
        'open':   closes,
        'high':   closes * 1.01,
        'low':    closes * 0.99,
        'close':  closes,
        'volume': [1_000_000] * (n - 1) + [3_000_000],
    })


def run_scan(df, version):
    prepared = add_indicators_v7_2(df)
    price = float(df['close'].iloc[-1])
    return scan_universe(['TEST'], set(), {'TEST': price},
                         lambda t: prepared, version=version)


def run_scan_mutated(version, mutate):
    df = make_base_df()
    prepared = add_indicators_v7_2(df)
    mutate(prepared)
    price = float(df['close'].iloc[-1])
    return scan_universe(['TEST'], set(), {'TEST': price},
                         lambda t: prepared, version=version)


print("=" * 70)
print("V8.3 TREND-QUALITY FILTER VERIFICATION")
print("=" * 70)

base = add_indicators_v7_2(make_base_df())
last = base.iloc[-1]
print(f"Base setup: K={last['stoch_k']:.1f} adx={last['adx_14']:.1f} "
      f"close={last['close']:.2f} sma200={last['sma_200']:.2f} "
      f"ema8={last['ema_8']:.2f} sma20={last['sma_20']:.2f}")

# 1. Valid setup accepted under v8.3
cands = run_scan(make_base_df(), 'v8.3')
check("v8.3 accepts valid setup", len(cands) == 1,
      f"candidates={len(cands)}")

# 2. Same setup also accepted under v8.1 (filters inactive there)
cands81 = run_scan(make_base_df(), 'v8.1')
check("v8.1 accepts same setup (filters inactive)", len(cands81) == 1,
      f"candidates={len(cands81)}")

# 3. Low ADX -> rejected under v8.3, still accepted under v8.1
cands = run_scan_mutated('v8.3', lambda d: d.__setitem__('adx_14', 5.0))
check("v8.3 rejects low-ADX setup", len(cands) == 0,
      f"candidates={len(cands)}")
cands81 = run_scan_mutated('v8.1', lambda d: d.__setitem__('adx_14', 5.0))
check("v8.1 ignores ADX", len(cands81) == 1, f"candidates={len(cands81)}")

# 4. Price hugging SMA200 -> rejected under v8.3
def _sma_hug(d):
    d['sma_200'] = float(d['close'].iloc[-1]) * 0.99  # 1% below close < 1.5% prox
cands = run_scan_mutated('v8.3', _sma_hug)
check("v8.3 rejects SMA200-hugging entry", len(cands) == 0,
      f"candidates={len(cands)}")
cands81 = run_scan_mutated('v8.1', _sma_hug)
check("v8.1 ignores SMA200 proximity", len(cands81) == 1,
      f"candidates={len(cands81)}")

# 5. No breakout -> rejected under v8.3
def _no_breakout(d):
    d.loc[d.index[-21:-1], 'high'] = float(d['close'].iloc[-1]) * 2.0
cands = run_scan_mutated('v8.3', _no_breakout)
check("v8.3 rejects non-breakout", len(cands) == 0,
      f"candidates={len(cands)}")
cands81 = run_scan_mutated('v8.1', _no_breakout)
check("v8.1 ignores breakout", len(cands81) == 1, f"candidates={len(cands81)}")

# 6. Stop legs >5% below entry -> rejected under v8.3
def _wide_stop(d):
    d['ema_8'] = float(d['close'].iloc[-1]) * 0.5
    d['sma_20'] = float(d['close'].iloc[-1]) * 0.5
cands = run_scan_mutated('v8.3', _wide_stop)
check("v8.3 rejects stop distance >5%", len(cands) == 0,
      f"candidates={len(cands)}")
cands81 = run_scan_mutated('v8.1', _wide_stop)
check("v8.1 ignores stop distance", len(cands81) == 1,
      f"candidates={len(cands81)}")

# 7. NaN adx -> rejected under v8.3 (no silent pass-through)
cands = run_scan_mutated('v8.3', lambda d: d.__setitem__('adx_14', np.nan))
check("v8.3 rejects NaN ADX", len(cands) == 0, f"candidates={len(cands)}")

print()
print("=" * 70)
if failures:
    print(f"RESULT: FAIL ({len(failures)} checks failed)")
    sys.exit(1)
print("RESULT: ALL V8.3 FILTER CHECKS PASSED")
sys.exit(0)
