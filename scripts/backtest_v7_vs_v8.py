"""
backtest_v7_vs_v8.py
====================
Side-by-side comparison backtest: strategy v7.2 vs v8 on all 2,147 tickers.
Outputs a clear table showing CAGR, drawdown, Sharpe, win rate for both.
Does NOT modify production code. Read-only.
Exit code 0 = completed successfully.
"""

import sys
import os
import time
import traceback
import logging
from pathlib import Path
from typing import List, Dict

import numpy as np
import pandas as pd

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from src.strategy_v7_2 import add_indicators_v7_2
from src.strategy_v8 import backtest_ticker_v8

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backtest_compare')

DATA_DIR   = ROOT / 'data'
OUTPUT_DIR = ROOT / 'logs'
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Shared constants ───────────────────────────────────────────────────────────
INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_ROWS          = 300

# ── V7 parameters ─────────────────────────────────────────────────────────────
V7_HARD_STOP     = 0.05
V7_OVERBOUGHT    = 70.0
V7_STOCH_LOW     = 32.0
V7_STOCH_HIGH    = 80.0
V7_VOLUME_SURGE  = 1.5
V7_CAGR_FILTER   = 0.15
V7_LIQUIDITY_MIN = 500_000


def get_col(df, candidates):
    for c in candidates:
        if c in df.columns:
            return c
    return None


def load_ticker(path: Path):
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


def backtest_ticker_v7(ticker: str, df: pd.DataFrame) -> List[dict]:
    """V7.2 single-ticker backtest — exact copy of production logic."""
    try:
        close_col  = get_col(df, ['adjClose', 'Close', 'close'])
        volume_col = get_col(df, ['Volume', 'volume', 'adjVolume'])
        if close_col is None or volume_col is None:
            return []

        df = add_indicators_v7_2(df.copy())
        for col in ['stoch_k', 'stoch_d', 'sma_200', 'sma_25', 'volume_sma', 'atr']:
            if col not in df.columns:
                df[col] = np.nan

        close  = df[close_col].values.astype(float)
        volume = df[volume_col].values.astype(float)
        k      = df['stoch_k'].values.astype(float)
        d      = df['stoch_d'].values.astype(float)
        sma200 = df['sma_200'].values.astype(float)
        sma25  = df['sma_25'].values.astype(float)
        vsma   = df['volume_sma'].values.astype(float)
        atr    = df['atr'].values.astype(float)
        dates  = df.index
        n      = len(close)

        if n < MIN_ROWS:
            return []

        annual_ret = np.full(n, np.nan)
        for i in range(252, n):
            if close[i - 252] > 0:
                annual_ret[i] = (close[i] / close[i - 252]) - 1

        buy_mask = (
            (k >= V7_STOCH_LOW) & (k <= V7_STOCH_HIGH) &
            (close > sma200) &
            (volume >= vsma * V7_VOLUME_SURGE) &
            (annual_ret >= V7_CAGR_FILTER) &
            ((close * volume) >= V7_LIQUIDITY_MIN) &
            np.isfinite(close) & np.isfinite(k)
        )

        standard_sell = (((k < d) & (k > V7_OVERBOUGHT)) | (close < sma200))
        power_cond    = (k > 80) & np.isfinite(sma25) & (close > sma25)
        is_power      = power_cond & np.roll(power_cond, 1)
        is_power[0]   = False
        power_sell    = (close < sma25) | (close < atr * 3.0)
        sell_mask     = np.where(is_power, power_sell, standard_sell)

        trades      = []
        in_position = False
        entry_i     = 0
        entry_price = 0.0

        for i in range(1, n):
            if not in_position:
                if buy_mask[i]:
                    in_position = True
                    entry_i     = i
                    entry_price = close[i]
            else:
                exit_reason = None
                if entry_price > 0 and (close[i] - entry_price) / entry_price <= -V7_HARD_STOP:
                    exit_reason = 'Hard stop'
                elif sell_mask[i]:
                    exit_reason = 'Signal exit'
                if exit_reason:
                    pnl_pct = (close[i] - entry_price) / entry_price * 100
                    trades.append({
                        'ticker':      ticker,
                        'entry_date':  str(dates[entry_i].date()),
                        'exit_date':   str(dates[i].date()),
                        'entry_price': float(entry_price),
                        'exit_price':  float(close[i]),
                        'pnl_pct':     float(pnl_pct),
                        'reason':      exit_reason,
                    })
                    in_position = False

        if in_position and entry_price > 0:
            pnl_pct = (close[-1] - entry_price) / entry_price * 100
            trades.append({
                'ticker':      ticker,
                'entry_date':  str(dates[entry_i].date()),
                'exit_date':   str(dates[-1].date()),
                'entry_price': float(entry_price),
                'exit_price':  float(close[-1]),
                'pnl_pct':     float(pnl_pct),
                'reason':      'End of data',
            })

        return trades

    except Exception as e:
        logger.debug(f"v7 {ticker}: {e}")
        return []


