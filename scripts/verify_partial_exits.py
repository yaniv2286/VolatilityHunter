#!/usr/bin/env python3
"""
verify_partial_exits.py
=======================
Verify the v8.5 partial-exit + breakeven-stop mechanics:

  Engine (strategy_engine.check_exits, version='v8.5'):
    1. ema_3 < ema_8 on a non-partial position  -> partial exit dict, fraction 0.5
    2. Overbought rollover (k>80, k<d), no partial -> partial exit, fraction 0.5
    3. Same rollover with partial_taken -> full exit, fraction 1.0
    4. Price <= breakeven_stop after partial -> full exit (Breakeven stop)
    5. partial_taken + close < ema_8 -> full exit (Final exit)
    6. v8.1 parity: same inputs -> plain exit dicts, no fraction field

  Executor (daily_trading_loop.execute_exits with stub IBKR):
    7. fraction=0.5 exit -> shares halved, partial_taken=True,
       breakeven_stop=entry_price, cash credited for half, position kept
    8. fraction=1.0 exit -> position removed, full proceeds credited

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
from src.strategy_engine import check_exits
from src.strategy_v7_2 import add_indicators_v7_2

failures = []


def check(name, ok, detail=''):
    status = 'OK' if ok else 'FAIL'
    print(f"[{status}] {name}: {detail}")
    if not ok:
        failures.append(name)


def make_df():
    """300-bar uptrend; indicator values get mutated per-scenario after prep."""
    n = 300
    closes = np.linspace(50.0, 120.0, n)
    return pd.DataFrame({
        'open': closes, 'high': closes * 1.01, 'low': closes * 0.99,
        'close': closes, 'volume': [2_000_000] * n,
    })


def prepared_df(**mut):
    df = add_indicators_v7_2(make_df())
    for col, val in mut.items():
        df[col] = val
    return df


def portfolio(pos_kwargs):
    pos = {'shares': 100, 'entry_price': 100.0, 'entry_date': '2026-10-01',
           'highest_price': 100.0, 'is_power_stock': False}
    pos.update(pos_kwargs)
    return {'cash': 50000.0, 'positions': {'TEST': pos},
            'total_value': 60000.0, 'high_water_mark': 60000.0}


def run(pos_kwargs, price, version='v8.5', **mut):
    df = prepared_df(**mut)
    port = portfolio(pos_kwargs)
    return check_exits(port, {'TEST': price}, lambda t: df,
                     version=version, today='2026-10-19')


# Neutral indicator state: no ATR stop (price=entry), no OB, no SMA200 break
NEUTRAL = dict(stoch_k=50.0, stoch_d=50.0, sma_200=50.0, sma_25=50.0, atr=1.0)

print("=" * 70)
print("V8.5 PARTIAL-EXIT VERIFICATION")
print("=" * 70)

# 1. ema_3 < ema_8 -> partial 0.5
ex = run({}, 100.0, **NEUTRAL, ema_3=1.0, ema_8=2.0)
check("ema_3<ema_8 -> partial 0.5",
      len(ex) == 1 and ex[0].get('fraction') == 0.5
      and 'Partial' in ex[0].get('reason', ''),
      f"exits={ex}")

# 2. Overbought rollover -> partial 0.5
ex = run({}, 100.0, **{**NEUTRAL, 'stoch_k': 85.0, 'stoch_d': 90.0}, ema_3=5.0, ema_8=4.0)
check("OB rollover -> partial 0.5",
      len(ex) == 1 and ex[0].get('fraction') == 0.5
      and 'overbought' in ex[0].get('reason', '').lower(),
      f"exits={ex}")

# 3. Same rollover with partial already taken -> full 1.0
ex = run({'partial_taken': True, 'breakeven_stop': 100.0}, 105.0,
         **{**NEUTRAL, 'stoch_k': 85.0, 'stoch_d': 90.0}, ema_3=5.0, ema_8=4.0)
check("2nd rollover after partial -> full 1.0",
      len(ex) == 1 and ex[0].get('fraction') == 1.0
      and 'final' in ex[0].get('reason', '').lower(),
      f"exits={ex}")

# 4. Price <= breakeven_stop -> full Breakeven stop
# (recent entry_date so TIME_STOP backstop doesn't fire first)
ex = run({'partial_taken': True, 'breakeven_stop': 100.0,
          'entry_date': '2026-10-16'}, 99.0,
         **NEUTRAL, ema_3=5.0, ema_8=4.0)
check("price<=breakeven -> Breakeven stop 1.0",
      len(ex) == 1 and ex[0].get('fraction') == 1.0
      and 'Breakeven' in ex[0].get('reason', ''),
      f"exits={ex}")

# 5. partial_taken + close < ema_8 -> Final exit 1.0
ex = run({'partial_taken': True, 'breakeven_stop': 100.0}, 102.0,
         **NEUTRAL, ema_3=105.0, ema_8=103.0)
check("partial + close<ema_8 -> Final exit 1.0",
      len(ex) == 1 and ex[0].get('fraction') == 1.0
      and 'ema_8' in ex[0].get('reason', ''),
      f"exits={ex}")

# 6. v8.1 parity: same inputs, v8.1 -> no exit (no rollover/ema logic at k=50)
ex81 = run({}, 100.0, version='v8.1', **NEUTRAL, ema_3=1.0, ema_8=2.0)
check("v8.1 ignores ema cross (no exit)", len(ex81) == 0, f"exits={ex81}")
ex81 = run({}, 100.0, version='v8.1',
           **{**NEUTRAL, 'stoch_k': 85.0, 'stoch_d': 90.0})
check("v8.1 OB rollover -> full exit, no fraction key",
      len(ex81) == 1 and 'fraction' not in ex81[0], f"exits={ex81}")

# 7-8. Executor fraction handling (stub IBKR)
print()
print("Executor: daily_trading_loop.execute_exits with stub IBKR")
try:
    from scripts.daily_trading_loop import execute_exits

    class StubIBKR:
        def place_market_order(self, ticker, shares, side, ref_px):
            return {'success': True, 'filled_avg_price': ref_px,
                    'shares': shares, 'side': side}

    # 7. partial: 100sh, fraction 0.5 at price 110 (entry 100)
    port = {'cash': 50000.0,
            'positions': {'TEST': {'shares': 100, 'entry_price': 100.0,
                                   'entry_date': '2026-10-01'}},
            'trade_history': []}
    executed = execute_exits([{'ticker': 'TEST', 'price': 110.0,
                               'reason': 'Partial: test', 'fraction': 0.5}],
                             port, StubIBKR())
    pos = port['positions'].get('TEST', {})
    ok = (len(executed) == 1 and pos.get('shares') == 50
          and pos.get('partial_taken') is True
          and pos.get('breakeven_stop') == 100.0
          and pos.get('initial_shares') == 100
          and abs(port['cash'] - (50000.0 + 50 * 110.0)) < 0.01)
    check("partial exec: shares halved, be_stop=entry, cash+=half proceeds", ok,
          f"shares={pos.get('shares')} be={pos.get('breakeven_stop')} cash={port['cash']:.2f}")

    # 8. full: remaining 50sh, fraction 1.0 at price 95
    executed = execute_exits([{'ticker': 'TEST', 'price': 95.0,
                               'reason': 'Breakeven stop', 'fraction': 1.0}],
                             port, StubIBKR())
    ok = ('TEST' not in port['positions'] and len(executed) == 1
          and abs(port['cash'] - (55500.0 + 50 * 95.0)) < 0.01)
    check("full exec: position removed, full proceeds credited", ok,
          f"cash={port['cash']:.2f} positions={list(port['positions'])}")

except Exception as e:
    import traceback
    check("execute_exits import/run", False, f"{e}\n{traceback.format_exc()}")

print()
print("=" * 70)
if failures:
    print(f"RESULT: FAIL ({len(failures)} checks failed)")
    sys.exit(1)
print("RESULT: ALL PARTIAL-EXIT CHECKS PASSED")
sys.exit(0)
