"""
backtest_v8_1_vs_v8_1_1.py
==========================
Compare v8.1 (baseline) vs v8.1.1 (trailing stop ONLY).
This isolates the impact of adding trailing stops for standard positions.

Exit code 0 = completed successfully.
"""

import sys
import os
import time
import json
import logging
from pathlib import Path
from typing import List, Dict, Optional

import numpy as np
import pandas as pd

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from src.strategy_v8_1 import backtest_ticker_v8_1
from src.strategy_v8_1_1 import backtest_ticker_v8_1_1
from src.strategy_v7_2 import add_indicators_v7_2

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backtest_v81_v811')

DATA_DIR   = ROOT / 'data'
OUTPUT_DIR = ROOT / 'logs'
OUTPUT_DIR.mkdir(exist_ok=True)

INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_ROWS          = 300

SECTOR_MAX        = 3
REGIME_MAX_POS    = 3


def get_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_ticker(path: Path) -> Optional[pd.DataFrame]:
    try:
        df = pd.read_parquet(path)
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)
        return df
    except Exception:
        return None


def build_spy_regime(spy_df: pd.DataFrame) -> pd.Series:
    """Returns a boolean Series: True = SPY above its 200-day SMA (bull regime)."""
    close_col = get_col(spy_df, ['adjClose', 'Close', 'close'])
    if close_col is None:
        return pd.Series(dtype=bool)
    spy_df = add_indicators_v7_2(spy_df.copy())
    if 'sma_200' not in spy_df.columns:
        return pd.Series(dtype=bool)
    bull = spy_df[close_col] > spy_df['sma_200']
    return bull


def build_equity_curve(all_trades: List[dict],
                       spy_regime: pd.Series) -> pd.Series:
    """Equity curve with regime-aware max positions and sector cap (same for both versions)."""
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    trades = sorted(all_trades, key=lambda t: t['entry_date'])
    equity = INITIAL_CAPITAL
    curve  = [(trades[0]['entry_date'], equity)]
    active = []
    hwm    = equity

    def close_expired(cur_date):
        nonlocal equity
        still_open = []
        for pos in active:
            if pos['exit_date'] <= cur_date:
                gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
                equity = equity - pos['allocated'] + gain
                curve.append((pos['exit_date'], equity))
            else:
                still_open.append(pos)
        active.clear()
        active.extend(still_open)

    for t in trades:
        close_expired(t['entry_date'])
        if equity > hwm:
            hwm = equity
        dd = (equity - hwm) / hwm if hwm > 0 else 0
        dd_scale = 0.25 if dd < -0.20 else 0.50 if dd < -0.10 else 1.0

        # Regime-aware max positions
        entry_dt = pd.Timestamp(t['entry_date'])
        if spy_regime.empty or entry_dt not in spy_regime.index:
            is_bull = True
        else:
            is_bull = bool(spy_regime.loc[entry_dt])
        max_pos_now = MAX_POSITIONS if is_bull else REGIME_MAX_POS

        open_count  = len(active)
        sector      = t.get('sector', 'Unknown')
        sector_count = sum(1 for p in active if p.get('sector') == sector)

        if open_count >= max_pos_now:
            continue
        if sector_count >= SECTOR_MAX:
            continue

        vol_scale = t.get('vol_scale', 1.0)
        allocated = equity * POSITION_SIZE_PCT * dd_scale * vol_scale
        if allocated > 0:
            active.append({
                'exit_date': t['exit_date'],
                'pnl_pct':   t['pnl_pct'],
                'allocated': allocated,
                'sector':    sector,
            })
            curve.append((t['entry_date'], equity))

    for pos in sorted(active, key=lambda x: x['exit_date']):
        gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
        equity = equity - pos['allocated'] + gain
        curve.append((pos['exit_date'], equity))

    ec = pd.Series(
        [v for _, v in curve],
        index=pd.to_datetime([d for d, _ in curve])
    ).sort_index()
    return ec


