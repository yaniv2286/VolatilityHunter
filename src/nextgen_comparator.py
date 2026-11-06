"""Next-generation engine comparator (v10 research family).

Literature-grounded momentum engine on the SAME corrected ledger,
execution model and costs as v8.1/FT comparators. Designed so each
experiment is one config dict (--strategy nextgen --ng-config '{...}'),
registered in reports/NG_REGISTER.md.

Implemented components (all causal, all from tier-1 numpy arrays):
  - mom12_1 : 252-day return skipping last 21 days (Jegadeesh-Titman 12-1)
  - tsmom   : own 252-day return (Moskowitz-Ooi-Pedersen time-series mom)
  - w52h    : close / 252-day high (George & Hwang 2004)
  - vol20   : annualized 20-day realized vol
  - gap_evt : |open/prev_close-1| > thresh + volume > N*vol_sma30 (PEAD proxy)
  - spy_regime : SPY close vs SMA200 (bear shelter)

Portfolio layer:
  - Long book: top_n names by rank metric on monthly rebalance; hold
    with a rank-decay buffer (sell when rank falls below top_n*decay_mult).
  - Short book: bear regime buys inverse ETFs (level1 SH/PSQ,
    level2 SDS/SQQQ) - ordinary long buys, cash-ledger legal.
  - Sizing: fixed fraction OR vol-target (equity*risk_pct / ATR14$),
    capped per position; optional cash buffer.
  - Trade mgmt: hard stop, optional ATR trailing stop on closes,
    rank-decay exits on rebalance days, PEAD max-hold timer.

Deliberately excluded: true margin shorts (cash-only rule), intraday
fills, options, point-in-time earnings dates.
"""

import json
import logging
import os
import sys
from typing import Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import CorrectedBacktest

logger = logging.getLogger(__name__)

INVERSE_L1 = ('SH', 'PSQ')           # 1x inverse S&P/Nasdaq (2006+)
INVERSE_L2 = ('SDS', 'SQQQ')         # 2x inverse (2008/2010+)
VOL_PROXY = ('VXX', 'UVXY', 'VIXY', 'SVXY')
SHELTER = ('TLT', 'GLD')
ETF_SET = set(INVERSE_L1 + INVERSE_L2 + VOL_PROXY + SHELTER) | {'SPY'}

DEFAULT_CFG = {
    'lookback': 252, 'skip': 21,           # 12-1 formation
    'rank_metric': 'mom12_1',              # mom12_1|w52h|tsmom
    'top_n': 10, 'decay_mult': 2.0,        # hold buffer = top_n*decay
    'tsmom_gate': False,                   # require tsmom > 0
    'mom_min': 0.0,                        # minimum rank-metric value
    'min_dollar_vol': 2e6,                 # 30d avg dollar-volume floor
    'per_pos_cap': 0.10,
    'sizing': 'fixed_frac',                # fixed_frac|vol_target
    'risk_pct': 0.01,                      # vol_target: equity risk/pos
    'cash_buffer': 0.0,
    'hard_stop': 0.20,
    'trailing_atr': None,                  # None or e.g. 3.0
    'bear_mode': 'cash',                   # cash|inverse|none
    'inverse_level': 1,                    # 1=SH/PSQ 2=SDS/SQQQ
    'inverse_alloc': 0.30,                 # fraction of equity in bear
    'pead': False, 'gap_thresh': 0.08, 'gap_vol_mult': 3.0,
    'pead_max_hold': 60,
    # data-hygiene gates (junk bars destroy momentum rankings)
    'min_price': 1.0,            # exclude penny/garbage prices
    'max_1day_ret': 10.0,        # |1d ret| > 10x in lookback -> untradeable
    'max_zero_vol_share': 0.10,  # >10% zero-volume days in lookback -> skip
    'exclude_tickers': (),
}


