"""Corrected daily backtest engine.

Drives src/portfolio_ledger.py through the SAME decision functions the
live paper loop uses (src/strategy_engine.py): check_exits,
promote_power_stocks, scan_universe, can_enter, calc_position_size.

Timing model (disclosed approximation of the live 09:35 ET loop):
  - Signals are computed on completed EOD bar T.
  - Queued orders fill at the next session's raw OPEN (T+1), with a
    configurable slippage haircut and per-share commission.
  - Orders that cannot fill (no bar, zero volume) are dropped after
    MAX_PENDING_SESSIONS sessions; positions that can never be sold
    (zombie/delisted bars) are force-liquidated at their last traded
    price and flagged.
  - Dividends (divCash) and splits (splitFactor) are applied at the
    ex-date session BEFORE that session's fills.
  - All decisions see only data <= signal bar T (point-in-time slices);
    indicators are causal so full-history precomputation is equivalent.

Cash rules: buys are funded from SETTLED cash only (T+1 settlement of
sale proceeds), enforced by the ledger — the legacy "invest 200% of
equity" bug is impossible here.
"""

import logging
import os
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

import numpy as np
import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.portfolio_ledger import PortfolioLedger
from src.strategy_v7_2 import add_indicators_v7_2
from src.strategy_engine import (
    DEFAULT_VERSION,
    MIN_PRICE, MIN_LIQUIDITY, VOLUME_SURGE,
    CAGR_FILTER, STOCH_LOW, STOCH_HIGH,
    check_exits as engine_check_exits,
    scan_universe as engine_scan_universe,
    promote_power_stocks,
    update_highest_prices,
    update_high_water_mark,
    can_enter,
    calc_position_size,
    get_regime_max_positions,
    get_params,
)

logger = logging.getLogger(__name__)

# Windows reserved device names cannot be used as filenames
_WIN_RESERVED = {'con', 'prn', 'aux', 'nul',
                 *(f'com{i}' for i in range(1, 10)),
                 *(f'lpt{i}' for i in range(1, 10))}


def price_filename(ticker: str) -> str:
    """Canonical parquet filename for a ticker (shared with downloader)."""
    name = ticker.lower()
    if name in _WIN_RESERVED:
        name += '_'
    return name + '.parquet'

MAX_PENDING_SESSIONS = 20   # days an unfilled exit order may retry


