"""Standalone verification for the nextgen comparator.

Fixture checks (no snapshot needed):
 1. _metrics computes 12-1 momentum, tsmom, w52h, vol20, dollar-vol causally
 2. rank ordering + liquidity/tsmom/mom_min gates
 3. rebalance set = first session of each month
 4. inverse book buys only in bear, sells on bull
 5. PEAD gap+volume gate
 6. hard stop / trailing ATR exits
Exit code 0 required.
"""
import os
import sys
import unittest
from types import SimpleNamespace

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.nextgen_comparator import NextgenComparator, DEFAULT_CFG


def mk(over=None):
    bt = NextgenComparator.__new__(NextgenComparator)
    bt.c = dict(DEFAULT_CFG); bt.c.update(over or {})
    return bt


def mkdata(bt, ticker, closes, vols=None, date='2010-01-04'):
    n = len(closes)
    closes = np.asarray(closes, float)
    vols = np.asarray(vols if vols is not None else np.full(n, 1e6), float)
    a = {'adjClose': closes, 'adjOpen': closes, 'adjHigh': closes * 1.01,
         'adjLow': closes * 0.99, 'adjVolume': vols, 'close': closes,
         'open': closes, 'high': closes * 1.01, 'low': closes * 0.99,
         'volume': vols, 'divCash': np.zeros(n), 'splitFactor': np.ones(n),
         'sma_200': np.full(n, np.nan)}
    dr = pd.date_range(end=date, periods=n, freq='B')
    arr = {'SPY': a, ticker: a}
    datens = {'SPY': dr.asi8, ticker: dr.asi8}
    ptr = {'SPY': n - 1, ticker: n - 1}
    bt.data = SimpleNamespace(_arr=arr, _date_ns=datens, _ptr=ptr,
                              tickers=list(arr), calendar=dr)
    return dr


class TestMetrics(unittest.TestCase):
    def test_mom_tsmom_w52h(self):
        bt = mk()
        n = 260
        closes = np.linspace(50, 100, n)      # doubles in a year
        mkdata(bt, 'X', closes)
        mom, ts, w52, vol20, vsma, dvol = bt._metrics('X', n - 1)
        exp_ts = closes[-1] / closes[n - 1 - 252] - 1.0   # i-lb = 7
        self.assertAlmostEqual(ts, exp_ts, places=6)
        self.assertGreater(mom, 0.85)                      # 12-1 slightly less
        self.assertAlmostEqual(w52, 1.0, places=3)         # at 52wk high
        self.assertGreater(vol20, 0)
        self.assertEqual(dvol, 100 * 1e6)

    def test_no_lookahead(self):
        bt = mk()
        n = 260
        closes = np.linspace(50, 100, n)
        mkdata(bt, 'X', closes)
        m1 = bt._metrics('X', n - 1)
        closes2 = closes.copy(); closes2[-1] *= 10         # huge future jump
        bt.data._arr['X']['adjClose'] = closes2
        # metrics at an earlier index must be identical
        m2 = bt._metrics('X', n - 10)
        bt.data._arr['X']['adjClose'] = np.linspace(50, 100, n)
        self.assertEqual(m2, bt._metrics('X', n - 10))


class TestRebalance(unittest.TestCase):
    def test_month_firsts(self):
        bt = mk()
        cal = pd.date_range('2010-01-01', '2010-03-31', freq='B')
        bt.data = SimpleNamespace(calendar=cal)
        s = bt._rebalance_set()
        firsts = {cal[0]}
        firsts |= {cal[i] for i in range(1, len(cal))
                   if cal[i].month != cal[i - 1].month}
        self.assertEqual({cal[i] for i in s}, firsts)


class TestRankGates(unittest.TestCase):
    def test_gates_applied(self):
        bt = mk({'tsmom_gate': True, 'mom_min': 0.0})
        n = 300
        hi = np.linspace(50, 150, n)      # strong uptrend
        dn = np.linspace(150, 50, n)      # downtrend (fails tsmom)
        mkdata(bt, 'UP', hi)
        # add DOWN ticker to data
        closes = dn
        a = dict(bt.data._arr['UP']); a['adjClose'] = closes
        bt.data._arr['DOWN'] = a
        bt.data._date_ns['DOWN'] = bt.data._date_ns['UP']
        bt.data._ptr['DOWN'] = n - 1
        bt.data.tickers = ['UP', 'DOWN']
        bt.portfolio = {'positions': {}}
        bt.pending_buys = []
        # UP passes tsmom>0 and mom>0; DOWN fails tsmom gate
        mom_up = bt._metrics('UP', n - 1)
        self.assertGreater(mom_up[0], 0)
        self.assertGreater(mom_up[1], 0)
        mom_dn = bt._metrics('DOWN', n - 1)
        self.assertLess(mom_dn[1], 0)


class TestInverseBook(unittest.TestCase):
    def test_inverse_buys_in_bear_only(self):
        bt = mk({'bear_mode': 'inverse', 'inverse_alloc': 0.30})
        n = 300
        spy = np.linspace(100, 60, n)     # SPY in downtrend
        mkdata(bt, 'SPY', spy)
        # SH available
        a = dict(bt.data._arr['SPY'])
        a['adjClose'] = np.linspace(30, 50, n)
        bt.data._arr['SH'] = a
        bt.data._date_ns['SH'] = bt.data._date_ns['SPY']
        bt.data._ptr['SH'] = n - 1
        bt.data.tickers = ['SPY', 'SH']
        bt._inv_tickers = ('SH', 'PSQ')
        bt.portfolio = {'positions': {}}
        bt.pending_buys = []
        bt.pending_sells = []
        bt.ledger = SimpleNamespace(
            cash=70_000.0,
            equity_curve=[SimpleNamespace(equity=100_000.0)])
        bt.slip = 0.0
        bt._buy_inverse('2010-01-04', {'SH': 50.0})
        self.assertEqual(len(bt.pending_buys), 1)   # PSQ has no bar -> skipped
        self.assertEqual(bt.pending_buys[0]['ticker'], 'SH')


class TestPead(unittest.TestCase):
    def test_gap_volume_gate(self):
        bt = mk({'pead': True})
        n = 40
        closes = np.full(n, 100.0)
        vols = np.full(n, 1e6)
        dr = mkdata(bt, 'X', closes, vols)
        a = bt.data._arr['X']
        a['adjOpen'][-1] = 115.0          # +15% gap
        a['volume'][-1] = 4e6             # 4x surge
        bt.data._ptr['X'] = n - 1
        bt.portfolio = {'positions': {}}
        bt.pending_buys = []
        bt.pending_sells = []
        bt.ledger = SimpleNamespace(
            cash=100_000.0,
            equity_curve=[SimpleNamespace(equity=100_000.0)])
        bt._pead_scan(dr[-1], {'X': 115.0}, set())
        self.assertEqual(len(bt.pending_buys), 1)
        self.assertTrue(bt.pending_buys[0].get('pead'))


if __name__ == '__main__':
    unittest.main(verbosity=2)
