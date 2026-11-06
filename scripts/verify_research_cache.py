import os
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import BacktestData, CorrectedBacktest
from src.freedom_trader_comparator import FreedomTraderComparator, _features

ROOT = Path(__file__).resolve().parents[1]


class ResearchCacheTests(unittest.TestCase):
    def test_scheduled_prefilter_matches_scalar_every_session(self):
        prices = ROOT / 'temp/ws_snapshot_test/prices'
        data = BacktestData(prices, ['SPY', 'AAPL', 'MSFT', 'AXL', 'SPLK', 'TWTR'], max_cached=1)
        calendar = data.build_calendar('2020-01-01', '2021-12-31')
        for day in calendar:
            data.advance(day)
            for days, threshold in ((None, None), (20, 0.05), (20, 0.0)):
                self.assertEqual(data.prefilter_candidates(day, days, threshold),
                                 data._prefilter_candidates_scalar(day, days, threshold))

    def test_decisions_are_invariant_to_adjusted_price_scale(self):
        source = pd.read_parquet(ROOT / 'temp/ws_snapshot_test/prices/spy.parquet')
        with tempfile.TemporaryDirectory() as directory:
            views = []
            for i, multiplier in enumerate((1.0, 0.01)):
                prices = Path(directory) / str(i)
                prices.mkdir()
                frame = source.copy()
                for column in ('adjOpen', 'adjHigh', 'adjLow', 'adjClose'):
                    frame[column] *= multiplier
                frame.to_parquet(prices / 'spy.parquet')
                data = BacktestData(prices, ['SPY'])
                views.append(data.decision_frame('SPY', '2020-06-17'))
            columns = ['adjClose', 'sma_25', 'sma_200', 'atr', 'stoch_k']
            np.testing.assert_allclose(views[0][columns], views[1][columns],
                                       rtol=1e-9, atol=1e-9, equal_nan=True)
            self.assertAlmostEqual(views[0]['adjClose'].iloc[-1],
                                   views[0]['close'].iloc[-1])

    def test_freedom_features_do_not_read_future_weeks(self):
        frame = pd.read_parquet(ROOT / 'temp/ws_snapshot_test/prices/spy.parquet')
        for cutoff in ('2020-06-17', '2020-06-19', '2020-06-22'):
            truncated = _features(frame.loc[:cutoff])
            full = _features(frame).loc[:cutoff]
            pd.testing.assert_frame_equal(truncated, full)

    def test_freedom_cache_replay_equivalence(self):
        prices = ROOT / 'temp/ws_snapshot_test/prices'
        with tempfile.TemporaryDirectory() as directory:
            outputs = []
            for cache in (None, Path(directory), Path(directory)):
                data = BacktestData(prices, ['SPY', 'AAPL', 'MSFT'], max_cached=2,
                                    indicator_cache=cache)
                data.build_calendar('2020-01-01', '2021-12-31')
                outputs.append(FreedomTraderComparator(data, version='v8.1').run())
            for result in outputs[1:]:
                pd.testing.assert_frame_equal(outputs[0]['equity'], result['equity'])
                self.assertEqual(outputs[0]['entries'], result['entries'])
                self.assertEqual(outputs[0]['exits'], result['exits'])

    def test_cache_replay_equivalence_and_invalidation(self):
        prices = ROOT / 'temp/ws_snapshot_test/prices'
        tickers = ['SPY', 'AAPL', 'MSFT', 'AXL', 'SPLK', 'TWTR']
        with tempfile.TemporaryDirectory() as directory:
            cache = Path(directory) / 'cache'
            outputs = []
            for cache_dir in (None, cache, cache):
                data = BacktestData(prices, tickers, max_cached=1,
                                    indicator_cache=cache_dir)
                data.build_calendar('2020-01-01', '2021-12-31')
                result = CorrectedBacktest(data, version='v8.1').run()
                outputs.append(result)
                for ticker, arrays in data._arr.items():
                    for name, array in arrays.items():
                        self.assertTrue(array.flags.owndata, (ticker, name))
            for output in outputs[1:]:
                pd.testing.assert_frame_equal(outputs[0]['equity'], output['equity'])
                self.assertEqual(outputs[0]['entries'], output['entries'])
                self.assertEqual(outputs[0]['exits'], output['exits'])
            source = Path(directory) / 'prices'
            source.mkdir()
            frame = pd.read_parquet(prices / 'spy.parquet')
            frame.to_parquet(source / 'spy.parquet')
            first = BacktestData(source, ['SPY'], indicator_cache=cache)._ensure('SPY')
            frame.loc[frame.index[-1], 'close'] *= 1.1
            frame.to_parquet(source / 'spy.parquet')
            second = BacktestData(source, ['SPY'], indicator_cache=cache)._ensure('SPY')
            self.assertFalse(np.isclose(first['close'].iloc[-1], second['close'].iloc[-1]))


if __name__ == '__main__':
    unittest.main()
