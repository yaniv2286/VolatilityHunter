#!/usr/bin/env python3
"""
Debug Portfolio Data - Investigate why Feb 10 data isn't being saved
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
from src.notifications import log_info

def debug_portfolio_data():
    """Debug portfolio data issues by comparing local vs API data"""
    
    # Define portfolio tickers
    portfolio_tickers = ['MNKD', 'SCHW', 'AEP', 'LNC', 'GAP', 'UMBF', 'SIMO', 'OPLN', 'ONB', 'HASI']
    
    print("="*80)
    print("DEBUG PORTFOLIO DATA - Local vs API Comparison")
    print("="*80)
    
    # Initialize data loader
    loader = get_data_loader()
    print(f"📊 Data Loader: {type(loader).__name__}")
    print(f"📊 Data Source: Tiingo")
    print()
    
    for ticker in portfolio_tickers:
        print(f"🔍 Debugging {ticker}:")
        print("-" * 40)
        
        # 1. Check local parquet file
        local_file = f"data/{ticker.lower()}.parquet"
        local_latest_date = None
        local_latest_price = None
        
        if os.path.exists(local_file):
            try:
                df_local = pd.read_parquet(local_file)
                if not df_local.empty:
                    # Convert date column to datetime if it's not already
                    if 'date' in df_local.columns:
                        df_local['date'] = pd.to_datetime(df_local['date'])
                        local_latest_date = df_local['date'].max().strftime('%Y-%m-%d')
                        local_latest_price = df_local.loc[df_local['date'].idxmax(), 'close']
                    
                    print(f"[LOCAL] {ticker} Latest Date: {local_latest_date} | Price: ${local_latest_price:.2f}")
                else:
                    print(f"[LOCAL] {ticker} File exists but is EMPTY")
            except Exception as e:
                print(f"[LOCAL] {ticker} ERROR reading file: {e}")
        else:
            print(f"[LOCAL] {ticker} File NOT found: {local_file}")
        
        # 2. Force fetch from API
        try:
            print(f"[API]   Fetching {ticker} from 2026-02-05...")
            
            # Use the correct API access method for Tiingo
            from src.data_loader import fetch_tiingo_data
            api_data = fetch_tiingo_data([ticker], start_date='2026-02-05')
            
            if ticker in api_data and not api_data[ticker].empty:
                df_api = api_data[ticker]
                api_latest_date = df_api['date'].max().strftime('%Y-%m-%d')
                api_latest_price = df_api.loc[df_api['date'].idxmax(), 'close']
                
                print(f"[API]   Returned {len(df_api)} rows. Last Date: {api_latest_date} | Price: ${api_latest_price:.2f}")
                
                # 3. Compare & Save
                if local_latest_date is None:
                    print(f"[ACTION] No local data found - SAVING!")
                    loader.storage.save_data(ticker, df_api)
                elif api_latest_date > local_latest_date:
                    print(f"[ACTION] API data newer - UPDATING!")
                    loader.storage.save_data(ticker, df_api)
                elif api_latest_date == local_latest_date:
                    print(f"[ACTION] Data current - NO UPDATE NEEDED")
                else:
                    print(f"[ACTION] API data older - SKIPPING")
                    
            else:
                print(f"[API]   No data returned for {ticker}")
                
        except Exception as e:
            print(f"[API]   ERROR fetching {ticker}: {e}")
        
        print()
    
    print("="*80)
    print("DEBUG COMPLETE")
    print("="*80)

if __name__ == "__main__":
    debug_portfolio_data()
