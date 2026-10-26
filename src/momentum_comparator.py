"""Medium-term relative-strength momentum comparator.

A deliberately simple, literature-standard benchmark run on the SAME
ledger, execution model and costs as the corrected v8.1 engine. It is a
hypothesis test: does plain 12-1 price momentum beat our custom
stochastic-pullback system on identical data and constraints?

Rules (fixed for the comparator, not part of PARAMS):
  - Eligible: >=274 sessions of history, raw close >= MIN_PRICE,
    close*volume >= MIN_LIQUIDITY, finite inputs.
  - Score: adjClose[p-21] / adjClose[p-273] - 1
    (12-month return skipping the most recent ~1 month).
  - First trading session each month: target = top 10 by score.
    Positions outside the target are queued for exit at next open;
    new names are bought equal-weight (equity / 10) at next open.
    Existing target holdings are not re-weighted.
  - No stops, no power-stock mode, no earnings guard. Forced
    liquidation on untradeable names is inherited from the base class.

This file intentionally does NOT modify strategy_engine: it is a
benchmark hypothesis, not a production strategy version.
"""

import logging
import os
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import CorrectedBacktest
from src.strategy_engine import MIN_PRICE, MIN_LIQUIDITY

logger = logging.getLogger(__name__)

FORMATION = 273      # sessions of history required
SKIP = 21            # skip most recent ~1 month
TOP_N = 10


class MomentumComparator(CorrectedBacktest):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._last_rebal_month = None

    def _scores(self, date):
        """{ticker: momentum score} for eligible names today."""
        ts = pd.Timestamp(date)
        out = {}
        for t in self.data.tickers:
            p = self.data._ptr.get(t)
            dates = self.data._dates.get(t)
            a = self.data._arr.get(t)
            if p is None or dates is None or a is None:
                continue
            if p >= len(dates) or dates[p] != ts or p < FORMATION:
                continue
            close = a['close'][p]
            vol = a['volume'][p]
            if not np.isfinite(close) or not np.isfinite(vol):
                continue
            if close < MIN_PRICE or close * vol < MIN_LIQUIDITY:
                continue
            adj = a['adjClose']
            p_end, p_start = adj[p - SKIP], adj[p - FORMATION]
            if not np.isfinite(p_end) or not np.isfinite(p_start) \
                    or p_start <= 0:
                continue
            out[t] = p_end / p_start - 1.0
        return out

    def _signal_pass(self, date, prices):
        ts = pd.Timestamp(date)
        month_key = (ts.year, ts.month)
        if month_key == self._last_rebal_month:
            return
        self._last_rebal_month = month_key

        scores = self._scores(date)
        if not scores:
            return
        target = set(sorted(scores, key=scores.get, reverse=True)[:TOP_N])
        equity = self.ledger.equity_curve[-1].equity \
            if self.ledger.equity_curve else self.ledger.cash

        # exits first (mirrors live ordering; fills happen next open)
        held = set(self.portfolio['positions'])
        for t in held - target:
            if not any(o['ticker'] == t for o in self.pending_sells):
                self.pending_sells.append({
                    'ticker': t, 'fraction': 1.0,
                    'reason': 'Momentum rebalance: left top-10',
                    'tries': 0})

        self._sync_cash()
        # positions remaining after queued full sells
        surviving = held - {o['ticker'] for o in self.pending_sells
                            if o['fraction'] >= 1.0}
        open_slots = TOP_N - len(surviving)
        committed = 0.0
        for t in sorted(target - held, key=lambda x: -scores[x]):
            if len(self.pending_buys) >= open_slots:
                break
            alloc = equity / TOP_N
            px = prices.get(t)
            if not px or px <= 0:
                continue
            shares = int(alloc / px)
            if shares <= 0:
                continue
            est_cost = shares * px * (1 + self.slip)
            if committed + est_cost > self.ledger.settled_cash:
                continue   # ledger enforces affordability at fill anyway
            committed += est_cost
            self.pending_buys.append({
                'ticker': t, 'price': px, 'shares': shares, 'atr': 0.0,
                'score': scores[t], 'reason': f'12-1 mom={scores[t]:.1%}'})
