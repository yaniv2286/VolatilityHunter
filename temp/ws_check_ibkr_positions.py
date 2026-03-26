#!/usr/bin/env python3
"""
Check real IBKR positions and account status
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.brokerage_interface import get_brokerage_interface
import logging

logging.basicConfig(level=logging.INFO)

def check_ibkr_positions():
    """Show real IBKR positions and account info"""
    
    print("=== IBKR REAL POSITIONS ===")
    
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
    
    # Get account info
    print("\n📊 ACCOUNT INFO:")
    account_info = ibkr.get_account_info()
    if account_info:
        print(f"   Cash: ${account_info.get('cash', 0):,.2f}")
        print(f"   Portfolio Value: ${account_info.get('portfolio_value', 0):,.2f}")
        print(f"   Buying Power: ${account_info.get('buying_power', 0):,.2f}")
        print(f"   Equity: ${account_info.get('equity', 0):,.2f}")
    else:
        print("   ❌ No account info available")
    
    # Get positions
    print("\n📈 POSITIONS:")
    positions = ibkr.get_positions()
    
    if not positions:
        print("   No positions found")
    else:
        total_value = 0
        total_pnl = 0
        
        for pos in positions:
            symbol = pos['symbol']
            shares = pos['quantity']
            entry_price = pos['entry_price']
            current_price = pos['current_price']
            market_value = pos['market_value']
            unrealized_pnl = pos['unrealized_pl']
            unrealized_pnl_pct = pos['unrealized_plpc']
            
            print(f"\n   {symbol}:")
            print(f"     Shares: {shares:,}")
            print(f"     Entry: ${entry_price:.2f}")
            print(f"     Current: ${current_price:.2f}")
            print(f"     Market Value: ${market_value:,.2f}")
            print(f"     P&L: ${unrealized_pnl:,.2f} ({unrealized_pnl_pct:+.1f}%)")
            
            total_value += market_value
            total_pnl += unrealized_pnl
        
        print(f"\n📊 SUMMARY:")
        print(f"   Total Positions: ${total_value:,.2f}")
        print(f"   Total P&L: ${total_pnl:,.2f}")
        print(f"   Number of Positions: {len(positions)}")
    
    # Get open orders
    print("\n🔄 OPEN ORDERS:")
    try:
        if hasattr(ibkr, 'ib') and ibkr.ib:
            open_orders = ibkr.ib.openOrders()
            if not open_orders:
                print("   No open orders")
            else:
                for order in open_orders:
                    print(f"   {order.contract.symbol}: {order.action} {order.totalQuantity} @ {order.orderType}")
                    if hasattr(order, 'limitPrice') and order.limitPrice:
                        print(f"     Limit Price: ${order.limitPrice:.2f}")
                    print(f"     Status: {order.orderStatus.status}")
    except Exception as e:
        print(f"   Error getting orders: {e}")
    
    ibkr.disconnect()
    print("\n✅ IBKR check complete!")
    return True

if __name__ == "__main__":
    check_ibkr_positions()
