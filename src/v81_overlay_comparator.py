"""v8.1 + Freedom-Trader element overlay comparator.

Tests individual FT rule elements ON TOP of the corrected v8.1 engine
(the only profitable base we have measured), via the research hooks in
CorrectedBacktest. Same ledger, fills, costs, and universe as the
integrity_fix baseline.

Registered overlays (enable via --overlays a,b,c):
  breakeven   - FT +2% ratchet: once close >= 1.02*entry, raise
                stop_loss_price to entry price (evaluated on closes).
  cashbuffer  - FT 4-quarters: cumulative buys this pass capped so that
                >=20% of account equity stays in cash.
  retracement - FT 50% limit routing: when the signal bar's range exceeds
                2.5%, queue a limit at low+0.5*range; fill only if the
                next open <= limit (conservative, no intraday path).
  vetoes      - FT anti-chase/anti-knife vetoes on entry candidates:
                flagpole (4 green bars & 4d gain >8%), snapback (close
                >8% above SMA25), trap door (%K<%D gap>6 or %D slope
                <-1.5 while %K<%D) using the engine's stoch arrays.
"""

import logging
import os
import sys

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import CorrectedBacktest

logger = logging.getLogger(__name__)

BREAKEVEN_TRIGGER = 0.02
CASH_BUFFER = 0.20
RETRACE_RANGE = 0.025
FLAGPOLE_RET = 0.08
SNAPBACK_PCT = 0.08
TRAPDOOR_GAP = 6.0
TRAPDOOR_DSLOPE = -1.5


class V81OverlayComparator(CorrectedBacktest):
    VALID_OVERLAYS = {'breakeven', 'cashbuffer', 'retracement', 'vetoes'}

    def __init__(self, *args, overlays=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.overlays = set(overlays or ())
        bad = self.overlays - self.VALID_OVERLAYS
        if bad:
            raise ValueError(f'unknown overlays: {sorted(bad)}')

    def _on(self, name):
        return name in self.overlays

    def _arrays(self, t, date):
        """(ptr, arr-dict) for ticker at exactly date, else (None, None)."""
        p = self.data._ptr.get(t)
        dates = self.data._date_ns.get(t)
        a = self.data._arr.get(t)
        if p is None or dates is None or a is None or p >= len(dates):
            return None, None
        if dates[p] != pd.Timestamp(date).value:
            return None, None
        return p, a

    # ---- hook: breakeven ratchet before exit evaluation ----
    def _hook_pre_exits(self, date, prices):
        if not self._on('breakeven'):
            return
        for t, pos in self.portfolio['positions'].items():
            px = prices.get(t)
            if not px or px <= 0:
                continue
            entry = pos['entry_price']
            if px >= entry * (1 + BREAKEVEN_TRIGGER):
                pos['stop_loss_price'] = max(
                    pos.get('stop_loss_price') or 0.0, entry)

    # ---- hook: extra cash ceiling (20% equity buffer) ----
    def _hook_extra_cash_ceiling(self):
        if not self._on('cashbuffer'):
            return None
        equity = self.ledger.equity_curve[-1].equity \
            if self.ledger.equity_curve else self.ledger.cash
        return self.ledger.cash - CASH_BUFFER * equity

    # ---- hook: entry vetoes + retracement limit tagging ----
    def _hook_veto_candidate(self, cand, date):
        p, a = self._arrays(cand['ticker'], date)
        if p is None:
            return False
        # raw price space: fills and ft_limit are raw; all ratios used
        # below are scale-invariant so raw == adjusted for these tests.
        op, cl, hi, lo = a['open'], a['close'], a['high'], a['low']
        if self._on('retracement'):
            rng = (hi[p] - lo[p]) / cl[p] if cl[p] > 0 else 0.0
            if np.isfinite(rng) and rng > RETRACE_RANGE:
                cand['ft_limit'] = float(lo[p]) + 0.5 * float(hi[p] - lo[p])
        if not self._on('vetoes'):
            return False
        # flagpole: 4 straight green bars and 4-day gain >8%
        if p >= 4 and np.isfinite(cl[p - 4]):
            green = int(np.sum(cl[p - 3:p + 1] > op[p - 3:p + 1]))
            ret4 = cl[p] / cl[p - 4] - 1.0
            if green >= 4 and ret4 > FLAGPOLE_RET:
                return True
        # snapback: close >8% above SMA25 (from adjusted closes)
        if p >= 24:
            sma25 = np.mean(cl[p - 24:p + 1])
            if np.isfinite(sma25) and sma25 > 0 \
                    and (cl[p] - sma25) / sma25 > SNAPBACK_PCT:
                return True
        # trap door: %K<%D gap>6, or %D falling fast while %K<%D
        if 'stoch_k' in a and 'stoch_d' in a:
            k, d = a['stoch_k'][p], a['stoch_d'][p]
            if np.isfinite(k) and np.isfinite(d) and k < d:
                if (d - k) > TRAPDOOR_GAP:
                    return True
                if p >= 1 and np.isfinite(a['stoch_d'][p - 1]):
                    ds = d - a['stoch_d'][p - 1]
                    if ds < TRAPDOOR_DSLOPE:
                        return True
        return False

    # ---- hook: retracement limit enforced at fill ----
    def _hook_fill_buy_ok(self, cand, row):
        lim = cand.get('ft_limit')
        if lim is None:
            return True
        op = row.get('open') if row is not None else None
        return op is not None and op <= lim
