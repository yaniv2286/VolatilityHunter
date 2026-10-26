"""Hand-calculated regression fixtures for src/portfolio_ledger.py.

Each case was worked out by hand first; the ledger must reproduce it
exactly. Exit 0 only if every check passes.

Cases:
 1. Cash ceiling  - the legacy $200k-from-$100k bug cannot recur.
 2. Oversell      - cannot sell shares not held (no shorting).
 3. Dividend      - cash dividend credits cash by shares x divCash.
 4. Split         - 4:1 split quadruples shares, basis divides; 7:2 split
                    pays fractional remainder as cash-in-lieu.
 5. Daily marks    - interim unrealized loss appears in equity before exit.
 6. Settlement     - sale proceeds cannot fund a same-day/next-day buy
                    until T+1.
 7. Fees           - fees reduce cash and lift per-share cost basis.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.portfolio_ledger import PortfolioLedger

FAILURES = []


def check(name, actual, expected, tol=1e-6):
    ok = abs(actual - expected) <= tol if isinstance(expected, float) \
        else actual == expected
    status = 'PASS' if ok else 'FAIL'
    print(f"  [{status}] {name}: got {actual}, want {expected}")
    if not ok:
        FAILURES.append(name)


def case_1_cash_ceiling():
    print("1. Cash ceiling (legacy bug reproduction)")
    L = PortfolioLedger(100_000.0)
    filled = sum(
        1 for i in range(10)
        if L.buy(f'T{i}', 'd0', 10.0, 2000).status == 'filled'  # $20k each
    )
    check("only 5 of 10 orders fill", filled, 5)
    check("cash fully spent", L.cash, 0.0)
    # every held name +10%
    eq = L.equity({f'T{i}': 11.0 for i in range(5)})
    check("equity after +10% is $110k, not $120k", eq, 110_000.0)


def case_2_oversell():
    print("2. Oversell rejection")
    L = PortfolioLedger(10_000.0)
    L.begin_session(0)
    L.buy('A', 'd0', 10.0, 100)
    L.begin_session(1)
    rec = L.sell('A', 'd1', 11.0, 150)
    check("sell > held rejected", rec.status, 'rejected')
    rec = L.sell('ZZZ', 'd1', 11.0, 10)
    check("sell with no position rejected", rec.status, 'rejected')
    check("position still 100 shares", L.positions['A'].shares, 100)


def case_3_dividend():
    print("3. Dividend credit")
    L = PortfolioLedger(10_000.0)
    L.buy('A', 'd0', 10.0, 500)
    amount = L.apply_dividend('A', 'd1', 0.25)
    check("dividend = 500 x $0.25", amount, 125.0)
    check("cash = 5000 + 125", L.cash, 5_125.0)


def case_4_split():
    print("4. Splits")
    L = PortfolioLedger(10_000.0)
    L.buy('A', 'd0', 100.0, 10)
    L.apply_split('A', 'd1', 4.0, price=25.0)
    check("4:1 -> 40 shares", L.positions['A'].shares, 40)
    check("basis $100 -> $25", L.positions['A'].avg_cost, 25.0)
    L2 = PortfolioLedger(10_000.0)
    L2.buy('B', 'd0', 10.0, 5)
    cil = L2.apply_split('B', 'd1', 0.5, price=20.0)  # reverse 1:2
    check("1:2 reverse on 5 sh -> 2 sh + 0.5 x $20 cash-in-lieu",
          cil, 10.0)
    check("cash = 9950 + 10", L2.cash, 9_960.0)
    check("2 shares remain", L2.positions['B'].shares, 2)


def case_5_daily_marks():
    print("5. Daily mark-to-market")
    L = PortfolioLedger(10_000.0)
    L.buy('A', 'd0', 10.0, 200)
    L.mark_to_market('d0', {'A': 10.0}, 0)
    L.mark_to_market('d1', {'A': 8.0}, 1)   # -20% interim loss
    L.mark_to_market('d2', {'A': 12.0}, 2)
    eqs = [p.equity for p in L.equity_curve]
    check("equity path 10k -> 9.6k -> 10.4k", eqs,
          [10_000.0, 9_600.0, 10_400.0])
    # drawdown must see the interim loss
    peak, mdd = eqs[0], 0.0
    for e in eqs:
        peak = max(peak, e)
        mdd = min(mdd, e / peak - 1.0)
    check("max drawdown = -4%", mdd, -0.04)


def case_6_settlement():
    print("6. Settlement")
    L = PortfolioLedger(10_000.0, settlement_days=1)
    L.begin_session(0)
    L.buy('A', 'd0', 10.0, 500)                      # spend $5000
    L.mark_to_market('d0', {'A': 10.0}, 0)
    L.begin_session(1)
    L.sell('A', 'd1', 10.0, 500)                     # $5000 unsettled
    check("cash back to 10k", L.cash, 10_000.0)
    check("but settled cash still 5k", L.settled_cash, 5_000.0)
    rec = L.buy('B', 'd1', 10.0, 900)                # needs $9000 settled
    check("buy funded by unsettled proceeds rejected",
          rec.status, 'rejected')
    L.mark_to_market('d1', {'A': 10.0}, 1)
    L.begin_session(2)                               # T+1 settlement sweeps
    check("after T+1, settled cash = 10k", L.settled_cash, 10_000.0)
    rec = L.buy('B', 'd2', 10.0, 900)
    check("same buy fills next session", rec.status, 'filled')


def case_7_fees():
    print("7. Fees")
    L = PortfolioLedger(10_000.0)
    L.begin_session(0)
    L.buy('A', 'd0', 10.0, 100, fee=5.0)
    check("cash = 10000 - 1000 - 5", L.cash, 8_995.0)
    check("cost basis = 1005/100", L.positions['A'].avg_cost, 10.05)
    L.begin_session(1)
    L.sell('A', 'd1', 11.0, 100, fee=5.0)
    check("proceeds = 1100 - 5", L.cash, 10_090.0)
    check("total fees = 10", L.total_fees, 10.0)


if __name__ == '__main__':
    for case in (case_1_cash_ceiling, case_2_oversell, case_3_dividend,
                 case_4_split, case_5_daily_marks, case_6_settlement,
                 case_7_fees):
        case()
    print()
    if FAILURES:
        print(f"FAILED: {len(FAILURES)} check(s): {FAILURES}")
        sys.exit(1)
    print("All ledger checks passed.")
    sys.exit(0)
