import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import price_filename

ROOT = Path(__file__).resolve().parents[1]


def verify(path):
    summary = json.loads(path.read_text())
    prefix = str(path)[:-len('_summary.json')]
    equity = pd.read_csv(prefix + '_equity.csv', parse_dates=['date'])
    trades = pd.read_csv(prefix + '_trades.csv', parse_dates=['date'])
    config = summary['config']
    snapshot = Path(config['snapshot'])
    if not snapshot.is_absolute():
        snapshot = ROOT / snapshot
    checks = {}
    checks['sessions'] = len(equity) == summary['sessions']
    checks['dates_sorted_unique'] = bool(equity.date.is_monotonic_increasing and equity.date.is_unique)
    checks['cash_nonnegative'] = bool((equity.cash >= -1e-6).all())
    checks['settled_cash_valid'] = bool(((equity.settled_cash >= -1e-6)
                                        & (equity.settled_cash <= equity.cash + 1e-6)).all())
    checks['equity_identity'] = bool(np.allclose(equity.equity,
                                                equity.cash + equity.positions_value, atol=1e-6))
    final = float(equity.equity.iloc[-1])
    years = len(equity) / 252.0
    cagr = ((final / config['cash']) ** (1 / years) - 1) * 100
    drawdown = (equity.equity / equity.equity.cummax() - 1) * 100
    underwater = float((equity.equity < equity.equity.cummax()).mean() * 100)
    checks['final_equity'] = abs(final - summary['final_equity']) <= 0.011
    checks['cagr'] = abs(cagr - summary['cagr_pct']) <= 0.011
    checks['max_drawdown'] = abs(float(drawdown.min()) - summary['max_drawdown_pct']) <= 0.011
    checks['underwater'] = abs(underwater - summary['time_underwater_pct']) <= 0.11
    checks['entry_count'] = int(trades.type.eq('BUY').sum()) == summary['entries']
    checks['exit_count'] = int(trades.type.eq('SELL').sum()) == summary['exits']
    fees = sum(max(config['min_commission'], config['commission_per_share'] * shares)
               for shares in trades.shares)
    checks['fees'] = abs(fees - summary['total_fees']) <= 0.011
    spy = pd.read_parquet(snapshot / 'prices' / price_filename('SPY'))
    if 'date' in spy.columns:
        spy = spy.set_index('date')
    spy = spy.loc[summary['start']:summary['end']]
    benchmark = (spy.adjClose.iloc[-1] / spy.adjClose.iloc[0] - 1) * 100
    checks['benchmark_window_total_return'] = abs(float(benchmark) - summary['spy_total_return_pct']) <= 0.011
    stale, fill_errors = [], []
    last_events = trades.sort_values('date', kind='stable').groupby('ticker').tail(1)
    open_names = set(last_events.loc[last_events.type.eq('BUY'), 'ticker'])
    for ticker, group in trades.groupby('ticker'):
        frame = pd.read_parquet(snapshot / 'prices' / price_filename(ticker))
        if 'date' in frame.columns:
            frame = frame.set_index('date')
        for trade in group.itertuples():
            if str(trade.reason).startswith('Forced liquidation'):
                continue
            if trade.date not in frame.index:
                fill_errors.append(f'{ticker} {trade.date}: missing fill bar')
                continue
            sign = 1 if trade.type == 'BUY' else -1
            expected = float(frame.loc[trade.date, 'open']) * (1 + sign * config['slippage_bps'] / 10000)
            if not np.isclose(trade.price, expected, rtol=1e-9, atol=1e-8):
                fill_errors.append(f'{ticker} {trade.date}: fill differs from modeled open')
        if ticker in open_names:
            positive = frame.loc[:summary['end']]
            positive = positive[positive.volume > 0]
            if positive.empty:
                stale.append(ticker)
            else:
                gap = int((spy.index > positive.index[-1]).sum())
                if gap > 20:
                    stale.append(ticker)
    checks['fill_prices'] = not fill_errors
    checks['no_ended_tickers_still_open'] = not stale
    return {'summary': str(path), 'checks': checks, 'passed': all(checks.values()),
            'metrics_recomputed': {'final_equity': final, 'cagr_pct': cagr,
                                   'max_drawdown_pct': float(drawdown.min()),
                                   'spy_total_return_pct': float(benchmark)},
            'stale_open_tickers': stale, 'fill_errors': fill_errors,
            'open_tickers_from_last_trade': sorted(open_names)}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--summary', nargs='+', required=True, type=Path)
    parser.add_argument('--output', required=True, type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error('output exists; choose a new filename')
    results = [verify(path.resolve()) for path in args.summary]
    args.output.write_text(json.dumps(results, indent=2), encoding='utf-8')
    for result in results:
        print(('PASS' if result['passed'] else 'FAIL') + ': ' + result['summary'])
        for name, passed in result['checks'].items():
            if not passed:
                print('  FAIL: ' + name)
    return 0 if all(result['passed'] for result in results) else 1


if __name__ == '__main__':
    sys.exit(main())