class BacktestData:
    """Point-in-time data access over a research snapshot directory."""

    def __init__(self, prices_dir: Path, tickers: List[str],
                 max_cached: int = 800):
        self.prices_dir = Path(prices_dir)
        self.tickers = list(tickers)
        # Tier 1 (all tickers): dates index + numpy column arrays used by
        # prefilter, session prices and bar lookups. Bounded memory.
        self._dates: Dict[str, pd.DatetimeIndex] = {}
        self._ptr: Dict[str, int] = {}
        self._arr: Dict[str, Dict[str, np.ndarray]] = {}
        # Tier 2 (LRU): full indicator DataFrames, materialized only for
        # tickers the shared engine actually reads via load_fn/asof.
        self._frames: "OrderedDict[str, pd.DataFrame]" = OrderedDict()
        self._today = None
        self.max_cached = max_cached
        self.calendar: Optional[pd.DatetimeIndex] = None
        self._missing = set()

    _ARR_COLS = ('adjClose', 'close', 'open', 'volume',
                 'divCash', 'splitFactor',
                 'stoch_k', 'stoch_d', 'sma_200', 'volume_sma')

    def _read_frame(self, ticker: str) -> Optional[pd.DataFrame]:
        path = self.prices_dir / price_filename(ticker)
        if not path.exists():
            return None
        try:
            df = pd.read_parquet(path)
        except Exception:
            logger.exception("cannot read %s", path)
            return None
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        if getattr(df.index, 'tz', None) is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')].sort_index()
        return add_indicators_v7_2(df)

    def _put_frame(self, ticker: str, df: pd.DataFrame):
        self._frames[ticker] = df
        self._frames.move_to_end(ticker)
        while len(self._frames) > self.max_cached:
            old, _ = self._frames.popitem(last=False)
            # arrays and pointers SURVIVE eviction - only the frame goes
        return df

    def _ensure(self, ticker: str) -> Optional[pd.DataFrame]:
        """Guarantee _dates/_arr exist; return a (possibly fresh) frame."""
        if ticker in self._missing:
            return None
        if ticker in self._arr:
            if ticker in self._frames:
                self._frames.move_to_end(ticker)
                return self._frames[ticker]
            df = self._read_frame(ticker)   # frame was evicted: rebuild
            if df is None:
                return None
            return self._put_frame(ticker, df)
        df = self._read_frame(ticker)
        if df is None:
            self._missing.add(ticker)
            return None
        self._dates[ticker] = df.index
        self._arr[ticker] = {c: df[c].values for c in self._ARR_COLS
                             if c in df.columns}
        return self._put_frame(ticker, df)

    def build_calendar(self, start, end, benchmark='SPY'):
        spy = self._ensure(benchmark)
        if spy is None:
            raise RuntimeError(f"benchmark {benchmark} not in snapshot")
        cal = spy.index[(spy.index >= pd.Timestamp(start)) &
                        (spy.index <= pd.Timestamp(end))]
        if cal.empty:
            raise RuntimeError("empty trading calendar")
        self.calendar = cal
        return cal

    def asof(self, ticker: str, date) -> Optional[pd.DataFrame]:
        """DataFrame slice containing only rows <= date (completed bars)."""
        df = self._ensure(ticker)
        if df is None:
            return None
        ts = pd.Timestamp(date)
        if ts == self._today:
            # fast path: pointer already advanced to this session
            p = self._ptr.get(ticker, 0)
            pos = p + 1 if p < len(self._dates[ticker]) \
                and self._dates[ticker][p] == ts else p
        else:
            pos = self._dates[ticker].searchsorted(ts, 'right')
        if pos == 0:
            return None
        return df.iloc[:pos]

    def advance(self, date):
        """Advance per-ticker day pointers to `date`. Call once per session,
        in chronological order."""
        ts = pd.Timestamp(date)
        self._today = ts
        for t in self.tickers:
            if t not in self._arr:
                self._ensure(t)  # light path: arrays + dates only
            dates = self._dates.get(t)
            if dates is None:
                continue
            p = self._ptr.get(t, 0)
            n = len(dates)
            while p < n and dates[p] < ts:
                p += 1
            self._ptr[t] = p

    def bar(self, ticker: str, date):
        """Dict of raw fields at exactly `date`, or None (no bar)."""
        dates = self._dates.get(ticker)
        a = self._arr.get(ticker)
        if dates is None or a is None:
            return None
        p = self._ptr.get(ticker, 0)
        if p < len(dates) and dates[p] == pd.Timestamp(date):
            return {k: v[p] for k, v in a.items()}
        return None

    def prefilter_candidates(self, date, mom_days=None, mom_min=None):
        """Exact-equivalence scan prefilter.

        Returns the tickers that CAN produce a scan_universe candidate
        today: a bar exists, raw close >= MIN_PRICE, required indicators
        finite, >=253 bars of history, and the base buy-block passes
        (stoch band, price>sma200, volume surge, annual return, momentum,
        liquidity). Extra version filters only REJECT candidates, so
        this set is exact for every version sharing the base block.
        The engine re-evaluates every condition for survivors - output
        is identical, provable by verify_prefilter.py.
        """
        ts = pd.Timestamp(date)
        out = []
        for t in self.tickers:
            p = self._ptr.get(t)
            dates = self._dates.get(t)
            a = self._arr.get(t)
            if p is None or dates is None or a is None:
                continue
            if p >= len(dates) or dates[p] != ts:
                continue            # no bar today -> prices.get() misses
            close = a['close'][p]
            if not np.isfinite(close) or close < MIN_PRICE:
                continue
            if p < 252:
                continue            # need >=253 rows for annual return
            k = a['stoch_k'][p]
            d = a['stoch_d'][p]
            sma200 = a['sma_200'][p]
            vsma = a['volume_sma'][p]
            volume = a['volume'][p]
            if not all(np.isfinite(v)
                       for v in (k, d, sma200, vsma, volume)):
                continue
            adj = a['adjClose']
            p252 = adj[p - 252]
            if not np.isfinite(p252) or p252 <= 0:
                continue
            last_adj = adj[p]
            if not np.isfinite(last_adj):
                continue
            if last_adj / p252 - 1.0 < CAGR_FILTER:
                continue
            if mom_days and mom_min is not None:
                p20 = adj[p - mom_days]
                if not np.isfinite(p20) or p20 <= 0:
                    continue
                if last_adj / p20 - 1.0 < mom_min:
                    continue
            if not (STOCH_LOW <= k <= STOCH_HIGH):
                continue
            if not (close > sma200):
                continue
            if not (volume >= vsma * VOLUME_SURGE):
                continue
            if not (close * volume >= MIN_LIQUIDITY):
                continue
            out.append(t)
        return out

    def session_prices(self, date) -> Dict[str, float]:
        """{ticker: raw close} for every ticker with a bar this session."""
        ts = pd.Timestamp(date)
        out = {}
        for t in self.tickers:
            dates = self._dates.get(t)
            a = self._arr.get(t)
            if dates is None or a is None:
                continue
            p = self._ptr.get(t, 0)
            if p < len(dates) and dates[p] == ts:
                c = a['close'][p]
                if np.isfinite(c) and c > 0:
                    out[t] = float(c)
        return out


