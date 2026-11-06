"""Freedom Trader ('Sweet Spot') backtest comparator.

Deterministic long-only port of the strategy spec in
`freedom_trader_master_devin_handoff.md` (Mostafa Hussein Patreon rules +
Part 6 reference implementation), run on the SAME ledger, execution
model and costs as the corrected v8.1 engine.

Implemented faithfully from the spec:
  - Daily Stoch(10,3,3) and weekly Stoch(19,4,4) on W-FRI resample
    (forward-filled onto the daily index - completed weeks only, no
    lookahead).
  - Sweet spot [32,80]; daily %K rising and (%K>=%D or slope>1.5);
    weekly in-spot aligned up OR PowerStockMode (close>sma25>50>100>200
    AND weekly %K>=80 and %K>=%D).
  - Trap-door veto, flagpole veto (4 green bars & 4d gain >8%),
    snapback veto (>8% above sma25).
  - Candlestick confirmation: bullish engulfing / hammer / tweezer or
    strong close above prior high.
  - Structure: W-breakout / staircase higher-low / close > sma25.
  - SMA hierarchy clearance >=1% to nearest overhead SMA
    (order 100>200>50>25).
  - Conviction sizing LOW 5% / MEDIUM 10% / HIGH 20%, max 4 positions,
    20% equity cash buffer.
  - Stops: entry-candle low / support pivot buffered 0.3%, clipped to
    1.0-3.5%; breakeven ratchet at +2% (evaluated on closes);
    targets: 0.998 * SMA barrier else max(2R, +4%).
  - Stochastic rollover exit: daily %K>80 and %K<%D.
  - 50% retracement routing: oversized signal candle (>2.5% range)
    queues a limit buy at low+0.5*range; fills next open only if
    open <= limit (conservative: no intraday path assumed).

Deliberately excluded (not testable on daily data / user constraints):
  intraday time windows & 15m stoch, bid/ask spread veto, earnings and
  holiday calendars, Yahoo most-actives scanner (universe scanned
  wholesale; liquidity gate already restricts to liquid names),
  SHORT direction (project is long-only).
"""

import hashlib
import logging
import os
import sys
from pathlib import Path
from collections import OrderedDict
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import CorrectedBacktest, price_filename

logger = logging.getLogger(__name__)

SWEET_LO, SWEET_HI = 32.0, 80.0
MIN_VOL30 = 2_000_000.0
MAX_POS = 4
CASH_BUFFER = 0.20
BREAKEVEN_TRIGGER = 0.02


def _stoch(df, k_len, d_len, smooth):
    lo = df['low'].rolling(k_len, min_periods=k_len).min()
    hi = df['high'].rolling(k_len, min_periods=k_len).max()
    raw = 100.0 * (df['close'] - lo) / (hi - lo).replace(0.0, np.nan)
    k = raw.rolling(smooth, min_periods=smooth).mean()
    d = k.rolling(d_len, min_periods=d_len).mean()
    return k, d


