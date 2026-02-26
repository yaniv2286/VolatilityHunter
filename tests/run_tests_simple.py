#!/usr/bin/env python3
"""
VOLATILITYHUNTER - SIMPLE TEST RUNNER
Run all tests without Unicode issues
"""

import subprocess
import sys
import os

def run_test(test_file):
    """Run a single test file"""
    try:
        result = subprocess.run(
            [sys.executable, test_file],
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            print(f"[PASS] {test_file}")
            return True
        else:
            print(f"[FAIL] {test_file}")
            print(f"  Error: {result.stderr[:200]}")
            return False
            
    except subprocess.TimeoutExpired:
        print(f"[TIMEOUT] {test_file}")
        return False
    except Exception as e:
        print(f"[ERROR] {test_file}: {e}")
        return False

def main():
    """Main function"""
    print("VOLATILITYHUNTER TEST RUNNER")
    print("=" * 50)
    
    test_files = [
        'test_data_agent.py',
        'test_strategy_agent.py', 
        'test_execution_agent.py',
        'test_sync_agent.py',
        'test_scheduler_agent.py',
        'test_notification_agent.py',
        'test_daily_emails.py',
        'test_basic_integration.py'  # Basic pipeline integration test
    ]
    
    results = []
    
    for test_file in test_files:
        success = run_test(test_file)
        results.append((test_file, success))
    
    # Summary
    print("\n" + "=" * 50)
    print("TEST SUMMARY")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    print(f"Total: {total}")
    print(f"Passed: {passed}")
    print(f"Failed: {total - passed}")
    print(f"Success Rate: {(passed/total)*100:.1f}%")
    
    if passed == total:
        print("\nALL TESTS PASSED!")
        return 0
    else:
        print(f"\n{total - passed} TESTS FAILED")
        return 1

if __name__ == "__main__":
    exit(main())
