"""
Smart Update Stock Universe with Data Preservation
Implements intelligent append logic to prevent data destruction
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from tqdm import tqdm

# FORCE WORKING DIRECTORY TO SCRIPT LOCATION
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)
print(f"📍 Working Directory set to: {os.getcwd()}")

from src.config_manager import get_config
from src.data_loader_factory import get_data_loader
from src.storage import DataStorage

def get_smart_start_date(ticker, force_full_refresh=False):
    """
    Determine the optimal start date for downloading data to avoid duplicates
    and preserve existing historical data.
    """
    if force_full_refresh:
        return '2000-01-01'  # Full historical download
    
    parquet_path = f"data/{ticker.lower()}.parquet"
    
    if os.path.exists(parquet_path):
        try:
            # Load existing data
            existing_df = pd.read_parquet(parquet_path)
            if not existing_df.empty and 'date' in existing_df.columns:
                existing_df['date'] = pd.to_datetime(existing_df['date'])
                max_date = existing_df['date'].max()
                
                # Start from 1 day before max date to ensure overlap safety
                start_date = (max_date - timedelta(days=1)).strftime('%Y-%m-%d')
                print(f"    📅 {ticker}: Existing data found, max date {max_date.strftime('%Y-%m-%d')}, starting from {start_date}")
                return start_date
        except Exception as e:
            print(f"    ⚠️  {ticker}: Error reading existing data: {e}, using full refresh")
            return '2000-01-01'
    
    # No existing data, get full history
    return '2000-01-01'

def smart_update_ticker(ticker, headers, force_full_refresh=False):
    """
    Smart update for a single ticker with data preservation
    """
    try:
        # Determine optimal start date
        start_date = get_smart_start_date(ticker, force_full_refresh)
        end_date = datetime.now().strftime('%Y-%m-%d')
        
        # Download data from Tiingo
        url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'resampleFreq': 'daily'
        }
        
        import requests
        response = requests.get(url, headers=headers, params=params, timeout=30)
        response.raise_for_status()
        data = response.json()
        
        if not data:
            return {'success': False, 'reason': 'No data received'}
        
        # Process new data
        new_df = pd.DataFrame(data)
        new_df['date'] = pd.to_datetime(new_df['date'])
        
        # V7.3 SANITIZATION: Price ceiling filter to reject split-adjustment ghosts
        if 'adjClose' in new_df.columns:
            max_price = new_df['adjClose'].max()
            if max_price > 500:
                return {'success': False, 'reason': f'Price ceiling violation: ${max_price:.2f} > $500 (split-adjustment ghost)'}
        
        # Standardize column names to match existing parquet format
        new_df = new_df.rename(columns={
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
        
        # Handle existing data merge
        parquet_path = f"data/{ticker.lower()}.parquet"
        if os.path.exists(parquet_path) and not force_full_refresh:
            try:
                existing_df = pd.read_parquet(parquet_path)
                if not existing_df.empty:
                    existing_df['date'] = pd.to_datetime(existing_df['date'])
                    
                    # Concatenate and deduplicate
                    combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                    combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                    combined_df = combined_df.sort_values('date').reset_index(drop=True)
                    
                    # Save combined data
                    combined_df.to_parquet(parquet_path, index=False)
                    
                    return {
                        'success': True,
                        'total_rows': len(combined_df),
                        'new_rows': len(new_df),
                        'date_range': f"{combined_df['date'].min().strftime('%Y-%m-%d')} to {combined_df['date'].max().strftime('%Y-%m-%d')}"
                    }
            except Exception as e:
                print(f"    ⚠️  {ticker}: Error merging data: {e}, saving new data only")
        
        # No existing data or force refresh - save new data directly
        new_df = new_df.sort_values('date').reset_index(drop=True)
        new_df.to_parquet(parquet_path, index=False)
        
        return {
            'success': True,
            'total_rows': len(new_df),
            'new_rows': len(new_df),
            'date_range': f"{new_df['date'].min().strftime('%Y-%m-%d')} to {new_df['date'].max().strftime('%Y-%m-%d')}"
        }
        
    except Exception as e:
        return {'success': False, 'reason': str(e)}

def purge_corrupted_data():
    """
    Purge all existing parquet files before The Great Redownload
    """
    data_dir = "data"
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
        return
    
    parquet_files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    purged_count = 0
    
    print(f"🔥 PURGING CORRUPTED DATA: {len(parquet_files)} parquet files found")
    
    for file in parquet_files:
        file_path = os.path.join(data_dir, file)
        try:
            os.remove(file_path)
            purged_count += 1
        except Exception as e:
            print(f"    ❌ Failed to delete {file}: {e}")
    
    print(f"✅ PURGED {purged_count} corrupted parquet files")
    return purged_count

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
    """Smart update market data for entire stock universe with data preservation"""
    print("="*80)
    print("VolatilityHunter - Smart Update Stock Universe")
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
        
        # Step 3: Check if this is The Great Redownload
        force_full_refresh = '--purge' in sys.argv
        if force_full_refresh:
            print("\n[STEP 3] THE GREAT REDOWNLOAD - Purging corrupted data...")
            purge_corrupted_data()
        
        # Step 4: Smart Mass Update
        print(f"\n[STEP 4] Smart Updating {total_tickers} Tickers...")
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
        total_rows_downloaded = 0
        
        # Progress bar with tqdm
        with tqdm(tickers, desc="📊 Downloading", unit="ticker", ncols=100) as pbar:
            for ticker in pbar:
                pbar.set_postfix_str(f"Updated: {updated_count}, Errors: {error_count}")
                
                result = smart_update_ticker(ticker, headers, force_full_refresh)
                
                if result['success']:
                    updated_count += 1
                    total_rows_downloaded += result['total_rows']
                    
                    # Show detailed info for first few tickers
                    if updated_count <= 5:
                        pbar.write(f"    ✅ {ticker}: {result['total_rows']} rows ({result['date_range']})")
                else:
                    error_count += 1
                    if error_count <= 10:  # Show first 10 errors only
                        pbar.write(f"    ❌ {ticker}: {result['reason'][:50]}...")
        
        # Step 5: Summary
        print("\n[STEP 5] Summary")
        print("="*80)
        print(f"[OK] Smart universe update completed!")
        print(f"[UPDATED] {updated_count}/{total_tickers} tickers")
        print(f"[ERRORS] {error_count}/{total_tickers} tickers")
        print(f"[SUCCESS RATE] {(updated_count/total_tickers)*100:.1f}%")
        print(f"[TOTAL ROWS] {total_rows_downloaded:,} rows downloaded")
        print(f"[TIME] Completed: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
        if force_full_refresh:
            print(f"[🔥] THE GREAT REDOWNLOAD COMPLETED!")
        
        print("="*80)
        
        # Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] Smart universe update failed: {e}")
        print("="*80)
        sys.exit(1)

if __name__ == '__main__':
    main()
