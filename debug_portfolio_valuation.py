#!/usr/bin/env python3
"""
Debug Portfolio Valuation - Identify why current prices aren't being used
"""

import os
import sys
import pandas as pd
from datetime import datetime

# Set working directory
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

# Import VolatilityHunter components
from src.data_loader_factory import get_data_loader
from src.execution import get_executor

def debug_portfolio_valuation():
    """Debug why portfolio valuation uses entry prices instead of current prices"""
    
    print("="*80)
    print("DEBUG PORTFOLIO VALUATION")
    print("="*80)
    
    # Get executor
    executor = get_executor()
    print(f"📊 Executor: {type(executor).__name__}")
    print(f"💰 Cash: ${executor.state['cash']:,.2f}")
    print(f"📈 Positions: {len(executor.state['positions'])}")
    print()
    
    # Get current market prices for portfolio positions
    data_loader = get_data_loader()
    current_prices = {}
    
    print("🔍 Loading Current Market Prices:")
    print("-" * 40)
    
    for ticker in executor.state['positions'].keys():
        try:
            # Load current data from parquet file
            df = pd.read_parquet(f"data/{ticker.lower()}.parquet")
            if not df.empty:
                latest_price = df.iloc[-1]['close']
                latest_date = df.iloc[-1]['date']
                current_prices[ticker] = latest_price
                print(f"[PRICE] {ticker}: ${latest_price:.2f} (Date: {latest_date})")
            else:
                print(f"[PRICE] {ticker}: No data available")
        except Exception as e:
            print(f"[PRICE] {ticker}: ERROR - {e}")
    
    print()
    
    # Test portfolio summary WITHOUT current prices (current behavior)
    print("🔍 Portfolio Summary WITHOUT Current Prices (Current Behavior):")
    print("-" * 40)
    summary_old = executor.get_portfolio_summary()
    print(f"Total Value: ${summary_old['total_value']:,.2f}")
    print(f"Positions Value: ${summary_old['positions_value']:,.2f}")
    print(f"Total Return: ${summary_old['total_return_dollars']:,.2f}")
    
    # Show individual positions
    for pos in summary_old['positions_detail'][:3]:  # Show first 3
        print(f"  {pos['ticker']}: ${pos['current_price']:.2f} (Entry: ${pos['entry_price']:.2f})")
    
    print()
    
    # Test portfolio summary WITH current prices (fixed behavior)
    print("🔍 Portfolio Summary WITH Current Prices (Fixed Behavior):")
    print("-" * 40)
    summary_new = executor.get_portfolio_summary(current_prices)
    print(f"Total Value: ${summary_new['total_value']:,.2f}")
    print(f"Positions Value: ${summary_new['positions_value']:,.2f}")
    print(f"Total Return: ${summary_new['total_return_dollars']:,.2f}")
    
    # Show individual positions
    for pos in summary_new['positions_detail'][:3]:  # Show first 3
        print(f"  {pos['ticker']}: ${pos['current_price']:.2f} (Entry: ${pos['entry_price']:.2f})")
    
    print()
    
    # Calculate the difference
    value_diff = summary_new['total_value'] - summary_old['total_value']
    return_diff = summary_new['total_return_dollars'] - summary_old['total_return_dollars']
    
    print("🔍 IMPACT ANALYSIS:")
    print("-" * 40)
    print(f"Value Difference: ${value_diff:,.2f}")
    print(f"Return Difference: ${return_diff:,.2f}")
    print(f"Current Prices Available: {len(current_prices)} tickers")
    
    print()
    print("="*80)
    print("DEBUG COMPLETE")
    print("="*80)

if __name__ == "__main__":
    debug_portfolio_valuation()
