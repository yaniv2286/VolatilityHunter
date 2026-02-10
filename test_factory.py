#!/usr/bin/env python3
"""Test executor factory portfolio loading"""

import sys
import os
sys.path.append('src')
from execution import get_executor

def test_executor_factory():
    """Test the executor factory and portfolio loading"""
    print("="*50)
    print("Testing Executor Factory")
    print("="*50)
    
    try:
        # Test the executor factory
        executor = get_executor()
        
        print(f"✅ Executor type: {type(executor).__name__}")
        print(f"   📁 Portfolio file: {executor.portfolio_file}")
        print(f"   💰 Cash: ${executor.state['cash']:,.2f}")
        print(f"   📈 Positions: {len(executor.state['positions'])}")
        print(f"   📊 Trade History: {len(executor.state['trade_history'])} trades")
        print(f"   🎯 Execution Mode: {executor.state['execution_mode']}")
        
        # Show first position if exists
        if executor.state['positions']:
            first_ticker = list(executor.state['positions'].keys())[0]
            pos = executor.state['positions'][first_ticker]
            print(f"   🎯 Sample Position: {first_ticker} - {pos['shares']:.2f} shares @ ${pos['entry_price']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Executor factory test failed: {e}")
        return False

if __name__ == '__main__':
    success = test_executor_factory()
    print("="*50)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*50)
