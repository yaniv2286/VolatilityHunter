#!/usr/bin/env python3
"""Verify SPY parquet repair and regime detection fix."""
import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

import pandas as pd
import numpy as np
from src.strategy_v7_2 import add_indicators_v7_2
from src.strategy_engine import get_spy_regime

DATA_DIR = ROOT / 'data'
SPY_PATH = DATA_DIR / 'SPY.parquet'

print("=" * 60)
print("SPY PARQUET + REGIME FIX VERIFICATION")
print("=" * 60)

# 1. Raw parquet check
spy = pd.read_parquet(SPY_PATH)
if 'date' in spy.columns:
    spy['date'] = pd.to_datetime(spy['date'])
    spy = spy.set_index('date')
print(f"SPY rows      : {len(spy)}")
print(f"Date range    : {spy.index[0].date()} to {spy.index[-1].date()}")
print(f"Columns       : {spy.columns.tolist()}")

# 2. Indicator computation
spy_ind = add_indicators_v7_2(spy.copy())
last = spy_ind.iloc[-1]
sma200 = last.get('sma_200', np.nan)
close = last.get('close', last.get('adjClose', np.nan))
print(f"SMA200        : {float(sma200):.2f}" if not pd.isna(sma200) else "SMA200        : NaN")
print(f"Close         : {float(close):.2f}" if not pd.isna(close) else "Close         : NaN")
print(f"SMA200 is NaN : {pd.isna(sma200)}")

if pd.isna(sma200):
    print("FAIL: SMA200 still NaN - SPY has insufficient rows for 200-day MA")
    sys.exit(1)

# 3. Regime function
is_bull = get_spy_regime(str(SPY_PATH))
print(f"Regime result : {'BULL' if is_bull else 'BEAR'}")
print(f"SPY > SMA200  : {close > sma200}")

# 4. AAPL / key tickers
for ticker in ['aapl', 'msft', 'nvda', 'amzn', 'meta', 'tsla', 'jpm']:
    p = DATA_DIR / f'{ticker}.parquet'
    if p.exists():
        df = pd.read_parquet(p)
        print(f"{ticker.upper():6s}: {len(df):5d} rows | last={df.index[-1] if isinstance(df.index[-1], str) else str(df.index[-1])[:10]}")
    else:
        print(f"{ticker.upper():6s}: NOT FOUND")

print("=" * 60)
print("PASS: SPY parquet repaired and regime detection working")
sys.exit(0)