def build_equity_curve(all_trades: List[dict]) -> pd.Series:
    """Portfolio equity curve with compounding + drawdown scaling."""
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    trades  = sorted(all_trades, key=lambda t: t['entry_date'])
    equity  = INITIAL_CAPITAL
    slots   = MAX_POSITIONS
    curve   = [(trades[0]['entry_date'], equity)]
    active  = []
    hwm     = equity

    def close_expired(cur_date):
        nonlocal equity, slots
        still_open = []
        for pos in active:
            if pos['exit_date'] <= cur_date:
                gain    = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
                equity  = equity - pos['allocated'] + gain
                slots  += 1
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

        if slots > 0:
            allocated = equity * POSITION_SIZE_PCT * dd_scale
            if allocated > 0:
                active.append({'exit_date': t['exit_date'],
                               'pnl_pct': t['pnl_pct'],
                               'allocated': allocated})
                slots -= 1
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

    # 5-year slice
    cutoff5  = ec.index[-1] - pd.DateOffset(years=5)
    ec5      = ec[ec.index >= cutoff5]
    tr5      = trades if not ec5.empty else []
    cutoff5_str = str(cutoff5.date())
    tr5      = [t for t in trades if t['entry_date'] >= cutoff5_str]
    cagr5    = 0.0
    if len(ec5) > 1:
        yrs5  = max((ec5.index[-1] - ec5.index[0]).days / 365.25, 0.01)
        cagr5 = ((float(ec5.iloc[-1]) / float(ec5.iloc[0])) ** (1 / yrs5)) - 1

    return {
        'final_equity':  final,
        'total_return':  (final / INITIAL_CAPITAL - 1) * 100,
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


def print_comparison(m7: dict, m8: dict):
    def delta(v8, v7, higher_is_better=True):
        d = v8 - v7
        sign = '+' if d >= 0 else ''
        marker = ''
        if higher_is_better:
            marker = ' [+]' if d > 0 else (' [-]' if d < 0 else '')
        else:
            marker = ' [+]' if d < 0 else (' [-]' if d > 0 else '')
        return f"{sign}{d:.2f}{marker}"

    print()
    print("=" * 68)
    print("STRATEGY COMPARISON: v7.2  vs  v8")
    print("v8 changes: hard stop -8%, overbought K>78, 20d momentum, re-entry")
    print("=" * 68)
    print(f"{'Metric':<28} {'v7.2':>10} {'v8':>10} {'Delta':>14}")
    print("-" * 68)
    rows = [
        ('26yr CAGR %',        'cagr',         True),
        ('5yr CAGR %',         'cagr_5yr',     True),
        ('Max Drawdown %',     'max_drawdown',  False),
        ('Sharpe Ratio',       'sharpe',        True),
        ('Win Rate %',         'win_rate',      True),
        ('Avg Win %',          'avg_win',       True),
        ('Avg Loss %',         'avg_loss',      False),
        ('Profit Factor',      'profit_factor', True),
        ('Total Trades',       'total_trades',  True),
        ('Final Equity $k',    'final_equity',  True),
    ]
    for label, key, hib in rows:
        v7v = m7.get(key, 0)
        v8v = m8.get(key, 0)
        if key == 'final_equity':
            print(f"  {label:<26} {v7v/1000:>10.1f} {v8v/1000:>10.1f} {delta(v8v/1000, v7v/1000, hib):>14}")
        elif key == 'total_trades':
            print(f"  {label:<26} {int(v7v):>10} {int(v8v):>10}")
        else:
            print(f"  {label:<26} {v7v:>10.2f} {v8v:>10.2f} {delta(v8v, v7v, hib):>14}")
    print("=" * 68)
    print()
    verdict = "v8 IMPROVEMENT" if m8.get('cagr', 0) > m7.get('cagr', 0) else "v7.2 STILL BETTER"
    cagr_d  = m8.get('cagr', 0) - m7.get('cagr', 0)
    dd_d    = m8.get('max_drawdown', 0) - m7.get('max_drawdown', 0)
    print(f"VERDICT: {verdict}")
    print(f"  CAGR delta: {cagr_d:+.2f}%  |  Drawdown delta: {dd_d:+.2f}%")
    print()


def main():
    t0 = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print("=" * 68)
    print("VOLATILITYHUNTER BACKTEST: v7.2 vs v8 COMPARISON")
    print(f"Universe: {len(parquet_files)} tickers | Capital: ${INITIAL_CAPITAL:,.0f}")
    print("=" * 68)

    v7_trades = []
    v8_trades = []
    loaded = skipped = 0

    print(f"\nRunning per-ticker backtests ({len(parquet_files)} tickers)...")
    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(parquet_files)} | v7:{len(v7_trades)} v8:{len(v8_trades)} trades")

        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        if get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue

        v7_trades.extend(backtest_ticker_v7(ticker, df))
        v8_trades.extend(backtest_ticker_v8(ticker, df))
        loaded += 1

    print(f"  Done: {loaded} tickers | {skipped} skipped")
    print(f"  v7 trades: {len(v7_trades)} | v8 trades: {len(v8_trades)}")

    if not v7_trades or not v8_trades:
        print("ERROR: No trades generated.")
        return 1

    print("\nBuilding equity curves...")
    ec7 = build_equity_curve(v7_trades)
    ec8 = build_equity_curve(v8_trades)

    m7 = calc_metrics(ec7, v7_trades)
    m8 = calc_metrics(ec8, v8_trades)

    print_comparison(m7, m8)

    # Save to logs
    import json
    out = {
        'generated': pd.Timestamp.now().isoformat(),
        'v7': m7,
        'v8': m8,
        'delta_cagr': m8.get('cagr', 0) - m7.get('cagr', 0),
        'delta_drawdown': m8.get('max_drawdown', 0) - m7.get('max_drawdown', 0),
    }
    out_path = OUTPUT_DIR / f"backtest_v7_vs_v8_{pd.Timestamp.now().strftime('%Y%m%d_%H%M')}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"Results saved: {out_path}")
    print(f"Total time: {time.time() - t0:.0f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
