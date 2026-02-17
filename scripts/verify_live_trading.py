#!/usr/bin/env python3
"""
VolatilityHunter Live Trading Validation Script
Phase 8: Live Trading Integration Verification
"""

import os
import sys
import json
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
sys.path.append(project_root)

def test_brokerage_interface():
    """Test brokerage interface functionality"""
    print("[TEST] Testing Brokerage Interface...")
    
    try:
        from src.brokerage_interface import get_brokerage_interface, BrokerageInterface
        
        # Test with mock config
        config = {
            'BROKERAGE_TYPE': 'alpaca',
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_SECRET_KEY': 'test_secret',
            'ALPACA_BASE_URL': 'https://paper-api.alpaca.markets'
        }
        
        # Test factory function
        brokerage = get_brokerage_interface(config)
        
        if isinstance(brokerage, BrokerageInterface):
            print("  ✅ Brokerage interface created successfully")
            print(f"  ✅ Brokerage type: {type(brokerage).__name__}")
            return True
        else:
            print("  ❌ Failed to create brokerage interface")
            return False
            
    except ImportError as e:
        print(f"  ❌ Import error: {e}")
        return False
    except Exception as e:
        print(f"  ❌ Unexpected error: {e}")
        return False

def test_live_executor():
    """Test LiveExecutor initialization"""
    print("[TEST] Testing Live Executor...")
    
    try:
        from src.execution import LiveExecutor
        
        # Create test config file
        test_config = {
            'TRADING_MODE': 'LIVE',
            'BROKERAGE_TYPE': 'alpaca',
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_SECRET_KEY': 'test_secret'
        }
        
        config_file = 'test_live_config.json'
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        # Test portfolio file
        test_portfolio = {
            'cash': 100000.0,
            'positions': {},
            'trade_history': [],
            'execution_mode': 'LIVE'
        }
        
        portfolio_file = 'test_live_portfolio.json'
        with open(portfolio_file, 'w') as f:
            json.dump(test_portfolio, f, indent=2)
        
        # Create LiveExecutor
        executor = LiveExecutor(portfolio_file, config_file)
        
        if isinstance(executor, LiveExecutor):
            print("  ✅ LiveExecutor created successfully")
            print(f"  ✅ Execution mode: {executor.execution_mode}")
            print(f"  ✅ Portfolio loaded: {len(executor.state['positions'])} positions")
            return True
        else:
            print("  ❌ Failed to create LiveExecutor")
            return False
            
    except Exception as e:
        print(f"  ❌ LiveExecutor test failed: {e}")
        return False
    finally:
        # Cleanup test files
        for file in ['test_live_config.json', 'test_live_portfolio.json']:
            if os.path.exists(file):
                os.remove(file)

def test_executor_factory():
    """Test executor factory with live mode"""
    print("[TEST] Testing Executor Factory...")
    
    try:
        from src.execution import get_executor
        
        # Create test config
        test_config = {
            'TRADING_MODE': 'LIVE',
            'BROKERAGE_TYPE': 'alpaca',
            'ALPACA_API_KEY': 'test_key',
            'ALPACA_SECRET_KEY': 'test_secret'
        }
        
        config_file = 'test_factory_config.json'
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        # Test factory function
        executor = get_executor(config_file, 'test_portfolio.json')
        
        if executor.__class__.__name__ == 'LiveExecutor':
            print("  ✅ Factory returned LiveExecutor for LIVE mode")
            return True
        else:
            print(f"  ❌ Factory returned {type(executor).__name__} instead of LiveExecutor")
            return False
            
    except Exception as e:
        print(f"  ❌ Factory test failed: {e}")
        return False
    finally:
        # Cleanup test files
        for file in ['test_factory_config.json']:
            if os.path.exists(file):
                os.remove(file)

def test_paper_fallback():
    """Test paper trading fallback"""
    print("[TEST] Testing Paper Trading Fallback...")
    
    try:
        from src.execution import LiveExecutor
        
        # Create test config with invalid credentials
        test_config = {
            'TRADING_MODE': 'LIVE',
            'BROKERAGE_TYPE': 'alpaca',
            'ALPACA_API_KEY': 'invalid_key',
            'ALPACA_SECRET_KEY': 'invalid_secret'
        }
        
        config_file = 'test_fallback_config.json'
        with open(config_file, 'w') as f:
            json.dump(test_config, f, indent=2)
        
        # Create LiveExecutor with invalid credentials
        executor = LiveExecutor('test_portfolio.json', config_file)
        
        # Should fallback to PAPER_FALLBACK mode
        if executor.execution_mode == 'PAPER_FALLBACK':
            print("  ✅ Paper trading fallback activated correctly")
            return True
        else:
            print(f"  ❌ Expected PAPER_FALLBACK, got {executor.execution_mode}")
            return False
            
    except Exception as e:
        print(f"  ❌ Fallback test failed: {e}")
        return False
    finally:
        # Cleanup test files
        for file in ['test_fallback_config.json']:
            if os.path.exists(file):
                os.remove(file)

def test_order_validation():
    """Test order validation logic"""
    print("[TEST] Testing Order Validation...")
    
    try:
        from src.brokerage_interface import BrokerageInterface
        
        # Create mock brokerage for validation testing
        class MockBrokerage(BrokerageInterface):
            def connect(self): return False
            def disconnect(self): pass
            def get_account_info(self): return {}
            def get_positions(self): return []
            def place_market_order(self, symbol, quantity, side): return {}
            def place_limit_order(self, symbol, quantity, side, price): return {}
            def cancel_order(self, order_id): return {}
            def get_order_status(self, order_id): return {}
        
        brokerage = MockBrokerage({})
        
        # Test valid order
        result = brokerage.validate_order('AAPL', 100, 'buy')
        if result['valid']:
            print("  ✅ Valid order validation passed")
        else:
            print(f"  ❌ Valid order failed: {result['reason']}")
            return False
        
        # Test invalid quantity
        result = brokerage.validate_order('AAPL', -10, 'buy')
        if not result['valid']:
            print("  ✅ Invalid quantity validation passed")
        else:
            print("  ❌ Invalid quantity validation failed")
            return False
        
        # Test invalid side
        result = brokerage.validate_order('AAPL', 100, 'invalid')
        if not result['valid']:
            print("  ✅ Invalid side validation passed")
        else:
            print("  ❌ Invalid side validation failed")
            return False
        
        return True
        
    except Exception as e:
        print(f"  ❌ Order validation test failed: {e}")
        return False

def main():
    """Main validation function"""
    print("="*80)
    print("VolatilityHunter Live Trading Validation")
    print("Phase 8: Live Trading Integration")
    print("="*80)
    
    tests = [
        test_brokerage_interface,
        test_live_executor,
        test_executor_factory,
        test_paper_fallback,
        test_order_validation
    ]
    
    passed = 0
    total = len(tests)
    
    for test in tests:
        try:
            if test():
                passed += 1
        except Exception as e:
            print(f"  ❌ Test failed with exception: {e}")
        print()
    
    print("="*80)
    print(f"Validation Results: {passed}/{total} tests passed")
    
    if passed == total:
        print("✅ All tests passed - Live Trading Integration is ready!")
        print("🚀 Phase 8 implementation complete")
        return 0
    else:
        print("❌ Some tests failed - Review implementation")
        return 1

if __name__ == '__main__':
    sys.exit(main())
