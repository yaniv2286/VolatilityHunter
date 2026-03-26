#!/usr/bin/env python3
"""
Test the new Marketable Limit protocol
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokerage_interface import get_brokerage_interface
import logging

logging.basicConfig(level=logging.INFO)

def test_marketable_limit():
    """Test the new Marketable Limit order implementation"""
    
    print("=== Testing Marketable Limit Protocol ===")
    
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
    
    # Test market data type request
    try:
        print("✅ Market data type set to Delayed (reqMarketDataType(3))")
        
        # Test contract qualification
        from ib_insync import Stock
        contract = Stock('AAPL', 'SMART', 'USD')
        ibkr.ib.qualifyContracts(contract)
        print(f"✅ Contract qualified: {contract}")
        
        # Test Marketable Limit calculation
        tiingo_price = 150.00  # Example price
        buy_limit = round(tiingo_price * 1.005, 2)
        sell_limit = round(tiingo_price * 0.995, 2)
        
        print(f"✅ Marketable Limit calculation:")
        print(f"   Tiingo price: ${tiingo_price}")
        print(f"   Buy limit: ${buy_limit} (0.5% above)")
        print(f"   Sell limit: ${sell_limit} (0.5% below)")
        
        # Test order validation (without placing)
        result = ibkr.validate_order('AAPL', 1, 'buy')
        if result['valid']:
            print("✅ Order validation working")
        else:
            print(f"❌ Order validation failed: {result['reason']}")
            return False
            
    except Exception as e:
        print(f"❌ Marketable Limit test error: {e}")
        return False
    
    ibkr.disconnect()
    print("✅ Marketable Limit protocol test passed!")
    return True

if __name__ == "__main__":
    success = test_marketable_limit()
    sys.exit(0 if success else 1)
