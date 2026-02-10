"""
Force Update Entire Stock Universe
Resolves stale data issue by forcing fresh download for all tickers in the universe
"""

import os
import sys
import pandas as pd
from datetime import datetime

# FORCE WORKING DIRECTORY TO SCRIPT LOCATION
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)
print(f"📍 Working Directory set to: {os.getcwd()}")

from src.config_manager import get_config
from src.data_loader_factory import get_data_loader
from src.storage import DataStorage

def load_ticker_universe():
    """Load the full list of tickers from tickers.txt"""
    ticker_file = "tickers.txt"
    
    if os.path.exists(ticker_file):
        with open(ticker_file, 'r') as f:
            tickers = [line.strip() for line in f if line.strip()]
        print(f"📋 Loaded {len(tickers)} tickers from {ticker_file}")
        return tickers
    else:
        print(f"❌ Ticker file not found: {ticker_file}")
        # Fallback to manual list
        fallback_tickers = [
            'NVDA', 'PLTR', 'SHOP', 'ZS', 'SPOT', 'CRWD', 'DECK', 
            'META', 'AVGO', 'LRCX', 'CSCO', 'MU', 'AMZN', 'MELI', 'TSLA', 
            'GOOGL', 'MSFT', 'AAPL', 'NFLX', 'AMD', 'INTC', 'PYPL', 'DIS',
            'BA', 'CAT', 'JPM', 'WMT', 'HD', 'UNH', 'PG', 'JNJ', 'V', 'MA'
        ]
        print(f"📋 Using fallback list of {len(fallback_tickers)} tickers")
        return fallback_tickers

def main():
    """Force update market data for entire stock universe"""
    print("="*80)
    print("VolatilityHunter - Force Update Stock Universe")
    print("="*80)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Initialize Components
        print("\n[STEP 1] Initializing Components...")
        config = get_config()
        loader = get_data_loader()
        storage = DataStorage()
        print(f"  - Data Loader: {type(loader).__name__}")
        print(f"  - Data Source: {config.config.data_source}")
        
        # Step 2: Load Ticker Universe
        print("\n[STEP 2] Loading Ticker Universe...")
        tickers = load_ticker_universe()
        total_tickers = len(tickers)
        
        # Step 3: Mass Update
        print(f"\n[STEP 3] Mass Updating {total_tickers} Tickers...")
        print("="*80)
        
        # Import Tiingo config for direct API access
        from src.config import TIINGO_KEY, TIINGO_BASE_URL
        import requests
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {TIINGO_KEY}'
        }
        
        updated_count = 0
        error_count = 0
        
        for i, ticker in enumerate(tickers, 1):
            try:
                # Progress indicator
                if i % 50 == 0 or i == total_tickers:
                    print(f"  📊 Progress: {i}/{total_tickers} ({(i/total_tickers)*100:.1f}%)")
                
                # Use individual ticker endpoint
                url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
                params = {
                    'startDate': '2026-01-25',  # 2 weeks back to bridge gap
                    'endDate': '2026-02-10',
                    'resampleFreq': 'daily'
                }
                
                response = requests.get(url, headers=headers, params=params, timeout=30)
                response.raise_for_status()
                data = response.json()
                
                if data:
                    df = pd.DataFrame(data)
                    df['date'] = pd.to_datetime(df['date'])
                    # Convert to lowercase to match existing parquet format
                    df = df.rename(columns={
                        'open': 'open',
                        'high': 'high', 
                        'low': 'low',
                        'close': 'close',
                        'volume': 'volume',
                        'adjClose': 'adjClose',
                        'adjHigh': 'adjHigh',
                        'adjLow': 'adjLow',
                        'adjOpen': 'adjOpen',
                        'adjVolume': 'adjVolume',
                        'divCash': 'divCash',
                        'splitFactor': 'splitFactor'
                    })
                    df = df.sort_values('date').reset_index(drop=True)
                    
                    # Force save to parquet directly
                    parquet_path = f"data/{ticker.lower()}.parquet"
                    df.to_parquet(parquet_path, index=False)
                    updated_count += 1
                    
                    # Show sample of latest dates for first few tickers
                    if i <= 5:
                        latest_dates = df['date'].tail(2).tolist()
                        print(f"    ✅ {ticker}: {len(df)} rows, latest: {latest_dates[-1].strftime('%Y-%m-%d')}")
                        
                else:
                    error_count += 1
                    if error_count <= 10:  # Show first 10 errors only
                        print(f"    ❌ {ticker}: No data received")
                    
            except Exception as e:
                error_count += 1
                if error_count <= 10:  # Show first 10 errors only
                    print(f"    ❌ {ticker}: {str(e)[:50]}...")
        
        # Step 4: Summary
        print("\n[STEP 4] Summary")
        print("="*80)
        print(f"[OK] Universe update completed!")
        print(f"[UPDATED] {updated_count}/{total_tickers} tickers")
        print(f"[ERRORS] {error_count}/{total_tickers} tickers")
        print(f"[SUCCESS RATE] {(updated_count/total_tickers)*100:.1f}%")
        print(f"[TIME] Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*80)
        
        # Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] Universe update failed: {e}")
        print("="*80)
        sys.exit(1)

if __name__ == '__main__':
    main()
