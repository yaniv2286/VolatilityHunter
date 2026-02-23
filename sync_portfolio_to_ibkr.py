#!/usr/bin/env python3
"""
Sync Current Local Portfolio to IBKR
"""

from src.brokerage_interface import get_brokerage_interface
import json
import os

def sync_portfolio_to_ibkr():
    print('🎯 SYNCING LOCAL PORTFOLIO TO IBKR!')
    print('=' * 50)
    
    try:
        # Load local portfolio
        script_dir = os.path.dirname(os.path.abspath(__file__))
        portfolio_file = os.path.join(script_dir, 'data', 'portfolio.json')
        
        with open(portfolio_file, 'r') as f:
            portfolio_data = json.load(f)
        
        print(f'📁 Local portfolio loaded: {portfolio_file}')
        print(f'💰 Cash: ${portfolio_data.get("cash", 0):,.2f}')
        print(f'📈 Positions: {len(portfolio_data.get("positions", []))}')
        
        # Connect to IBKR
        ibkr = get_brokerage_interface({
            'BROKERAGE_TYPE': 'ibkr',
            'IBKR_HOST': '127.0.0.1',
            'IBKR_PORT': 7497,
            'IBKR_CLIENT_ID': 666
        })
        
        print('🔗 Connecting to IBKR...')
        if not ibkr.connect():
            print('❌ Failed to connect to IBKR')
            return False
        
        print('✅ Connected to IBKR!')
        
        # Get IBKR account info
        account = ibkr.get_account_info()
        print(f'💰 IBKR Cash: ${account.get("cash", 0):,.2f}')
        
        # Get current IBKR positions
        ibkr_positions = ibkr.get_positions()
        print(f'📈 IBKR Positions: {len(ibkr_positions)}')
        
        for pos in ibkr_positions:
            symbol = pos.get('symbol', 'N/A')
            quantity = pos.get('quantity', 0)
            print(f'   - {symbol}: {quantity} shares')
        
        # Sync local positions to IBKR
        local_positions = portfolio_data.get('positions', {})
        print(f'\n🔄 Syncing {len(local_positions)} local positions to IBKR...')
        
        for symbol, position_data in local_positions.items():
            shares = position_data.get('shares', 0)
            if shares > 0:
                print(f'📈 Buying {shares} shares of {symbol}...')
                
                # Place buy order
                order_result = ibkr.place_market_order(symbol, shares, 'buy')
                
                if order_result.get('success', False):
                    order_id = order_result.get('order_id')
                    print(f'   ✅ Order placed: ID {order_id}')
                else:
                    reason = order_result.get('reason', 'Unknown')
                    print(f'   ❌ Order failed: {reason}')
        
        # Get final IBKR positions
        print('\n📊 Final IBKR Positions:')
        final_positions = ibkr.get_positions()
        print(f'📈 Total positions: {len(final_positions)}')
        
        for pos in final_positions:
            symbol = pos.get('symbol', 'N/A')
            quantity = pos.get('quantity', 0)
            print(f'   - {symbol}: {quantity} shares')
        
        ibkr.disconnect()
        print('✅ Disconnected from IBKR')
        print('\n🎉 PORTFOLIO SYNC COMPLETE!')
        print('👀 Check TWS GUI - you should see all positions!')
        
    except Exception as e:
        print(f'❌ Error: {e}')
        return False
    
    return True

if __name__ == "__main__":
    sync_portfolio_to_ibkr()
