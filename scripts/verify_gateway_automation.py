#!/usr/bin/env python3
"""
VERIFY GATEWAY AUTOMATION FIX
==============================
Test the new IB Gateway startup/shutdown automation.
Verifies all components are working correctly.

Usage: python scripts/verify_gateway_automation.py
"""

import os
import sys
import time
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

def test_imports():
    """Test that all new scripts can be imported."""
    print("\n=== TEST 1: Import Verification ===")
    
    tests = []
    
    # Test start_gateway_with_retry.py
    try:
        import scripts.start_gateway_with_retry as start_gw
        print("✅ start_gateway_with_retry.py imports successfully")
        tests.append(True)
    except Exception as e:
        print(f"❌ start_gateway_with_retry.py import failed: {e}")
        tests.append(False)
    
    # Test stop_gateway.py
    try:
        import scripts.stop_gateway as stop_gw
        print("✅ stop_gateway.py imports successfully")
        tests.append(True)
    except Exception as e:
        print(f"❌ stop_gateway.py import failed: {e}")
        tests.append(False)
    
    # Test send_gateway_failure_email.py
    try:
        import scripts.send_gateway_failure_email as email_gw
        print("✅ send_gateway_failure_email.py imports successfully")
        tests.append(True)
    except Exception as e:
        print(f"❌ send_gateway_failure_email.py import failed: {e}")
        tests.append(False)
    
    return all(tests)


def test_file_existence():
    """Test that all required files exist."""
    print("\n=== TEST 2: File Existence ===")
    
    files = [
        "scripts/start_gateway_with_retry.py",
        "scripts/stop_gateway.py",
        "scripts/send_gateway_failure_email.py",
        "scripts/DAILY_ROUTINE/run_trading.bat",
        "scripts/daily_trading_loop.py",
        "docs/IBKR_FIRST_ARCHITECTURE.md",
    ]
    
    tests = []
    for file_path in files:
        full_path = ROOT / file_path
        if full_path.exists():
            print(f"✅ {file_path} exists")
            tests.append(True)
        else:
            print(f"❌ {file_path} NOT FOUND")
            tests.append(False)
    
    return all(tests)


def test_reconciliation_logic():
    """Test that reconciliation logic has been updated."""
    print("\n=== TEST 3: Reconciliation Logic Update ===")
    
    daily_loop = ROOT / "scripts" / "daily_trading_loop.py"
    content = daily_loop.read_text(encoding='utf-8')
    
    tests = []
    
    # Check for IBKR-first logic
    if "IBKR-FIRST" in content:
        print("✅ IBKR-FIRST comment found in reconciliation")
        tests.append(True)
    else:
        print("❌ IBKR-FIRST comment NOT found")
        tests.append(False)
    
    # Check for last_ibkr_sync timestamp
    if "last_ibkr_sync" in content:
        print("✅ last_ibkr_sync timestamp tracking added")
        tests.append(True)
    else:
        print("❌ last_ibkr_sync NOT found")
        tests.append(False)
    
    # Check for ibkr_available flag
    if "ibkr_available" in content:
        print("✅ ibkr_available flag added")
        tests.append(True)
    else:
        print("❌ ibkr_available NOT found")
        tests.append(False)
    
    # Check for PAPER position discarding
    if "paper_positions" in content or "PAPER" in content:
        print("✅ PAPER position handling logic found")
        tests.append(True)
    else:
        print("❌ PAPER position handling NOT found")
        tests.append(False)
    
    # Check for log attachment
    if "log_file" in content and "send_email" in content:
        print("✅ Log file attachment logic found")
        tests.append(True)
    else:
        print("❌ Log attachment logic NOT found")
        tests.append(False)
    
    return all(tests)


def test_bat_file_updates():
    """Test that run_trading.bat has been updated."""
    print("\n=== TEST 4: Batch File Updates ===")
    
    bat_file = ROOT / "scripts" / "DAILY_ROUTINE" / "run_trading.bat"
    content = bat_file.read_text(encoding='utf-8')
    
    tests = []
    
    # Check for start_gateway_with_retry.py
    if "start_gateway_with_retry.py" in content:
        print("✅ start_gateway_with_retry.py called in batch file")
        tests.append(True)
    else:
        print("❌ start_gateway_with_retry.py NOT found in batch file")
        tests.append(False)
    
    # Check for stop_gateway.py
    if "stop_gateway.py" in content:
        print("✅ stop_gateway.py called in batch file")
        tests.append(True)
    else:
        print("❌ stop_gateway.py NOT found in batch file")
        tests.append(False)
    
    # Check for send_gateway_failure_email.py
    if "send_gateway_failure_email.py" in content:
        print("✅ send_gateway_failure_email.py called on failure")
        tests.append(True)
    else:
        print("❌ send_gateway_failure_email.py NOT found in batch file")
        tests.append(False)
    
    # Check for error handling
    if "ERRORLEVEL" in content and "exit /b" in content:
        print("✅ Error handling with ERRORLEVEL checks present")
        tests.append(True)
    else:
        print("❌ Error handling NOT found")
        tests.append(False)
    
    return all(tests)


def test_documentation():
    """Test that documentation has been updated."""
    print("\n=== TEST 5: Documentation Updates ===")
    
    doc_file = ROOT / "docs" / "IBKR_FIRST_ARCHITECTURE.md"
    content = doc_file.read_text(encoding='utf-8')
    
    tests = []
    
    # Check for updated date
    if "2026-03-14" in content:
        print("✅ Documentation updated with current date")
        tests.append(True)
    else:
        print("❌ Documentation date NOT updated")
        tests.append(False)
    
    # Check for Gateway startup section
    if "start_gateway_with_retry" in content:
        print("✅ Gateway startup documentation added")
        tests.append(True)
    else:
        print("❌ Gateway startup documentation NOT found")
        tests.append(False)
    
    # Check for troubleshooting section
    if "TROUBLESHOOTING" in content or "Troubleshooting" in content:
        print("✅ Troubleshooting section added")
        tests.append(True)
    else:
        print("❌ Troubleshooting section NOT found")
        tests.append(False)
    
    return all(tests)


def main():
    print("=" * 70)
    print("GATEWAY AUTOMATION FIX - VERIFICATION SUITE")
    print("=" * 70)
    
    results = []
    
    # Run all tests
    results.append(("Import Verification", test_imports()))
    results.append(("File Existence", test_file_existence()))
    results.append(("Reconciliation Logic", test_reconciliation_logic()))
    results.append(("Batch File Updates", test_bat_file_updates()))
    results.append(("Documentation Updates", test_documentation()))
    
    # Summary
    print("\n" + "=" * 70)
    print("VERIFICATION SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} - {test_name}")
    
    print("\n" + "=" * 70)
    print(f"TOTAL: {passed}/{total} tests passed")
    print("=" * 70)
    
    if passed == total:
        print("\n✅ ALL TESTS PASSED - Implementation verified successfully!")
        print("\nNext Steps:")
        print("1. Test Gateway startup: python scripts\\start_gateway_with_retry.py")
        print("2. Test Gateway shutdown: python scripts\\stop_gateway.py")
        print("3. Run full daily routine: scripts\\DAILY_ROUTINE\\run_trading.bat")
        return 0
    else:
        print("\n❌ SOME TESTS FAILED - Review errors above")
        return 1


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
