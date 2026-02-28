"""
VolatilityHunter Full-Universe Portfolio Backtester  (vectorized rewrite)
=========================================================================
- ALL 2,147+ parquet tickers, FULL date range per ticker (up to 26 years)
- Per-ticker vectorized signal generation (no Python loops over dates)
- Portfolio simulation: trade list aggregated from individual ticker results,
  then a shared equity curve built by sorting all trades chronologically.
- 20% position sizing, max 10 simultaneous positions, 8% hard stop.
- ASCII output only (Task Scheduler compatible).
"""

import sys
import os
import time
import traceback
import json
import logging
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Tuple

import pandas as pd
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from src.strategy_v7_2 import add_indicators_v7_2

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('full_backtest')

DATA_DIR   = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'data')))
OUTPUT_DIR = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'logs')))
OUTPUT_DIR.mkdir(exist_ok=True)

# ── Constants ─────────────────────────────────────────────────────────────────
INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
HARD_STOP_PCT     = 0.05     # 5% hard stop — tighter drawdown control
MIN_ROWS          = 300
LIQUIDITY_MIN     = 500_000
VOLUME_SURGE      = 1.5
CAGR_FILTER       = 0.15
STOCH_LOW         = 32.0
STOCH_HIGH        = 80.0
OVERBOUGHT_EXIT   = 70.0


def get_col(df: pd.DataFrame, candidates: list) -> Optional[str]:
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
        # Drop duplicate dates (keep last)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)
        return df
    except Exception as e:
        logger.debug(f"load {path.stem}: {e}")
        return None


def backtest_ticker(ticker: str, df: pd.DataFrame) -> List[dict]:
    """
    Fully vectorized single-ticker backtest.
    Returns list of trade dicts: entry_date, exit_date, entry_price,
    exit_price, pnl_pct, reason.
    Uses a state machine implemented via numpy arrays (no Python date loop).
    """
    try:
        close_col  = get_col(df, ['adjClose', 'Close', 'close'])
        volume_col = get_col(df, ['Volume', 'volume', 'adjVolume'])
        if close_col is None or volume_col is None:
            return []

        df = add_indicators_v7_2(df.copy())
        needed = ['stoch_k', 'stoch_d', 'sma_200', 'volume_sma', 'atr',
                  'sma_25', 'sma_50', 'sma_100']
        for col in needed:
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

        n = len(close)
        if n < 300:
            return []

        # 252-day annual return (CAGR proxy)
        annual_ret = np.full(n, np.nan)
        for i in range(252, n):
            if close[i - 252] > 0:
                annual_ret[i] = (close[i] / close[i - 252]) - 1

        # ── Vectorized buy/sell masks ──────────────────────────────────────
        buy_mask = (
            (k >= STOCH_LOW) & (k <= STOCH_HIGH) &
            (close > sma200) &
            (volume >= vsma * VOLUME_SURGE) &
            (annual_ret >= CAGR_FILTER) &
            ((close * volume) >= LIQUIDITY_MIN) &
            np.isfinite(close) & np.isfinite(k)
        )

        standard_sell = (
            ((k < d) & (k > OVERBOUGHT_EXIT)) |
            (close < sma200)
        )

        power_cond = (k > 80) & np.isfinite(sma25) & (close > sma25)
        is_power   = power_cond & np.roll(power_cond, 1)
        is_power[0] = False

        power_sell = (close < sma25) | (close < atr * 3.0)

        sell_mask = np.where(is_power, power_sell, standard_sell)

        # ── State-machine trade extraction (numpy loop over positions only) ─
        trades = []
        in_position  = False
        entry_i      = 0
        entry_price  = 0.0

        for i in range(1, n):
            if not in_position:
                if buy_mask[i]:
                    in_position = True
                    entry_i     = i
                    entry_price = close[i]
            else:
                exit_reason = None
                # Hard stop
                if entry_price > 0 and (close[i] - entry_price) / entry_price <= -HARD_STOP_PCT:
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
                        'reason':      exit_reason
                    })
                    in_position = False

        # Close open position at last price
        if in_position and entry_price > 0:
            pnl_pct = (close[-1] - entry_price) / entry_price * 100
            trades.append({
                'ticker':      ticker,
                'entry_date':  str(dates[entry_i].date()),
                'exit_date':   str(dates[-1].date()),
                'entry_price': float(entry_price),
                'exit_price':  float(close[-1]),
                'pnl_pct':     float(pnl_pct),
                'reason':      'End of data'
            })

        return trades

    except Exception as e:
        logger.debug(f"backtest_ticker {ticker}: {e}\n{traceback.format_exc()}")
        return []


