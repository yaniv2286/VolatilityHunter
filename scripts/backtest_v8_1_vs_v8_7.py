"""
backtest_v8_1_vs_v8_7.py
========================
Ranking experiment: does the ORDER in which same-day candidates are filled
matter? Cash caps usable slots (~5), so when more tickers qualify than slots
exist, the score function decides which get in.

The v8.1 per-ticker backtest generates the trade universe once; each trade is
enriched with entry-day indicator values. Equity curves are then rebuilt under
different intra-day orderings:

  arrival  - baseline harness order (alphabetical within a day)
  stoch    - current live score: 0.6*annual_normalized + 0.4*(1-|K-56|/24)
  momentum - 20-day momentum, descending
  rsi      - rsi_8, descending
  volume   - volume / volume_sma (surge ratio), descending
  combo    - mean of momentum-rank and volume-rank percentiles
  reverse  - live composite score ascending (worst first; harm check)
  random   - deterministic hash shuffle per day (arrival-vs-random check)

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
from src.strategy_v7_2 import add_indicators_v7_2

logging.basicConfig(level=logging.WARNING, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('backtest_v81_v87')

DATA_DIR   = ROOT / 'data'
OUTPUT_DIR = ROOT / 'logs'
OUTPUT_DIR.mkdir(exist_ok=True)

INITIAL_CAPITAL   = 100_000.0
MAX_POSITIONS     = 10
POSITION_SIZE_PCT = 0.20
MIN_ROWS          = 300
SECTOR_MAX        = 3
REGIME_MAX_POS    = 3

RANK_MODES = ['arrival', 'stoch', 'momentum', 'rsi', 'volume', 'combo',
              'reverse', 'random', 'random2', 'random3']


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
    close_col = get_col(spy_df, ['adjClose', 'Close', 'close'])
    if close_col is None:
        return pd.Series(dtype=bool)
    spy_df = add_indicators_v7_2(spy_df.copy())
    if 'sma_200' not in spy_df.columns:
        return pd.Series(dtype=bool)
    return spy_df[close_col] > spy_df['sma_200']


def get_sector(ticker: str) -> str:
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


def enrich_trades(trades: List[dict], df: pd.DataFrame) -> None:
    """Attach entry-day ranking inputs to each trade record in place."""
    close_col = get_col(df, ['adjClose', 'Close', 'close'])
    vol_col   = get_col(df, ['Volume', 'volume', 'adjVolume'])
    if close_col is None or vol_col is None or not trades:
        return
    dfi = add_indicators_v7_2(df)
    close  = dfi[close_col]
    mom20  = close.pct_change(20)
    annual = close.pct_change(252)
    k      = dfi['stoch_k']   if 'stoch_k'   in dfi else pd.Series(np.nan, index=dfi.index)
    rsi    = dfi['rsi_8']     if 'rsi_8'     in dfi else pd.Series(np.nan, index=dfi.index)
    vsma   = dfi['volume_sma'] if 'volume_sma' in dfi else pd.Series(np.nan, index=dfi.index)
    vol    = dfi[vol_col]
    for t in trades:
        try:
            dt = pd.Timestamp(t['entry_date'])
            if dt not in dfi.index:
                continue
            k_v    = float(k.loc[dt])
            mom_v  = float(mom20.loc[dt])
            rsi_v  = float(rsi.loc[dt])
            ann_v  = float(annual.loc[dt])
            vol_r  = float(vol.loc[dt] / vsma.loc[dt]) if vsma.loc[dt] else np.nan
            # live composite: 0.6*annual_normalized + 0.4*stoch_score
            if np.isfinite(ann_v) and np.isfinite(k_v):
                ann_norm = (min(max(ann_v, -0.5), 1.0) + 0.5) / 1.5
                t['score_stoch'] = 0.6 * ann_norm + 0.4 * (1.0 - abs(k_v - 56) / 24)
            else:
                t['score_stoch'] = np.nan
            t['score_momentum'] = mom_v  if np.isfinite(mom_v) else np.nan
            t['score_rsi']      = rsi_v  if np.isfinite(rsi_v) else np.nan
            t['score_volume']   = vol_r  if np.isfinite(vol_r) else np.nan
        except Exception as e:
            logger.debug(f"enrich {t.get('ticker')} {t.get('entry_date')}: {e}")


def build_equity_curve(all_trades: List[dict], spy_regime: pd.Series,
                       rank_mode: str) -> pd.Series:
    """v8.1 equity curve; same-day entries ordered by `rank_mode` score."""
    if not all_trades:
        return pd.Series([INITIAL_CAPITAL])

    if rank_mode == 'combo':
        # percentile ranks within each entry_date cohort, then average
        by_day: Dict[str, List[dict]] = {}
        for t in all_trades:
            by_day.setdefault(t['entry_date'], []).append(t)
        for day, group in by_day.items():
            moms = pd.Series({id(t): (t.get('score_momentum')
                                      if np.isfinite(t.get('score_momentum', np.nan))
                                      else -1e9) for t in group})
            vols = pd.Series({id(t): (t.get('score_volume')
                                      if np.isfinite(t.get('score_volume', np.nan))
                                      else -1e9) for t in group})
            combo = moms.rank(pct=True) + vols.rank(pct=True)
            for t in group:
                t['_rank'] = float(combo.loc[id(t)])
        keyf = lambda t: (t['entry_date'], -t.get('_rank', 0))
    elif rank_mode == 'arrival':
        keyf = lambda t: t['entry_date']          # stable: alphabetical (baseline)
    elif rank_mode == 'reverse':
        keyf = lambda t: (t['entry_date'],
                          (t.get('score_stoch')
                           if np.isfinite(t.get('score_stoch', np.nan)) else 1e9))
    elif rank_mode.startswith('random'):
        import zlib
        salt = rank_mode.encode()                  # random / random2 / random3 seeds
        # deterministic per-(day, ticker) hash - reproducible shuffle
        keyf = lambda t: (t['entry_date'],
                          zlib.crc32(salt + f"{t['ticker']}|{t['entry_date']}".encode()))
    else:
        field = f'score_{rank_mode}'
        keyf = lambda t: (t['entry_date'],
                          -(t.get(field) if np.isfinite(t.get(field, np.nan)) else -1e9))

    trades = sorted(all_trades, key=keyf)
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

        entry_dt = pd.Timestamp(t['entry_date'])
        if spy_regime.empty or entry_dt not in spy_regime.index:
            is_bull = True
        else:
            is_bull = bool(spy_regime.loc[entry_dt])
        max_pos_now = MAX_POSITIONS if is_bull else REGIME_MAX_POS

        sector       = t.get('sector', 'Unknown')
        sector_count = sum(1 for p in active if p.get('sector') == sector)
        if len(active) >= max_pos_now or sector_count >= SECTOR_MAX:
            continue

        vol_scale = t.get('vol_scale', 1.0)
        allocated = equity * POSITION_SIZE_PCT * dd_scale * vol_scale
        if allocated > 0:
            active.append({'exit_date': t['exit_date'], 'pnl_pct': t['pnl_pct'],
                           'allocated': allocated, 'sector': sector})
            curve.append((t['entry_date'], equity))

    for pos in sorted(active, key=lambda x: x['exit_date']):
        gain   = pos['allocated'] * (1 + pos['pnl_pct'] / 100)
        equity = equity - pos['allocated'] + gain
        curve.append((pos['exit_date'], equity))

    ec = pd.Series([v for _, v in curve],
                   index=pd.to_datetime([d for d, _ in curve])).sort_index()
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
    cutoff5 = ec.index[-1] - pd.DateOffset(years=5)
    ec5     = ec[ec.index >= cutoff5]
    cagr5   = 0.0
    if len(ec5) > 1:
        yrs5  = max((ec5.index[-1] - ec5.index[0]).days / 365.25, 0.01)
        cagr5 = ((float(ec5.iloc[-1]) / float(ec5.iloc[0])) ** (1 / yrs5)) - 1
    return {'final_equity': final, 'cagr': cagr * 100, 'cagr_5yr': cagr5 * 100,
            'max_drawdown': dd * 100, 'sharpe': sharpe, 'years': years}


def main():
    t0 = time.time()
    parquet_files = sorted(DATA_DIR.glob('*.parquet'))
    print("=" * 76)
    print("VOLATILITYHUNTER BACKTEST: v8.1 RANKING EXPERIMENT (v8.7)")
    print(f"Universe: {len(parquet_files)} tickers | Capital: ${INITIAL_CAPITAL:,.0f}")
    print(f"Rank modes: {RANK_MODES}")
    print("=" * 76)

    spy_regime = pd.Series(dtype=bool)
    spy_path = DATA_DIR / 'SPY.parquet'
    if spy_path.exists():
        spy_df = load_ticker(spy_path)
        if spy_df is not None:
            spy_regime = build_spy_regime(spy_df)
            print(f"\nSPY regime: {int(spy_regime.sum())} bull / {int((~spy_regime).sum())} bear days")

    all_trades = []
    loaded = skipped = 0
    print(f"\nPass 1 - per-ticker backtests + score enrichment ({len(parquet_files)} tickers)...")
    for i, fpath in enumerate(parquet_files):
        if (i + 1) % 300 == 0:
            print(f"  {i+1}/{len(parquet_files)} | {len(all_trades)} trades")
        df = load_ticker(fpath)
        if df is None or len(df) < MIN_ROWS:
            skipped += 1
            continue
        if get_col(df, ['adjClose', 'Close', 'close']) is None:
            skipped += 1
            continue
        ticker = fpath.stem.upper()
        trades = backtest_ticker_v8_1(ticker, df, spy_sma200=spy_regime,
                                    sector=get_sector(ticker))
        enrich_trades(trades, df)
        all_trades.extend(trades)
        loaded += 1

    print(f"  Done: {loaded} tickers | {skipped} skipped | {len(all_trades)} trades")
    if not all_trades:
        print("ERROR: No trades generated.")
        return 1

    # Contention stats: how often does same-day demand exceed slots?
    from collections import Counter
    per_day = Counter(t['entry_date'] for t in all_trades)
    busy = sum(v for d, v in per_day.items() if v > MAX_POSITIONS)
    print(f"  Signal-days with >{MAX_POSITIONS} candidates: "
          f"{sum(1 for v in per_day.values() if v > MAX_POSITIONS)} "
          f"({busy} excess signals)")

    print("\nPass 2 - equity curves per ranking mode...")
    results = {}
    for mode in RANK_MODES:
        ec = build_equity_curve(all_trades, spy_regime, mode)
        results[mode] = calc_metrics(ec, all_trades)
        m = results[mode]
        print(f"  {mode:<9} CAGR {m['cagr']:6.2f}% | 5yr {m['cagr_5yr']:6.2f}% | "
              f"DD {m['max_drawdown']:7.2f}% | Sharpe {m['sharpe']:.2f} | "
              f"final ${m['final_equity']/1000:,.0f}k")

    print("\n" + "=" * 76)
    base = results['arrival']
    best = max((m for m in RANK_MODES
                if m not in ('arrival', 'reverse')
                and not m.startswith('random')),
               key=lambda m: results[m]['cagr'])
    print(f"Best vs baseline('arrival'): '{best}' "
          f"CAGR {results[best]['cagr'] - base['cagr']:+.2f}% | "
          f"DD {results[best]['max_drawdown'] - base['max_drawdown']:+.2f} | "
          f"Sharpe {results[best]['sharpe'] - base['sharpe']:+.2f}")
    live = results['stoch']
    print(f"Current live ranking ('stoch') vs arrival: "
          f"CAGR {live['cagr'] - base['cagr']:+.2f}% | "
          f"DD {live['max_drawdown'] - base['max_drawdown']:+.2f}")
    print("=" * 76)

    out = {'generated': pd.Timestamp.now().isoformat(),
           'experiment': 'v8.7 ranking modes on v8.1 trade universe',
           'rank_modes': results, 'total_trades': len(all_trades)}
    ts = pd.Timestamp.now().strftime('%Y%m%d_%H%M')
    out_path = OUTPUT_DIR / f"backtest_v8_1_vs_v8_7_ranking_{ts}.json"
    with open(out_path, 'w') as f:
        json.dump(out, f, indent=2)
    print(f"\nResults saved: {out_path}")
    print(f"Total time: {time.time() - t0:.0f}s")
    return 0


if __name__ == '__main__':
    sys.exit(main())
