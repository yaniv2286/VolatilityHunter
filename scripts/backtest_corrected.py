"""Run the corrected backtest over a frozen research snapshot.

Usage:
  python scripts/backtest_corrected.py \
      --snapshot data/research/snapshot_1998_20261022 \
      --start 2000-01-03 --end 2025-12-31 --version v8.1 \
      [--slippage-bps 5] [--commission-per-share 0.005] [--limit N]

Writes reports/backtest_<version>_<start>_<end>_{summary.json,equity.csv,
trades.csv} and prints the headline metrics.
"""

import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import BacktestData, CorrectedBacktest

logger = logging.getLogger(__name__)
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))


def max_drawdown(eq: pd.Series, dates: pd.Series):
    peak = eq.cummax()
    dd = eq / peak - 1.0
    end_pos = int(dd.values.argmin())
    start_pos = int(eq.values[:end_pos + 1].argmax())
    return (float(dd.iloc[end_pos]),
            pd.Timestamp(dates.iloc[start_pos]).date(),
            pd.Timestamp(dates.iloc[end_pos]).date())


def time_underwater(eq: pd.Series) -> float:
    peak = eq.cummax()
    return float((eq < peak).mean())


def yearly_returns(dates: pd.Series, eq: pd.Series) -> dict:
    df = pd.DataFrame({'date': pd.to_datetime(dates), 'eq': eq})
    out = {}
    for y, g in df.groupby(df['date'].dt.year):
        prev = df[df['date'] < g['date'].iloc[0]]
        base = prev['eq'].iloc[-1] if len(prev) else g['eq'].iloc[0]
        out[int(y)] = float(g['eq'].iloc[-1] / base - 1.0)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--start', required=True)
    ap.add_argument('--end', required=True)
    ap.add_argument('--version', default='v8.1')
    ap.add_argument('--strategy', default='engine',
                    choices=['engine', 'momentum', 'freedom', 'overlay',
                             'nextgen'],
                    help='engine = shared strategy version; momentum/freedom = comparators')
    ap.add_argument('--cash', type=float, default=100_000.0)
    ap.add_argument('--slippage-bps', type=float, default=0.0)
    ap.add_argument('--commission-per-share', type=float, default=0.005)
    ap.add_argument('--min-commission', type=float, default=1.0)
    ap.add_argument('--settlement-days', type=int, default=1)
    ap.add_argument('--capital-ceiling', type=float, default=1e18,
                    help='buying-power cap; default lifts the live $100k '
                         'ops ceiling so research equity can compound')
    ap.add_argument('--limit', type=int, default=0,
                    help='restrict universe to first N tickers (testing)')
    ap.add_argument('--tickers', default='',
                    help='comma list or @file restricting the universe')
    ap.add_argument('--ng-config', default='',
                    help='nextgen config: inline JSON or @file')
    ap.add_argument('--overlays', default='',
                    help='comma list of v8.1 overlay elements to ENABLE: '
                         'breakeven,cashbuffer,retracement,vetoes')
    ap.add_argument('--ft-disable', default='',
                    help='comma list of Freedom-Trader elements to disable '
                         '(ablation): weekly,power,trapdoor,flagpole,'
                         'snapback,candle,structure,barrier,retracement,'
                         'breakeven,rollover,conviction,cashbuffer')
    ap.add_argument('--max-cached-frames', type=int, default=64)
    ap.add_argument('--indicator-cache', default=None)
    ap.add_argument('--tag', default='')
    args = ap.parse_args()
    code_files = ('src/backtest_engine.py', 'src/portfolio_ledger.py',
                  'src/strategy_engine.py', 'src/strategy_v7_2.py',
                  'src/freedom_trader_comparator.py',
                  'src/v81_overlay_comparator.py',
                  'src/nextgen_comparator.py',
                  'scripts/backtest_corrected.py')
    code_sha256 = {name: hashlib.sha256((ROOT / name).read_bytes()).hexdigest()
                   for name in code_files}

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')

    snap = Path(args.snapshot)
    manifest = json.loads((snap / 'manifest.json').read_text())
    tickers = [t for t, r in manifest['records'].items()
               if r.get('status') == 'ok']
    tickers.sort()
    if args.tickers:
        sel = args.tickers
        if sel.startswith('@'):
            want = [x.strip().upper() for x in
                    Path(sel[1:]).read_text().replace(',', '\n').splitlines()
                    if x.strip()]
        else:
            want = [x.strip().upper() for x in sel.split(',') if x.strip()]
        want = set(want) | {'SPY'}   # SPY required as calendar/benchmark
        tickers = [t for t in tickers if t in want]
    if args.limit:
        tickers = tickers[:args.limit]
    if 'SPY' not in tickers:
        logger.error('snapshot lacks SPY - required as calendar/benchmark')
        return 1
    logger.info('universe: %d tickers from %s', len(tickers), snap)

    data = BacktestData(snap / 'prices', tickers,
                        max_cached=args.max_cached_frames,
                        indicator_cache=Path(args.indicator_cache) if args.indicator_cache else None)
    cal = data.build_calendar(args.start, args.end)
    logger.info('calendar: %s sessions %s -> %s',
                len(cal), cal[0].date(), cal[-1].date())

    if args.strategy == 'momentum':
        from src.momentum_comparator import MomentumComparator
        bt = MomentumComparator(
            data, starting_cash=args.cash, version=args.version,
            commission_per_share=args.commission_per_share,
            min_commission=args.min_commission,
            slippage_bps=args.slippage_bps,
            settlement_days=args.settlement_days,
            earnings_map={}, capital_ceiling=args.capital_ceiling)
    elif args.strategy == 'freedom':
        from src.freedom_trader_comparator import FreedomTraderComparator
        bt = FreedomTraderComparator(
            data, starting_cash=args.cash, version=args.version,
            commission_per_share=args.commission_per_share,
            min_commission=args.min_commission,
            slippage_bps=args.slippage_bps,
            settlement_days=args.settlement_days,
            earnings_map={}, capital_ceiling=args.capital_ceiling,
            ablations={x.strip() for x in args.ft_disable.split(',')
                       if x.strip()})
    elif args.strategy == 'nextgen':
        from src.nextgen_comparator import NextgenComparator, parse_ng_config
        bt = NextgenComparator(
            data, starting_cash=args.cash, version=args.version,
            commission_per_share=args.commission_per_share,
            min_commission=args.min_commission,
            slippage_bps=args.slippage_bps,
            settlement_days=args.settlement_days,
            earnings_map={},
            capital_ceiling=args.capital_ceiling,
            ng_config=parse_ng_config(args.ng_config))
    elif args.strategy == 'overlay':
        from src.v81_overlay_comparator import V81OverlayComparator
        bt = V81OverlayComparator(
            data, starting_cash=args.cash, version=args.version,
            commission_per_share=args.commission_per_share,
            min_commission=args.min_commission,
            slippage_bps=args.slippage_bps,
            settlement_days=args.settlement_days,
            earnings_map={},
            capital_ceiling=args.capital_ceiling,
            overlays={x.strip() for x in args.overlays.split(',')
                      if x.strip()})
    else:
        bt = CorrectedBacktest(
            data, starting_cash=args.cash, version=args.version,
            commission_per_share=args.commission_per_share,
            min_commission=args.min_commission,
            slippage_bps=args.slippage_bps,
            settlement_days=args.settlement_days,
            earnings_map={},  # empty: earnings guard off in historical runs
            capital_ceiling=args.capital_ceiling)
    res = bt.run()
    if any(hashlib.sha256((ROOT / name).read_bytes()).hexdigest() != digest
           for name, digest in code_sha256.items()):
        raise RuntimeError('Research source changed during replay; rerun with frozen code')

    eq = res['equity']
    eq['date'] = pd.to_datetime(eq['date'])
    n_days = len(eq)
    years = n_days / 252.0
    total_ret = res['final_equity'] / args.cash - 1.0
    cagr = (res['final_equity'] / args.cash) ** (1 / years) - 1 if years > 0 else 0
    mdd, dd_start, dd_end = max_drawdown(eq['equity'], eq['date'])

    # SPY benchmark over identical sessions
    spy = data.asof('SPY', cal[-1]).reindex(cal)
    spy_col = 'adjClose' if 'adjClose' in spy.columns else 'close'
    spy_ret = float(spy[spy_col].iloc[-1] / spy[spy_col].iloc[0] - 1)
    spy_cagr = (1 + spy_ret) ** (1 / years) - 1 if years > 0 else 0

    exposure = float((eq['positions_value'] > 0).mean())
    invested_turnover = sum(r['cost'] for r in res['entries'])
    sells = res['exits']
    wins = [r for r in sells if r['pnl'] > 0]
    gross_win = sum(r['pnl'] for r in wins)
    gross_loss = -sum(r['pnl'] for r in sells if r['pnl'] <= 0)

    summary = {
        'config': vars(args),
        'snapshot_manifest': {
            'created_utc': manifest.get('created_utc'),
            'code_revision': manifest.get('code_revision'),
            'declared_universe_count': manifest.get('universe_count'),
            'universe_count': len(tickers),
            'manifest_sha256': hashlib.sha256((snap / 'manifest.json').read_bytes()).hexdigest(),
            'loaded_tickers_sha256': hashlib.sha256('\n'.join(tickers).encode()).hexdigest(),
        },
        'code_sha256': code_sha256,
        'strategy_params': bt.params,
        'benchmark': {'ticker': 'SPY', 'column': spy_col,
                      'start': str(cal[0].date()), 'end': str(cal[-1].date()),
                      'costs_included': False},
        'universe_size': len(tickers),
        'sessions': n_days,
        'years': round(years, 3),
        'start': str(cal[0].date()), 'end': str(cal[-1].date()),
        'final_equity': round(res['final_equity'], 2),
        'total_return_pct': round(total_ret * 100, 2),
        'cagr_pct': round(cagr * 100, 2),
        'spy_total_return_pct': round(spy_ret * 100, 2),
        'spy_cagr_pct': round(spy_cagr * 100, 2),
        'max_drawdown_pct': round(mdd * 100, 2),
        'dd_window': [str(dd_start), str(dd_end)],
        'time_underwater_pct': round(time_underwater(eq['equity']) * 100, 1),
        'yearly_returns_pct': {k: round(v * 100, 2)
                               for k, v in yearly_returns(eq['date'],
                                                          eq['equity']).items()},
        'entries': len(res['entries']),
        'exits': len(sells),
        'win_rate_pct': round(res['win_rate'] * 100, 2),
        'profit_factor': round(gross_win / gross_loss, 3)
        if gross_loss > 0 else None,
        'turnover_dollars': round(invested_turnover, 2),
        'total_fees': round(res['total_fees'], 2),
        'total_dividends': round(res['total_dividends'], 2),
        'days_with_positions_pct': round(exposure * 100, 1),
        'avg_positions': round(float(eq['positions'].mean()), 2),
        'rejected_orders': sum(1 for o in res['orders']
                               if o.status == 'rejected'),
        'limitations': [
            'Signals on completed bar T fill at T+1 open (approximates '
            'live 09:35 ET intraday fills).',
            'Universe uses successful records in the frozen snapshot; missing '
            'delisted histories and recycled symbol identities remain limitations.',
            'Missing-bar exits retry for 20 sessions then use the last observed '
            'price; this is optimistic and not verified delisting proceeds.',
            'SPY benchmark uses measured-window adjusted closes without trading costs.',
            'Sector map and earnings calendar are current, not point-in-time.',
            'Adjusted-price indicators embed post-event corporate actions.',
            'Research decision frames rescale adjusted price indicators to current '
            'raw-price units; the production loader is not yet reconciled to this view.',
        ],
    }

    reports = ROOT / 'reports'
    reports.mkdir(exist_ok=True)
    tag = f"_{args.tag}" if args.tag else ''
    strat = '' if args.strategy == 'engine' else f'{args.strategy}_'
    base = f"backtest_{strat}{args.version}_{args.start}_{args.end}{tag}"
    (reports / f'{base}_summary.json').write_text(
        json.dumps(summary, indent=2))
    eq.to_csv(reports / f'{base}_equity.csv', index=False)
    pd.DataFrame(res['entries'] + res['exits']).to_csv(
        reports / f'{base}_trades.csv', index=False)

    print(json.dumps({k: v for k, v in summary.items()
                      if k not in ('limitations', 'config')}, indent=2))
    logger.info('reports written: reports/%s_*', base)
    return 0


if __name__ == '__main__':
    sys.exit(main())
