#!/usr/bin/env python3
"""
Flush all parquet files with fresh OHLCV data using the surgical strike data loader.
This replaces the old poisoned data (high=price, low=price) with real OHLCV.
"""

import os
import sys
from pathlib import Path

# Add src to path for imports
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from src.smart_data_loader_factory import get_data_loader

def main():
    print("=" * 60)
    print("VOLATILITYHUNTER PARQUET POISON FLUSH")
    print("Replacing stale data with fresh OHLCV from Tiingo")
    print("=" * 60)
    
    # Load all tickers
    tickers_file = ROOT / 'tickers.txt'
    if not tickers_file.exists():
        print(f"ERROR: {tickers_file} not found")
        return 1
    
    with open(tickers_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(tickers)} tickers from tickers.txt")
    
    # Get data loader
    loader = get_data_loader()
    
    # Process in batches of 100 to avoid API limits
    batch_size = 100
    total_updated = 0
    total_failed = 0
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i:i + batch_size]
        batch_num = (i // batch_size) + 1
        total_batches = (len(tickers) + batch_size - 1) // batch_size
        
        print(f"\nProcessing batch {batch_num}/{total_batches} ({len(batch)} tickers)...")
        
        result = loader.update_all_stocks(batch)
        
        if result['success']:
            batch_updated = result['updated']
            batch_failed = len(batch) - batch_updated
            total_updated += batch_updated
            total_failed += batch_failed
            
            print(f"  ✅ Batch {batch_num}: {batch_updated} updated, {batch_failed} failed")
            
            # Show sample of updated data if available
            ohlcv = result.get('ohlcv', {})
            if ohlcv and batch_num == 1:  # Only show first batch sample
                print(f"\nSample OHLCV data from batch {batch_num}:")
                for j, (ticker, data) in enumerate(list(ohlcv.items())[:3]):
                    print(f"  {ticker}: O=${data['open']:.2f} H=${data['high']:.2f} L=${data['low']:.2f} C=${data['close']:.2f} V={data['volume']:,}")
        else:
            print(f"  ❌ Batch {batch_num} failed: {result.get('error', 'Unknown error')}")
            total_failed += len(batch)
    
    print("\n" + "=" * 60)
    print("PARQUET POISON FLUSH COMPLETE")
    print(f"✅ Total updated: {total_updated}/{len(tickers)} tickers")
    print(f"❌ Total failed: {total_failed}/{len(tickers)} tickers")
    
    if total_updated > 0:
        print("✅ Fresh OHLCV data now in parquet files")
        print("✅ No more high=price, low=price poison")
        print("✅ Ready for clean foundation backtest")
    else:
        print("❌ No files updated - check API connection")
    
    print("=" * 60)
    
    return 0 if total_updated > 0 else 1

if __name__ == '__main__':
    sys.exit(main())
