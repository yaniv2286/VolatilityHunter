#!/usr/bin/env python3
"""Test PaperExecutor portfolio loading with robust error handling"""

import sys
import os
sys.path.append('src')
from execution import PaperExecutor

def test_paper_executor_loading():
    """Test the PaperExecutor portfolio loading logic"""
    print("="*50)
    print("Testing PaperExecutor Portfolio Loading")
    print("="*50)
    
    try:
        # Test loading the existing portfolio
        executor = PaperExecutor('data/portfolio.json')
        
        print("✅ PaperExecutor portfolio loaded successfully!")
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
        print(f"❌ PaperExecutor portfolio loading failed: {e}")
        return False

if __name__ == '__main__':
    success = test_paper_executor_loading()
    print("="*50)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*50)
