#!/usr/bin/env python3
"""Verify IBKR execution safety invariants."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
BROKERAGE = ROOT / "src" / "brokerage_interface.py"
DAILY = ROOT / "scripts" / "daily_trading_loop.py"


def main() -> int:
    brokerage = BROKERAGE.read_text(encoding="utf-8")
    daily = DAILY.read_text(encoding="utf-8")

    checks = [
        ("Adaptive orders wait for confirmed fill", "_wait_for_trade_fill" in brokerage and "status == 'Filled'" in brokerage),
        ("Order success includes filled quantity", "'filled_qty': fill_result.get('filled_qty', 0)" in brokerage),
        ("No unsafe default BUY price", "return 100.0" not in brokerage),
        ("No unsafe default SELL price", "return 50.0" not in brokerage),
        ("Fallback pricing aborts without reliable data", "No reliable price source" in brokerage),
        ("Order monitor still present", "class OrderMonitor" in daily),
    ]

    failed = False
    for name, ok in checks:
        if ok:
            print(f"[OK] {name}")
        else:
            failed = True
            print(f"[FAIL] {name}")

    if failed:
        print("[FAIL] Execution invariants failed")
        return 1
    print("[OK] Execution invariants verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
