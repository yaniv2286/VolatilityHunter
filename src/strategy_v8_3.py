"""
strategy_v8_3.py
================
VolatilityHunter v8.3 — v8.1 + trend-quality entry filters.
All changes vs v8.1 (param-gated mirrors of strategy_engine.scan_universe):
  1. ADX filter: require adx_14 >= ADX_MIN (sideways regime rejection)
  2. SMA200 proximity guard: reject entries within SMA200_PROXIMITY of the 200-SMA
  3. Breakout requirement: close > max(high, BREAKOUT_LOOKBACK) (prior N highs)
  4. Stop-distance cap: initial stop = min(candle_low, ema_8, sma_20);
     reject if stop is more than MAX_STOP_PCT below entry

v8.1 baseline (all preserved):
  - ATR/hard stop capped at 8%, overbought exit K>78
  - 20-day momentum filter: +5% min, re-entry allowed
  - Regime filter, sector cap, time stop, vol sizing
"""

import numpy as np
import pandas as pd
from typing import List, Optional
from src.strategy_v7_2 import add_indicators_v7_2

# ── V8.1 Parameters (unchanged) ────────────────────────────────────────────────
HARD_STOP_PCT       = 0.08
OVERBOUGHT_EXIT     = 78.0
STOCH_LOW           = 32.0
STOCH_HIGH          = 80.0
VOLUME_SURGE        = 1.5
CAGR_FILTER         = 0.15
LIQUIDITY_MIN       = 500_000
MOMENTUM_DAYS       = 20
MOMENTUM_MIN        = 0.05
REENTRY             = True

# DD-reduction params
REGIME_MAX_POS      = 3      # max positions when SPY < SMA200
TIME_STOP_DAYS      = 10     # exit losing position after N trading days
SECTOR_MAX          = 3      # max positions per sector
VOL_SIZE_ENABLED    = True   # volatility-adjusted position sizing

# ── V8.3 trend-quality params (match PARAMS['v8.3'] in strategy_engine.py) ─────
ADX_MIN             = 20.0   # sideways filter
SMA200_PROXIMITY    = 0.015  # pause entries within 1.5% of SMA200
BREAKOUT_LOOKBACK   = 20     # close > max(high, 20)
MAX_STOP_PCT        = 0.05   # reject if initial stop >5% below entry


