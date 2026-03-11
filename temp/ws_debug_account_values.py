"""
Debug script to see what account values IBKR is returning
"""
import os
import sys
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from ib_insync import IB

def debug_account_values():
    """Debug what account values IBKR returns"""
    print("Connecting to IBKR...")
    
    ib = IB()
    ib.connect('127.0.0.1', 7497, clientId=999)
    
    print("✅ Connected")
    print("\nAll Account Values:")
    print("=" * 80)
    
    account_values = ib.accountValues()
    
    # Group by tag
    values_by_tag = {}
    for value in account_values:
        tag = value.tag
        if tag not in values_by_tag:
            values_by_tag[tag] = []
        values_by_tag[tag].append(value)
    
    # Print relevant tags
    relevant_tags = [
        'AvailableFunds',
        'CashBalance', 
        'TotalCashValue',
        'NetLiquidation',
        'GrossPositionValue',
        'BuyingPower'
    ]
    
    for tag in relevant_tags:
        if tag in values_by_tag:
            print(f"\n{tag}:")
            for value in values_by_tag[tag]:
                print(f"  {value.currency}: {value.value}")
    
    print("\n" + "=" * 80)
    print("All tags (first 20):")
    for i, tag in enumerate(sorted(values_by_tag.keys())[:20]):
        print(f"  {tag}")
    
    ib.disconnect()

if __name__ == "__main__":
    debug_account_values()
