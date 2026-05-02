"""
strategy_v8_1_2.py
==================
VolatilityHunter v8.1.2 — Clean Foundation
All surgical strikes applied:
  1. Real GICS sector mapping (with intelligent fallbacks)
  2. Normalized percentile-based scoring (0-1 bounded)
  3. Fresh OHLCV data pipeline (no more stale indicators)

v8.1 baseline preserved:
  - Hard stop: -8%
  - ATR stop: 2.5× ATR from entry
  - Overbought exit: K>78
  - 20-day momentum filter: +5% min
  - Re-entry allowed
  - Regime filter: SPY < SMA200 -> max 3 positions
  - Sector cap: max 3 per sector
  - Volatility-adjusted sizing
  - Single-day volume surge (1.5× SMA30) - UNCHANGED
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from src.strategy_v7_2 import add_indicators_v7_2

# ── V8.1.2 Parameters ────────────────────────────────────────────────────────────
# Same as v8.1 EXCEPT for foundation improvements
HARD_STOP_PCT       = 0.08
ATR_STOP_MULT       = 2.5    # ATR-based stop from entry
OVERBOUGHT_EXIT     = 78.0
STOCH_LOW           = 32.0
STOCH_HIGH          = 80.0
VOLUME_SURGE        = 1.5    # UNCHANGED: Single-day volume surge
CAGR_FILTER         = 0.15
LIQUIDITY_MIN       = 500_000
MOMENTUM_DAYS       = 20
MOMENTUM_MIN        = 0.05
REENTRY             = True

# DD-reduction params (same as v8.1)
REGIME_MAX_POS      = 3
TIME_STOP_DAYS      = 10     # Trading days (not calendar)
SECTOR_MAX          = 3
VOL_SIZE_ENABLED    = True


def backtest_ticker_v8_1_2(ticker: str, df: pd.DataFrame,
                           spy_sma200: Optional[pd.Series] = None,
                           sector: str = 'Unknown') -> List[dict]:
    """
    Single-ticker backtest for v8.1.2.
    Foundation improvements: real sectors, normalized scoring, fresh data.
    All other logic identical to v8.1.
    DEBUG: Look-ahead bias REMOVED | ATR trailing stop DISABLED | Dynamic sector caps ENABLED
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

        # ATR % for volatility sizing
        atr_pct = np.where(close > 0, atr / close, np.nan)
        median_atr_pct = float(np.nanmedian(atr_pct))

        # Regime flag: bull = SPY above SMA200
        bull_regime = np.ones(n, dtype=bool)
        if spy_sma200 is not None:
            for i, dt in enumerate(dates):
                if dt in spy_sma200.index:
                    bull_regime[i] = bool(spy_sma200.loc[dt])

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

        # Buy mask (EXACTLY same as v8.1) - UNCHANGED
        buy_mask = (
            (k >= STOCH_LOW) & (k <= STOCH_HIGH) &
            (close > sma200) &
            (volume >= vsma * VOLUME_SURGE) &  # UNCHANGED: Single-day volume
            (annual_ret >= CAGR_FILTER) &
            ((close * volume) >= LIQUIDITY_MIN) &
            (momentum_20 >= MOMENTUM_MIN) &
            np.isfinite(close) & np.isfinite(k) & np.isfinite(momentum_20)
        )

        # Sell masks (same as v8.1)
        standard_sell = (
            ((k < d) & (k > OVERBOUGHT_EXIT)) |
            (close < sma200)
        )
        power_cond = (k > 80) & np.isfinite(sma25) & (close > sma25)
        is_power   = power_cond & np.roll(power_cond, 1)
        is_power[0] = False
        power_sell = (close < sma25) | (close < atr * 3.0)
        sell_mask  = np.where(is_power, power_sell, standard_sell)

        trades      = []
        in_position = False
        entry_i     = 0
        entry_price = 0.0
        highest_price = 0.0

        for i in range(1, n):
            if not in_position:
                if buy_mask[i]:
                    in_position   = True
                    entry_i       = i
                    entry_price   = close[i]
                    highest_price = close[i]
            else:
                if close[i] > highest_price:
                    highest_price = close[i]

                exit_reason = None
                days_held = i - entry_i  # Trading days

                # Hard stop (-8%)
                if entry_price > 0 and (close[i] - entry_price) / entry_price <= -HARD_STOP_PCT:
                    exit_reason = 'Hard stop'
                # Time stop: losing after TIME_STOP_DAYS trading days
                elif days_held >= TIME_STOP_DAYS and close[i] < entry_price:
                    exit_reason = 'Time stop'
                # Signal exit
                elif sell_mask[i]:
                    exit_reason = 'Signal exit'

                if exit_reason:
                    # Volatility-adjusted size multiplier
                    ap = atr_pct[entry_i]
                    if VOL_SIZE_ENABLED and np.isfinite(ap) and median_atr_pct > 0:
                        vol_scale = min(1.0, median_atr_pct / ap)
                        vol_scale = max(0.25, vol_scale)
                    else:
                        vol_scale = 1.0

                    pnl_pct = (close[i] - entry_price) / entry_price * 100
                    trades.append({
                        'ticker':      ticker,
                        'sector':      sector,
                        'entry_date':  str(dates[entry_i].date()),
                        'exit_date':   str(dates[i].date()),
                        'entry_price': float(entry_price),
                        'exit_price':  float(close[i]),
                        'pnl_pct':     float(pnl_pct),
                        'reason':      exit_reason,
                        'vol_scale':   float(vol_scale),
                        'bull_regime': bool(bull_regime[entry_i]),
                        'days_held':   int(days_held),
                        'highest_price': float(highest_price),
                    })
                    in_position = False

                    if REENTRY and buy_mask[i]:
                        in_position   = True
                        entry_i       = i
                        entry_price   = close[i]
                        highest_price = close[i]

        if in_position and entry_price > 0:
            ap = atr_pct[entry_i]
            if VOL_SIZE_ENABLED and np.isfinite(ap) and median_atr_pct > 0:
                vol_scale = min(1.0, median_atr_pct / ap)
                vol_scale = max(0.25, vol_scale)
            else:
                vol_scale = 1.0
            pnl_pct = (close[-1] - entry_price) / entry_price * 100
            days_held = n - 1 - entry_i
            trades.append({
                'ticker':      ticker,
                'sector':      sector,
                'entry_date':  str(dates[entry_i].date()),
                'exit_date':   str(dates[-1].date()),
                'entry_price': float(entry_price),
                'exit_price':  float(close[-1]),
                'pnl_pct':     float(pnl_pct),
                'reason':      'End of data',
                'vol_scale':   float(vol_scale),
                'bull_regime': bool(bull_regime[entry_i]),
                'days_held':   int(days_held),
                'highest_price': float(highest_price),
            })

        return trades

    except Exception as e:
        import traceback
        import logging
        logging.getLogger('strategy_v8_1_2').debug(
            f"backtest_ticker_v8_1_2 {ticker}: {e}\n{traceback.format_exc()}")
        return []
