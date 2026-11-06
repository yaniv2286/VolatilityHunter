import os
import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import CorrectedBacktest
from src.freedom_trader_comparator import FreedomTraderComparator


class FreedomIntegrityTests(unittest.TestCase):
    def test_missing_bars_queue_exit(self):
        bt = FreedomTraderComparator.__new__(FreedomTraderComparator)
        bt.portfolio = {'positions': {t: {} for t in ('A', 'B', 'C', 'D')}}
        bt.pending_sells, bt.pending_buys = [], []
        bt._ft = {}
        bt.data = SimpleNamespace(bar=lambda t, date: None)
        bt._features = lambda t: None
        bt._signal_pass(pd.Timestamp('2020-01-02'), {})
        self.assertEqual({o['ticker'] for o in bt.pending_sells}, {'A', 'B', 'C', 'D'})
        self.assertTrue(all(o['fraction'] == 1.0 for o in bt.pending_sells))

    def test_shared_replay_queues_missing_holding_once(self):
        bt = CorrectedBacktest.__new__(CorrectedBacktest)
        bt.ledger = SimpleNamespace(positions={'ENDED': object(), 'ACTIVE': object()})
        bt.pending_sells = []
        bt.data = SimpleNamespace(bar=lambda t, date:
                                  None if t == 'ENDED' else {'volume': 100.0})
        for _ in range(2):
            bt._queue_untradeable_exits(pd.Timestamp('2020-01-02'))
        self.assertEqual(len(bt.pending_sells), 1)
        self.assertEqual(bt.pending_sells[0]['ticker'], 'ENDED')

    def test_ended_holding_liquidates_after_retry_window(self):
        data = SimpleNamespace(bar=lambda t, date: None)
        bt = CorrectedBacktest(data, version='v8.1', min_commission=0.0,
                               commission_per_share=0.0)
        date = pd.Timestamp('2020-01-02')
        bt.ledger.begin_session(0)
        bt.ledger.buy('ENDED', date, 10.0, 100)
        bt._record_buy('ENDED', 100, 10.0, date, {}, 0.0)
        bt.ledger.mark_to_market(date, {'ENDED': 11.0}, 0)
        bt._queue_untradeable_exits(date)
        for i in range(1, 21):
            day = date + pd.offsets.BDay(i)
            bt.ledger.begin_session(i)
            bt._fill_open(day)
        self.assertNotIn('ENDED', bt.ledger.positions)
        self.assertNotIn('ENDED', bt.portfolio['positions'])
        self.assertEqual(len(bt.exit_log), 1)
        self.assertEqual(bt.ledger.cash, 100100.0)
        self.assertEqual(bt.ledger.settled_cash, 99000.0)
        bt.ledger.begin_session(21)
        self.assertEqual(bt.ledger.settled_cash, 100100.0)

    def test_split_adjusts_freedom_state(self):
        bt = FreedomTraderComparator.__new__(FreedomTraderComparator)
        bt._ft = {'A': {'stop': 98.0, 'target': 110.0, 'be_done': True}}
        bt.data = SimpleNamespace(bar=lambda t, date: {'splitFactor': 2.0})
        with patch.object(CorrectedBacktest, '_apply_corporate_actions'):
            bt._apply_corporate_actions(pd.Timestamp('2020-01-02'))
        self.assertEqual(bt._ft['A'], {'stop': 49.0, 'target': 55.0, 'be_done': True})


if __name__ == '__main__':
    unittest.main()
