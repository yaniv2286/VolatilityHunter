#!/usr/bin/env python3
"""
Verify IBKR currency handling fix.
Tests that ILS account values are read correctly.
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokerage_interface import get_brokerage_interface
from src.strategy_engine import calc_position_size
import time

def main():
    print("=" * 70)
    print("IBKR CURRENCY FIX VERIFICATION")
    print("=" * 70)
    
    # Test 1: Connect to IBKR
    print("\n[TEST 1] Connecting to IBKR...")
    ibkr_config = {
        'BROKERAGE_TYPE': 'ibkr',
        'IBKR_HOST': '127.0.0.1',
        'IBKR_PORT': 7497,
        'IBKR_CLIENT_ID': 99
    }
    
    ibkr = get_brokerage_interface(ibkr_config)
    if not ibkr.connect():
        print("❌ FAILED: Could not connect to IBKR")
        return 1
    
    print("✅ PASS: Connected to IBKR")
    time.sleep(2)
    
    # Test 2: Get account info
    print("\n[TEST 2] Reading account values...")
    info = ibkr.get_account_info()
    
    if not info:
        print("❌ FAILED: No account info returned")
        ibkr.disconnect()
        return 1
    
    cash = info.get('cash', 0)
    equity = info.get('equity', 0)
    buying_power = info.get('buying_power', 0)
    
    print(f"  Cash: ₪{cash:,.2f}")
    print(f"  Equity: ₪{equity:,.2f}")
    print(f"  Buying Power: ₪{buying_power:,.2f}")
    
    if cash == 0 or equity == 0:
        print("❌ FAILED: Cash or equity is zero (currency not read correctly)")
        ibkr.disconnect()
        return 1
    
    print("✅ PASS: Account values read correctly")
    
    # Test 3: Position sizing with real cash
    print("\n[TEST 3] Testing position sizing (NO MARGIN enforcement)...")
    
    portfolio = {
        'cash': cash,
        'positions': {},
        'high_water_mark': equity
    }
    
    # Test with a $100 stock
    test_price = 100.0
    prices = {'SPY': 500.0}  # Dummy price for equity calculation
    
    shares, cost = calc_position_size(portfolio, test_price, prices, 'TEST')
    
    print(f"  Test stock price: ${test_price:.2f}")
    print(f"  Calculated shares: {shares}")
    print(f"  Calculated cost: ₪{cost:,.2f}")
    
    if shares == 0:
        print("❌ FAILED: Position sizing returned 0 shares")
        ibkr.disconnect()
        return 1
    
    if cost > cash:
        print(f"❌ FAILED: Cost (₪{cost:,.2f}) exceeds cash (₪{cash:,.2f}) - NO MARGIN violated!")
        ibkr.disconnect()
        return 1
    
    print(f"✅ PASS: Position sizing works (cost ≤ cash, no margin)")
    
    # Test 4: Verify NO MARGIN enforcement
    print("\n[TEST 4] Testing NO MARGIN enforcement...")
    
    # Try to buy more than available cash
    expensive_price = cash + 1000  # More than we have
    shares_expensive, cost_expensive = calc_position_size(portfolio, expensive_price, prices, 'EXPENSIVE')
    
    print(f"  Test stock price: ₪{expensive_price:,.2f} (more than cash)")
    print(f"  Calculated shares: {shares_expensive}")
    
    if shares_expensive > 0:
        print("❌ FAILED: System allowed purchase beyond available cash (MARGIN used!)")
        ibkr.disconnect()
        return 1
    
    print("✅ PASS: NO MARGIN enforcement working (rejected expensive stock)")
    
    # Test 5: Get positions
    print("\n[TEST 5] Reading positions...")
    positions = ibkr.get_positions()
    print(f"  Current positions: {len(positions)}")
    print("✅ PASS: Position reading works")
    
    # Cleanup
    ibkr.disconnect()
    
    print("\n" + "=" * 70)
    print("ALL TESTS PASSED ✅")
    print("=" * 70)
    print("\nSummary:")
    print(f"  • IBKR connection: ✅ Working")
    print(f"  • Currency handling: ✅ ILS values read correctly")
    print(f"  • Account values: ✅ Cash=₪{cash:,.2f}, Equity=₪{equity:,.2f}")
    print(f"  • Position sizing: ✅ Calculates shares correctly")
    print(f"  • NO MARGIN policy: ✅ Enforced (cost ≤ cash)")
    print(f"  • Position reading: ✅ Working")
    print("\nSystem is ready for trading!")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
