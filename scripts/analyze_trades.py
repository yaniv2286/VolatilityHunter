"""Trade forensics: enrich every backtest trade with entry-day context and
segment winners vs losers.

Usage:
  python scripts/analyze_trades.py \
      --trades reports/backtest_v8.1_..._trades.csv \
      --snapshot data/research/snapshot_1998_20261022 \
      [--out reports/forensics_v81.csv]

For each SELL record, finds its matching BUY (FIFO per ticker), pulls the
signal-day features from the frozen snapshot (stoch_k/d, distance above
SMA200, 252-day momentum, volume surge ratio, ATR%, bars of history,
SPY bull/bear regime), then reports:
  - feature means for big winners (top 5%), ordinary winners, losers
  - outcome rates bucketed by each entry feature (quartiles)
  - exit-reason anatomy per outcome bucket
Writes the enriched per-trade table to --out.
"""
import argparse
import json
import os
import sys
from pathlib import Path

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import BacktestData


def pair_trades(tr: pd.DataFrame) -> pd.DataFrame:
    """Match SELL rows to BUY rows FIFO per ticker."""
    tr = tr.copy()
    tr['date'] = pd.to_datetime(tr['date'])
    buys = tr[tr['type'] == 'BUY']
    sells = tr[tr['type'] == 'SELL']
    queues = {}
    for _, b in buys.iterrows():
        queues.setdefault(b['ticker'], []).append(b)
    rows = []
    for _, s in sells.iterrows():
        q = queues.get(s['ticker'])
        if not q:
            continue
        b = q[0]
        shares = s['shares']
        # FIFO consume for full exits; partial exits keep residual
        rows.append({
            'ticker': s['ticker'], 'entry_date': b['date'],
            'exit_date': s['date'], 'entry_px': b['price'],
            'exit_px': s['price'], 'pnl': s['pnl'],
            'pnl_pct': s['pnl_pct'], 'exit_reason': s['reason'],
            'entry_reason': b.get('reason', ''),
            'hold_days': (s['date'] - b['date']).days,
            'shares': shares, 'entry_atr': b.get('atr', np.nan)})
        if s.get('fraction', 1.0) >= 1.0:
            q.pop(0)
    return pd.DataFrame(rows)


def entry_features(data: BacktestData, ticker: str, date) -> dict:
    """Signal-day context from tier-1 arrays; NaNs when unavailable."""
    dates = data._date_ns.get(ticker)
    a = data._arr.get(ticker)
    out = {}
    if dates is None or a is None:
        return out
    ts = pd.Timestamp(date).value
    idx = np.searchsorted(dates, ts)
    if idx >= len(dates) or dates[idx] != ts:
        return out
    i = int(idx)
    adj = 'adjClose' in a
    cl = a['adjClose'] if adj else a['close']
    vol = a['volume']
    def g(name):
        return a[name][i] if name in a else np.nan
    c = cl[i]
    out['stoch_k'] = g('stoch_k')
    out['stoch_d'] = g('stoch_d')
    sma200 = g('sma_200')
    out['pct_above_sma200'] = (c / sma200 - 1) * 100 \
        if np.isfinite(sma200) and sma200 > 0 else np.nan
    if i >= 252 and np.isfinite(cl[i - 252]) and cl[i - 252] > 0:
        out['mom_1yr'] = (c / cl[i - 252] - 1) * 100
    else:
        out['mom_1yr'] = np.nan
    if i >= 20 and np.isfinite(cl[i - 20]) and cl[i - 20] > 0:
        out['mom_20d'] = (c / cl[i - 20] - 1) * 100
    else:
        out['mom_20d'] = np.nan
    vsma = g('volume_sma')
    out['vol_surge'] = vol[i] / vsma if np.isfinite(vsma) and vsma > 0 else np.nan
    atr = g('atr')
    out['atr_pct'] = atr / c * 100 if np.isfinite(atr) and c > 0 else np.nan
    out['hist_bars'] = i
    out['log_mktcap_proxy'] = np.log10(c * max(vsma, 1.0)) \
        if np.isfinite(vsma) else np.nan   # price*vol ~ dollar-volume
    return out


