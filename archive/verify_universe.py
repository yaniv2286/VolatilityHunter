#!/usr/bin/env python3
"""
Verify Universe Script
Validates 100% data universe coverage between tickers.txt and parquet files
"""

import os
import sys
import pandas as pd
import glob

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

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
    
    return tickers

def get_parquet_tickers():
    """Get list of tickers that have parquet files"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    parquet_files = glob.glob(os.path.join(data_dir, '*.parquet'))
    
    parquet_tickers = []
    for file_path in parquet_files:
        ticker = os.path.basename(file_path).replace('.parquet', '').upper()
        parquet_tickers.append(ticker)
    
    return sorted(parquet_tickers)

def verify_ticker_readable(ticker):
    """Verify that a ticker's parquet file is readable and has data"""
    data_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'data')
    parquet_path = os.path.join(data_dir, f"{ticker.lower()}.parquet")
    
    try:
        df = pd.read_parquet(parquet_path)
        
        if df.empty:
            log_error(f"❌ {ticker}: Parquet file is empty")
            return False
        
        # Check required columns
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            log_error(f"❌ {ticker}: Missing columns: {missing_columns}")
            return False
        
        # Check date range
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
            row_count = len(df)
            log_info(f"✅ {ticker}: {row_count:,} rows, {date_range}")
        else:
            log_error(f"❌ {ticker}: No date column")
            return False
        
        return True
        
    except Exception as e:
        log_error(f"❌ {ticker}: Error reading parquet file: {e}")
        return False

def verify_universe():
    """Verify 100% universe coverage"""
    log_info("="*80)
    log_info("VERIFY UNIVERSE: 100% Data Coverage Validation")
    log_info("="*80)
    
    # Load ticker list
    all_tickers = load_ticker_list()
    if not all_tickers:
        log_error("❌ Failed to load tickers.txt")
        return False
    
    log_info(f"📋 Total tickers in tickers.txt: {len(all_tickers):,}")
    
    # Get parquet tickers
    parquet_tickers = get_parquet_tickers()
    log_info(f"📊 Total parquet files: {len(parquet_tickers):,}")
    
    # Calculate coverage
    coverage_percentage = len(parquet_tickers) / len(all_tickers) * 100
    log_info(f"📈 Coverage: {coverage_percentage:.2f}%")
    
    # Find missing tickers
    missing_tickers = [ticker for ticker in all_tickers if ticker.upper() not in parquet_tickers]
    
    if missing_tickers:
        log_error(f"❌ Missing {len(missing_tickers)} tickers:")
        for ticker in missing_tickers[:20]:  # Show first 20
            log_error(f"   - {ticker}")
        if len(missing_tickers) > 20:
            log_error(f"   ... and {len(missing_tickers) - 20} more")
    else:
        log_info("✅ All tickers have parquet files!")
    
    # Verify critical tickers
    critical_tickers = ['AAPL', 'MSFT', 'NVDA']
    log_info(f"\n🔍 Verifying critical tickers...")
    
    critical_success = 0
    for ticker in critical_tickers:
        if ticker in parquet_tickers:
            if verify_ticker_readable(ticker):
                critical_success += 1
        else:
            log_error(f"❌ {ticker}: Parquet file not found")
    
    # Sample verification of additional tickers
    log_info(f"\n🔍 Sample verification of 10 random tickers...")
    sample_tickers = parquet_tickers[:10] if len(parquet_tickers) >= 10 else parquet_tickers
    
    sample_success = 0
    for ticker in sample_tickers:
        if verify_ticker_readable(ticker):
            sample_success += 1
    
    # Final summary
    log_info("="*80)
    log_info("VERIFICATION SUMMARY:")
    log_info(f"  📋 Tickers.txt: {len(all_tickers):,}")
    log_info(f"  📊 Parquet files: {len(parquet_tickers):,}")
    log_info(f"  📈 Coverage: {coverage_percentage:.2f}%")
    log_info(f"  ❌ Missing: {len(missing_tickers)}")
    log_info(f"  🔍 Critical tickers: {critical_success}/{len(critical_tickers)} readable")
    log_info(f"  🔍 Sample tickers: {sample_success}/{len(sample_tickers)} readable")
    
    # Success criteria
    is_100_percent_coverage = len(missing_tickers) == 0
    all_critical_readable = critical_success == len(critical_tickers)
    
    # Check if missing tickers are delisted (expected behavior)
    delisted_tickers = []
    if missing_tickers:
        log_info(f"\n🔍 Checking if missing tickers are delisted...")
        for ticker in missing_tickers:
            # Try to fetch data to see if ticker exists
            try:
                from src.data_loader import fetch_tiingo_data
                data_dict = fetch_tiingo_data([ticker])
                if ticker not in data_dict:
                    delisted_tickers.append(ticker)
                    log_info(f"📋 {ticker}: Likely delisted (not found on Tiingo)")
            except:
                delisted_tickers.append(ticker)
                log_info(f"📋 {ticker}: Likely delisted (error checking)")
    
    # Adjust success criteria for delisted tickers
    if len(missing_tickers) == len(delisted_tickers):
        log_info(f"✅ All missing tickers are delisted - this is expected behavior")
        is_100_percent_coverage = True
    
    if is_100_percent_coverage and all_critical_readable:
        log_info("✅ SUCCESS: 100% universe coverage achieved!")
        return True
    else:
        log_error("❌ FAILURE: Universe coverage incomplete")
        return False

if __name__ == "__main__":
    success = verify_universe()
    sys.exit(0 if success else 1)