def calc_metrics(ec: pd.Series, trades: List[dict]) -> dict:
    if ec.empty or not trades:
        return {}
    final  = float(ec.iloc[-1])
    years  = max((ec.index[-1] - ec.index[0]).days / 365.25, 0.01)
    cagr   = ((final / INITIAL_CAPITAL) ** (1 / years)) - 1

    daily  = ec.resample('B').last().ffill().dropna()
    dd     = float(((daily - daily.cummax()) / daily.cummax()).min())
    ret    = daily.pct_change().dropna()
    sharpe = float((ret.mean() / ret.std()) * 252 ** 0.5) if ret.std() > 0 else 0.0

    winners  = [t for t in trades if t['pnl_pct'] > 0]
    losers   = [t for t in trades if t['pnl_pct'] <= 0]
    win_rate = len(winners) / len(trades) * 100 if trades else 0
    avg_win  = float(np.mean([t['pnl_pct'] for t in winners])) if winners else 0
    avg_loss = float(np.mean([t['pnl_pct'] for t in losers]))  if losers  else 0
    pf_denom = abs(sum(t['pnl_pct'] for t in losers)) or 1
    pf       = sum(t['pnl_pct'] for t in winners) / pf_denom

    cutoff5     = ec.index[-1] - pd.DateOffset(years=5)
    ec5         = ec[ec.index >= cutoff5]
    cutoff5_str = str(cutoff5.date())
    tr5         = [t for t in trades if t['entry_date'] >= cutoff5_str]
    cagr5       = 0.0
    if len(ec5) > 1:
        yrs5  = max((ec5.index[-1] - ec5.index[0]).days / 365.25, 0.01)
        cagr5 = ((float(ec5.iloc[-1]) / float(ec5.iloc[0])) ** (1 / yrs5)) - 1

    return {
        'final_equity':  final,
        'cagr':          cagr * 100,
        'cagr_5yr':      cagr5 * 100,
        'max_drawdown':  dd * 100,
        'sharpe':        sharpe,
        'win_rate':      win_rate,
        'avg_win':       avg_win,
        'avg_loss':      avg_loss,
        'profit_factor': pf,
        'total_trades':  len(trades),
        'years':         years,
    }


def print_comparison(m81: dict, m811: dict):
    def delta(v811, v81, higher_is_better=True):
        d = v811 - v81
        sign = '+' if d >= 0 else ''
        if higher_is_better:
            marker = ' [+]' if d > 0 else (' [-]' if d < 0 else '')
        else:
            marker = ' [+]' if d < 0 else (' [-]' if d > 0 else '')
        return f"{sign}{d:.2f}{marker}"

    print()
    print("=" * 72)
    print("STRATEGY COMPARISON: v8.1 (baseline)  vs  v8.1.1 (trailing stop ONLY)")
    print("v8.1.1 adds: trailing stop for standard positions (2× ATR from highest)")
    print("=" * 72)
    print(f"{'Metric':<28} {'v8.1':>10} {'v8.1.1':>10} {'Delta':>14}")
    print("-" * 72)
    rows = [
        ('26yr CAGR %',     'cagr',          True),
        ('5yr CAGR %',      'cagr_5yr',      True),
        ('Max Drawdown %',  'max_drawdown',   False),
        ('Sharpe Ratio',    'sharpe',         True),
        ('Win Rate %',      'win_rate',       True),
        ('Avg Win %',       'avg_win',        True),
        ('Avg Loss %',      'avg_loss',       False),
        ('Profit Factor',   'profit_factor',  True),
        ('Total Trades',    'total_trades',   True),
        ('Final Equity $k', 'final_equity',   True),
    ]
    for label, key, hib in rows:
        v81v = m81.get(key,  0)
        v811v = m811.get(key, 0)
        if key == 'final_equity':
            print(f"  {label:<26} {v81v/1000:>10.1f} {v811v/1000:>10.1f} {delta(v811v/1000, v81v/1000, hib):>14}")
        elif key == 'total_trades':
            print(f"  {label:<26} {int(v81v):>10} {int(v811v):>10}")
        else:
            print(f"  {label:<26} {v81v:>10.2f} {v811v:>10.2f} {delta(v811v, v81v, hib):>14}")
    print("=" * 72)
    print()
    dd_d   = m811.get('max_drawdown', 0) - m81.get('max_drawdown', 0)
    cagr_d = m811.get('cagr', 0) - m81.get('cagr', 0)
    if dd_d < 0 and cagr_d >= 0:
        verdict = "v8.1.1 WINS  (lower DD, CAGR improved or preserved)"
    elif dd_d < 0 and cagr_d >= -1.0:
        verdict = "v8.1.1 MIXED (lower DD but CAGR cost < 1%)"
    elif cagr_d > 0 and dd_d <= 0:
        verdict = "v8.1.1 WINS  (higher CAGR, DD improved or same)"
    else:
        verdict = "v8.1 STILL BETTER"
    print(f"VERDICT: {verdict}")
    print(f"  CAGR delta: {cagr_d:+.2f}%  |  Drawdown delta: {dd_d:+.2f}%")
    print()


