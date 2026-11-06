#!/usr/bin/env python3
"""
Production Bridge Verification Script
Validates the bulletproof bridge between Command Center and orchestrator.

Verification Checklist:
1. run_trading.bat calls run_daily_orchestrator.py
2. Orchestrator has pyautogui.size() environment check
3. smart_data_loader_factory.py uses 100-ticker chunks
4. All critical paths use flush=True for console logging

Exit Code 0: All checks PASS
Exit Code 1: One or more checks FAIL
"""

import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent

def check_batch_file():
    """Verify run_trading.bat calls orchestrator."""
    print("[CHECK 1] Verifying run_trading.bat calls orchestrator...")
    
    batch_file = ROOT / "scripts" / "DAILY_ROUTINE" / "run_trading.bat"
    if not batch_file.exists():
        print("  ❌ FAIL: run_trading.bat not found")
        return False
    
    content = batch_file.read_text(encoding='utf-8')
    
    if "python scripts\\run_daily_orchestrator.py" not in content:
        print("  ❌ FAIL: Batch file does not call run_daily_orchestrator.py")
        return False
    
    print("  ✅ PASS: Batch file calls run_daily_orchestrator.py")
    return True


def check_orchestrator_gui_check():
    """Verify orchestrator has pyautogui.size() environment check."""
    print("[CHECK 2] Verifying orchestrator GUI environment check...")
    
    orchestrator = ROOT / "scripts" / "run_daily_orchestrator.py"
    if not orchestrator.exists():
        print("  ❌ FAIL: run_daily_orchestrator.py not found")
        return False
    
    content = orchestrator.read_text(encoding='utf-8')
    
    checks = [
        ("import pyautogui", "pyautogui import"),
        ("_check_gui_environment", "GUI environment check function"),
        ("pyautogui.size()", "pyautogui.size() call"),
        ("HEADLESS ENVIRONMENT DETECTED", "headless detection error message"),
        ("FAILED_GUI_ENVIRONMENT", "GUI failure status"),
    ]
    
    for pattern, description in checks:
        if pattern not in content:
            print(f"  ❌ FAIL: Missing {description}")
            return False
    
    print("  ✅ PASS: Orchestrator has complete GUI environment check")
    return True


def check_data_loader_chunks():
    """Verify smart_data_loader_factory.py uses 100-ticker chunks."""
    print("[CHECK 3] Verifying data loader uses 100-ticker chunks...")
    
    loader = ROOT / "src" / "smart_data_loader_factory.py"
    if not loader.exists():
        print("  ❌ FAIL: smart_data_loader_factory.py not found")
        return False
    
    content = loader.read_text(encoding='utf-8')
    
    checks = [
        ("chunk_size = 100", "100-ticker chunk size"),
        ("BLUEPRINT ENFORCEMENT", "Blueprint enforcement comment"),
        ("prevents 502 Bad Gateway", "502 prevention documentation"),
    ]
    
    for pattern, description in checks:
        if pattern not in content:
            print(f"  ❌ FAIL: Missing {description}")
            return False
    
    print("  ✅ PASS: Data loader enforces 100-ticker chunks per Blueprint")
    return True


def check_console_logging():
    """Verify critical paths use flush=True."""
    print("[CHECK 4] Verifying No Silent Failures console logging...")
    
    orchestrator = ROOT / "scripts" / "run_daily_orchestrator.py"
    ghost_typist = ROOT / "scripts" / "ibc_login_helper.py"
    
    files_to_check = [
        (orchestrator, "run_daily_orchestrator.py"),
        (ghost_typist, "ibc_login_helper.py"),
    ]
    
    all_pass = True
    for file_path, name in files_to_check:
        if not file_path.exists():
            print(f"  ❌ FAIL: {name} not found")
            all_pass = False
            continue
        
        content = file_path.read_text(encoding='utf-8')
        flush_count = content.count("flush=True")
        
        if flush_count == 0:
            print(f"  ❌ FAIL: {name} has no flush=True statements")
            all_pass = False
        else:
            print(f"  ✅ PASS: {name} has {flush_count} flush=True statements")
    
    return all_pass


def main():
    print("="*80)
    print("PRODUCTION BRIDGE VERIFICATION")
    print("="*80)
    print()
    
    checks = [
        check_batch_file,
        check_orchestrator_gui_check,
        check_data_loader_chunks,
        check_console_logging,
    ]
    
    results = [check() for check in checks]
    
    print()
    print("="*80)
    if all(results):
        print("✅ ALL CHECKS PASSED - Production bridge is bulletproof")
        print("="*80)
        return 0
    else:
        failed = sum(1 for r in results if not r)
        print(f"❌ {failed}/{len(results)} CHECKS FAILED - Production bridge needs fixes")
        print("="*80)
        return 1


if __name__ == "__main__":
    sys.exit(main())