def _features(df: pd.DataFrame) -> pd.DataFrame:
    """One-time causal feature build per ticker (no lookahead)."""
    source = df
    df = df[['open', 'high', 'low', 'close', 'volume']].copy()
    scale = pd.Series(1.0, index=df.index)
    if all(c in source.columns for c in ('adjOpen', 'adjHigh', 'adjLow', 'adjClose')):
        scale = source['close'] / source['adjClose']
        for raw, adjusted in (('open', 'adjOpen'), ('high', 'adjHigh'),
                              ('low', 'adjLow'), ('close', 'adjClose')):
            df[raw] = source[adjusted]
    for p in (25, 50, 100, 200):
        df[f'sma_{p}'] = df['close'].rolling(p, min_periods=p).mean()
    df['vol_sma_30'] = df['volume'].rolling(30, min_periods=30).mean()
    df['k1'], df['d1'] = _stoch(df, 10, 3, 3)
    df['k1_slope'] = df['k1'].diff()
    df['d1_slope'] = df['d1'].diff()

    wk = df[['open', 'high', 'low', 'close', 'volume']].resample('W-FRI').agg(
        {'open': 'first', 'high': 'max', 'low': 'min', 'close': 'last',
         'volume': 'sum'}).dropna(subset=['close'])
    wk['kw'], wk['dw'] = _stoch(wk, 19, 4, 4)
    wk['kw_slope'] = wk['kw'].diff()
    df[['kw', 'dw', 'kw_slope']] = wk[['kw', 'dw', 'kw_slope']].reindex(
        df.index, method='ffill')

    o, h, l, c = df['open'], df['high'], df['low'], df['close']
    po, ph, pl, pc = o.shift(), h.shift(), l.shift(), c.shift()
    body, pbody = (c - o).abs(), (pc - po).abs()
    rng = (h - l).replace(0.0, np.nan)
    uw, lw = h - np.maximum(o, c), np.minimum(o, c) - l
    puw, plw = ph - np.maximum(po, pc), np.minimum(po, pc) - pl
    df['bull_engulf'] = ((pc < po) & (c > o) & (c >= po) & (o <= pc)
                         & (body > pbody))
    df['hammer'] = ((lw >= 2.0 * np.maximum(body, 1e-6))
                    & (uw <= 0.15 * rng) & (c >= l + 0.65 * rng))
    body_match = ((body - pbody).abs()
                  <= 0.20 * np.maximum(0.5 * (body + pbody), 1e-4))
    df['bull_tweezer'] = (body_match & (lw >= 1.5 * np.maximum(body, 1e-6))
                          & (plw >= 1.5 * np.maximum(pbody, 1e-6))
                          & ((l - pl).abs() / c <= 0.004) & (c > o))
    df['range_pct'] = (h - l) / c
    df['strong_close'] = (c > o) & (c > ph)

    # 25-bar line-chart structure (W bottom / staircase HL)
    closes = c.values
    n = len(closes)
    w_break = np.zeros(n, bool)
    stair = np.zeros(n, bool)
    support = np.full(n, np.nan)
    for i in range(25, n):
        win = closes[i - 25:i + 1]
        hist = win[:-1]
        mins = [(j, hist[j]) for j in range(1, len(hist) - 1)
                if hist[j] <= hist[j - 1] and hist[j] <= hist[j + 1]]
        if mins:
            support[i] = mins[-1][1]
            if len(mins) >= 2:
                i1, p1 = mins[-2]
                i2, p2 = mins[-1]
                if i2 - i1 >= 2 and p2 >= p1 * 0.995:
                    neck = float(np.max(hist[i1:i2 + 1]))
                    if win[-1] > neck and win[-2] <= neck * 1.005:
                        w_break[i] = True
                    elif win[-1] > p2 and win[-1] > win[-2] and p2 > p1:
                        stair[i] = True
    df['w_break'], df['stair'], df['support'] = w_break, stair, support
    for column in ('open', 'high', 'low', 'close', 'sma_25', 'sma_50',
                   'sma_100', 'sma_200', 'support'):
        df[column] = df[column] * scale
    return df


