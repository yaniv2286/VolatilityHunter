#!/usr/bin/env python3
"""
Standalone verification for the post-audit data pipeline fixes.
Tests: EOD volume sanity, sector mapping, position sizing ATR storage, ATR stop cap.
"""

import os
import sys
import pandas as pd
import numpy as np

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from src.strategy_engine import get_sector, calc_position_size, check_exits, get_params
from src.market_hours import MarketHours


def _sample_df():
    """A minimal 300-row df with enough indicators."""
    n = 300
    prices = 100.0 + np.cumsum(np.random.randn(n) * 0.5)
    df = pd.DataFrame({
        'open': prices * 0.99,
        'high': prices * 1.02,
        'low': prices * 0.98,
        'close': prices,
        'volume': [1_000_000] * n,
        'adjOpen': prices * 0.99,
        'adjHigh': prices * 1.02,
        'adjLow': prices * 0.98,
        'adjClose': prices,
        'adjVolume': [1_000_000.0] * n,
        'divCash': 0.0,
        'splitFactor': 1.0,
    }, index=pd.date_range(end='2026-09-01', periods=n, freq='B'))
    from src.strategy_v7_2 import add_indicators_v7_2
    return add_indicators_v7_2(df)


def check_last_bar_volume_sanity():
    path = os.path.join(ROOT, 'data', 'aapl.parquet')
    if not os.path.exists(path):
        raise AssertionError('AAPL parquet missing')
    df = pd.read_parquet(path)
    if len(df) < 60:
        raise AssertionError('AAPL parquet too short')
    if 'volume_sma' not in df.columns:
        df['volume_sma'] = df['volume'].rolling(window=30, min_periods=1).mean()
    last = df.iloc[-1]
    vsma = last.get('volume_sma')
    vol = last.get('volume')
    if pd.isna(vsma) or vsma <= 0 or pd.isna(vol):
        raise AssertionError('Cannot compute volume sanity for AAPL')
    ratio = vol / vsma
    if ratio < 0.2:
        raise AssertionError(f'AAPL last-bar volume ratio {ratio:.4f} looks partial/poisoned')
    print(f'[OK] AAPL last-bar volume ratio: {ratio:.2f}')


def check_sector_mapping():
    sector = get_sector('AAPL')
    if not sector or sector == 'Unknown' or 'not available' in str(sector).lower():
        raise AssertionError(f'AAPL sector is still bad: {sector}')
    print(f'[OK] AAPL sector: {sector}')


def check_position_sizing():
    df = _sample_df()
    def load_fn(t):
        return df
    price = float(df['close'].iloc[-1])
    portfolio = {'cash': 100_000, 'positions': {}, 'high_water_mark': 100_000}
    shares, cost, atr = calc_position_size(portfolio, price, {}, 'TEST', load_fn)
    if shares <= 0 or cost <= 0 or atr <= 0:
        raise AssertionError(f'calc_position_size first trade failed: {shares}, {cost}, {atr}')

    # With an open position that has atr, the median branch should still work.
    portfolio['positions']['TEST'] = {
        'shares': 10, 'entry_price': price, 'atr': atr * 1.5,
    }
    shares2, cost2, atr2 = calc_position_size(portfolio, price, {}, 'TEST2', load_fn)
    if shares2 <= 0 or cost2 <= 0:
        raise AssertionError(f'calc_position_size second trade failed: {shares2}, {cost2}')
    print(f'[OK] calc_position_size returns atr and sizes correctly (first={shares}, second={shares2})')


def check_atr_stop_cap():
    df = _sample_df()
    last = df.iloc[-1]
    price = float(last['close'])
    entry = price * 1.12  # force a loss
    atr = float(last['atr'])
    portfolio = {
        'positions': {
            'TEST': {
                'shares': 10,
                'entry_price': entry,
                'entry_date': '2026-08-15',
                'highest_price': entry,
            }
        }
    }
    # 2.5 * ATR may be > 8%; the cap should still trigger at -8%.
    exits = check_exits(portfolio, {'TEST': price}, lambda t: df, version='v8.1')
    reasons = [e['reason'] for e in exits]
    if not any('ATR stop' in r or 'Hard stop' in r for r in reasons):
        raise AssertionError(f'ATR stop cap did not trigger: {reasons}')
    print(f'[OK] ATR stop cap triggered: {reasons[0]}')


def check_market_holidays():
    mh = MarketHours()
    from datetime import datetime
    juneteenth = datetime(2026, 6, 19, 10, 0)
    if mh.is_trading_day(juneteenth):
        raise AssertionError('Juneteenth 2026 should be a market holiday')
    print('[OK] Juneteenth 2026 correctly flagged as non-trading day')


def main() -> int:
    print('=' * 70)
    print('DATA PIPELINE VERIFICATION')
    print('=' * 70)
    check_last_bar_volume_sanity()
    check_sector_mapping()
    check_position_sizing()
    check_atr_stop_cap()
    check_market_holidays()
    print('=' * 70)
    print('ALL VERIFICATION CHECKS PASSED')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
