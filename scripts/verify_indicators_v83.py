#!/usr/bin/env python3
"""
verify_indicators_v83.py
========================
Verify the new v8.3+ shared indicators added to add_indicators_v7_2():
  ema_3, ema_8, sma_20, rsi_8, adx_14, plus_di_14, minus_di_14

Checks on 3 sample parquets (AAPL, MSFT, SPY):
  - All new columns exist
  - No NaNs after ~60-row warmup
  - RSI within [0, 100], ADX >= 0
  - RSI cross-checked against a hand-computed Wilder RSI on synthetic data

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
from src.strategy_v7_2 import add_indicators_v7_2, calculate_rsi_v7_2

DATA_DIR = ROOT / 'data'
NEW_COLS = ['ema_3', 'ema_8', 'sma_20', 'rsi_8', 'adx_14', 'plus_di_14', 'minus_di_14']
WARMUP = 60

failures = []


def check(name, ok, detail=''):
    status = 'OK' if ok else 'FAIL'
    print(f"[{status}] {name}: {detail}")
    if not ok:
        failures.append(name)


def load_parquet(ticker):
    p = DATA_DIR / f"{ticker.lower()}.parquet"
    if not p.exists():
        return None
    df = pd.read_parquet(p)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    return df


print("=" * 70)
print("INDICATOR VERIFICATION (v8.3 infrastructure)")
print("=" * 70)

# ── Part 1: real parquets ────────────────────────────────────────────────────
for ticker in ['AAPL', 'MSFT', 'SPY']:
    raw = load_parquet(ticker)
    if raw is None:
        check(f"{ticker} parquet loads", False, "file missing")
        continue
    check(f"{ticker} parquet loads", True, f"{len(raw)} rows")

    df = add_indicators_v7_2(raw)
    missing = [c for c in NEW_COLS if c not in df.columns]
    check(f"{ticker} new columns exist", not missing, f"missing={missing}")
    if missing:
        continue

    tail = df.iloc[WARMUP:]
    nan_counts = {c: int(tail[c].isna().sum()) for c in NEW_COLS}
    bad_nan = {c: n for c, n in nan_counts.items() if n > 0}
    check(f"{ticker} no NaNs after warmup({WARMUP})", not bad_nan, f"nan_counts={nan_counts}")

    rsi = tail['rsi_8']
    rsi_ok = bool(((rsi >= 0) & (rsi <= 100)).all())
    check(f"{ticker} rsi_8 in [0,100]", rsi_ok,
          f"min={rsi.min():.2f} max={rsi.max():.2f}")

    adx = tail['adx_14']
    check(f"{ticker} adx_14 >= 0", bool((adx >= 0).all()),
          f"min={adx.min():.2f} max={adx.max():.2f}")

    di_ok = bool(((tail['plus_di_14'] >= 0) & (tail['minus_di_14'] >= 0)).all())
    check(f"{ticker} plus/minus DI >= 0", di_ok,
          f"+DI last={tail['plus_di_14'].iloc[-1]:.2f} -DI last={tail['minus_di_14'].iloc[-1]:.2f}")

    # Sanity: EMA3 should track close more tightly than EMA8 on average
    close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
    d3 = (tail[close_col] - tail['ema_3']).abs().mean()
    d8 = (tail[close_col] - tail['ema_8']).abs().mean()
    check(f"{ticker} ema_3 tracks close tighter than ema_8", bool(d3 < d8),
          f"mean|px-ema3|={d3:.3f} vs mean|px-ema8|={d8:.3f}")

# ── Part 2: hand-computed RSI cross-check on synthetic series ────────────────
print()
print("RSI cross-check vs hand-computed Wilder RSI (8-period)")

np.random.seed(7)
n = 40
synthetic_close = 100 + np.cumsum(np.random.randn(n) * 2)
syn = pd.DataFrame({
    'open': synthetic_close,
    'high': synthetic_close + 1,
    'low': synthetic_close - 1,
    'close': synthetic_close,
    'volume': [1_000_000] * n,
})

# Hand computation: Wilder recursion (rma convention, same as pandas ewm alpha=1/n)
period = 8
deltas = np.diff(synthetic_close)
gains = np.where(deltas > 0, deltas, 0.0)
losses = np.where(deltas < 0, -deltas, 0.0)
alpha = 1.0 / period
avg_gain = gains[0]
avg_loss = losses[0]
expected_last = None
for i in range(1, len(deltas)):
    avg_gain = alpha * gains[i] + (1 - alpha) * avg_gain
    avg_loss = alpha * losses[i] + (1 - alpha) * avg_loss
    if avg_loss == 0:
        expected_last = 100.0 if avg_gain > 0 else 50.0
    else:
        rs = avg_gain / avg_loss
        expected_last = 100.0 - 100.0 / (1.0 + rs)

got = calculate_rsi_v7_2(syn, period).iloc[-1]
diff = abs(got - expected_last)
check("rsi_8 matches hand-computed Wilder RSI", diff < 0.01,
      f"expected={expected_last:.4f} got={got:.4f} diff={diff:.6f}")

# EMA correctness: pandas ewm on same synthetic series
from src.strategy_v7_2 import calculate_ema_v7_2
ema_got = calculate_ema_v7_2(syn, 8).iloc[-1]
ema_exp = syn['close'].ewm(span=8, adjust=False).mean().iloc[-1]
check("ema_8 matches pandas ewm", abs(ema_got - ema_exp) < 1e-9,
      f"expected={ema_exp:.6f} got={ema_got:.6f}")

# ── Part 3: v8.1 untouched columns still present ─────────────────────────────
df = add_indicators_v7_2(load_parquet('AAPL'))
legacy = ['stoch_k', 'stoch_d', 'sma_25', 'sma_50', 'sma_100', 'sma_200',
          'volume_sma', 'atr']
missing_legacy = [c for c in legacy if c not in df.columns]
check("legacy v8.1 indicator columns intact", not missing_legacy,
      f"missing={missing_legacy}")

print()
print("=" * 70)
if failures:
    print(f"RESULT: FAIL ({len(failures)} checks failed)")
    sys.exit(1)
print("RESULT: ALL INDICATOR CHECKS PASSED")
sys.exit(0)
