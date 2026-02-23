"""
Sweet Spot Configuration Validation Script
Validates all Sweet Spot Blueprint settings and dependencies
"""

import sys
import os
import json
from datetime import datetime

# Add project root to path
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

def validate_config_file():
    """Validate config.json structure and Sweet Spot settings"""
    print("="*60)
    print("Validating Configuration File")
    print("="*60)
    
    try:
        # Check if config file exists
        if not os.path.exists('config.json'):
            print("❌ config.json not found")
            return False
        
        # Load and validate config
        with open('config.json', 'r') as f:
            config = json.load(f)
        
        print("✅ config.json loaded successfully")
        
        # Validate required top-level keys
        required_keys = ['TIME_OFFSET', 'EMAIL_RECIPIENTS', 'RISK_TOLERANCE', 'DATA_SOURCE', 'TRADING_MODE']
        for key in required_keys:
            if key not in config:
                print(f"❌ Missing required key: {key}")
                return False
        print("✅ Required top-level keys present")
        
        # Validate Sweet Spot configuration
        if 'SWEET_SPOT' not in config:
            print("❌ SWEET_SPOT configuration missing")
            return False
        
        ss_config = config['SWEET_SPOT']
        print("✅ SWEET_SPOT configuration found")
        
        # Validate Sweet Spot settings
        ss_required = ['enable_patterns', 'enable_spread_monitoring', 'enable_time_filters', 'pattern_weight', 'min_enhanced_score']
        for key in ss_required:
            if key not in ss_config:
                print(f"❌ Missing Sweet Spot setting: {key}")
                return False
        print("✅ Sweet Spot settings complete")
        
        # Validate strategy selection
        strategy_selection = config.get('STRATEGY_SELECTION', 'v7_2')
        if strategy_selection not in ['v7_2', 'sweet_spot']:
            print(f"❌ Invalid strategy selection: {strategy_selection}")
            return False
        print(f"✅ Strategy selection: {strategy_selection}")
        
        # Validate Sweet Spot sub-configurations
        if 'spread_limits' in ss_config:
            limits = ss_config['spread_limits']
            required_limits = ['under_100_max_cents', '250_to_299_max_cents', 'over_300_max_cents']
            for limit in required_limits:
                if limit not in limits:
                    print(f"❌ Missing spread limit: {limit}")
                    return False
            print("✅ Spread limits configured")
        
        if 'time_filters' in ss_config:
            filters = ss_config['time_filters']
            required_filters = ['enable_10_06_rule', 'enable_friday_rule']
            for filter_key in required_filters:
                if filter_key not in filters:
                    print(f"❌ Missing time filter: {filter_key}")
                    return False
            print("✅ Time filters configured")
        
        if 'pattern_weights' in ss_config:
            weights = ss_config['pattern_weights']
            required_patterns = ['engulfing', 'hammer', 'doji', 'w_formation', 'm_formation', 'head_shoulders', 'fifty_percent_rule']
            for pattern in required_patterns:
                if pattern not in weights:
                    print(f"❌ Missing pattern weight: {pattern}")
                    return False
            print("✅ Pattern weights configured")
        
        return True
        
    except json.JSONDecodeError as e:
        print(f"❌ Invalid JSON in config.json: {e}")
        return False
    except Exception as e:
        print(f"❌ Error validating config: {e}")
        return False

def validate_module_imports():
    """Validate all Sweet Spot modules can be imported"""
    print("="*60)
    print("Validating Module Imports")
    print("="*60)
    
    modules = [
        ('src.strategy_factory', 'StrategyFactory'),
        ('src.sweet_spot_strategy', 'SweetSpotStrategy'),
        ('src.patterns.candlestick_patterns', 'get_candlestick_signals'),
        ('src.patterns.chart_patterns', 'get_chart_pattern_signals'),
        ('src.patterns.pattern_utils', 'combine_pattern_signals'),
        ('src.market_microstructure.time_filters', 'check_10_06_rule'),
        ('src.market_microstructure.spread_monitor', 'SpreadMonitor')
    ]
    
    for module_name, class_name in modules:
        try:
            module = __import__(module_name, fromlist=[class_name])
            getattr(module, class_name)
            print(f"✅ {module_name}.{class_name}")
        except ImportError as e:
            print(f"❌ Failed to import {module_name}.{class_name}: {e}")
            return False
        except AttributeError as e:
            print(f"❌ {class_name} not found in {module_name}: {e}")
            return False
    
    return True

def validate_pattern_functionality():
    """Validate pattern recognition functionality"""
    print("="*60)
    print("Validating Pattern Functionality")
    print("="*60)
    
    try:
        import pandas as pd
        import numpy as np
        from src.patterns.candlestick_patterns import get_candlestick_signals
        from src.patterns.chart_patterns import get_chart_pattern_signals
        from src.patterns.pattern_utils import combine_pattern_signals, get_pattern_summary
        
        # Create test data
        dates = pd.date_range('2023-01-01', periods=30, freq='D')
        np.random.seed(42)
        
        df = pd.DataFrame({
            'open': 100 + np.random.randn(30) * 0.5,
            'high': 100 + np.random.randn(30) * 0.5 + 1,
            'low': 100 + np.random.randn(30) * 0.5 - 1,
            'close': 100 + np.random.randn(30) * 0.5,
            'volume': np.random.randint(100000, 1000000, 30)
        }, index=dates)
        
        print("✅ Test data created")
        
        # Test candlestick patterns
        candlestick_signals = get_candlestick_signals(df)
        if not isinstance(candlestick_signals, dict):
            print("❌ Candlestick signals not a dictionary")
            return False
        print("✅ Candlestick patterns working")
        
        # Test chart patterns
        chart_signals = get_chart_pattern_signals(df)
        if not isinstance(chart_signals, dict):
            print("❌ Chart signals not a dictionary")
            return False
        print("✅ Chart patterns working")
        
        # Test pattern utilities
        combined_signals = combine_pattern_signals(candlestick_signals, chart_signals)
        pattern_summary = get_pattern_summary(combined_signals)
        
        if not isinstance(pattern_summary, dict):
            print("❌ Pattern summary not a dictionary")
            return False
        print("✅ Pattern utilities working")
        
        return True
        
    except Exception as e:
        print(f"❌ Pattern functionality error: {e}")
        return False

