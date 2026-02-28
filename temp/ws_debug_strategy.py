#!/usr/bin/env python3
"""
Debug the strategy function to understand its output format
"""

import sys
import os
import pandas as pd

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))

from src.strategy_v7_2 import analyze_stock_v7_2
from src.storage import DataStorage

def debug_strategy():
    """Debug the strategy function"""
    print("🔍 DEBUGGING STRATEGY FUNCTION")
    print("=" * 50)
    
    storage = DataStorage()
    
    # Test with AAPL
    ticker = "AAPL"
    print(f"📊 Testing with {ticker}...")
    
    # Load data
    data = storage.load_data(ticker)
    if data is None:
        print(f"❌ No data for {ticker}")
        return
    
    print(f"✅ Loaded {len(data)} days of data for {ticker}")
    print(f"📋 Data columns: {list(data.columns)}")
    print(f"📋 Data shape: {data.shape}")
    
    # Run strategy analysis
    print(f"\n🔄 Running strategy analysis...")
    try:
        result = analyze_stock_v7_2(data, ticker)
        print(f"✅ Strategy analysis completed")
        print(f"📋 Result type: {type(result)}")
        
        if result:
            print(f"📋 Result keys: {list(result.keys())}")
            
            # Check for signals
            if 'signal' in result:
                signal = result['signal']
                print(f"📊 Signal: {signal}")
                print(f"📋 Signal type: {type(signal)}")
                print(f"📋 Signal keys: {list(signal.keys()) if isinstance(signal, dict) else 'Not a dict'}")
            else:
                print("❌ No 'signal' key in result")
            
            # Check reason
            if 'reason' in result:
                reason = result['reason']
                print(f"📊 Reason: {reason}")
            
            # Check indicators
            if 'indicators' in result:
                indicators = result['indicators']
                print(f"📊 Indicators type: {type(indicators)}")
                if isinstance(indicators, dict):
                    print(f"📋 Indicators keys: {list(indicators.keys())}")
                elif isinstance(indicators, pd.DataFrame):
                    print(f"📋 Indicators DataFrame shape: {indicators.shape}")
                    print(f"📋 Indicators columns: {list(indicators.columns)}")
            else:
                print("❌ No 'indicators' key in result")
        else:
            print("❌ Strategy analysis returned None")
            
    except Exception as e:
        print(f"❌ Error in strategy analysis: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_strategy()
