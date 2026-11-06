#!/usr/bin/env python3
"""
verify_scan_candidates.py
=========================
Verify that after the parquet repair + data loader fix, the scan
now produces candidates. Exit code 0 = candidates found, 1 = still 0.
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
from src.strategy_engine import scan_universe, DEFAULT_VERSION, get_spy_regime
from src.strategy_v7_2 import add_indicators_v7_2

DATA_DIR = ROOT / 'data'
SPY_PATH = DATA_DIR / 'SPY.parquet'

# ── Load tickers ──────────────────────────────────────────────────────────────
with open(ROOT / 'tickers.txt') as f:
    all_tickers = [t.strip() for t in f if t.strip()]

print(f"Tickers loaded: {len(all_tickers)}")

# ── Load fn using parquet-only (post-fix behaviour) ───────────────────────────
def load_fn(ticker):
    p = DATA_DIR / f"{ticker.lower()}.parquet"
    if not p.exists():
        return None
    try:
        df = pd.read_parquet(p)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)
        if len(df) < 300:
            return None
        return add_indicators_v7_2(df)
    except Exception:
        return None

# ── Build price dict from parquets ────────────────────────────────────────────
prices = {}
for ticker in all_tickers:
    p = DATA_DIR / f"{ticker.lower()}.parquet"
    if p.exists():
        try:
            df = pd.read_parquet(p)
            if 'date' in df.columns:
                df = df.set_index(pd.to_datetime(df['date']))
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            prices[ticker] = float(df[close_col].iloc[-1])
        except Exception:
            pass

print(f"Prices available: {len(prices)}")

# ── SPY regime ────────────────────────────────────────────────────────────────
is_bull = get_spy_regime(str(SPY_PATH))
print(f"SPY regime: {'BULL' if is_bull else 'BEAR'}")

# ── Quick filter-level audit (sample 200 tickers) ─────────────────────────────
import random
random.seed(1)
sample = random.sample([t for t in all_tickers if (DATA_DIR / f"{t.lower()}.parquet").exists()], 200)
pass_all = fail_data = fail_stoch = fail_sma = fail_vol = fail_cagr = fail_mom = 0
for t in sample:
    df = load_fn(t)
    if df is None:
        fail_data += 1
        continue
    last = df.iloc[-1]
    k      = last.get('stoch_k',    float('nan'))
    sma200 = last.get('sma_200',    float('nan'))
    vsma   = last.get('volume_sma', float('nan'))
    vol    = last.get('volume',     float('nan'))
    close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
    price = float(last[close_col]) if close_col in last.index else float('nan')
    if any(np.isnan(v) for v in [k, sma200, vsma, vol, price]):
        fail_data += 1
        continue
    if len(df) < 253:
        fail_data += 1
        continue
    p252 = df[close_col].iloc[-253]
    annual_ret = (df[close_col].iloc[-1] / p252 - 1) if p252 > 0 else float('nan')
    if np.isnan(annual_ret):
        fail_data += 1
        continue
    p20   = df[close_col].iloc[-21] if len(df) >= 21 else float('nan')
    mom20 = (df[close_col].iloc[-1] / p20 - 1) if p20 > 0 else float('nan')

    if not (32 <= k <= 80):    fail_stoch += 1
    elif price <= sma200:      fail_sma   += 1
    elif vol < vsma * 1.5:     fail_vol   += 1
    elif annual_ret < 0.15:    fail_cagr  += 1
    elif np.isnan(mom20) or mom20 < 0.02: fail_mom += 1
    else:                      pass_all   += 1

print()
print(f"Filter audit (200-ticker sample):")
print(f"  PASS all      : {pass_all}")
print(f"  FAIL data/NaN : {fail_data}")
print(f"  FAIL stoch    : {fail_stoch}")
print(f"  FAIL SMA200   : {fail_sma}")
print(f"  FAIL vol surge: {fail_vol}")
print(f"  FAIL CAGR<15% : {fail_cagr}")
print(f"  FAIL mom<2%   : {fail_mom}")

# ── Full scan ─────────────────────────────────────────────────────────────────
print()
print("Running full scan_universe()...")
candidates = scan_universe(all_tickers, set(), prices, load_fn, version=DEFAULT_VERSION)

print()
print(f"CANDIDATES FOUND: {len(candidates)}")
for c in candidates[:15]:
    print(f"  {c['ticker']:6s}  score={c['score']:.3f}  K={c['stoch_k']:.1f}  "
          f"1yr={c['annual_return']:.1%}  | {c['reason']}")

print()
if len(candidates) == 0:
    print("FAIL: Still 0 candidates - further investigation needed")
    sys.exit(1)
else:
    print(f"PASS: {len(candidates)} candidates generated - scan is functional")
    sys.exit(0)