def backtest_ticker_v8_3(ticker: str, df: pd.DataFrame,
                          spy_sma200: Optional[pd.Series] = None,
                          sector: str = 'Unknown',
                          adx_min: Optional[float] = ADX_MIN,
                          sma200_prox: Optional[float] = SMA200_PROXIMITY,
                          breakout_lookback: Optional[int] = BREAKOUT_LOOKBACK,
                          max_stop_pct: Optional[float] = MAX_STOP_PCT,
                          rsi_min: Optional[float] = None) -> List[dict]:
    """
    Single-ticker backtest for v8.3 (v8.1 + trend-quality entry filters).
    Pass None for any filter param to disable it (e.g. v8.3b = adx+prox only).
    spy_sma200: pd.Series indexed by date, True = SPY above SMA200 (bull regime).
    sector: GICS sector string for the ticker.
    Returns list of trade dicts (same schema as v8.1).
    """
    try:
        close_col  = next((c for c in ['adjClose', 'Close', 'close'] if c in df.columns), None)
        volume_col = next((c for c in ['Volume', 'volume', 'adjVolume'] if c in df.columns), None)
        high_col   = next((c for c in ['adjHigh', 'High', 'high'] if c in df.columns), None)
        low_col    = next((c for c in ['adjLow', 'Low', 'low'] if c in df.columns), None)
        if close_col is None or volume_col is None or high_col is None or low_col is None:
            return []

        df = add_indicators_v7_2(df.copy())
        for col in ['stoch_k', 'stoch_d', 'sma_200', 'sma_25', 'sma_50',
                    'sma_100', 'volume_sma', 'atr', 'adx_14', 'ema_8', 'sma_20']:
            if col not in df.columns:
                df[col] = np.nan

        close  = df[close_col].values.astype(float)
        volume = df[volume_col].values.astype(float)
        high   = df[high_col].values.astype(float)
        low    = df[low_col].values.astype(float)
        k      = df['stoch_k'].values.astype(float)
        d      = df['stoch_d'].values.astype(float)
        sma200 = df['sma_200'].values.astype(float)
        sma25  = df['sma_25'].values.astype(float)
        vsma   = df['volume_sma'].values.astype(float)
        atr    = df['atr'].values.astype(float)
        adx    = df['adx_14'].values.astype(float)
        ema8   = df['ema_8'].values.astype(float)
        sma20  = df['sma_20'].values.astype(float)
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

        # ── V8.3 filter masks (each independently disableable via None) ──────
        # 1. ADX trend-strength filter
        adx_ok = (adx >= adx_min) if adx_min is not None else np.ones(n, dtype=bool)

        # 2. SMA200 proximity guard (reject entries hugging the 200-SMA)
        if sma200_prox is not None:
            with np.errstate(divide='ignore', invalid='ignore'):
                sma200_dist = np.abs(close - sma200) / sma200
            sma200_prox_ok = sma200_dist > sma200_prox
        else:
            sma200_prox_ok = np.ones(n, dtype=bool)

        # 3. Breakout: close > max(high) of prior breakout_lookback bars
        if breakout_lookback is not None:
            high_s = pd.Series(high, index=df.index)
            prior_high_max = high_s.rolling(breakout_lookback).max().shift(1).values
            breakout_ok = close > prior_high_max
        else:
            breakout_ok = np.ones(n, dtype=bool)

        # 4. Stop-distance cap: initial stop = min(low, ema_8, sma_20)
        if max_stop_pct is not None:
            initial_stop = np.minimum(np.minimum(low, ema8), sma20)
            with np.errstate(divide='ignore', invalid='ignore'):
                stop_dist = (close - initial_stop) / close
            stop_dist_ok = np.isfinite(stop_dist) & (stop_dist <= max_stop_pct)
        else:
            stop_dist_ok = np.ones(n, dtype=bool)

        # 5. RSI momentum gate (v8.4): rsi_8 >= rsi_min
        rsi = df['rsi_8'].values.astype(float) if 'rsi_8' in df.columns else np.full(n, np.nan)
        rsi_ok = (rsi >= rsi_min) if rsi_min is not None else np.ones(n, dtype=bool)

        # Buy mask (v8.1 base + v8.3 filters)
        buy_mask = (
            (k >= STOCH_LOW) & (k <= STOCH_HIGH) &
            (close > sma200) &
            (volume >= vsma * VOLUME_SURGE) &
            (annual_ret >= CAGR_FILTER) &
            ((close * volume) >= LIQUIDITY_MIN) &
            (momentum_20 >= MOMENTUM_MIN) &
            adx_ok & sma200_prox_ok & breakout_ok & stop_dist_ok & rsi_ok &
            np.isfinite(close) & np.isfinite(k) & np.isfinite(momentum_20)
        )

        # Sell masks (identical to v8.1)
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
                days_held = i - entry_i

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
                    # Volatility-adjusted size multiplier (stored for equity curve use)
                    ap = atr_pct[entry_i]
                    if VOL_SIZE_ENABLED and np.isfinite(ap) and median_atr_pct > 0:
                        vol_scale = min(1.0, median_atr_pct / ap)
                        vol_scale = max(0.25, vol_scale)  # floor at 25%
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
            })

        return trades

    except Exception as e:
        import traceback
        import logging
        logging.getLogger('strategy_v8_3').debug(
            f"backtest_ticker_v8_3 {ticker}: {e}\n{traceback.format_exc()}")
        return []
