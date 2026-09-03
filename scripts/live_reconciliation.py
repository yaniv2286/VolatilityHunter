#!/usr/bin/env python3
"""
live_reconciliation.py
======================
Daily live-vs-backtest reconciliation for VolatilityHunter.

Actions:
  1. Record the latest completed-EOD live equity snapshot from
     data/portfolio.json to data/live_equity.jsonl.
  2. Load the latest backtest equity curve (v8.1 by default) from
     logs/backtest_v8_vs_v8_1_curves_*.json.
  3. Compare live performance to the backtest over the same live window.
  4. Print a report and write alerts to logs/live_reconciliation_alerts.log
     if divergence exceeds thresholds.

Exit code 0 = completed (alerts are warnings, not failures).
"""

import json
import os
import sys
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional

import pandas as pd
import numpy as np

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from src.email_notifier import EmailNotifier
from src.smart_data_loader_factory import get_data_loader

DATA_DIR = ROOT / 'data'
LOGS_DIR = ROOT / 'logs'
LIVE_EQUITY_FILE = DATA_DIR / 'live_equity.jsonl'
ALERT_LOG = LOGS_DIR / 'live_reconciliation_alerts.log'
DEFAULT_BACKTEST_VERSION = 'v8_1'

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('live_reconciliation')


def last_completed_eod_date() -> str:
    """Return the latest completed US-EOD date as an ISO string."""
    try:
        loader = get_data_loader()
        dt = loader._last_completed_eod_date()
        return dt.date().isoformat()
    except Exception as e:
        logger.warning(f'Could not determine last completed EOD date: {e}; using today')
        return datetime.now().date().isoformat()


