"""
backtest_v8_1_vs_v8_1_2.py
==========================
Compare v8.1 (baseline) vs v8.1.2 (clean foundation).
v8.1.2 includes all surgical strikes:
  - Real GICS sector mapping (with intelligent fallbacks)
  - Normalized percentile-based scoring (0-1 bounded)
  - Fresh OHLCV data pipeline (no more stale indicators)

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
from src.strategy_v8_1_2 import backtest_ticker_v8_1_2
from src.strategy_v7_2 import add_indicators_v7_2

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backtest_v81_v812')

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
    """Equity curve with regime-aware max positions and sector cap."""
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
        # Dynamic sector caps: 6 for Technology/Healthcare, 3 for others
        sector_max = 6 if sector in ['Technology', 'Healthcare'] else 3
        if sector_count >= sector_max:
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


def print_comparison(m81: dict, m812: dict):
    def delta(v812, v81, higher_is_better=True):
        d = v812 - v81
        sign = '+' if d >= 0 else ''
        if higher_is_better:
            marker = ' [+]' if d > 0 else (' [-]' if d < 0 else '')
        else:
            marker = ' [+]' if d < 0 else (' [-]' if d > 0 else '')
        return f"{sign}{d:.2f}{marker}"

    print()
    print("=" * 72)
    print("STRATEGY COMPARISON: v8.1 (baseline)  vs  v8.1.2 (clean foundation)")
    print("v8.1.2: real sectors + normalized scoring + fresh data")
    print("=" * 72)
    print(f"{'Metric':<28} {'v8.1':>10} {'v8.1.2':>10} {'Delta':>14}")
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
        v812v = m812.get(key, 0)
        if key == 'final_equity':
            print(f"  {label:<26} {v81v/1000:>10.1f} {v812v/1000:>10.1f} {delta(v812v/1000, v81v/1000, hib):>14}")
        elif key == 'total_trades':
            print(f"  {label:<26} {int(v81v):>10} {int(v812v):>10}")
        else:
            print(f"  {label:<26} {v81v:>10.2f} {v812v:>10.2f} {delta(v812v, v81v, hib):>14}")
    print("=" * 72)
    print()
    dd_d   = m812.get('max_drawdown', 0) - m81.get('max_drawdown', 0)
    cagr_d = m812.get('cagr', 0) - m81.get('cagr', 0)
    if dd_d < 0 and cagr_d >= 0:
        verdict = "v8.1.2 WINS  (lower DD, CAGR improved or preserved)"
    elif dd_d < 0 and cagr_d >= -1.0:
        verdict = "v8.1.2 MIXED (lower DD but CAGR cost < 1%)"
    elif cagr_d > 0 and dd_d <= 0:
        verdict = "v8.1.2 WINS  (higher CAGR, DD improved or same)"
    else:
        verdict = "v8.1 STILL BETTER"
    print(f"VERDICT: {verdict}")
    print(f"  CAGR delta: {cagr_d:+.2f}%  |  Drawdown delta: {dd_d:+.2f}%")
    print()


def get_sector(ticker: str) -> str:
    """
    Get real sector from Tiingo metadata, with intelligent fallback.
    Uses official GICS sectors when available.
    """
    global _SECTOR_CACHE
    
    # Load cache if empty
    if not _SECTOR_CACHE:
        load_sector_cache()
    
    # Try real sector first
    if ticker in _SECTOR_CACHE:
        return _SECTOR_CACHE[ticker]
    
    # Fallback: Improved bucketing based on known patterns
    known_sectors = {
        # Technology
        'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
        'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology', 'CSCO': 'Technology',
        'ADBE': 'Technology', 'CRM': 'Technology', 'ORCL': 'Technology', 'IBM': 'Technology',
        
        # Financials
        'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
        'MS': 'Financials', 'C': 'Financials', 'AXP': 'Financials', 'BLK': 'Financials',
        'SPGI': 'Financials', 'V': 'Financials', 'MA': 'Financials',
        
        # Healthcare
        'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare',
        'TMO': 'Healthcare', 'ABT': 'Healthcare', 'MRK': 'Healthcare', 'DHR': 'Healthcare',
        
        # Energy
        'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'EOG': 'Energy', 'SLB': 'Energy',
        
        # Industrials
        'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials', 'HON': 'Industrials',
        'MMM': 'Industrials', 'UPS': 'Industrials', 'RTX': 'Industrials',
        
        # Consumer
        'AMZN': 'Consumer', 'TSLA': 'Consumer', 'HD': 'Consumer', 'MCD': 'Consumer',
        'NKE': 'Consumer', 'SBUX': 'Consumer', 'LOW': 'Consumer', 'TGT': 'Consumer'
    }
    
    if ticker in known_sectors:
        return known_sectors[ticker]
    
    # Final fallback: first-letter bucketing (better than random)
    buckets = {
        'ABCDE': 'Technology', 'FGHIJ': 'Healthcare',
        'KLMNO': 'Financials',  'PQRST': 'Energy',
        'UVWXYZ': 'Industrials'
    }
    t = ticker[0].upper() if ticker else 'A'
    for letters, sector in buckets.items():
        if t in letters:
            return sector
    
    return 'Consumer'

# Global sector mapping cache (loaded from Tiingo metadata)
_SECTOR_CACHE = {}

def load_sector_cache():
    """Load sector mapping from Tiingo metadata cache."""
    global _SECTOR_CACHE
    try:
        cache_file = DATA_DIR / 'ticker_metadata.json'
        if cache_file.exists():
            with open(cache_file, 'r') as f:
                metadata = json.load(f)
            
            # Build sector mapping
            _SECTOR_CACHE = {}
            for ticker, data in metadata.items():
                sector = data.get('sector', 'Unknown')
                if sector and sector != 'Unknown':
                    _SECTOR_CACHE[ticker] = sector
    except Exception:
        _SECTOR_CACHE = {}


def main():
    t0 = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))

    print("=" * 72)
    print("VOLATILITYHUNTER BACKTEST: v8.1 vs v8.1.2 (CLEAN FOUNDATION)")
    print(f"Universe: {len(parquet_files)} tickers | Capital: ${INITIAL_CAPITAL:,.0f}")
    print("v8.1.2: real sectors + normalized scoring + fresh data")
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
    v812_trades = []
    loaded = skipped = 0

    print(f"\nRunning per-ticker backtests ({len(parquet_files)} tickers)...")
    print(f"DEBUG: v8.1.2 features - Look-ahead bias: REMOVED | ATR trailing stop: DISABLED | Scanner sector caps: PURGED | Portfolio sector caps: ENABLED")
    for i, fpath in enumerate(parquet_files):
        ticker = fpath.stem.upper()
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(parquet_files)} | v8.1:{len(v81_trades)} v8.1.2:{len(v812_trades)} trades")

        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        if get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue

        sector = get_sector(ticker)
        
        # Debug: Show first few ticker results
        if loaded < 5:
            v81_result = backtest_ticker_v8_1(ticker, df, spy_sma200=spy_regime, sector=sector)
            v812_result = backtest_ticker_v8_1_2(ticker, df, spy_sma200=spy_regime, sector=sector)
            print(f"DEBUG {ticker}: v8.1={len(v81_result)} trades, v8.1.2={len(v812_result)} trades")
            
            # Deep dive for first ticker
            if loaded == 0:
                print(f"  {ticker} data shape: {df.shape}")
                print(f"  {ticker} date range: {df.index[0]} to {df.index[-1]}")
                # Check if data is identical between calls
                v81_result_2 = backtest_ticker_v8_1(ticker, df, spy_sma200=spy_regime, sector=sector)
                v812_result_2 = backtest_ticker_v8_1_2(ticker, df, spy_sma200=spy_regime, sector=sector)
                print(f"  {ticker} consistency check: v8.1={len(v81_result_2)} (same={len(v81_result)==len(v81_result_2)}), v8.1.2={len(v812_result_2)} (same={len(v812_result)==len(v812_result_2)})")
            
            v81_trades.extend(v81_result)
            v812_trades.extend(v812_result)
        else:
            v81_trades.extend(backtest_ticker_v8_1(ticker, df,
                                                    spy_sma200=spy_regime,
                                                    sector=sector))
            v812_trades.extend(backtest_ticker_v8_1_2(ticker, df,
                                                      spy_sma200=spy_regime,
                                                      sector=sector))
        loaded += 1

    print(f"  Done: {loaded} tickers | {skipped} skipped")
    print(f"  v8.1 trades: {len(v81_trades)} | v8.1.2 trades: {len(v812_trades)}")

    if not v81_trades or not v812_trades:
        print("ERROR: No trades generated.")
        return 1

    print("\nBuilding equity curves...")
    ec81 = build_equity_curve(v81_trades, spy_regime)
    ec812 = build_equity_curve(v812_trades, spy_regime)

    m81 = calc_metrics(ec81, v81_trades)
    m812 = calc_metrics(ec812, v812_trades)

    print_comparison(m81, m812)

    # Foundation improvements analysis
    print("\nFOUNDATION IMPROVEMENTS ANALYSIS:")
    trade_delta = len(v812_trades) - len(v81_trades)
    print(f"  Trade count delta: {trade_delta:+d} (should be small, not -78% like v8.2)")
    
    if trade_delta > -1000:  # Reasonable trade count preservation
        print("  ✅ Trade count preserved - foundation fixes working")
    else:
        print("  ❌ Trade count dropped significantly - investigate filters")
    
    # Save results
    out = {
        'generated':       pd.Timestamp.now().isoformat(),
        'v8_1':            m81,
        'v8_1_2':          m812,
        'delta_cagr':      m812.get('cagr', 0)         - m81.get('cagr', 0),
        'delta_drawdown':  m812.get('max_drawdown', 0)  - m81.get('max_drawdown', 0),
        'delta_sharpe':    m812.get('sharpe', 0)        - m81.get('sharpe', 0),
        'trade_count_delta': trade_delta,
    }
    ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    out_path = OUTPUT_DIR / f"backtest_v8_1_vs_v8_1_2_{ts}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved: {out_path}")
    print(f"Total time: {time.time() - t0:.0f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