def spy_regime(data: BacktestData, date) -> float:
    dates = data._date_ns.get('SPY')
    a = data._arr.get('SPY')
    if dates is None or a is None or 'sma_200' not in a:
        return np.nan
    ts = pd.Timestamp(date).value
    idx = np.searchsorted(dates, ts)
    if idx >= len(dates):
        return np.nan
    if dates[idx] != ts:
        idx -= 1          # last completed SPY bar before entry date
        if idx < 0:
            return np.nan
    cl = a['adjClose'] if 'adjClose' in a else a['close']
    return 1.0 if cl[idx] > a['sma_200'][idx] else 0.0


def bucket_stats(df: pd.DataFrame, feat: str) -> pd.DataFrame:
    d = df.dropna(subset=[feat])
    if len(d) < 50:
        return None
    try:
        d = d.copy()
        d['q'] = pd.qcut(d[feat], 4, duplicates='drop')
    except ValueError:
        return None
    g = d.groupby('q', observed=True)
    return pd.DataFrame({
        'n': g.size(),
        'win%': g['pnl_pct'].apply(lambda s: (s > 0).mean() * 100),
        'avg_ret%': g['pnl_pct'].apply(lambda s: s.mean() * 100),
        'big_win%': g['pnl_pct'].apply(lambda s: (s > 0.25).mean() * 100),
        'avg_loss%': g['pnl_pct'].apply(
            lambda s: s[s <= 0].mean() * 100),
        'pf': g['pnl'].apply(
            lambda s: s[s > 0].sum() / max(-s[s <= 0].sum(), 1e-9)),
        'net_$': g['pnl'].sum()})


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--trades', required=True)
    ap.add_argument('--snapshot', required=True)
    ap.add_argument('--out', default='')
    args = ap.parse_args()

    tr = pd.read_csv(args.trades)
    pairs = pair_trades(tr)
    print(f'matched {len(pairs)} buy->sell pairs')

    snap = Path(args.snapshot)
    manifest = json.loads((snap / 'manifest.json').read_text())
    tickers = sorted(t for t, r in manifest['records'].items()
                     if r.get('status') == 'ok')
    data = BacktestData(snap / 'prices', tickers)
    uniq = pairs['ticker'].unique()
    for t in uniq:
        data._ensure(t)

    feats = []
    for _, r in pairs.iterrows():
        f = entry_features(data, r['ticker'], r['entry_date'])
        f['spy_bull'] = spy_regime(data, r['entry_date'])
        feats.append(f)
    df = pd.concat([pairs.reset_index(drop=True),
                    pd.DataFrame(feats)], axis=1)
    df['exit_key'] = df['exit_reason'].str.replace(r'\d.*', '', regex=True)

    if args.out:
        df.to_csv(args.out, index=False)
        print('enriched trades ->', args.out)

    # ---- outcome segmentation ----
    df['bucket'] = np.where(df['pnl_pct'] > 0.25, 'BIG_WIN(>25%)',
                    np.where(df['pnl_pct'] > 0, 'win', 'loss'))
    num = ['stoch_k', 'pct_above_sma200', 'mom_1yr', 'mom_20d', 'vol_surge',
           'atr_pct', 'hist_bars', 'log_mktcap_proxy', 'spy_bull',
           'hold_days', 'entry_atr']
    print('\n== means by outcome bucket ==')
    print(df.groupby('bucket')[num + ['pnl_pct']].mean().round(3).to_string())

    print('\n== exit-reason mix by bucket ==')
    print(pd.crosstab(df['exit_key'], df['bucket'],
                      normalize='columns').round(3).to_string())

    print('\n== quartile analysis (does the feature predict outcome?) ==')
    for f in ['stoch_k', 'pct_above_sma200', 'mom_1yr', 'vol_surge',
              'atr_pct', 'hist_bars', 'log_mktcap_proxy', 'spy_bull']:
        tab = bucket_stats(df, f)
        if tab is None:
            continue
        print(f'\n--- {f} ---')
        print(tab.round(2).to_string())
    return 0


if __name__ == '__main__':
    sys.exit(main())