def build_portfolio_equity_curve(all_trades: List[dict],
                                  fixed_capital: bool = False) -> pd.Series:
    """
    Simulate portfolio-level equity from sorted trade list.
    fixed_capital=False: 20% of current compounding equity per trade (full compounding)
    fixed_capital=True:  20% of fixed INITIAL_CAPITAL per trade (realistic live account)
    Respects MAX_POSITIONS cap.
    """
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    trades = sorted(all_trades, key=lambda t: t['entry_date'])

    equity       = INITIAL_CAPITAL
    open_slots   = MAX_POSITIONS
    equity_curve = [(trades[0]['entry_date'], equity)]
    active: List[dict] = []

    def close_expired(current_date: str):
        nonlocal equity, open_slots
        still_open = []
        for pos in active:
            if pos['exit_date'] <= current_date:
                gain = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
                equity = equity - pos['allocated'] + gain
                open_slots += 1
                equity_curve.append((pos['exit_date'], equity))
            else:
                still_open.append(pos)
        active.clear()
        active.extend(still_open)

    high_water_mark = equity

    for t in trades:
        close_expired(t['entry_date'])

        # Update high-water mark
        if equity > high_water_mark:
            high_water_mark = equity

        # Gradual position size reduction during drawdown (never block entirely)
        # -10% DD -> use 50% of normal size; -20% DD -> use 25% of normal size
        current_dd = (equity - high_water_mark) / high_water_mark if high_water_mark > 0 else 0
        if current_dd < -0.20:
            dd_scale = 0.25
        elif current_dd < -0.10:
            dd_scale = 0.50
        else:
            dd_scale = 1.0

        if open_slots > 0:
            # Fixed capital mode: always allocate % of $100k base, never more
            base = INITIAL_CAPITAL if fixed_capital else equity
            allocated = base * POSITION_SIZE_PCT * dd_scale
            if allocated > 0:
                active.append({
                    'ticker':    t['ticker'],
                    'exit_date': t['exit_date'],
                    'pnl_pct':   t['pnl_pct'],
                    'allocated': allocated
                })
                open_slots -= 1
                equity_curve.append((t['entry_date'], equity))

    active.sort(key=lambda x: x['exit_date'])
    for pos in active:
        gain = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
        equity = equity - pos['allocated'] + gain
        open_slots += 1
        equity_curve.append((pos['exit_date'], equity))

    ec = pd.Series(
        [v for _, v in equity_curve],
        index=pd.to_datetime([d for d, _ in equity_curve])
    ).sort_index()
    return ec


def calc_metrics(equity_curve: pd.Series, all_trades: List[dict]) -> dict:
    if equity_curve.empty or not all_trades:
        return {}

    final_equity = float(equity_curve.iloc[-1])
    start        = equity_curve.index[0]
    end          = equity_curve.index[-1]
    years        = max((end - start).days / 365.25, 0.01)
    total_return = (final_equity / INITIAL_CAPITAL) - 1
    cagr         = ((final_equity / INITIAL_CAPITAL) ** (1 / years)) - 1

    # Resample to daily before drawdown to avoid same-day multi-point artifacts
    daily_eq  = equity_curve.resample('B').last().ffill().dropna()
    roll_max  = daily_eq.cummax()
    drawdown  = (daily_eq - roll_max) / roll_max
    max_dd    = float(drawdown.min())

    daily_ret = daily_eq.pct_change().dropna()
    sharpe    = float((daily_ret.mean() / daily_ret.std()) * 252 ** 0.5) if daily_ret.std() > 0 else 0.0

    winners = [t for t in all_trades if t['pnl_pct'] > 0]
    losers  = [t for t in all_trades if t['pnl_pct'] <= 0]
    win_rate = len(winners) / len(all_trades) * 100 if all_trades else 0

    gross_profit = sum(t['pnl_pct'] for t in winners)
    gross_loss   = abs(sum(t['pnl_pct'] for t in losers)) or 1
    profit_factor = gross_profit / gross_loss

    return {
        'initial_capital': INITIAL_CAPITAL,
        'final_equity':    final_equity,
        'total_return':    total_return * 100,
        'cagr':            cagr * 100,
        'max_drawdown':    max_dd * 100,
        'sharpe_ratio':    sharpe,
        'win_rate':        win_rate,
        'profit_factor':   profit_factor,
        'total_trades':    len(all_trades),
        'winning_trades':  len(winners),
        'losing_trades':   len(losers),
        'avg_win_pct':     float(np.mean([t['pnl_pct'] for t in winners])) if winners else 0,
        'avg_loss_pct':    float(np.mean([t['pnl_pct'] for t in losers]))  if losers  else 0,
        'years_tested':    years
    }


