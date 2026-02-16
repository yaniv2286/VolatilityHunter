#!/usr/bin/env python3
"""
Fill Data Gaps Script
Downloads missing tickers using TiingoDataLoader and converts to Parquet format
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.data_loader import fetch_tiingo_data
from src.storage import DataStorage
from src.notifications import log_info, log_error, log_warning

def load_ticker_list():
    """Load tickers from tickers.txt"""
    ticker_file = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'tickers.txt')
    
    if not os.path.exists(ticker_file):
        log_error(f"tickers.txt not found at {ticker_file}")
        return []
    
    with open(ticker_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    
    log_info(f"Loaded {len(tickers)} tickers from tickers.txt")
    return tickers

def get_existing_parquet_tickers():
    """Get list of tickers that already have parquet files"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    parquet_files = glob.glob(os.path.join(data_dir, '*.parquet'))
    
    existing_tickers = []
    for file_path in parquet_files:
        ticker = os.path.basename(file_path).replace('.parquet', '').upper()
        existing_tickers.append(ticker)
    
    log_info(f"Found {len(existing_tickers)} existing parquet files")
    return existing_tickers

def convert_to_parquet_format(df, ticker):
    """Convert DataFrame to match expected parquet format"""
    if df.empty:
        return None
    
    # Ensure required columns exist
    required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
    
    # Map Tiingo columns to standard format
    column_mapping = {
        'adjClose': 'close',  # Use adjusted close as close price
        'adj_close': 'close',
        'Open': 'open',
        'High': 'high', 
        'Low': 'low',
        'Close': 'close',
        'Volume': 'volume'
    }
    
    # Rename columns
    df = df.rename(columns=column_mapping)
    
    # Ensure date column
    if 'date' not in df.columns:
        log_error(f"No date column found for {ticker}")
        return None
    
    # Convert date to datetime
    df['date'] = pd.to_datetime(df['date'])
    
    # Filter to required columns only
    available_columns = [col for col in required_columns if col in df.columns]
    df = df[available_columns].copy()
    
    # Sort by date
    df = df.sort_values('date').reset_index(drop=True)
    
    return df

def save_to_parquet(df, ticker):
    """Save DataFrame to parquet format"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    os.makedirs(data_dir, exist_ok=True)
    
    parquet_path = os.path.join(data_dir, f"{ticker.lower()}.parquet")
    
    try:
        df.to_parquet(parquet_path, index=False)
        log_info(f"Saved {ticker} to parquet format: {parquet_path}")
        return True
    except Exception as e:
        log_error(f"Error saving {ticker} to parquet: {e}")
        return False

def download_missing_tickers():
    """Download tickers that are missing from parquet format"""
    log_info("="*80)
    log_info("FILL DATA GAPS: Downloading Missing Tickers")
    log_info("="*80)
    
    # Load ticker list
    all_tickers = load_ticker_list()
    if not all_tickers:
        log_error("No tickers loaded from tickers.txt")
        return False
    
    # Get existing parquet tickers
    existing_tickers = get_existing_parquet_tickers()
    
    # Find missing tickers
    missing_tickers = [ticker for ticker in all_tickers if ticker.upper() not in existing_tickers]
    
    log_info(f"Total tickers in tickers.txt: {len(all_tickers)}")
    log_info(f"Existing parquet files: {len(existing_tickers)}")
    log_info(f"Missing tickers: {len(missing_tickers)}")
    
    if len(missing_tickers) == 0:
        log_info("✅ All tickers already have parquet files!")
        return True
    
    # Download missing tickers
    success_count = 0
    failure_count = 0
    
    # Download in batches to avoid rate limits
    batch_size = 10
    
    for i in range(0, len(missing_tickers), batch_size):
        batch = missing_tickers[i:i+batch_size]
        log_info(f"Processing batch {i//batch_size + 1}/{(len(missing_tickers) + batch_size - 1)//batch_size}")
        
        for ticker in batch:
            try:
                log_info(f"Downloading {ticker}...")
                
                # Download data from Tiingo (full history)
                data_dict = fetch_tiingo_data([ticker])
                
                if ticker in data_dict:
                    df = data_dict[ticker]
                    
                    # Convert to parquet format
                    parquet_df = convert_to_parquet_format(df, ticker)
                    
                    if parquet_df is not None:
                        # Save to parquet
                        if save_to_parquet(parquet_df, ticker):
                            success_count += 1
                        else:
                            failure_count += 1
                    else:
                        log_error(f"Failed to convert {ticker} to parquet format")
                        failure_count += 1
                else:
                    log_error(f"No data returned for {ticker}")
                    failure_count += 1
                    
            except Exception as e:
                log_error(f"Error processing {ticker}: {e}")
                failure_count += 1
        
        # Rate limit pause between batches
        if i + batch_size < len(missing_tickers):
            log_info("Pausing for rate limit...")
            time.sleep(2)
    
    log_info("="*80)
    log_info(f"DOWNLOAD SUMMARY:")
    log_info(f"  ✅ Success: {success_count}")
    log_info(f"  ❌ Failed: {failure_count}")
    log_info(f"  📊 Success Rate: {success_count/(success_count+failure_count)*100:.1f}%")
    log_info("="*80)
    
    return failure_count == 0

if __name__ == "__main__":
    import glob
    import time
    
    success = download_missing_tickers()
    sys.exit(0 if success else 1)