class NextgenComparator(CorrectedBacktest):
    def __init__(self, *args, ng_config=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.c = dict(DEFAULT_CFG)
        self.c.update(ng_config or {})
        self._rebalance_days = self._rebalance_set()
        self._inv_tickers = INVERSE_L1 if self.c['inverse_level'] == 1 \
            else INVERSE_L2

    # ── calendar helpers ──────────────────────────────────────────────
    def _rebalance_set(self):
        cal = self.data.calendar
        if cal is None:
            return set()
        months = cal.to_period('M')
        return {int(i) for i in range(len(cal))
                if i == 0 or months[i] != months[i - 1]}

    def _is_rebalance(self, i):
        return i in self._rebalance_days

    # ── per-ticker metric extraction (arrays only, causal) ───────────
    def _metrics(self, t, i):
        """(mom12_1, tsmom, w52h, vol20, vsma30, dollar_vol, gap_ret)
        at index i in _arr, NaNs when insufficient history."""
        a = self.data._arr.get(t)
        if a is None:
            return None
        lb, sk = self.c['lookback'], self.c['skip']
        if i < lb:
            return None
        cl = a['adjClose'] if 'adjClose' in a else a['close']
        c, base, ref = cl[i], cl[i - lb], cl[i - sk]
        if not all(np.isfinite(v) for v in (c, base, ref)) or base <= 0:
            return None
        # hygiene: current bar + lookback sanity
        p = self.c
        if c < p['min_price']:
            return None
        win = cl[i - lb + 1:i + 1]
        prev = cl[i - lb:i]
        with np.errstate(divide='ignore', invalid='ignore'):
            rets = win / np.where(prev > 0, prev, np.nan) - 1.0
        if np.nanmax(np.abs(rets)) > p['max_1day_ret']:
            return None
        v = a['volume']
        if i >= 29:
            vsma = float(np.mean(v[i - 29:i + 1]))
            if vsma <= 0 or (v[i - lb + 1:i + 1] <= 0).mean() \
                    > p['max_zero_vol_share']:
                return None
        else:
            vsma = np.nan
        mom = ref / base - 1.0
        ts = c / base - 1.0
        w52 = c / np.nanmax(cl[i - lb + 1:i + 1]) if i >= lb - 1 else np.nan
        r20 = cl[i - 19:i + 1] / cl[i - 20:i] - 1.0
        vol20 = float(np.nanstd(r20) * np.sqrt(252)) if len(r20) >= 20 else np.nan
        dvol = c * vsma if np.isfinite(vsma) else np.nan
        return mom, ts, w52, vol20, vsma, dvol

    def _spy_regime(self, i):
        """(bull_bool, tsmom_spy) at SPY bar index i."""
        a = self.data._arr.get('SPY')
        if a is None:
            return True, np.nan
        cl = a['adjClose'] if 'adjClose' in a else a['close']
        sma = a.get('sma_200')
        c = cl[i]
        bull = bool(np.isfinite(sma[i]) and c > sma[i]) \
            if sma is not None else True
        lb = self.c['lookback']
        ts = c / cl[i - lb] - 1.0 if i >= lb and cl[i - lb] > 0 else np.nan
        return bull, ts

    def _atr14(self, t, i):
        a = self.data._arr.get(t)
        if a is None or i < 15:
            return np.nan
        hi = a['adjHigh'] if 'adjHigh' in a else a['high']
        lo = a['adjLow'] if 'adjLow' in a else a['low']
        cl = a['adjClose'] if 'adjClose' in a else a['close']
        tr = np.maximum(hi[i - 13:i + 1] - lo[i - 13:i + 1],
                        np.abs(hi[i - 13:i + 1] - cl[i - 14:i]))
        tr = np.maximum(tr, np.abs(lo[i - 13:i + 1] - cl[i - 14:i]))
        return float(np.nanmean(tr))

    def _ptr_of(self, t, date):
        """index of `date` in t's array, or None."""
        p = self.data._ptr.get(t)
        dates = self.data._date_ns.get(t)
        if p is None or dates is None or p >= len(dates):
            return None
        return p if dates[p] == pd.Timestamp(date).value else None

    # ── signal pass ───────────────────────────────────────────────────
    def _signal_pass(self, date, prices):
        ts = pd.Timestamp(date)
        day_i = self.data.calendar.get_loc(ts)
        bull, spy_ts = self._spy_regime(self._ptr_of('SPY', date) or 0)
        positions = self.portfolio['positions']
        stock_pos = [t for t in positions if t not in self._inv_tickers]
        inv_pos = [t for t in positions if t in self._inv_tickers]
        pend = {o['ticker'] for o in self.pending_sells}

        # 1) daily exits: hard stop / ATR trail / PEAD timer (all books)
        for t, pos in list(positions.items()):
            if t in pend:
                continue
            px = prices.get(t)
            if not px:
                continue
            entry = pos['entry_price']
            pnl = px / entry - 1.0
            reason = None
            if pnl <= -self.c['hard_stop']:
                reason = f'NG hard stop {pnl:.1%}'
            elif pos.get('pead') and \
                    (ts.date() - pd.Timestamp(pos['entry_date']).date()).days \
                    >= self.c['pead_max_hold']:
                reason = 'NG PEAD max hold'
            elif self.c['trailing_atr']:
                hi_mark = pos.get('highest_price', entry)
                if px > hi_mark:
                    pos['highest_price'] = px
                    hi_mark = px
                p = self._ptr_of(t, date)
                atr = self._atr14(t, p) if p is not None else np.nan
                if np.isfinite(atr) and px < hi_mark - \
                        self.c['trailing_atr'] * atr:
                    reason = f'NG ATR trail ({px:.2f}<{hi_mark - self.c["trailing_atr"]*atr:.2f})'
            if reason:
                self.pending_sells.append({'ticker': t, 'fraction': 1.0,
                                           'reason': reason, 'tries': 0})
        pend = {o['ticker'] for o in self.pending_sells}

        # 2) bear regime -> inverse book
        bear = (not bull) or (np.isfinite(spy_ts) and spy_ts < 0)
        if self.c['bear_mode'] == 'inverse':
            if bear and not inv_pos:
                self._buy_inverse(date, prices)
            elif not bear:
                for t in inv_pos:
                    if t not in pend:
                        self.pending_sells.append(
                            {'ticker': t, 'fraction': 1.0,
                             'reason': 'NG regime -> bull', 'tries': 0})
        elif self.c['bear_mode'] == 'cash' and bear and self._is_rebalance(day_i):
            pass  # long book just takes no new entries on rebalance

        # 3) monthly rebalance of the long book
        if self._is_rebalance(day_i):
            self._rebalance(date, prices, bull, pend)

        # 4) PEAD entries (daily scan, only when enabled)
        if self.c['pead'] and bull:
            self._pead_scan(date, prices, pend)

    def _buy_inverse(self, date, prices):
        equity = self.ledger.equity_curve[-1].equity \
            if self.ledger.equity_curve else self.ledger.cash
        budget = equity * self.c['inverse_alloc'] / len(self._inv_tickers)
        for t in self._inv_tickers:
            px = prices.get(t)
            if not px or px <= 0:
                continue
            shares = int(budget / px)
            if shares > 0:
                self.pending_buys.append({
                    'ticker': t, 'price': px, 'shares': shares, 'atr': 0.0,
                    'score': 1.0, 'reason': 'NG inverse bear book'})

    def _rank_universe(self, date):
        """list of (metric, -dvol, ticker) for eligible names, sorted."""
        p = self.c
        cands = []
        excl = set(p.get('exclude_tickers', ()))
        for t in self.data.tickers:
            if t in ETF_SET or t in excl \
                    or t in self.portfolio['positions'] \
                    or any(o['ticker'] == t for o in self.pending_buys):
                continue
            i = self._ptr_of(t, date)
            if i is None:
                continue
            m = self._metrics(t, i)
            if m is None:
                continue
            mom, ts, w52, vol20, vsma, dvol = m
            if not np.isfinite(dvol) or dvol < p['min_dollar_vol']:
                continue
            if p['tsmom_gate'] and not (np.isfinite(ts) and ts > 0):
                continue
            metric = {'mom12_1': mom, 'w52h': w52, 'tsmom': ts}[p['rank_metric']]
            if not np.isfinite(metric) or metric < p['mom_min']:
                continue
            cands.append((metric, -dvol, t))
        cands.sort(key=lambda x: (-x[0], x[1], x[2]))
        return cands

    def _rebalance(self, date, prices, bull, pend):
        p = self.c
        cands = self._rank_universe(date)
        top = [t for *_x, t in cands[:p['top_n']]]
        buffer = {t for *_x, t in cands[:int(p['top_n'] * p['decay_mult'])]}
        positions = self.portfolio['positions']
        # sells: names that decayed out of the buffer zone (or bear->cash)
        for t, pos in list(positions.items()):
            if t in self._inv_tickers or t in pend or pos.get('pead'):
                continue
            if t not in buffer or (p['bear_mode'] == 'cash' and not bull):
                self.pending_sells.append(
                    {'ticker': t, 'fraction': 1.0,
                     'reason': 'NG rank decay' if t in buffer or bull
                     else 'NG bear -> cash', 'tries': 0})
        pend = {o['ticker'] for o in self.pending_sells}
        if not bull:
            return   # no new long entries while bear
        equity = self.ledger.equity_curve[-1].equity \
            if self.ledger.equity_curve else self.ledger.cash
        slots = p['top_n'] - len([t for t in positions
                                  if t not in self._inv_tickers]) \
            - len(self.pending_buys)
        committed = 0.0
        cap_cash = self.ledger.cash - p['cash_buffer'] * equity
        for *_m, t in cands:
            if slots <= 0:
                break
            if t in pend or t in positions:
                continue
            px = prices.get(t)
            if not px or px <= 0:
                continue
            if p['sizing'] == 'vol_target':
                i = self._ptr_of(t, date)
                atr = self._atr14(t, i) if i is not None else np.nan
                if not np.isfinite(atr) or atr <= 0:
                    shares = int(p['per_pos_cap'] * equity / px)
                else:
                    shares = int(equity * p['risk_pct'] / atr)
                    shares = min(shares, int(p['per_pos_cap'] * equity / px))
            else:
                shares = int(p['per_pos_cap'] * equity / px)
            if shares <= 0:
                continue
            est = shares * px * (1 + self.slip)
            if committed + est > cap_cash:
                continue
            committed += est
            self.pending_buys.append({
                'ticker': t, 'price': px, 'shares': shares, 'atr': 0.0,
                'score': 1.0, 'reason': f'NG rank {p["rank_metric"]}'})
            slots -= 1

    def _pead_scan(self, date, prices, pend):
        p = self.c
        if len([t for t in self.portfolio['positions']]) >= 12:
            return
        equity = self.ledger.equity_curve[-1].equity \
            if self.ledger.equity_curve else self.ledger.cash
        cap_cash = self.ledger.cash - p['cash_buffer'] * equity
        for t in self.data.tickers:
            if t in ETF_SET or t in self.portfolio['positions'] \
                    or t in pend \
                    or any(o['ticker'] == t for o in self.pending_buys):
                continue
            i = self._ptr_of(t, date)
            if i is None or i < 30:
                continue
            a = self.data._arr[t]
            op = a['adjOpen'] if 'adjOpen' in a else a['open']
            cl = a['adjClose'] if 'adjClose' in a else a['close']
            v = a['volume']
            prev = cl[i - 1]
            if not np.isfinite(prev) or prev <= 0:
                continue
            gap = op[i] / prev - 1.0
            vsma = np.mean(v[i - 29:i + 1])
            if not np.isfinite(vsma) or vsma <= 0 \
                    or v[i] < p['gap_vol_mult'] * vsma \
                    or gap < p['gap_thresh']:
                continue
            px = prices.get(t)
            if not px:
                continue
            shares = int(p['per_pos_cap'] * equity / px)
            if shares <= 0 or shares * px > cap_cash:
                continue
            self.pending_buys.append({
                'ticker': t, 'price': px, 'shares': shares, 'atr': 0.0,
                'score': gap, 'reason': f'NG PEAD gap {gap:.1%}',
                'pead': True})

    # mark PEAD positions on fill
    def _record_buy(self, ticker, shares, fill_px, date, cand, atr):
        super()._record_buy(ticker, shares, fill_px, date, cand, atr)
        if cand.get('pead') and ticker in self.portfolio['positions']:
            self.portfolio['positions'][ticker]['pead'] = True


def parse_ng_config(arg: str) -> dict:
    """'{}' inline JSON or '@file' path."""
    if not arg:
        return {}
    if arg.startswith('@'):
        return json.loads(open(arg[1:]).read())
    return json.loads(arg)
