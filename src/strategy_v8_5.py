"""
strategy_v8_5.py
================
VolatilityHunter v8.5 — v8.1 entries + partial exit (half-and-half) system.
All changes vs v8.1 (param-gated mirrors of strategy_engine.check_exits):
  1. Partial exit: first exit signal sells PARTIAL_FRACTION (0.5) of shares
     - triggers: stoch_k > 80 AND k < d  OR  ema_3 < ema_8
  2. Breakeven floor: after partial, price <= entry_price -> full exit
  3. Final exit: after partial, close < ema_8 -> full exit on remaining shares
  4. Backstops unchanged: ATR/hard stop, time stop, SMA200 break = full exits

Trade records: a split position emits TWO records sharing 'pos_id', each with
'alloc_frac' = 0.5 (partial leg exits at partial date, runner leg at final date).
Equity curve builder counts slots by unique pos_id.

v8.1 baseline (all preserved):
  - ATR/hard stop capped at 8%, time stop, regime filter, sector cap, vol sizing
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

REGIME_MAX_POS      = 3
TIME_STOP_DAYS      = 10
SECTOR_MAX          = 3
VOL_SIZE_ENABLED    = True

# ── V8.5 partial-exit params (match PARAMS['v8.5'] in strategy_engine.py) ──────
PARTIAL_FRACTION    = 0.5
PARTIAL_STOCK_OB    = 80.0


def backtest_ticker_v8_5(ticker: str, df: pd.DataFrame,
                          spy_sma200: Optional[pd.Series] = None,
                          sector: str = 'Unknown') -> List[dict]:
    """
    Single-ticker backtest for v8.5 (v8.1 + partial exits + breakeven stop).
    Returns list of trade dicts; split positions emit two records sharing pos_id.
    """
    try:
        close_col  = next((c for c in ['adjClose', 'Close', 'close'] if c in df.columns), None)
        volume_col = next((c for c in ['Volume', 'volume', 'adjVolume'] if c in df.columns), None)
        if close_col is None or volume_col is None:
            return []

        df = add_indicators_v7_2(df.copy())
        for col in ['stoch_k', 'stoch_d', 'sma_200', 'sma_25', 'sma_50',
                    'sma_100', 'volume_sma', 'atr', 'ema_3', 'ema_8']:
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
        ema3   = df['ema_3'].values.astype(float)
        ema8   = df['ema_8'].values.astype(float)
        dates  = df.index
        n      = len(close)

        if n < 300:
            return []

        atr_pct = np.where(close > 0, atr / close, np.nan)
        median_atr_pct = float(np.nanmedian(atr_pct))

        bull_regime = np.ones(n, dtype=bool)
        if spy_sma200 is not None:
            for i, dt in enumerate(dates):
                if dt in spy_sma200.index:
                    bull_regime[i] = bool(spy_sma200.loc[dt])

        annual_ret = np.full(n, np.nan)
        for i in range(252, n):
            if close[i - 252] > 0:
                annual_ret[i] = (close[i] / close[i - 252]) - 1

        momentum_20 = np.full(n, np.nan)
        for i in range(MOMENTUM_DAYS, n):
            if close[i - MOMENTUM_DAYS] > 0:
                momentum_20[i] = (close[i] / close[i - MOMENTUM_DAYS]) - 1

        buy_mask = (
            (k >= STOCH_LOW) & (k <= STOCH_HIGH) &
            (close > sma200) &
            (volume >= vsma * VOLUME_SURGE) &
            (annual_ret >= CAGR_FILTER) &
            ((close * volume) >= LIQUIDITY_MIN) &
            (momentum_20 >= MOMENTUM_MIN) &
            np.isfinite(close) & np.isfinite(k) & np.isfinite(momentum_20)
        )

        power_cond = (k > 80) & np.isfinite(sma25) & (close > sma25)
        is_power   = power_cond & np.roll(power_cond, 1)
        is_power[0] = False
        power_sell = (close < sma25) | (close < atr * 3.0)

        def _vol_scale(i_entry):
            ap = atr_pct[i_entry]
            if VOL_SIZE_ENABLED and np.isfinite(ap) and median_atr_pct > 0:
                vs = min(1.0, median_atr_pct / ap)
                return max(0.25, vs)
            return 1.0

        def _rec(exit_i, pnl, reason, alloc_frac, pos_id):
            return {
                'ticker':      ticker,
                'sector':      sector,
                'pos_id':      pos_id,
                'alloc_frac':  alloc_frac,
                'entry_date':  str(dates[entry_i].date()),
                'exit_date':   str(dates[exit_i].date()),
                'entry_price': float(entry_price),
                'exit_price':  float(close[exit_i]),
                'pnl_pct':     float(pnl),
                'reason':      reason,
                'vol_scale':   float(_vol_scale(entry_i)),
                'bull_regime': bool(bull_regime[entry_i]),
            }

        trades        = []
        in_position   = False
        partial_taken = False
        entry_i       = 0
        entry_price   = 0.0
        highest_price = 0.0
        seq           = 0

        for i in range(1, n):
            if not in_position:
                if buy_mask[i]:
                    in_position   = True
                    partial_taken = False
                    entry_i       = i
                    entry_price   = close[i]
                    highest_price = close[i]
                    seq          += 1
                    pos_id        = f"{ticker}#{seq}"
            else:
                if close[i] > highest_price:
                    highest_price = close[i]

                exit_reason   = None
                partial_reason = None
                days_held = i - entry_i

                # ── Backstops (full exits) ───────────────────────────────────
                if entry_price > 0 and (close[i] - entry_price) / entry_price <= -HARD_STOP_PCT:
                    exit_reason = 'Hard stop'
                elif days_held >= TIME_STOP_DAYS and close[i] < entry_price:
                    exit_reason = 'Time stop'
                elif is_power[i]:
                    if power_sell[i]:
                        exit_reason = 'Signal exit (power)'
                else:
                    # ── v8.5 two-phase exit ladder ───────────────────────────
                    if partial_taken and close[i] <= entry_price:
                        exit_reason = 'Breakeven stop'
                    elif (k[i] < d[i]) and (k[i] > PARTIAL_STOCK_OB):
                        if partial_taken:
                            exit_reason = 'Overbought rollover final'
                        else:
                            partial_reason = 'Partial: overbought rollover'
                    elif close[i] < sma200[i]:
                        exit_reason = 'SMA200 break'
                    elif partial_taken:
                        if close[i] < ema8[i]:
                            exit_reason = 'Final: close < ema_8'
                    elif ema3[i] < ema8[i]:
                        partial_reason = 'Partial: ema_3 < ema_8'

                # ── Partial leg: sell fraction, keep runner ──────────────────
                if partial_reason and not exit_reason:
                    pnl = (close[i] - entry_price) / entry_price * 100
                    trades.append(_rec(i, pnl, partial_reason,
                                       PARTIAL_FRACTION, pos_id))
                    partial_taken = True
                    continue

                # ── Full exit ────────────────────────────────────────────────
                if exit_reason:
                    pnl = (close[i] - entry_price) / entry_price * 100
                    frac = PARTIAL_FRACTION if partial_taken else 1.0
                    trades.append(_rec(i, pnl, exit_reason, frac, pos_id))
                    in_position   = False
                    partial_taken = False

                    if REENTRY and buy_mask[i]:
                        in_position   = True
                        partial_taken = False
                        entry_i       = i
                        entry_price   = close[i]
                        highest_price = close[i]
                        seq          += 1
                        pos_id        = f"{ticker}#{seq}"

        if in_position and entry_price > 0:
            pnl = (close[-1] - entry_price) / entry_price * 100
            frac = PARTIAL_FRACTION if partial_taken else 1.0
            trades.append(_rec(n - 1, pnl, 'End of data', frac, pos_id))

        return trades

    except Exception as e:
        import traceback
        import logging
        logging.getLogger('strategy_v8_5').debug(
            f"backtest_ticker_v8_5 {ticker}: {e}\n{traceback.format_exc()}")
        return []
