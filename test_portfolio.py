#!/usr/bin/env python3
"""Test portfolio loading with robust error handling"""

import sys
import os
sys.path.append('src')
from tracker import Portfolio

def test_portfolio_loading():
    """Test the portfolio loading logic"""
    print("="*50)
    print("Testing Portfolio Loading")
    print("="*50)
    
    try:
        # Test loading the existing portfolio
        portfolio = Portfolio('data/portfolio.json')
        
        print("✅ Portfolio loaded successfully!")
        print(f"   💰 Cash: ${portfolio.state['cash']:,.2f}")
        print(f"   📈 Positions: {len(portfolio.state['positions'])}")
        print(f"   📊 Trade History: {len(portfolio.state['trade_history'])} trades")
        
        # Show first position if exists
        if portfolio.state['positions']:
            first_ticker = list(portfolio.state['positions'].keys())[0]
            pos = portfolio.state['positions'][first_ticker]
            print(f"   🎯 Sample Position: {first_ticker} - {pos['shares']:.2f} shares @ ${pos['entry_price']:.2f}")
        
        return True
        
    except Exception as e:
        print(f"❌ Portfolio loading failed: {e}")
        return False

if __name__ == '__main__':
    success = test_portfolio_loading()
    print("="*50)
    if success:
        print("✅ TEST PASSED")
    else:
        print("❌ TEST FAILED")
    print("="*50)
