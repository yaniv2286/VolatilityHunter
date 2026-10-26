"""Cash-only portfolio ledger for research backtests.

Single source of truth for portfolio accounting in the corrected
simulator. Enforces the rules the legacy equity-curve builder violated:

- Purchases debit available (settled) cash; unaffordable orders rejected.
- Sales are limited to shares actually held; shorting is impossible.
- Integer shares only.
- Open positions are valued daily via mark_to_market.
- Dividends credit cash; splits adjust share count (cash-in-lieu for
  fractional remainders).
- Sale proceeds settle after `settlement_days` trading days before they
  can fund new purchases (cash-account good-faith rule).
- Every fill and rejection is recorded for audit.

No strategy logic lives here. The harness decides what to trade and at
what price; the ledger decides whether the trade is legal and what it
does to cash, shares, and equity.
"""

import logging
from dataclasses import dataclass, field
from typing import Dict, List, Optional

import pandas as pd

logger = logging.getLogger(__name__)


@dataclass
class Position:
    ticker: str
    shares: int
    avg_cost: float          # per-share cost basis incl. buy fees
    entry_date: object


@dataclass
class OrderRecord:
    date: object
    ticker: str
    side: str                # 'buy' | 'sell'
    requested_shares: int
    filled_shares: int
    price: float
    fee: float
    status: str              # 'filled' | 'rejected'
    reason: str = ''


@dataclass
class EquityPoint:
    date: object
    cash: float
    settled_cash: float
    positions_value: float
    equity: float
    positions: int


class PortfolioLedger:
    def __init__(self, starting_cash: float, settlement_days: int = 1):
        if starting_cash <= 0:
            raise ValueError("starting_cash must be positive")
        self.starting_cash = float(starting_cash)
        self.cash = float(starting_cash)            # total cash incl. unsettled
        self._unsettled: List[dict] = []            # [{amount, settle_date}]
        self.positions: Dict[str, Position] = {}
        self.orders: List[OrderRecord] = []
        self.equity_curve: List[EquityPoint] = []
        self.last_prices: Dict[str, float] = {}
        self.settlement_days = settlement_days
        self._today_index = -1
        self.total_fees = 0.0
        self.total_dividends = 0.0

    # ── session lifecycle ────────────────────────────────────────────────

    def begin_session(self, index: int):
        """Start of a simulated trading day. Sweeps settlements that have
        reached their settle date, making those proceeds spendable."""
        if index <= self._today_index:
            raise ValueError("session index must strictly increase")
        self._today_index = index
        self._unsettled = [s for s in self._unsettled
                           if s['settle_index'] > index]

    # ── helpers ──────────────────────────────────────────────────────────

    @property
    def settled_cash(self) -> float:
        return self.cash - sum(s['amount'] for s in self._unsettled)

    def equity(self, prices: Optional[Dict[str, float]] = None) -> float:
        if prices:
            self.last_prices.update(prices)
        return self.cash + sum(
            p.shares * self.last_prices.get(t, p.avg_cost)
            for t, p in self.positions.items()
        )

    # ── orders ───────────────────────────────────────────────────────────

    def buy(self, ticker, date, price, shares, fee=0.0) -> OrderRecord:
        shares = int(shares)
        cost = price * shares + fee
        if shares <= 0 or price <= 0:
            rec = OrderRecord(date, ticker, 'buy', shares, 0, price, fee,
                              'rejected', 'invalid order')
        elif cost > self.settled_cash + 1e-9:
            rec = OrderRecord(date, ticker, 'buy', shares, 0, price, fee,
                              'rejected', 'insufficient settled cash')
        else:
            self.cash -= cost
            self.total_fees += fee
            per_share = cost / shares
            if ticker in self.positions:
                p = self.positions[ticker]
                p.avg_cost = ((p.avg_cost * p.shares) + cost) / (p.shares + shares)
                p.shares += shares
            else:
                self.positions[ticker] = Position(ticker, shares, per_share, date)
            self.last_prices[ticker] = price
            rec = OrderRecord(date, ticker, 'buy', shares, shares, price, fee,
                              'filled')
        self.orders.append(rec)
        return rec

    def sell(self, ticker, date, price, shares, fee=0.0) -> OrderRecord:
        shares = int(shares)
        held = self.positions.get(ticker)
        if held is None or shares <= 0 or price <= 0:
            rec = OrderRecord(date, ticker, 'sell', shares, 0, price, fee,
                              'rejected', 'no position or invalid order')
        elif shares > held.shares:
            rec = OrderRecord(date, ticker, 'sell', shares, 0, price, fee,
                              'rejected', 'cannot sell more than held')
        else:
            proceeds = price * shares - fee
            self.cash += proceeds
            self.total_fees += fee
            if self.settlement_days > 0:
                if self._today_index < 0:
                    raise ValueError(
                        "sell() before begin_session(): no trading-day index")
                self._unsettled.append({
                    'amount': proceeds,
                    'settle_index': self._today_index + self.settlement_days,
                })
            held.shares -= shares
            if held.shares == 0:
                del self.positions[ticker]
            self.last_prices[ticker] = price
            rec = OrderRecord(date, ticker, 'sell', shares, shares, price,
                              fee, 'filled')
        self.orders.append(rec)
        return rec

    # ── corporate actions ────────────────────────────────────────────────

    def apply_dividend(self, ticker, date, cash_per_share) -> float:
        p = self.positions.get(ticker)
        if not p or cash_per_share <= 0:
            return 0.0
        amount = cash_per_share * p.shares
        self.cash += amount
        self.total_dividends += amount
        return amount

    def apply_split(self, ticker, date, factor, price=None) -> float:
        """factor = new/old shares (e.g. 4.0 for a 4:1 split).

        Fractional remainder is paid out as cash-in-lieu at `price`
        (required when factor produces fractional shares).
        Returns cash-in-lieu credited."""
        p = self.positions.get(ticker)
        if not p or factor <= 0 or factor == 1:
            return 0.0
        new_shares = p.shares * factor
        whole = int(new_shares)
        frac = new_shares - whole
        cash_in_lieu = 0.0
        if frac > 1e-9:
            px = price if price else self.last_prices.get(ticker)
            if px is None:
                raise ValueError(f"split for {ticker} needs a price for "
                                 f"fractional remainder")
            cash_in_lieu = frac * px
            self.cash += cash_in_lieu
        p.avg_cost = p.avg_cost / factor
        p.shares = whole
        if whole == 0:
            del self.positions[ticker]
        return cash_in_lieu

    # ── daily valuation ──────────────────────────────────────────────────

    def mark_to_market(self, date, prices: Dict[str, float],
                       today_index: int) -> EquityPoint:
        """Record end-of-day equity. `prices` = {ticker: close} for names
        that printed today; missing tickers carry their last price."""
        if prices:
            self.last_prices.update(prices)
        value = sum(
            p.shares * self.last_prices.get(t, p.avg_cost)
            for t, p in self.positions.items()
        )
        point = EquityPoint(date, self.cash, self.settled_cash, value,
                            self.cash + value, len(self.positions))
        self.equity_curve.append(point)
        return point

    def equity_frame(self) -> pd.DataFrame:
        return pd.DataFrame([vars(p) for p in self.equity_curve])