def run_full_universe_backtest():
    t_start = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print("=" * 68)
    print("VOLATILITYHUNTER FULL-UNIVERSE PORTFOLIO BACKTEST")
    print("Strategy : v7.2 Fixed (F1-F6 bugs resolved)")
    print(f"Universe : {len(parquet_files)} tickers")
    print(f"Capital  : ${INITIAL_CAPITAL:,.0f} | Max positions: {MAX_POSITIONS}")
    print("History  : Full range per ticker (up to 26 years)")
    print("=" * 68)

    # ── Step 1: Per-ticker vectorized backtests ────────────────────────────
    print(f"\n[1/3] Running per-ticker backtests ({len(parquet_files)} tickers)...")
    all_trades: List[dict] = []
    loaded = skipped = 0
    ticker_trade_counts: Dict[str, int] = {}

    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 200 == 0:
            print(f"  {i+1}/{len(parquet_files)} tickers | {loaded} valid | "
                  f"{len(all_trades)} trades so far")

        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue

        close_col = get_col(df, ['adjClose', 'Close', 'close'])
        if close_col is None:
            skipped += 1
            continue

        trades = backtest_ticker(ticker, df)
        all_trades.extend(trades)
        ticker_trade_counts[ticker] = len(trades)
        loaded += 1

    print(f"  Done. {loaded} tickers | {skipped} skipped | {len(all_trades)} total trades")

    if not all_trades:
        print("ERROR: No trades generated. Check strategy parameters.")
        sys.exit(1)

    # ── Step 2: Portfolio equity curves (two modes) ───────────────────────
    print(f"\n[2/3] Building portfolio equity curves...")

    # Mode A: Full compounding (shows long-term wealth generation)
    ec_compound = build_portfolio_equity_curve(all_trades, fixed_capital=False)

    # Mode B: Fixed capital (realistic live account, $100k base throughout)
    ec_fixed    = build_portfolio_equity_curve(all_trades, fixed_capital=True)

    # Mode C: Recent 5-year slice on fixed capital (current live conditions)
    cutoff_5yr  = str((pd.Timestamp.now() - pd.DateOffset(years=5)).date())
    trades_5yr  = [t for t in all_trades if t['entry_date'] >= cutoff_5yr]
    ec_5yr      = build_portfolio_equity_curve(trades_5yr, fixed_capital=True)

    print(f"  Compounding  : {len(ec_compound)} pts | "
          f"${ec_compound.iloc[0]:,.0f} -> ${ec_compound.iloc[-1]:,.0f}")
    print(f"  Fixed $100k  : {len(ec_fixed)} pts | "
          f"${ec_fixed.iloc[0]:,.0f} -> ${ec_fixed.iloc[-1]:,.0f}")
    print(f"  Fixed 5yr    : {len(trades_5yr)} trades | "
          f"${ec_5yr.iloc[0]:,.0f} -> ${ec_5yr.iloc[-1]:,.0f}" if trades_5yr
          else "  Fixed 5yr    : no trades in last 5 years")

    # ── Step 3: Metrics & output ───────────────────────────────────────────
    print(f"\n[3/3] Calculating metrics...")
    m_compound = calc_metrics(ec_compound, all_trades)
    m_fixed    = calc_metrics(ec_fixed,    all_trades)
    m_5yr      = calc_metrics(ec_5yr,      trades_5yr) if trades_5yr else {}
    elapsed    = time.time() - t_start

    def print_result_block(label, metrics, trades_list):
        if not metrics:
            print(f"\n  {label}: no data")
            return
        print()
        print("=" * 68)
        print(f"RESULTS: {label}")
        print("=" * 68)
        ec_start = ec_compound.index[0] if 'compound' in label.lower() else \
                   (ec_5yr.index[0] if '5yr' in label.lower() else ec_fixed.index[0])
        ec_end   = ec_compound.index[-1] if 'compound' in label.lower() else \
                   (ec_5yr.index[-1] if '5yr' in label.lower() else ec_fixed.index[-1])
        print(f"  Period             : {metrics.get('years_tested', 0):.1f} years")
        print(f"  Initial capital    : ${metrics['initial_capital']:>12,.2f}")
        print(f"  Final equity       : ${metrics['final_equity']:>12,.2f}")
        print(f"  Total return       : {metrics['total_return']:>+10.2f}%")
        print(f"  CAGR               : {metrics['cagr']:>+10.2f}%   <-- TARGET: >15%")
        print(f"  Max Drawdown       : {metrics['max_drawdown']:>+10.2f}%   <-- TARGET: >-25%")
        print(f"  Sharpe Ratio       : {metrics['sharpe_ratio']:>10.2f}")
        print(f"  Win Rate           : {metrics['win_rate']:>10.1f}%")
        print(f"  Profit Factor      : {metrics['profit_factor']:>10.2f}")
        print(f"  Total trades       : {len(trades_list):>10,}")
        cagr = metrics['cagr']
        mdd  = metrics['max_drawdown']
        status_cagr = "[TARGET HIT]" if cagr >= 15 else ("[NEAR]" if cagr >= 10 else "[BELOW]")
        status_mdd  = "[TARGET HIT]" if mdd >= -25 else "[EXCEEDED]"
        print(f"  CAGR status        : {status_cagr}")
        print(f"  Drawdown status    : {status_mdd}")
        print("=" * 68)

    print_result_block("FULL 25yr COMPOUNDING (wealth generation)",  m_compound, all_trades)
    print_result_block("FULL 25yr FIXED $100k (live account model)", m_fixed,    all_trades)
    if trades_5yr:
        print_result_block("RECENT 5yr FIXED $100k (current conditions)",  m_5yr, trades_5yr)

    print(f"\n  Runtime: {elapsed:.1f}s")

    # Top tickers by trade count
    top_tickers = sorted(ticker_trade_counts.items(), key=lambda x: x[1], reverse=True)[:10]
    print(f"\n  Top 10 most-traded tickers:")
    for t, c in top_tickers:
        t_wins = sum(1 for tr in all_trades if tr['ticker'] == t and tr['pnl_pct'] > 0)
        print(f"    {t:8s}  {c:4d} trades  {t_wins/c*100 if c else 0:.0f}% WR")

    # Save JSON
    out_file = OUTPUT_DIR / f"full_backtest_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(out_file, 'w') as f:
        json.dump({
            'run_timestamp':  datetime.now().isoformat(),
            'compounding_25yr': m_compound,
            'fixed_25yr':       m_fixed,
            'fixed_5yr':        m_5yr,
            'top_trades':   sorted(all_trades, key=lambda x: x['pnl_pct'], reverse=True)[:20],
            'worst_trades': sorted(all_trades, key=lambda x: x['pnl_pct'])[:10]
        }, f, indent=2, default=str)
    print(f"\n  Full results saved: {out_file.name}")
    print("=" * 68)
    return m_5yr if m_5yr else m_compound


if __name__ == '__main__':
    try:
        metrics = run_full_universe_backtest()
        sys.exit(0 if metrics.get('total_trades', 0) > 0 else 1)
    except Exception as e:
        print(f"\nFATAL ERROR: {e}")
        traceback.print_exc()
        sys.exit(1)
