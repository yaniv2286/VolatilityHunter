"""
strategy_v8.py
==============
VolatilityHunter v8 — optimized strategy for backtest comparison.
All changes vs v7.2:
  1. Hard stop: -5% -> -8%       (reduce whipsaw stops on normal volatility)
  2. Overbought exit: K>70 -> K>78  (let winners run longer in strong trends)
  3. 20-day momentum filter: +5% min (only enter accelerating stocks)
  4. Re-entry allowed: stock exited today can re-qualify same day

Used ONLY by the comparison backtest (full_universe_backtest_v8.py).
Production stays on v7.2 until backtest numbers confirm improvement.
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from src.strategy_v7_2 import add_indicators_v7_2

# ── V8 Parameters ─────────────────────────────────────────────────────────────
HARD_STOP_PCT    = 0.08    # was 0.05
OVERBOUGHT_EXIT  = 78.0   # was 70.0
STOCH_LOW        = 32.0
STOCH_HIGH       = 80.0
VOLUME_SURGE     = 1.5
CAGR_FILTER      = 0.15
LIQUIDITY_MIN    = 500_000
MOMENTUM_DAYS    = 20
MOMENTUM_MIN     = 0.05   # +5% over 20 days required
REENTRY          = True   # allow re-entry on same ticker after exit


def backtest_ticker_v8(ticker: str, df: pd.DataFrame) -> List[dict]:
    """
    Fully vectorized single-ticker backtest for v8.
    Same structure as v7.2 backtest but with v8 parameters + momentum filter + re-entry.
    Returns list of trade dicts.
    """
    try:
        close_col  = next((c for c in ['adjClose', 'Close', 'close'] if c in df.columns), None)
        volume_col = next((c for c in ['Volume', 'volume', 'adjVolume'] if c in df.columns), None)
        if close_col is None or volume_col is None:
            return []

        df = add_indicators_v7_2(df.copy())
        for col in ['stoch_k', 'stoch_d', 'sma_200', 'sma_25', 'sma_50',
                    'sma_100', 'volume_sma', 'atr']:
            if col not in df.columns:
                df[col] = np.nan

        close  = df[close_col].values.astype(float)
        volume = df[volume_col].values.astype(float)
        k      = df['stoch_k'].values.astype(float)
        d      = df['stoch_d'].values.astype(float)
        sma200 = df['sma_200'].values.astype(float)
        sma25  = df['sma_25'].values.astype(float)
        vsma   = df['volume_sma'].values.astype(float)
        atr    = df['atr'].values.astype(float)
        dates  = df.index
        n      = len(close)

        if n < 300:
            return []

        # 252-day annual return
        annual_ret = np.full(n, np.nan)
        for i in range(252, n):
            if close[i - 252] > 0:
                annual_ret[i] = (close[i] / close[i - 252]) - 1

        # 20-day momentum
        momentum_20 = np.full(n, np.nan)
        for i in range(MOMENTUM_DAYS, n):
            if close[i - MOMENTUM_DAYS] > 0:
                momentum_20[i] = (close[i] / close[i - MOMENTUM_DAYS]) - 1

        # Buy mask: all v7 conditions + 20-day momentum filter
        buy_mask = (
            (k >= STOCH_LOW) & (k <= STOCH_HIGH) &
            (close > sma200) &
            (volume >= vsma * VOLUME_SURGE) &
            (annual_ret >= CAGR_FILTER) &
            ((close * volume) >= LIQUIDITY_MIN) &
            (momentum_20 >= MOMENTUM_MIN) &
            np.isfinite(close) & np.isfinite(k) & np.isfinite(momentum_20)
        )

        # Sell masks
        standard_sell = (
            ((k < d) & (k > OVERBOUGHT_EXIT)) |   # v8: 78 instead of 70
            (close < sma200)
        )

        power_cond = (k > 80) & np.isfinite(sma25) & (close > sma25)
        is_power   = power_cond & np.roll(power_cond, 1)
        is_power[0] = False

        power_sell = (close < sma25) | (close < atr * 3.0)
        sell_mask  = np.where(is_power, power_sell, standard_sell)

        # State machine with re-entry support
        trades       = []
        in_position  = False
        entry_i      = 0
        entry_price  = 0.0
        highest_price = 0.0

        for i in range(1, n):
            if not in_position:
                if buy_mask[i]:
                    in_position   = True
                    entry_i       = i
                    entry_price   = close[i]
                    highest_price = close[i]
            else:
                # Track highest price for ATR trailing stop
                if close[i] > highest_price:
                    highest_price = close[i]

                exit_reason = None

                # Hard stop (v8: -8%)
                if entry_price > 0 and (close[i] - entry_price) / entry_price <= -HARD_STOP_PCT:
                    exit_reason = 'Hard stop'
                elif sell_mask[i]:
                    exit_reason = 'Signal exit'

                if exit_reason:
                    pnl_pct = (close[i] - entry_price) / entry_price * 100
                    trades.append({
                        'ticker':      ticker,
                        'entry_date':  str(dates[entry_i].date()),
                        'exit_date':   str(dates[i].date()),
                        'entry_price': float(entry_price),
                        'exit_price':  float(close[i]),
                        'pnl_pct':     float(pnl_pct),
                        'reason':      exit_reason,
                    })
                    in_position = False

                    # Re-entry: immediately check if buy condition holds on same bar
                    if REENTRY and buy_mask[i]:
                        in_position   = True
                        entry_i       = i
                        entry_price   = close[i]
                        highest_price = close[i]

        # Close open position at last price
        if in_position and entry_price > 0:
            pnl_pct = (close[-1] - entry_price) / entry_price * 100
            trades.append({
                'ticker':      ticker,
                'entry_date':  str(dates[entry_i].date()),
                'exit_date':   str(dates[-1].date()),
                'entry_price': float(entry_price),
                'exit_price':  float(close[-1]),
                'pnl_pct':     float(pnl_pct),
                'reason':      'End of data',
            })

        return trades

    except Exception as e:
        import traceback
        import logging
        logging.getLogger('strategy_v8').debug(
            f"backtest_ticker_v8 {ticker}: {e}\n{traceback.format_exc()}")
        return []
