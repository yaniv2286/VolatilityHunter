#!/usr/bin/env python3
"""
Quick Test Runner
Fast validation script for VolatilityHunter functionality
"""

import sys
import os
import subprocess
from datetime import datetime

def run_lightning_tests():
    """Run lightning fast tests."""
    print("🚀 Running lightning fast validation...")
    
    try:
        result = subprocess.run([sys.executable, 'lightning_tests.py'], 
                              capture_output=True, text=True, timeout=30)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Lightning tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running lightning tests: {e}")
        return False

def run_quick_unit_tests():
    """Run quick unit tests."""
    print("🧪 Running quick unit tests...")
    
    try:
        result = subprocess.run([sys.executable, 'quick_tests.py'], 
                              capture_output=True, text=True, timeout=60)
        
        print(result.stdout)
        if result.stderr:
            print("STDERR:", result.stderr)
        
        return result.returncode == 0
    except subprocess.TimeoutExpired:
        print("❌ Unit tests timed out")
        return False
    except Exception as e:
        print(f"❌ Error running unit tests: {e}")
        return False

def check_system_health():
    """Check overall system health."""
    print("🏥 Checking system health...")
    
    health_checks = {
        'Python': sys.version_info >= (3, 9),
        'Virtual Environment': hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix),
        'Main Script': os.path.exists('main.py'),
        'Portfolio Data': os.path.exists('data/portfolio.json'),
        'Task Scheduler': os.path.exists('task_scheduler_run.ps1'),
        'Config File': os.path.exists('.env')
    }
    
    all_good = True
    for check, status in health_checks.items():
        status_icon = "[OK]" if status else "[FAIL]"
        print(f"  {status_icon} {check}")
        if not status:
            all_good = False
    
    return all_good

def main():
    """Main test runner."""
    print("=" * 60)
    print("VOLATILITYHUNTER QUICK TEST RUNNER")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # System health check
    health_ok = check_system_health()
    print()
    
    if not health_ok:
        print("⚠️  System health issues detected. Continue anyway...")
        print()
    
    # Run tests
    lightning_ok = run_lightning_tests()
    print()
    
    unit_ok = run_quick_unit_tests()
    print()
    
    # Final summary
    print("=" * 60)
    print("FINAL TEST SUMMARY")
    print("=" * 60)
    print(f"System Health: {'[PASS]' if health_ok else '[FAIL]'}")
    print(f"Lightning Tests: {'[PASS]' if lightning_ok else '[FAIL]'}")
    print(f"Unit Tests: {'[PASS]' if unit_ok else '[FAIL]'}")
    print()
    
    overall_success = health_ok and lightning_ok and unit_ok
    
    if overall_success:
        print("[SUCCESS] ALL TESTS PASSED!")
        print("VolatilityHunter is ready for production!")
        print()
        print("Next steps:")
        print("1. Set up Task Scheduler: powershell -ExecutionPolicy Bypass -File 'setup_scheduler.ps1'")
        print("2. Run manual test: powershell -ExecutionPolicy Bypass -File 'task_scheduler_run.ps1' -Test")
        print("3. Monitor daily execution at 9:00 AM")
    else:
        print("[FAIL] SOME TESTS FAILED")
        print("Please fix issues before production deployment")
        print()
        if not health_ok:
            print("System Health: Fix missing files or configuration")
        if not lightning_ok:
            print("Lightning Tests: Check core functionality")
        if not unit_ok:
            print("Unit Tests: Check detailed component tests")
    
    print("=" * 60)
    
    return overall_success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