def get_sector(ticker: str) -> str:
    """Simple sector bucket by ticker initial. Replace with GICS CSV for production."""
    buckets = {
        'ABCDE': 'Technology', 'FGHIJ': 'Healthcare',
        'KLMNO': 'Financials',  'PQRST': 'Energy',
        'UVWXYZ': 'Industrials'
    }
    t = ticker[0].upper()
    for letters, sector in buckets.items():
        if t in letters:
            return sector
    return 'Consumer'


def main():
    t0 = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print("=" * 72)
    print("VOLATILITYHUNTER BACKTEST: v8.1 vs v8.1.1 (TRAILING STOP ONLY)")
    print(f"Universe: {len(parquet_files)} tickers | Capital: ${INITIAL_CAPITAL:,.0f}")
    print("v8.1.1: trailing stop for standard positions ONLY")
    print("=" * 72)

    # Load SPY for regime filter
    spy_regime = pd.Series(dtype=bool)
    spy_path = DATA_DIR / 'SPY.parquet'
    if spy_path.exists():
        spy_df = load_ticker(spy_path)
        if spy_df is not None:
            spy_regime = build_spy_regime(spy_df)
            bull_days = int(spy_regime.sum())
            bear_days = int((~spy_regime).sum())
            print(f"\nSPY regime loaded: {bull_days} bull days / {bear_days} bear days")
    else:
        print("\nWARN: SPY.parquet not found — regime filter disabled (all bull)")

    v81_trades = []
    v811_trades = []
    loaded = skipped = 0

    print(f"\nRunning per-ticker backtests ({len(parquet_files)} tickers)...")
    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(parquet_files)} | v8.1:{len(v81_trades)} v8.1.1:{len(v811_trades)} trades")

        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        if get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue

        sector = get_sector(ticker)
        v81_trades.extend(backtest_ticker_v8_1(ticker, df,
                                                spy_sma200=spy_regime,
                                                sector=sector))
        v811_trades.extend(backtest_ticker_v8_1_1(ticker, df,
                                                  spy_sma200=spy_regime,
                                                  sector=sector))
        loaded += 1

    print(f"  Done: {loaded} tickers | {skipped} skipped")
    print(f"  v8.1 trades: {len(v81_trades)} | v8.1.1 trades: {len(v811_trades)}")

    if not v81_trades or not v811_trades:
        print("ERROR: No trades generated.")
        return 1

    print("\nBuilding equity curves...")
    ec81 = build_equity_curve(v81_trades, spy_regime)
    ec811 = build_equity_curve(v811_trades, spy_regime)

    m81 = calc_metrics(ec81, v81_trades)
    m811 = calc_metrics(ec811, v811_trades)

    print_comparison(m81, m811)

    # Trailing stop analysis
    trailing_stops = [t for t in v811_trades if 'Trailing stop' in t.get('reason', '')]
    if trailing_stops:
        ts_avg = float(np.mean([t['pnl_pct'] for t in trailing_stops]))
        ts_winners = sum(1 for t in trailing_stops if t['pnl_pct'] > 0)
        print(f"v8.1.1 Trailing stop trades: {len(trailing_stops)} | avg P&L: {ts_avg:.2f}% | winners: {ts_winners}")
        
        # Compare same trades without trailing stop
        # Find trades that would have been affected
        standard_exits = [t for t in v81_trades if t['ticker'] in [ts['ticker'] for ts in trailing_stops]]
        if standard_exits:
            standard_avg = float(np.mean([t['pnl_pct'] for t in standard_exits]))
            print(f"Same trades in v8.1 (no trailing stop): avg P&L: {standard_avg:.2f}%")
            print(f"Trailing stop improvement: {ts_avg - standard_avg:+.2f}% per trade")

    # Save results
    out = {
        'generated':       pd.Timestamp.now().isoformat(),
        'v8_1':            m81,
        'v8_1_1':          m811,
        'delta_cagr':      m811.get('cagr', 0)         - m81.get('cagr', 0),
        'delta_drawdown':  m811.get('max_drawdown', 0)  - m81.get('max_drawdown', 0),
        'delta_sharpe':    m811.get('sharpe', 0)        - m81.get('sharpe', 0),
        'trailing_stop_count': len(trailing_stops),
        'trade_count_delta': len(v811_trades) - len(v81_trades),
    }
    ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    out_path = OUTPUT_DIR / f"backtest_v8_1_vs_v8_1_1_{ts}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved: {out_path}")
    print(f"Total time: {time.time() - t0:.0f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
