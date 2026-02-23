#!/usr/bin/env python3
"""
Force a Real IBKR Trade - Bypass Position Cap
"""

from src.brokerage_interface import get_brokerage_interface
import time
import os

def force_trade():
    print('🎯 FORCING A REAL IBKR TRADE!')
    print('=' * 50)
    
    try:
        # Connect to IBKR
        ibkr = get_brokerage_interface({
            'BROKERAGE_TYPE': 'ibkr',
            'IBKR_HOST': '127.0.0.1',
            'IBKR_PORT': 7497,
            'IBKR_CLIENT_ID': 777
        })
        
        print('🔗 Connecting to IBKR...')
        if not ibkr.connect():
            print('❌ Failed to connect')
            return False
        
        print('✅ Connected to IBKR!')
        
        # Get account info
        account = ibkr.get_account_info()
        print(f'💰 Account Cash: ${account.get("cash", 0):,.2f}')
        
        # Buy 1 share of TSLA (different from AAPL)
        symbol = 'TSLA'
        shares = 1
        side = 'buy'
        
        print(f'📈 FORCING BUY {shares} share of {symbol}...')
        
        # Place market order directly through IBKR
        order_result = ibkr.place_market_order(symbol, shares, side)
        
        if order_result.get('success', False):
            order_id = order_result.get('order_id')
            print(f'✅ Order placed! ID: {order_id}')
            
            # Track order
            print('⏳ Tracking order...')
            time.sleep(3)
            
            status = ibkr.get_order_status(order_id)
            if status.get('success', False):
                order_status = status.get('status', 'unknown')
                print(f'📊 Order Status: {order_status}')
                
                if order_status.lower() == 'filled':
                    print('🎉 TRADE EXECUTED SUCCESSFULLY IN TWS!')
                    print('👀 Check TWS GUI - you should see TSLA position!')
                else:
                    print(f'⏳ Order status: {order_status}')
            else:
                print(f'❌ Status check failed: {status}')
        else:
            print(f'❌ Order failed: {order_result.get("reason", "Unknown")}')
        
        # Get updated positions
        print('📊 Getting updated positions...')
        positions = ibkr.get_positions()
        print(f'📈 Total positions: {len(positions)}')
        
        for pos in positions:
            symbol = pos.get('symbol', 'N/A')
            quantity = pos.get('quantity', 0)
            print(f'   - {symbol}: {quantity} shares')
        
        ibkr.disconnect()
        print('✅ Disconnected from IBKR')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    return True

if __name__ == "__main__":
    force_trade()
