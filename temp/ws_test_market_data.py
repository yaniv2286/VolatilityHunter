#!/usr/bin/env python3
"""
Quick test to verify market data access and order placement
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokerage_interface import get_brokerage_interface
import logging

logging.basicConfig(level=logging.INFO)

def test_market_data():
    """Test market data access and small order placement"""
    
    print("=== Testing Market Data Access ===")
    
    # Get IBKR interface
    IBKR_CONFIG = {
        'BROKERAGE_TYPE': 'ibkr',
        'IBKR_HOST':      '127.0.0.1',
        'IBKR_PORT':      7497,
    }
    ibkr = get_brokerage_interface(IBKR_CONFIG)
    
    if not ibkr.connect():
        print("❌ Failed to connect to IBKR")
        return False
    
    print("✅ Connected to IBKR")
    
    # Test market data for a liquid stock
    try:
        from ib_insync import Stock, util
        util.startLoop()
        
        # Create contract for AAPL (very liquid)
        contract = Stock('AAPL', 'SMART', 'USD')
        
        # Request market data
        ticker = ibkr.ib.reqMktData(contract, '', False, False)
        ibkr.ib.sleep(2)  # Wait for data
        
        if hasattr(ticker, 'last') and ticker.last:
            print(f"✅ Market data working: AAPL last price = ${ticker.last}")
        else:
            print("❌ Market data not received")
            return False
            
    except Exception as e:
        print(f"❌ Market data error: {e}")
        return False
    
    # Test small order placement (without actually placing)
    try:
        # Test our limit order logic
        price = ticker.last if hasattr(ticker, 'last') else 150.0
        limit_price = price * 1.005  # 0.5% above market
        
        print(f"✅ Limit order price calculation: ${limit_price:.2f} (based on ${price:.2f})")
        
        # Test order validation
        result = ibkr.validate_order('AAPL', 1, 'buy')
        if result['valid']:
            print("✅ Order validation working")
        else:
            print(f"❌ Order validation failed: {result['reason']}")
            return False
            
    except Exception as e:
        print(f"❌ Order test error: {e}")
        return False
    
    ibkr.disconnect()
    print("✅ All tests passed!")
    return True

if __name__ == "__main__":
    success = test_market_data()
    sys.exit(0 if success else 1)