def validate_market_microstructure():
    """Validate market microstructure components"""
    print("="*60)
    print("Validating Market Microstructure")
    print("="*60)
    
    try:
        from src.market_microstructure.time_filters import (
            check_10_06_rule, check_friday_rule, calculate_time_score
        )
        from src.market_microstructure.spread_monitor import SpreadMonitor
        
        # Test time filters
        is_10_06_optimal, msg_10_06 = check_10_06_rule()
        if not isinstance(is_10_06_optimal, bool):
            print("❌ 10:06 rule return type invalid")
            return False
        print("✅ 10:06 AM rule working")
        
        is_friday_optimal, msg_friday = check_friday_rule()
        if not isinstance(is_friday_optimal, bool):
            print("❌ Friday rule return type invalid")
            return False
        print("✅ Friday rule working")
        
        time_score = calculate_time_score()
        if not isinstance(time_score, (int, float)):
            print("❌ Time score return type invalid")
            return False
        print("✅ Time scoring working")
        
        # Test spread monitor
        monitor = SpreadMonitor(brokerage_interface=None)
        is_acceptable, msg, spread_pct = monitor.check_spread_limits('AAPL', 150.0)
        
        if not isinstance(is_acceptable, bool):
            print("❌ Spread check return type invalid")
            return False
        print("✅ Spread monitoring working (no IBKR)")
        
        return True
        
    except Exception as e:
        print(f"❌ Market microstructure error: {e}")
        return False

def validate_strategy_factory():
    """Validate strategy factory functionality"""
    print("="*60)
    print("Validating Strategy Factory")
    print("="*60)
    
    try:
        from src.strategy_factory import get_strategy_factory, create_trading_strategy
        
        # Test factory creation
        factory = get_strategy_factory()
        if factory is None:
            print("❌ Strategy factory not created")
            return False
        print("✅ Strategy factory created")
        
        # Test strategy info
        info = factory.get_strategy_info()
        if not isinstance(info, dict):
            print("❌ Strategy info not a dictionary")
            return False
        print("✅ Strategy info retrieved")
        
        # Test strategy creation
        strategy = create_trading_strategy()
        if strategy is None:
            print("❌ Strategy not created")
            return False
        print("✅ Trading strategy created")
        
        # Test strategy switching
        original_strategy = info['selected_strategy']
        if factory.switch_strategy('sweet_spot'):
            print("✅ Strategy switching works")
            # Switch back
            factory.switch_strategy(original_strategy)
        else:
            print("⚠️ Strategy switching failed (may be expected)")
        
        return True
        
    except Exception as e:
        print(f"❌ Strategy factory error: {e}")
        return False

def validate_data_dependencies():
    """Validate data files and dependencies"""
    print("="*60)
    print("Validating Data Dependencies")
    print("="*60)
    
    try:
        # Check for required directories
        required_dirs = ['src', 'data', 'logs', 'docs']
        for dir_name in required_dirs:
            if not os.path.exists(dir_name):
                print(f"❌ Missing directory: {dir_name}")
                return False
        print("✅ Required directories present")
        
        # Check for Sweet Spot subdirectories
        ss_dirs = ['src/patterns', 'src/market_microstructure']
        for dir_name in ss_dirs:
            if not os.path.exists(dir_name):
                print(f"❌ Missing Sweet Spot directory: {dir_name}")
                return False
        print("✅ Sweet Spot directories present")
        
        # Check for key files
        key_files = [
            'src/sweet_spot_strategy.py',
            'src/strategy_factory.py',
            'src/patterns/__init__.py',
            'src/patterns/candlestick_patterns.py',
            'src/patterns/chart_patterns.py',
            'src/patterns/pattern_utils.py',
            'src/market_microstructure/__init__.py',
            'src/market_microstructure/time_filters.py',
            'src/market_microstructure/spread_monitor.py'
        ]
        
        for file_name in key_files:
            if not os.path.exists(file_name):
                print(f"❌ Missing file: {file_name}")
                return False
        print("✅ Sweet Spot files present")
        
        return True
        
    except Exception as e:
        print(f"❌ Data dependency error: {e}")
        return False

def main():
    """Run all validation tests"""
    print("🔍 Sweet Spot Blueprint Configuration Validation")
    print(f"📅 Validation Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    tests = [
        ("Configuration File", validate_config_file),
        ("Module Imports", validate_module_imports),
        ("Pattern Functionality", validate_pattern_functionality),
        ("Market Microstructure", validate_market_microstructure),
        ("Strategy Factory", validate_strategy_factory),
        ("Data Dependencies", validate_data_dependencies)
    ]
    
    results = []
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
            print()
        except Exception as e:
            print(f"❌ {test_name} test crashed: {e}")
            results.append((test_name, False))
            print()
    
    # Summary
    print("="*60)
    print("VALIDATION SUMMARY")
    print("="*60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status}: {test_name}")
    
    print()
    print(f"Overall: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 All validations passed! Sweet Spot configuration is ready.")
        return True
    else:
        print("⚠️ Some validations failed. Please check the configuration.")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
