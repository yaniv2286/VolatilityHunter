"""
Force Market Data Update
Resolves stale data issue by forcing fresh download for portfolio tickers
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
from src.data_loader import fetch_tiingo_data
from src.storage import DataStorage

def inspect_data(ticker, title):
    """Inspect the last 3 rows of ticker data"""
    file_path = f"data/{ticker}.parquet"
    if os.path.exists(file_path):
        df = pd.read_parquet(file_path)
        print(f"\n{title}: {ticker}")
        print("="*50)
        if len(df) >= 3:
            last_3 = df[['date', 'close']].tail(3)
            for idx, row in last_3.iterrows():
                print(f"  {row['date']}: ${row['close']:.2f}")
        else:
            print(f"  Only {len(df)} rows available:")
            for idx, row in df.iterrows():
                print(f"  {row['date']}: ${row['close']:.2f}")
        print("="*50)
    else:
        print(f"\n{title}: {ticker} - FILE NOT FOUND at {file_path}")

def main():
    """Force update market data for portfolio tickers"""
    print("="*60)
    print("VolatilityHunter - Force Market Data Update")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Step 1: Initialize Components
        print("\n[STEP 1] Initializing Components...")
        config = get_config()
        loader = get_data_loader()
        storage = DataStorage()
        print(f"  - Data Loader: {type(loader).__name__}")
        print(f"  - Data Source: {config.config.data_source}")
        
        # Step 2: Inspect Before Update
        print("\n[STEP 2] Inspecting Data Before Update...")
        portfolio_tickers = ['LITE', 'PTCT', 'RCL', 'AAOI', 'HALO', 'FLG', 'WFC', 'LIND', 'TT', 'BFH']
        inspect_data('LITE', "BEFORE UPDATE")
        
        # Step 3: Force Download
        print("\n[STEP 3] Forcing Data Download...")
        updated_count = 0
        
        # Import Tiingo config
        from src.config import TIINGO_KEY, TIINGO_BASE_URL
        import requests
        
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Token {TIINGO_KEY}'
        }
        
        for ticker in portfolio_tickers:
            print(f"\n  Processing {ticker}...")
            try:
                # Use individual ticker endpoint
                url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
                params = {
                    'startDate': '2026-02-01',
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
                    
                    print(f"    ✅ Downloaded {len(df)} rows")
                    
                    # Force save to parquet directly
                    parquet_path = f"data/{ticker.lower()}.parquet"
                    df.to_parquet(parquet_path, index=False)
                    print(f"    ✅ Saved to {parquet_path}")
                    updated_count += 1
                    
                    # Show latest dates
                    latest_dates = df['date'].tail(3).tolist()
                    print(f"    📅 Latest dates: {latest_dates}")
                else:
                    print(f"    ❌ No data received")
                    
            except Exception as e:
                print(f"    ❌ Error: {e}")
        
        print(f"\n  ✅ Updated {updated_count}/{len(portfolio_tickers)} tickers")
        
        # Step 4: Inspect After Update
        print("\n[STEP 4] Inspecting Data After Update...")
        inspect_data('LITE', "AFTER UPDATE")
        
        # Step 5: Summary
        print("\n[STEP 5] Summary")
        print("="*60)
        print(f"[OK] Force update completed!")
        print(f"[UPDATED] {updated_count}/{len(portfolio_tickers)} tickers")
        print(f"[TIME] Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print("="*60)
        
        # Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] Force update failed: {e}")
        print("="*60)
        sys.exit(1)

if __name__ == '__main__':
    main()
