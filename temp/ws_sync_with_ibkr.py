"""
Sync portfolio.json with IBKR as ground truth
IBKR is the source of truth - portfolio.json reflects IBKR state
"""
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from ib_insync import IB, util
import json
from datetime import datetime

def sync_portfolio_with_ibkr():
    """Connect to IBKR and sync portfolio.json to match exactly"""
    
    ib = IB()
    
    try:
        print("Connecting to IBKR at 127.0.0.1:7497...")
        ib.connect('127.0.0.1', 7497, clientId=99)
        util.sleep(3)
        print("✅ Connected to IBKR\n")
        
        # Get account values
        account_values = ib.accountValues()
        
        # Get cash balance (in base currency)
        cash_values = [v for v in account_values if v.tag == 'TotalCashValue']
        base_currency = None
        total_cash = 0.0
        
        for cv in cash_values:
            if cv.currency == 'BASE':
                base_currency = 'BASE'
                total_cash = float(cv.value)
                break
        
        # If no BASE, use the primary currency (likely ILS or USD)
        if base_currency is None and cash_values:
            cv = cash_values[0]
            base_currency = cv.currency
            total_cash = float(cv.value)
        
        # Get net liquidation
        net_liq_values = [v for v in account_values if v.tag == 'NetLiquidation']
        net_liquidation = 0.0
        for nv in net_liq_values:
            if nv.currency == base_currency or nv.currency == 'BASE':
                net_liquidation = float(nv.value)
                break
        
        # Get positions
        positions = ib.positions()
        
        print(f"=== IBKR ACCOUNT STATUS ===")
        print(f"Currency: {base_currency}")
        print(f"Cash: {total_cash:,.2f}")
        print(f"Net Liquidation: {net_liquidation:,.2f}")
        print(f"Positions: {len(positions)}\n")
        
        # Build portfolio.json structure
        portfolio = {
            "cash": total_cash,
            "positions": {},
            "total_value": net_liquidation,
            "last_updated": str(datetime.now().timestamp()),
            "account": "DUP663578",
            "high_water_mark": max(net_liquidation, 100000.0),
            "trade_history": []
        }
        
        # Add positions from IBKR
        for pos in positions:
            if pos.position > 0:  # Only long positions
                symbol = pos.contract.symbol
                shares = int(pos.position)
                avg_cost = float(pos.avgCost)
                
                # Get current market price
                ib.qualifyContracts(pos.contract)
                ticker = ib.reqTickers(pos.contract)[0]
                util.sleep(0.5)
                
                current_price = ticker.marketPrice()
                if current_price != current_price:  # NaN check
                    current_price = avg_cost
                
                value = shares * current_price
                unrealized_pnl = value - (shares * avg_cost)
                
                # Calculate stop loss (8% hard stop as default)
                stop_loss = avg_cost * 0.92
                
                portfolio["positions"][symbol] = {
                    "shares": shares,
                    "entry_price": avg_cost,
                    "current_price": current_price,
                    "value": value,
                    "unrealized_pnl": unrealized_pnl,
                    "stop_loss": stop_loss,
                    "highest_price": current_price
                }
                
                print(f"  {symbol}: {shares} shares @ ${avg_cost:.2f} | Current: ${current_price:.2f} | P&L: ${unrealized_pnl:.2f}")
        
        # Load existing trade history if it exists
        portfolio_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'data', 'portfolio.json')
        if os.path.exists(portfolio_path):
            try:
                with open(portfolio_path, 'r') as f:
                    old_portfolio = json.load(f)
                    if 'trade_history' in old_portfolio:
                        portfolio['trade_history'] = old_portfolio['trade_history']
                        print(f"\n✅ Preserved {len(portfolio['trade_history'])} trade history entries")
            except Exception as e:
                print(f"⚠️ Could not load old trade history: {e}")
        
        # Save portfolio.json
        with open(portfolio_path, 'w') as f:
            json.dump(portfolio, f, indent=2)
        
        print(f"\n✅ portfolio.json synced with IBKR")
        print(f"   Cash: ${total_cash:,.2f}")
        print(f"   Equity: ${net_liquidation:,.2f}")
        print(f"   Positions: {len(portfolio['positions'])}")
        
        ib.disconnect()
        return portfolio
        
    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        if ib.isConnected():
            ib.disconnect()
        return None

if __name__ == "__main__":
    sync_portfolio_with_ibkr()
