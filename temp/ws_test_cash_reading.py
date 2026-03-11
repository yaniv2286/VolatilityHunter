"""
Test script to verify IBKR cash reading fix
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from src.brokerage_interface import get_brokerage_interface
from dotenv import load_dotenv

def test_cash_reading():
    """Test if we can read cash from IBKR correctly"""
    print("Testing IBKR cash reading...")
    print("=" * 60)
    
    # Load environment variables
    load_dotenv(ROOT / '.env')
    
    # Get IBKR interface
    config = {'BROKERAGE_TYPE': 'ibkr'}
    ibkr = get_brokerage_interface(config)
    
    if not ibkr:
        print("❌ Failed to get IBKR interface")
        return False
    
    # Connect
    print("Connecting to IBKR...")
    if not ibkr.connect():
        print("❌ Failed to connect to IBKR")
        return False
    
    print("✅ Connected to IBKR")
    
    # Get account info
    print("\nGetting account info...")
    account = ibkr.get_account_info()
    
    if not account:
        print("❌ Failed to get account info")
        return False
    
    print("✅ Account info retrieved:")
    print(f"   Cash: ${account.get('cash', 0):,.2f}")
    print(f"   Equity: ${account.get('equity', 0):,.2f}")
    print(f"   Portfolio Value: ${account.get('portfolio_value', 0):,.2f}")
    print(f"   Buying Power: ${account.get('buying_power', 0):,.2f}")
    
    # Get positions
    print("\nGetting positions...")
    positions = ibkr.get_positions()
    
    if positions is None:
        print("❌ Failed to get positions")
        return False
    
    print(f"✅ Positions retrieved: {len(positions)} positions")
    
    total_market_value = 0
    for pos in positions:
        print(f"   {pos['symbol']}: {pos['quantity']} shares @ ${pos['current_price']:.2f} = ${pos['market_value']:,.2f}")
        total_market_value += pos['market_value']
    
    print(f"\nTotal Market Value: ${total_market_value:,.2f}")
    
    # Disconnect
    ibkr.disconnect()
    
    # Verify cash is not zero
    if account.get('cash', 0) == 0 and account.get('equity', 0) == 0:
        print("\n❌ WARNING: Cash and equity are both $0.00")
        print("   This might indicate the account info is not being read correctly")
        return False
    
    print("\n✅ SUCCESS: Cash reading is working!")
    return True

if __name__ == "__main__":
    success = test_cash_reading()
    sys.exit(0 if success else 1)
