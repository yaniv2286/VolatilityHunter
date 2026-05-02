#!/usr/bin/env python3
"""Verify Gateway login automation invariants."""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
AUTO_TWS = ROOT / "scripts" / "auto_tws_manager.py"
GHOST = ROOT / "scripts" / "surgical_ghost_typist.py"
BATCH = ROOT / "scripts" / "DAILY_ROUTINE" / "run_trading.bat"


def fail(message: str) -> int:
    print(f"[FAIL] {message}")
    return 1


def main() -> int:
    checks = []
    auto_tws = AUTO_TWS.read_text(encoding="utf-8")
    ghost = GHOST.read_text(encoding="utf-8")
    batch = BATCH.read_text(encoding="utf-8")

    checks.append(("No IBC LOGON section generated", '"[LOGON]"' not in auto_tws))
    checks.append(("No IBC password injection in config", 'IbPassword=' not in auto_tws))
    checks.append(("Ghost-Typist owns login", "surgical_ghost_typist.py" in auto_tws))
    checks.append(("Ghost-Typist FAILSAFE disabled", "pyautogui.FAILSAFE = False" in ghost))
    checks.append(("Ghost-Typist does not maximize window", ".maximize()" not in ghost))
    checks.append(("Batch uses canonical orchestrator", "scripts\\run_daily_orchestrator.py" in batch))

    failed = False
    for name, ok in checks:
        if ok:
            print(f"[OK] {name}")
        else:
            failed = True
            print(f"[FAIL] {name}")

    if failed:
        return fail("Gateway login invariants failed")
    print("[OK] Gateway login invariants verified")
    return 0


if __name__ == "__main__":
    sys.exit(main())