class CorrectedBacktest:
    def __init__(self,
                 data: BacktestData,
                 starting_cash: float = 100_000.0,
                 version: str = DEFAULT_VERSION,
                 commission_per_share: float = 0.005,
                 min_commission: float = 1.0,
                 slippage_bps: float = 0.0,
                 settlement_days: int = 1,
                 earnings_map: Optional[dict] = None,
                 capital_ceiling: Optional[float] = None):
        self.data = data
        self.version = version
        if capital_ceiling is not None:
            # DISCLOSED live-vs-backtest difference: get_safe_buying_power
            # pins buying power to ABSOLUTE_CAPITAL_CEILING ($100k) as an
            # ops guard for the real $100k account. In research the equity
            # must be allowed to compound, so the ceiling is lifted; the
            # cash-only constraint (cash on hand) is still enforced by the
            # ledger. Live code is untouched - the constant is read at
            # call time and only this process is affected.
            import src.strategy_engine as _se
            _se.ABSOLUTE_CAPITAL_CEILING = capital_ceiling
        self.ledger = PortfolioLedger(starting_cash, settlement_days)
        self.slip = slippage_bps / 10_000.0
        self.cps = commission_per_share
        self.min_comm = min_commission
        self.earnings_map = earnings_map if earnings_map is not None else {}
        # Engine-facing view mirroring portfolio.json fields
        self.portfolio = {
            'cash': starting_cash,
            'positions': {},
            'high_water_mark': starting_cash,
            'trade_history': [],
        }
        self.pending_sells: List[dict] = []   # [{ticker, fraction, reason, tries}]
        self.pending_buys: List[dict] = []    # candidate dicts w/ signal info
        self.exit_log: List[dict] = []
        self.entry_log: List[dict] = []
        self.params = get_params(version)

    # ── helpers ──────────────────────────────────────────────────────────

    def _fee(self, shares: int) -> float:
        return max(self.min_comm, self.cps * shares) if shares > 0 else 0.0

    def _sync_cash(self):
        # engine views TOTAL cash (settled enforcement is the ledger's job)
        self.portfolio['cash'] = self.ledger.cash

    def _record_buy(self, ticker, shares, fill_px, date, cand, atr):
        pos = {
            'shares': shares,
            'entry_price': fill_px,
            'stop_loss_price': fill_px * (1 - self.params['HARD_STOP_PCT']),
            'entry_date': str(pd.Timestamp(date).date()),
            'quality_score': cand.get('score'),
            'execution_mode': 'BACKTEST',
            'is_power_stock': False,
            'highest_price': fill_px,
            'ticker': ticker,
            'atr': atr,
            'initial_shares': shares,
            'partial_taken': False,
            'breakeven_stop': None,
        }
        self.portfolio['positions'][ticker] = pos
        rec = {'type': 'BUY', 'ticker': ticker, 'shares': shares,
               'price': fill_px, 'cost': shares * fill_px,
               'date': str(pd.Timestamp(date).date()),
               'reason': cand.get('reason', ''),
               'quality_score': cand.get('score'), 'atr': atr}
        self.portfolio['trade_history'].append(rec)
        self.entry_log.append(rec)

    def _record_sell(self, ticker, shares, fill_px, date, reason, fraction):
        pos = self.portfolio['positions'].get(ticker)
        entry_px = pos['entry_price'] if pos else fill_px
        pnl = (fill_px - entry_px) * shares
        rec = {'type': 'SELL', 'ticker': ticker, 'shares': shares,
               'price': fill_px, 'proceeds': shares * fill_px,
               'pnl': pnl,
               'pnl_pct': (fill_px - entry_px) / entry_px if entry_px else 0,
               'date': str(pd.Timestamp(date).date()),
               'reason': reason, 'fraction': fraction}
        self.portfolio['trade_history'].append(rec)
        self.exit_log.append(rec)
        if pos:
            if fraction < 1.0 and ticker in self.ledger.positions:
                pos['shares'] = self.ledger.positions[ticker].shares
                pos['partial_taken'] = True
                pos['breakeven_stop'] = entry_px
            else:
                self.portfolio['positions'].pop(ticker, None)

    # ── corporate actions ────────────────────────────────────────────────

    def _apply_corporate_actions(self, date):
        for ticker in list(self.ledger.positions.keys()):
            row = self.data.bar(ticker, date)
            if row is None:
                continue
            div = row.get('divCash', 0) or 0
            if np.isfinite(div) and div > 0:
                self.ledger.apply_dividend(ticker, date, float(div))
            sf = row.get('splitFactor', 1) or 1
            if np.isfinite(sf) and sf != 1:
                price = row.get('open', row.get('close', np.nan))
                cil = self.ledger.apply_split(
                    ticker, date, float(sf), price=float(price))
                pos = self.portfolio['positions'].get(ticker)
                if pos and ticker in self.ledger.positions:
                    # keep engine fields consistent in split space
                    pos['shares'] = self.ledger.positions[ticker].shares
                    pos['entry_price'] /= sf
                    pos['highest_price'] = pos.get('highest_price', 0) / sf
                    if pos.get('stop_loss_price'):
                        pos['stop_loss_price'] /= sf
                elif pos and ticker not in self.ledger.positions:
                    pos['shares'] = 0
                if cil:
                    logger.info("%s split x%.4f on %s: cash-in-lieu $%.2f",
                                ticker, sf, date, cil)

    # ── order execution at session open ──────────────────────────────────

    def _fill_open(self, date):
        still_pending = []
        for order in self.pending_sells:
            t = order['ticker']
            row = self.data.bar(t, date)
            held = self.ledger.positions.get(t)
            if held is None:
                continue
            tradeable = (row is not None and
                         np.isfinite(row.get('open', np.nan)) and
                         row.get('open', 0) > 0 and
                         (row.get('volume', 0) or 0) > 0)
            if not tradeable:
                order['tries'] += 1
                if order['tries'] >= MAX_PENDING_SESSIONS:
                    last_px = self.ledger.last_prices.get(t)
                    if last_px:
                        self.ledger.sell(t, date, last_px, held.shares,
                                         fee=self._fee(held.shares))
                        self._record_sell(t, held.shares, last_px, date,
                                          'Forced liquidation (untradeable)',
                                          1.0)
                    else:
                        still_pending.append(order)
                else:
                    still_pending.append(order)
                continue
            fill_px = float(row['open']) * (1.0 - self.slip)
            shares = (held.shares if order['fraction'] >= 1.0
                      else int(held.shares * order['fraction']))
            if shares <= 0:
                continue
            rec = self.ledger.sell(t, date, fill_px, shares,
                                   fee=self._fee(shares))
            if rec.status == 'filled':
                self._record_sell(t, shares, fill_px, date,
                                  order['reason'], order['fraction'])
        self.pending_sells = still_pending

        for cand in self.pending_buys:
            t = cand['ticker']
            if t in self.ledger.positions:
                continue
            row = self.data.bar(t, date)
            tradeable = (row is not None and
                         np.isfinite(row.get('open', np.nan)) and
                         row.get('open', 0) > 0 and
                         (row.get('volume', 0) or 0) > 0)
            if not tradeable:
                logger.info("BUY %s unfilled - no bar/zero volume on %s", t, date)
                continue
            fill_px = float(row['open']) * (1.0 + self.slip)
            shares = cand['shares']
            rec = self.ledger.buy(t, date, fill_px, shares,
                                  fee=self._fee(shares))
            if rec.status == 'filled':
                self._record_buy(t, shares, fill_px, date, cand,
                                 cand.get('atr', 0.0))
            else:
                logger.info("BUY %s %s sh rejected: %s",
                            t, shares, rec.reason)
        self.pending_buys = []

    # ── signal pass on completed bar T (mirrors live loop order) ─────────

    def _signal_pass(self, date, prices):
        p = self.params
        load_fn = lambda t: self.data.asof(t, date)  # noqa: E731
        today = pd.Timestamp(date).date()

        update_highest_prices(self.portfolio, prices)
        update_high_water_mark(self.portfolio, prices)

        # exits first, exactly like the live loop
        exits = engine_check_exits(
            self.portfolio, prices, load_fn, version=self.version,
            today=today, earnings_map=self.earnings_map)
        open_tickers = set(self.portfolio['positions'])
        for ex in exits:
            t = ex['ticker']
            if any(o['ticker'] == t for o in self.pending_sells):
                continue
            self.pending_sells.append({
                'ticker': t, 'fraction': ex.get('fraction', 1.0),
                'reason': ex['reason'], 'tries': 0})

        promote_power_stocks(self.portfolio, prices, load_fn)

        # entries only if slots could open (exits pending still count open)
        spy = self.data.asof('SPY', date)
        is_bull = True
        if spy is not None and not spy.empty and 'sma_200' in spy.columns:
            close_col = next((c for c in ('adjClose', 'close', 'Close')
                              if c in spy.columns), None)
            sc = spy.iloc[-1]
            if close_col and np.isfinite(sc.get('sma_200', np.nan)):
                is_bull = float(sc[close_col]) > float(sc['sma_200'])

        max_pos = get_regime_max_positions(is_bull, self.version)
        free_slots = max_pos - len(self.portfolio['positions'])
        if free_slots <= 0:
            return  # scan would be rejected by can_enter for every name

        self._sync_cash()
        scan_list = self.data.prefilter_candidates(
            date, self.params.get('MOMENTUM_DAYS'),
            self.params.get('MOMENTUM_MIN'))
        candidates = engine_scan_universe(
            scan_list, open_tickers, prices, load_fn,
            version=self.version, today=today,
            earnings_map=self.earnings_map)

        committed = 0.0   # est cost already queued this signal pass
        for cand in candidates:
            t = cand['ticker']
            if t in self.portfolio['positions']:
                continue
            allowed, _reason = can_enter(t, self.portfolio, is_bull,
                                         self.version)
            if not allowed:
                continue
            shares, _cost, atr = calc_position_size(
                self.portfolio, cand['price'], prices,
                ticker=t, load_fn=load_fn, version=self.version)
            if shares <= 0:
                continue
            # ledger enforces settled-cash affordability at fill time;
            # stop queueing once queued buys would exhaust settled cash
            est_cost = shares * cand['price'] * (1 + self.slip)
            if committed + est_cost > self.ledger.settled_cash:
                continue   # live skips unaffordable, tries next candidate
            committed += est_cost
            self.pending_buys.append({**cand, 'shares': shares, 'atr': atr})
            if len(self.pending_buys) >= free_slots:
                break

    # ── main loop ────────────────────────────────────────────────────────

    def run(self):
        cal = self.data.calendar
        if cal is None:
            raise RuntimeError("call data.build_calendar() first")
        for i, date in enumerate(cal):
            self.ledger.begin_session(i)
            self.data.advance(date)
            self._apply_corporate_actions(date)
            self._fill_open(date)
            self._sync_cash()
            prices = self.data.session_prices(date)
            self.ledger.mark_to_market(date, prices, i)
            self._signal_pass(date, prices)
            self._sync_cash()
            if i % 500 == 0:
                logger.info("day %s/%s %s equity=$%.0f pos=%d",
                            i, len(cal), date.date(),
                            self.ledger.equity_curve[-1].equity,
                            len(self.ledger.positions))
        return self.results()

    def results(self) -> dict:
        eq = self.ledger.equity_frame()
        sells = [r for r in self.exit_log]
        wins = [r for r in sells if r['pnl'] > 0]
        return {
            'version': self.version,
            'equity': eq,
            'orders': self.ledger.orders,
            'entries': self.entry_log,
            'exits': self.exit_log,
            'final_equity': float(eq['equity'].iloc[-1]) if not eq.empty else 0,
            'total_fees': self.ledger.total_fees,
            'total_dividends': self.ledger.total_dividends,
            'n_sells': len(sells),
            'win_rate': len(wins) / len(sells) if sells else 0,
        }