class FreedomTraderComparator(CorrectedBacktest):
    VALID_ABLATIONS = {
        'weekly',       # weekly Stoch(19,4,4) sweet-spot gate
        'power',        # 80+ power-stock weekly override
        'trapdoor',     # %K<%D gap and falling-%D vetoes
        'flagpole',     # 4 green bars & 4d gain >8% veto
        'snapback',     # >8% above sma25 veto
        'candle',       # bullish candle confirmation gate
        'structure',    # W-break / staircase / close>sma25 gate
        'barrier',      # SMA overhead-clearance veto + barrier targets
        'retracement',  # 50%-retracement limit routing on wide bars
        'breakeven',    # +2% breakeven ratchet
        'rollover',     # stoch rollover exit (K>80, K<D)
        'conviction',   # LOW/MED/HIGH sizing -> flat 10% alloc
        'cashbuffer',   # permanent 20% equity cash buffer -> 0%
    }

    def __init__(self, *args, ablations=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ablations = set(ablations or ())
        bad = self.ablations - self.VALID_ABLATIONS
        if bad:
            raise ValueError(f'unknown ablations: {sorted(bad)}')
        self._feat: "OrderedDict[str, pd.DataFrame]" = OrderedDict()
        self._ft = {}   # ticker -> {'stop','target','be_done'}
        self._gate = {}  # ticker -> (k1 float32, vol_sma30 float32)

    def _off(self, name):
        return name in self.ablations

    def _gate_arrays(self, t):
        """Cached (daily %K(10,3,3) smoothed, vol_sma30) float32 arrays.

        Identical math to the previous per-day slice loop: raw %K uses a
        10-bar high/low window, smoothed by 3 (NaN if any of the 3 raw
        values is NaN); vol_sma30 is a 30-bar rolling mean."""
        g = self._gate.get(t)
        if g is not None:
            return g
        a = self.data._arr.get(t)
        if a is None:
            return None
        adjusted = all(c in a for c in
                       ('adjOpen', 'adjHigh', 'adjLow', 'adjClose'))
        hi = a['adjHigh'] if adjusted else a['high']
        lo = a['adjLow'] if adjusted else a['low']
        cl = a['adjClose'] if adjusted else a['close']
        hi_s = pd.Series(hi).rolling(10, min_periods=10).max()
        lo_s = pd.Series(lo).rolling(10, min_periods=10).min()
        raw = 100.0 * (pd.Series(cl) - lo_s) \
            / (hi_s - lo_s).replace(0.0, np.nan)
        k1s = raw.rolling(3, min_periods=3).mean()
        k1 = k1s.to_numpy(np.float32)
        vs = pd.Series(a['volume']).rolling(30, min_periods=30).mean() \
            .to_numpy(np.float32)
        d1 = k1s.rolling(3, min_periods=3).mean().to_numpy(np.float32)
        ks = k1s.diff().to_numpy(np.float32)
        g = (k1, d1, ks, vs)
        self._gate[t] = g
        return g

    def _features(self, t):
        if t in self._feat:
            self._feat.move_to_end(t)
            return self._feat[t]
        cached = None
        if self.data.indicator_cache:
            source = self.data.prices_dir / price_filename(t)
            key = hashlib.sha256(source.read_bytes() + Path(__file__).read_bytes()).hexdigest()
            cached = self.data.indicator_cache / f'ft_{t.lower()}_{key}.parquet'
        if cached and cached.exists():
            f = pd.read_parquet(cached)
        else:
            # Build OHLCV straight from tier-1 numpy arrays: FT features
            # never use v7_2 indicators, so skip _ensure/_read_frame (and
            # its parquet read + full indicator build) entirely.
            dates = self.data._dates.get(t)
            a = self.data._arr.get(t)
            if dates is None or a is None:
                return None
            df = pd.DataFrame({c: a[c] for c in
                               ('open', 'high', 'low', 'close', 'volume')
                               if c in a}, index=dates)
            f = _features(df)
            if cached:
                temporary = cached.with_suffix(f'.{os.getpid()}.tmp')
                f.to_parquet(temporary)
                os.replace(temporary, cached)
        self._feat[t] = f
        while len(self._feat) > self.data.max_cached:
            self._feat.popitem(last=False)
        return f

    def _eval_long(self, f, i):
        """Return (ok, conviction_pct, stop, target, limit_px, reason)."""
        r = f.iloc[i]
        c = float(r['close'])
        vs = r['vol_sma_30']
        if not np.isfinite(vs) or vs < MIN_VOL30:
            return None
        k, d, ks, ds = r['k1'], r['d1'], r['k1_slope'], r['d1_slope']
        wk, wd, wks = r['kw'], r['dw'], r['kw_slope']
        s25, s50, s100, s200 = r['sma_25'], r['sma_50'], r['sma_100'], r['sma_200']
        vals = (k, d, ks, ds, wk, wd, wks, s25, s50, s100, s200)
        if not all(np.isfinite(v) for v in vals):
            return None

        stacked = c > s25 > s50 > s100 > s200
        power = (not self._off('power')) and stacked and wk >= SWEET_HI \
            and wk >= wd
        weekly_ok = ((SWEET_LO <= wk <= SWEET_HI) and (wk >= wd or wks > 0)) \
            or power
        daily_ok = (SWEET_LO <= k <= SWEET_HI) and ks > 0 \
            and (k >= d or ks > 1.5)
        if not daily_ok or (not self._off('weekly') and not weekly_ok):
            return None
        # trap door
        if not self._off('trapdoor'):
            if k < d and (d - k) > 6.0:
                return None
            if ds < -1.5 and k < d:
                return None
        # snapback + flagpole
        if not self._off('snapback') and (c - s25) / s25 > 0.08:
            return None
        if not self._off('flagpole') and i >= 4:
            rec = f.iloc[i - 3:i + 1]
            green = int((rec['close'] > rec['open']).sum())
            ret4 = c / float(f['close'].iloc[i - 4]) - 1.0
            if green >= 4 and ret4 > 0.08:
                return None
        # candle confirmation
        if not self._off('candle') and not (
                r['bull_engulf'] or r['hammer'] or r['bull_tweezer']
                or r['strong_close']):
            return None
        # structure
        if not self._off('structure') and not (
                r['w_break'] or r['stair'] or c > s25):
            return None
        # SMA barrier clearance >=1% (hierarchy 100>200>50>25)
        barrier = None
        if not self._off('barrier'):
            rank = {100: 0, 200: 1, 50: 2, 25: 3}
            barriers = [(float(r[f'sma_{p}']), p) for p in (100, 200, 50, 25)
                        if np.isfinite(r[f'sma_{p}'])
                        and r[f'sma_{p}'] > c * 1.001]
            if barriers:
                barriers.sort(key=lambda x: (x[0] - c, rank[x[1]]))
                barrier = barriers[0][0]
                if (barrier - c) / c < 0.01:
                    return None
        # conviction
        if self._off('conviction'):
            alloc = 0.10
        else:
            vol_conf = np.isfinite(r['volume']) and r['volume'] >= vs
            if vol_conf and (r['w_break'] or power):
                alloc = 0.20
            else:
                alloc = 0.10 if weekly_ok else 0.05
        # stop: min(candle low, support pivot) -0.3%, clipped 1-3.5%
        raw = min(float(r['low']), float(r['support'])
                  if np.isfinite(r['support']) else float(r['low'])) * 0.997
        dist = float(np.clip((c - raw) / c, 0.01, 0.035))
        stop = c * (1.0 - dist)
        if barrier is not None:
            target = barrier * 0.998
        else:
            target = c * (1.0 + max(2.0 * dist, 0.04))
        limit_px = None
        if not self._off('retracement') and r['range_pct'] > 0.025:
            limit_px = float(r['low']) + 0.5 * (float(r['high'])
                                                - float(r['low']))
        return alloc, stop, target, limit_px

    def _apply_corporate_actions(self, date):
        for t, state in self._ft.items():
            row = self.data.bar(t, date)
            sf = row.get('splitFactor', 1.0) if row is not None else 1.0
            if np.isfinite(sf) and sf > 0 and sf != 1.0:
                state['stop'] /= sf
                state['target'] /= sf
        super()._apply_corporate_actions(date)

    def _signal_pass(self, date, prices):
        ts = pd.Timestamp(date)
        # ---- exits first (EOD approximation: fill next open) ----
        for t, pos in list(self.portfolio['positions'].items()):
            if any(o['ticker'] == t for o in self.pending_sells):
                continue
            row = self.data.bar(t, date)
            if row is None or not np.isfinite(row.get('volume', np.nan)) \
                    or row.get('volume', 0) <= 0:
                self.pending_sells.append({'ticker': t, 'fraction': 1.0,
                                           'reason': 'FT missing/untradeable bar',
                                           'tries': 0})
                continue
            st = self._ft.get(t)
            f = self._features(t)
            if f is None or st is None:
                continue
            i = f.index.searchsorted(ts)
            if i >= len(f.index) or f.index[i] != ts:
                continue
            c = float(f['close'].iloc[i])
            reason = None
            if c <= st['stop']:
                reason = f"FT stop hit (close {c:.2f} <= {st['stop']:.2f})"
            elif c >= st['target']:
                reason = f"FT target hit (close {c:.2f} >= {st['target']:.2f})"
            else:
                k, d = f['k1'].iloc[i], f['d1'].iloc[i]
                if not self._off('rollover') and np.isfinite(k) \
                        and np.isfinite(d) and k > SWEET_HI and k < d:
                    reason = f"FT stoch rollover (K {k:.0f} > 80 below D)"
                elif not self._off('breakeven') and not st['be_done'] and \
                        c >= pos['entry_price'] * (1 + BREAKEVEN_TRIGGER):
                    st['stop'] = max(st['stop'], pos['entry_price'])
                    st['be_done'] = True
            if reason:
                self.pending_sells.append({'ticker': t, 'fraction': 1.0,
                                           'reason': reason, 'tries': 0})
        # ---- entries ----
        n_open = len(self.portfolio['positions'])
        slots = MAX_POS - n_open - len(self.pending_buys)
        if slots <= 0:
            return
        equity = self.ledger.equity_curve[-1].equity \
            if self.ledger.equity_curve else self.ledger.cash
        cands = []
        for t in self.data.tickers:
            if t == 'SPY' or t in self.portfolio['positions'] \
                    or any(o['ticker'] == t for o in self.pending_buys):
                continue
            # cheap exact gate on raw arrays BEFORE building features:
            # bar exists, >=220 bars history, vol_sma30>=2M, daily %K in
            # [32,80] (10,3,3 computed on raw high/low/close slices)
            p = self.data._ptr.get(t)
            dates = self.data._date_ns.get(t)
            a = self.data._arr.get(t)
            if p is None or dates is None or a is None or p < 220:
                continue
            if p >= len(dates) or dates[p] != ts.value:
                continue
            g = self._gate_arrays(t)
            if g is None:
                continue
            k1, d1, ks, vs30 = g[0][p], g[1][p], g[2][p], g[3][p]
            if not np.isfinite(vs30) or vs30 < MIN_VOL30:
                continue
            # full daily_ok: %K in spot, rising, %K>=%D or slope>1.5
            if not (np.isfinite(k1) and np.isfinite(d1)
                    and np.isfinite(ks)
                    and SWEET_LO <= k1 <= SWEET_HI and ks > 0
                    and (k1 >= d1 or ks > 1.5)):
                continue
            f = self._features(t)
            if f is None:
                continue
            i = f.index.searchsorted(ts)
            if i >= len(f.index) or f.index[i] != ts or i < 220:
                continue
            ev = self._eval_long(f, i)
            if ev:
                alloc, stop, target, limit_px = ev
                vol = float(f['volume'].iloc[i])
                cands.append((alloc, -vol, t, stop, target, limit_px))
        cands.sort(key=lambda x: (-x[0], x[1], x[2]))   # higher conviction, then higher volume
        self._sync_cash()
        for alloc, _v, t, stop, target, limit_px in cands[:slots]:
            px = prices.get(t)
            if not px or px <= 0:
                continue
            budget = min(alloc * equity,
                         self.ledger.cash - (
                             0.0 if self._off('cashbuffer')
                             else CASH_BUFFER) * equity)
            shares = int(budget / px)
            if shares <= 0:
                continue
            self.pending_buys.append({
                'ticker': t, 'price': px, 'shares': shares, 'atr': 0.0,
                'score': alloc,
                'reason': f'FT {alloc:.0%} stop={stop:.2f} tgt={target:.2f}',
                'ft_stop': stop, 'ft_target': target,
                'ft_limit': limit_px})

    def _fill_open(self, date):
        # honor 50%-retracement limits: only fill if open <= limit
        kept = []
        for o in self.pending_buys:
            lim = o.pop('ft_limit', None)
            if lim is not None:
                row = self.data.bar(o['ticker'], date)
                op = row.get('open') if row is not None else None
                if op is not None and op > lim:
                    continue  # limit not reached -> order cancelled
            kept.append(o)
        self.pending_buys = kept
        super()._fill_open(date)
        for o in kept:
            t = o['ticker']
            if t in self.portfolio['positions']:
                self._ft[t] = {'stop': o['ft_stop'],
                               'target': o['ft_target'],
                               'be_done': False}

    def _record_sell(self, ticker, shares, fill_px, date, reason, fraction):
        super()._record_sell(ticker, shares, fill_px, date, reason, fraction)
        if ticker not in self.portfolio['positions']:
            self._ft.pop(ticker, None)
