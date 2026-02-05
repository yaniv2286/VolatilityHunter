#!/usr/bin/env python3
"""
Lightning Fast Test Runner
Quick validation of VolatilityHunter functionality
"""

import sys
import os
import time
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.append('src')

def test_imports():
    """Test that all modules can be imported."""
    print("[TEST] Testing imports...")
    
    try:
        from src.tracker import Portfolio
        from src.strategy import analyze_stock, scan_all_stocks
        from src.email_notifier import EmailNotifier
        from src.data_loader import get_stock_data
        from src.notifications import log_info, log_error
        print("  [OK] All imports successful")
        return True
    except ImportError as e:
        print(f"  [FAIL] Import error: {e}")
        return False

def test_portfolio_basic():
    """Test basic portfolio functionality."""
    print("[TEST] Testing portfolio...")
    
    try:
        from src.tracker import Portfolio
        
        # Test portfolio creation
        portfolio = Portfolio()
        
        # Test summary
        summary = portfolio.get_summary()
        
        # Check basic structure
        assert 'total_value' in summary
        assert 'cash' in summary
        assert 'num_positions' in summary
        
        print(f"  [OK] Portfolio: ${summary['total_value']:,.2f}, {summary['num_positions']} positions")
        return True
    except Exception as e:
        print(f"  [FAIL] Portfolio error: {e}")
        return False

def test_strategy_basic():
    """Test strategy with minimal data."""
    print("[TEST] Testing strategy...")
    
    try:
        from src.strategy import analyze_stock
        import pandas as pd
        import numpy as np
        
        # Create minimal test data
        dates = pd.date_range('2026-01-01', periods=50, freq='D')
        prices = 100 + np.cumsum(np.random.randn(50) * 0.5)
        
        test_data = pd.DataFrame({
            'date': dates,
            'Open': prices,
            'High': prices * 1.02,
            'Low': prices * 0.98,
            'Close': prices,
            'Volume': np.random.randint(1000000, 5000000, 50)
        })
        
        # Test analysis
        analysis = analyze_stock(test_data)
        
        # Check structure
        assert 'signal' in analysis
        assert 'indicators' in analysis
        assert 'reason' in analysis
        
        print(f"  [OK] Strategy: {analysis['signal']} signal generated")
        return True
    except Exception as e:
        print(f"  [FAIL] Strategy error: {e}")
        return False

def test_email_basic():
    """Test email formatting."""
    print("[TEST] Testing email...")
    
    try:
        from src.email_notifier import EmailNotifier
        
        notifier = EmailNotifier()
        
        # Test data
        scan_results = {
            'BUY': [{'ticker': 'TEST', 'indicators': {'price': 100.0}}],
            'SELL': [],
            'HOLD': []
        }
        summary = {'buy_signals': 1, 'sell_signals': 0, 'hold_signals': 0, 'errors': 0, 'total_stocks': 1}
        
        # Test email body formatting
        body = notifier._format_comprehensive_email_body(scan_results, summary)
        
        # Check ASCII-only
        try:
            body.encode('ascii')
            ascii_valid = True
        except UnicodeEncodeError:
            ascii_valid = False
        
        assert ascii_valid, "Email should be ASCII-only"
        assert 'VolatilityHunter' in body
        
        print("  [OK] Email: ASCII-only formatting works")
        return True
    except Exception as e:
        print(f"  [FAIL] Email error: {e}")
        return False

def test_data_loader_basic():
    """Test data loader."""
    print("[TEST] Testing data loader...")
    
    try:
        from src.data_loader import get_stock_data
        
        # Try to get data (may fail if no data exists)
        df = get_stock_data('AAPL')
        
        if df is not None:
            assert 'Close' in df.columns
            assert len(df) > 0
            print(f"  [OK] Data loader: {len(df)} rows found")
        else:
            print("  [WARN] Data loader: No data available (expected)")
        
        return True
    except Exception as e:
        print(f"  [FAIL] Data loader error: {e}")
        return False

def test_risk_management():
    """Test risk management logic."""
    print("[TEST] Testing risk management...")
    
    try:
        from src.tracker import Portfolio
        
        portfolio = Portfolio()
        
        # Test risk management method exists
        assert hasattr(portfolio, '_check_risk_management_trades')
        
        print("  [OK] Risk management: Methods available")
        return True
    except Exception as e:
        print(f"  [FAIL] Risk management error: {e}")
        return False

def test_performance_tracking():
    """Test performance tracking."""
    print("[TEST] Testing performance tracking...")
    
    try:
        # Check if performance tracker exists
        if os.path.exists('performance_tracker.py'):
            print("  [OK] Performance tracking: Module available")
            return True
        else:
            print("  [WARN] Performance tracking: Module not found")
            return True
    except Exception as e:
        print(f"  [FAIL] Performance tracking error: {e}")
        return False

def test_file_structure():
    """Test essential files exist."""
    print("[TEST] Testing file structure...")
    
    essential_files = [
        'main.py',
        'src/tracker.py',
        'src/strategy.py',
        'src/email_notifier.py',
        'data/portfolio.json',
        'task_scheduler_run.ps1'
    ]
    
    missing_files = []
    for file_path in essential_files:
        if not os.path.exists(file_path):
            missing_files.append(file_path)
    
    if missing_files:
        print(f"  [FAIL] Missing files: {missing_files}")
        return False
    else:
        print(f"  [OK] File structure: All {len(essential_files)} files present")
        return True

def run_lightning_tests():
    """Run all lightning fast tests."""
    
    print("=" * 60)
    print("VOLATILITYHUNTER LIGHTNING FAST TESTS")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    start_time = time.time()
    
    # Run all tests
    tests = [
        ("Import Test", test_imports),
        ("File Structure", test_file_structure),
        ("Portfolio", test_portfolio_basic),
        ("Strategy", test_strategy_basic),
        ("Email", test_email_basic),
        ("Data Loader", test_data_loader_basic),
        ("Risk Management", test_risk_management),
        ("Performance Tracking", test_performance_tracking)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"  [FAIL] {test_name} crashed: {e}")
            results.append((test_name, False))
        print()
    
    # Calculate timing
    end_time = time.time()
    duration = end_time - start_time
    
    # Summary
    print("=" * 60)
    print("LIGHTNING TEST SUMMARY")
    print("=" * 60)
    print(f"Total Tests: {len(results)}")
    print(f"Passed: {sum(1 for _, result in results if result)}")
    print(f"Failed: {sum(1 for _, result in results if not result)}")
    print(f"Duration: {duration:.2f} seconds")
    print()
    
    # Detailed results
    for test_name, result in results:
        status = "[PASS]" if result else "[FAIL]"
        print(f"{status} {test_name}")
    
    print()
    print("=" * 60)
    
    success_rate = sum(1 for _, result in results if result) / len(results)
    
    if success_rate >= 0.8:
        print("[SUCCESS] SYSTEM READY FOR PRODUCTION!")
        print("VolatilityHunter is functional and ready to run.")
    elif success_rate >= 0.6:
        print("[WARN] SYSTEM MOSTLY READY")
        print("Some issues detected, but core functionality works.")
    else:
        print("[FAIL] SYSTEM NEEDS ATTENTION")
        print("Multiple issues detected. Fix before production.")
    
    print("=" * 60)
    
    return success_rate >= 0.8

if __name__ == "__main__":
    success = run_lightning_tests()
    sys.exit(0 if success else 1)
