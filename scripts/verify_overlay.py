"""Standalone verification for the v8.1 FT-overlay comparator.

Fixture-level checks (no snapshot needed):
  1. breakeven ratchet raises stop_loss_price to entry after +2% close
     and never lowers it.
  2. cashbuffer caps cumulative queued buys at cash - 20%*equity.
  3. vetoes reject flagpole, snapback, and trap-door candidates.
  4. retracement tags wide signal bars and cancels fills above limit.

Exit code 0 required.
"""
import os
import sys
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.v81_overlay_comparator import V81OverlayComparator


def make(overlays):
    bt = V81OverlayComparator.__new__(V81OverlayComparator)
    bt.overlays = set(overlays)
    return bt


def arr(closes, opens=None, k=None, d=None):
    closes = np.asarray(closes, float)
    n = len(closes)
    opens = np.asarray(opens if opens is not None else closes, float)
    return {'open': opens, 'close': closes,
            'high': closes * 1.01, 'low': closes * 0.99,
            'volume': np.full(n, 1e6),
            'stoch_k': np.asarray(k if k is not None else [50] * n, float),
            'stoch_d': np.asarray(d if d is not None else [50] * n, float)}


def with_data(bt, closes, opens=None, k=None, d=None):
    n = len(closes)
    bt.data = SimpleNamespace(
        _ptr={'X': n - 1},
        _date_ns={'X': pd.date_range(end='2020-01-08', periods=n).asi8},
        _arr={'X': arr(closes, opens, k, d)})


class TestBreakeven(unittest.TestCase):
    def test_ratchet_raises_stop_only(self):
        bt = make({'breakeven'})
        bt.portfolio = {'positions': {
            'X': {'entry_price': 100.0, 'stop_loss_price': 95.0},
            'Y': {'entry_price': 100.0, 'stop_loss_price': 90.0}}}
        bt._hook_pre_exits('2020-01-10', {'X': 102.5, 'Y': 101.0})
        self.assertEqual(bt.portfolio['positions']['X']['stop_loss_price'],
                         100.0)
        self.assertEqual(bt.portfolio['positions']['Y']['stop_loss_price'],
                         90.0)

    def test_ratchet_off_by_default(self):
        bt = make(set())
        bt.portfolio = {'positions': {
            'X': {'entry_price': 100.0, 'stop_loss_price': 95.0}}}
        bt._hook_pre_exits('2020-01-10', {'X': 102.5})
        self.assertEqual(bt.portfolio['positions']['X']['stop_loss_price'],
                         95.0)


class TestCashBuffer(unittest.TestCase):
    def test_cap_is_cash_minus_20pct_equity(self):
        bt = make({'cashbuffer'})
        bt.ledger = SimpleNamespace(
            cash=60_000.0,
            equity_curve=[SimpleNamespace(equity=100_000.0)])
        self.assertAlmostEqual(bt._hook_extra_cash_ceiling(), 40_000.0)

    def test_no_cap_when_off(self):
        bt = make(set())
        bt.ledger = SimpleNamespace(cash=60_000.0, equity_curve=[])
        self.assertIsNone(bt._hook_extra_cash_ceiling())


class TestVetoes(unittest.TestCase):
    DATE = pd.Timestamp('2020-01-08')

    def test_flagpole_rejected(self):
        bt = make({'vetoes'})
        with_data(bt, closes=[100, 110, 112, 114, 120, 122, 124, 126],
                  opens=[100, 108, 110, 112, 118, 120, 122, 124])
        self.assertTrue(bt._hook_veto_candidate({'ticker': 'X'}, self.DATE))

    def test_snapback_rejected(self):
        bt = make({'vetoes'})
        closes = [100.0] * 24 + [100.0, 109.5]   # >8% above sma25
        with_data(bt, closes=closes)
        self.assertTrue(bt._hook_veto_candidate({'ticker': 'X'}, self.DATE))

    def test_trapdoor_rejected(self):
        bt = make({'vetoes'})
        with_data(bt, closes=[100.0] * 8, k=[50, 50, 50, 50, 50, 50, 50, 40],
                  d=[50, 50, 50, 50, 50, 50, 50, 48])
        self.assertTrue(bt._hook_veto_candidate({'ticker': 'X'}, self.DATE))

    def test_clean_candidate_passes(self):
        bt = make({'vetoes'})
        closes = [100, 101, 99, 102, 101, 103, 102, 103]
        opens = [100, 100.5, 99.5, 101, 100, 102, 102, 101]
        with_data(bt, closes=closes, opens=opens)
        self.assertFalse(bt._hook_veto_candidate({'ticker': 'X'}, self.DATE))


class TestRetracement(unittest.TestCase):
    DATE = pd.Timestamp('2020-01-08')

    def test_wide_bar_tags_limit_and_gates_fill(self):
        bt = make({'retracement'})
        with_data(bt, closes=[100, 100, 100, 100, 100, 100, 100, 100],
                  opens=[100] * 8)
        # make last bar wide: high 110 low 90 close 100 -> range 20%
        bt.data._arr['X']['high'][-1] = 110.0
        bt.data._arr['X']['low'][-1] = 90.0
        cand = {'ticker': 'X'}
        self.assertFalse(bt._hook_veto_candidate(cand, self.DATE))
        self.assertAlmostEqual(cand['ft_limit'], 100.0)
        self.assertFalse(bt._hook_fill_buy_ok(cand, {'open': 101.0}))
        self.assertTrue(bt._hook_fill_buy_ok(cand, {'open': 99.0}))

    def test_narrow_bar_no_limit(self):
        bt = make({'retracement'})
        with_data(bt, closes=[100] * 8, opens=[100] * 8)
        cand = {'ticker': 'X'}
        bt._hook_veto_candidate(cand, self.DATE)
        self.assertNotIn('ft_limit', cand)


if __name__ == '__main__':
    unittest.main(verbosity=2)