def get_latest_backtest_path() -> Optional[Path]:
    """Find the most recent backtest output that includes equity curves."""
    # Prefer explicit curve exports.
    curve_files = sorted(LOGS_DIR.glob('backtest_v8_vs_v8_1_curves_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in curve_files:
        data = json.loads(f.read_text(encoding='utf-8'))
        key = f'equity_curve_{DEFAULT_BACKTEST_VERSION}'
        if key in data and data[key]:
            return f

    # Fallback: any v8 vs v8.1 JSON that happens to contain curves.
    files = sorted(LOGS_DIR.glob('backtest_v8_vs_v8_1_*.json'), key=lambda p: p.stat().st_mtime, reverse=True)
    for f in files:
        try:
            data = json.loads(f.read_text(encoding='utf-8'))
            key = f'equity_curve_{DEFAULT_BACKTEST_VERSION}'
            if key in data and data[key]:
                return f
        except Exception:
            continue
    return None


def load_backtest_curve(bt_path: Path, version: str = DEFAULT_BACKTEST_VERSION) -> pd.Series:
    """Load the requested backtest equity curve as a daily pandas Series."""
    data = json.loads(bt_path.read_text(encoding='utf-8'))
    key = f'equity_curve_{version}'
    curve = data.get(key)
    if not curve:
        raise ValueError(f'No equity curve {key} found in {bt_path}')
    series = pd.Series({pd.Timestamp(d): float(v) for d, v in curve})
    return series.sort_index().resample('B').last().ffill()


def record_snapshot() -> Optional[Dict]:
    """Record the latest completed-EOD live equity snapshot from portfolio.json."""
    portfolio_path = DATA_DIR / 'portfolio.json'
    if not portfolio_path.exists():
        logger.warning('portfolio.json not found; cannot record snapshot')
        return None

    try:
        portfolio = json.loads(portfolio_path.read_text(encoding='utf-8'))
    except Exception as e:
        logger.error(f'Failed to read portfolio.json: {e}')
        return None

    snapshot_date = last_completed_eod_date()

    # Use the total_value the trading loop saved, or compute from cash + positions.
    equity = portfolio.get('total_value')
    if equity is None:
        equity = portfolio.get('cash', 0.0)
        for t, pos in portfolio.get('positions', {}).items():
            equity += pos.get('shares', 0) * pos.get('entry_price', 0)
    equity = float(equity)

    cash = float(portfolio.get('cash', 0.0))
    positions = len(portfolio.get('positions', {}))

    # Realized P/L for the snapshot date only.
    realized_today = 0.0
    trades_today = 0
    for th in portfolio.get('trade_history', []):
        try:
            ts = th.get('timestamp', '')
            if not ts:
                continue
            ts_date = ts.split('T')[0]
            if ts_date == snapshot_date and th.get('type') == 'SELL':
                realized_today += float(th.get('pnl', 0.0))
                trades_today += 1
        except Exception:
            continue

    snapshot = {
        'date': snapshot_date,
        'equity': round(equity, 2),
        'cash': round(cash, 2),
        'positions': positions,
        'realized_pnl_today': round(realized_today, 2),
        'trades_today': trades_today,
        'source': 'portfolio',
    }

    existing: List[Dict] = []
    if LIVE_EQUITY_FILE.exists():
        try:
            with open(LIVE_EQUITY_FILE, 'r', encoding='utf-8') as f:
                existing = [json.loads(line) for line in f if line.strip()]
        except Exception as e:
            logger.warning(f'Could not read existing {LIVE_EQUITY_FILE}: {e}')

    # Keep the latest run for a given date.
    existing = [s for s in existing if s.get('date') != snapshot_date]
    existing.append(snapshot)
    existing.sort(key=lambda x: x['date'])

    LIVE_EQUITY_FILE.parent.mkdir(exist_ok=True)
    with open(LIVE_EQUITY_FILE, 'w', encoding='utf-8') as f:
        for s in existing:
            f.write(json.dumps(s) + '\n')

    logger.info(f'Recorded live snapshot for {snapshot_date}: equity=${equity:,.2f}')
    return snapshot


def build_live_curve() -> pd.Series:
    """Build a daily live equity curve from the recorded snapshots."""
    if not LIVE_EQUITY_FILE.exists():
        return pd.Series(dtype=float)
    snapshots = []
    with open(LIVE_EQUITY_FILE, 'r', encoding='utf-8') as f:
        for line in f:
            if not line.strip():
                continue
            try:
                s = json.loads(line)
                snapshots.append((pd.Timestamp(s['date']), float(s['equity'])))
            except Exception:
                continue
    if not snapshots:
        return pd.Series(dtype=float)
    series = pd.Series({d: v for d, v in snapshots}).sort_index()
    return series.resample('B').last().ffill()


def load_backtest_summary(bt_path: Path, version: str = DEFAULT_BACKTEST_VERSION) -> Dict:
    data = json.loads(bt_path.read_text(encoding='utf-8'))
    return data.get(version, {})


def live_trade_stats(portfolio: Dict) -> Dict:
    """Compute realized trade statistics from portfolio.json trade_history."""
    sells = [t for t in portfolio.get('trade_history', []) if t.get('type') == 'SELL']
    if not sells:
        return {}
    pnls = [float(t.get('pnl_pct', 0.0)) for t in sells]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p <= 0]
    win_rate = len(wins) / len(pnls) * 100 if pnls else 0.0
    avg_win = float(np.mean(wins)) if wins else 0.0
    avg_loss = float(np.mean(losses)) if losses else 0.0
    pf = (sum(wins) / abs(sum(losses))) if losses and sum(losses) != 0 else (999.0 if wins else 0.0)
    return {
        'total_trades': len(sells),
        'win_rate': win_rate,
        'avg_win': avg_win,
        'avg_loss': avg_loss,
        'profit_factor': pf,
        'realized_pnl': sum(float(t.get('pnl', 0.0)) for t in sells),
    }


def compare_curves(live: pd.Series, backtest: pd.Series, version: str) -> Optional[Dict]:
    """Compare live equity curve to the backtest curve over the live window."""
    if live.empty or backtest.empty:
        return None

    # Align backtest values to each live date (last valid backtest value <= live date).
    bt_aligned = backtest.reindex(live.index, method='ffill')
    valid = bt_aligned.notna()
    if not valid.any():
        return None

    # Baseline is the first live date that has a backtest value.
    first_idx = live.index[valid][0]
    live_window = live[live.index >= first_idx]
    bt_window = bt_aligned[bt_aligned.index >= first_idx].dropna()

    if live_window.empty or bt_window.empty:
        return None

    # Rebase both to 100 at the baseline.
    baseline_live = live_window.iloc[0]
    baseline_bt = bt_window.iloc[0]
    live_rebased = (live_window / baseline_live) * 100
    bt_rebased = (bt_window / baseline_bt) * 100

    live_ret = live_rebased.iloc[-1] - 100
    bt_ret = bt_rebased.iloc[-1] - 100
    divergence = live_ret - bt_ret

    def max_dd(s: pd.Series) -> float:
        return float(((s - s.cummax()) / s.cummax()).min() * 100)

    live_dd = max_dd(live_rebased)
    bt_dd = max_dd(bt_rebased)

    diff_series = live_rebased - bt_rebased
    max_divergence = float(diff_series.max())
    min_divergence = float(diff_series.min())

    start = live_window.index[0]
    end = live_window.index[-1]
    days = max((end - start).days, 1)
    years = days / 365.25
    live_cagr = ((live_window.iloc[-1] / live_window.iloc[0]) ** (1 / years) - 1) * 100 if years > 0 else 0.0
    bt_cagr = ((bt_window.iloc[-1] / bt_window.iloc[0]) ** (1 / years) - 1) * 100 if years > 0 else 0.0

    return {
        'start_date': str(start.date()),
        'end_date': str(end.date()),
        'live_return_pct': round(live_ret, 2),
        'backtest_return_pct': round(bt_ret, 2),
        'divergence_pct': round(divergence, 2),
        'max_divergence_pct': round(max_divergence, 2),
        'min_divergence_pct': round(min_divergence, 2),
        'live_cagr_pct': round(live_cagr, 2),
        'backtest_cagr_pct': round(bt_cagr, 2),
        'live_max_dd_pct': round(live_dd, 2),
        'backtest_max_dd_pct': round(bt_dd, 2),
        'trading_days': int(days),
    }


def write_alert(message: str):
    """Log a divergence alert to file and logger."""
    logger.warning(message)
    ALERT_LOG.parent.mkdir(exist_ok=True)
    with open(ALERT_LOG, 'a', encoding='utf-8') as f:
        f.write(f"{datetime.now().isoformat()} {message}\n")
    try:
        notifier = EmailNotifier()
        notifier.send_email(
            'VolatilityHunter Live/Backtest Divergence Alert',
            message
        )
    except Exception as e:
        logger.warning(f'Email alert failed: {e}')


def main() -> int:
    logger.info('=' * 70)
    logger.info('LIVE vs BACKTEST RECONCILIATION')
    logger.info('=' * 70)

    snapshot = record_snapshot()
    if not snapshot:
        logger.error('Could not record live snapshot; aborting')
        return 1

    bt_path = get_latest_backtest_path()
    if not bt_path:
        logger.error('No backtest curve JSON found in logs/')
        logger.error('Run: python scripts/export_backtest_curves.py')
        return 1
    logger.info(f'Using backtest: {bt_path}')

    try:
        bt_curve = load_backtest_curve(bt_path, DEFAULT_BACKTEST_VERSION)
        bt_summary = load_backtest_summary(bt_path, DEFAULT_BACKTEST_VERSION)
    except Exception as e:
        logger.error(f'Failed to load backtest: {e}')
        return 1

    live_curve = build_live_curve()
    if live_curve.empty:
        logger.warning('No live equity history yet; only snapshot recorded')
        return 0

    comp = compare_curves(live_curve, bt_curve, DEFAULT_BACKTEST_VERSION)
    if comp is None:
        logger.warning('Could not align live and backtest curves; backtest may be stale. Run export_backtest_curves.py after update_data.')
        return 0

    portfolio_path = DATA_DIR / 'portfolio.json'
    portfolio = json.loads(portfolio_path.read_text(encoding='utf-8')) if portfolio_path.exists() else {}
    live_stats = live_trade_stats(portfolio)

    print()
    print('=' * 70)
    print(f'LIVE vs BACKTEST ({DEFAULT_BACKTEST_VERSION})')
    print('=' * 70)
    print(f"Live window        : {comp['start_date']} -> {comp['end_date']} ({comp['trading_days']} days)")
    print(f"Live return        : {comp['live_return_pct']:+.2f}%")
    print(f"Backtest return    : {comp['backtest_return_pct']:+.2f}%")
    print(f"Divergence (live - backtest): {comp['divergence_pct']:+.2f}%")
    print(f"Max/Min divergence : {comp['max_divergence_pct']:+.2f}% / {comp['min_divergence_pct']:+.2f}%")
    print(f"Live CAGR          : {comp['live_cagr_pct']:.2f}%")
    print(f"Backtest CAGR      : {comp['backtest_cagr_pct']:.2f}%")
    print(f"Live max DD        : {comp['live_max_dd_pct']:.2f}%")
    print(f"Backtest max DD    : {comp['backtest_max_dd_pct']:.2f}%")
    print()
    if live_stats:
        print('LIVE TRADE STATS (realized SELLs)')
        print(f"  Total trades : {live_stats['total_trades']}")
        print(f"  Win rate     : {live_stats['win_rate']:.1f}%")
        print(f"  Avg win      : {live_stats['avg_win']:.2f}%")
        print(f"  Avg loss     : {live_stats['avg_loss']:.2f}%")
        print(f"  Profit factor: {live_stats['profit_factor']:.2f}")
        print(f"  Realized P/L : ${live_stats['realized_pnl']:,.2f}")
        print()
        if bt_summary:
            print('BACKTEST EXPECTED STATS')
            print(f"  Total trades : {int(bt_summary.get('total_trades', 0))}")
            print(f"  Win rate     : {bt_summary.get('win_rate', 0):.1f}%")
            print(f"  Avg win      : {bt_summary.get('avg_win', 0):.2f}%")
            print(f"  Avg loss     : {bt_summary.get('avg_loss', 0):.2f}%")
            print(f"  Profit factor: {bt_summary.get('profit_factor', 0):.2f}")
            print()
    print('=' * 70)

    alerts = []
    if comp['divergence_pct'] < -5.0:
        alerts.append(f"ALERT: live return is {comp['divergence_pct']:+.2f}% below backtest (threshold -5%)")
    if comp['live_max_dd_pct'] < comp['backtest_max_dd_pct'] - 10.0:
        alerts.append(f"ALERT: live max drawdown {comp['live_max_dd_pct']:.2f}% is >10pp deeper than backtest {comp['backtest_max_dd_pct']:.2f}%")
    if live_stats and live_stats['win_rate'] < bt_summary.get('win_rate', 0) * 0.7:
        alerts.append(f"ALERT: live win rate {live_stats['win_rate']:.1f}% is <70% of backtest {bt_summary.get('win_rate', 0):.1f}%")
    if live_stats and live_stats['avg_loss'] < bt_summary.get('avg_loss', 0) * 1.5:
        alerts.append(f"ALERT: live avg loss {live_stats['avg_loss']:.2f}% is much worse than backtest {bt_summary.get('avg_loss', 0):.2f}%")

    if alerts:
        print('\n'.join(alerts))
        for a in alerts:
            write_alert(a)
    else:
        print('No material divergence detected.')

    logger.info('Reconciliation complete')
    return 0


if __name__ == '__main__':
    sys.exit(main())
