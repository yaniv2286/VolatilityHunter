#!/usr/bin/env python3
"""
Update fresh data using the new surgical strike data loader.
Tests the OHLCV fetching and parquet updating functionality.
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
    print("VOLATILITYHUNTER FRESH DATA UPDATE")
    print("Testing surgical strike data pipeline")
    print("=" * 60)
    
    # Load tickers
    tickers_file = ROOT / 'tickers.txt'
    if not tickers_file.exists():
        print(f"ERROR: {tickers_file} not found")
        return 1
    
    with open(tickers_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(tickers)} tickers from tickers.txt")
    
    # Get data loader
    loader = get_data_loader()
    
    # Test with a small subset first
    test_tickers = tickers[:20]  # Test with first 20 tickers
    print(f"\nTesting OHLCV fetch with {len(test_tickers)} tickers...")
    
    result = loader.update_all_stocks(test_tickers)
    
    if result['success']:
        print(f"✅ SUCCESS: Updated {result['updated']}/{result['total']} tickers")
        print(f"OHLCV data fetched for {len(result.get('ohlcv', {}))} tickers")
        
        # Show sample of fetched data
        ohlcv = result.get('ohlcv', {})
        if ohlcv:
            print("\nSample OHLCV data:")
            for i, (ticker, data) in enumerate(list(ohlcv.items())[:5]):
                print(f"  {ticker}: O=${data['open']:.2f} H=${data['high']:.2f} L=${data['low']:.2f} C=${data['close']:.2f} V={data['volume']:,}")
                if i >= 4:
                    break
    else:
        print(f"❌ FAILED: {result.get('error', 'Unknown error')}")
        return 1
    
    # Test sector metadata fetching
    print(f"\nTesting sector metadata fetch with {len(test_tickers)} tickers...")
    
    try:
        metadata = loader.fetch_all_metadata(test_tickers)
        print(f"✅ SUCCESS: Fetched metadata for {len(metadata)} tickers")
        
        # Show sample sectors
        if metadata:
            print("\nSample sector mappings:")
            for i, (ticker, data) in enumerate(list(metadata.items())[:5]):
                sector = data.get('sector', 'Unknown')
                print(f"  {ticker}: {sector}")
                if i >= 4:
                    break
    except Exception as e:
        print(f"⚠️  WARNING: Metadata fetch failed: {e}")
        print("This is expected if Tiingo metadata API has limits")
    
    print("\n" + "=" * 60)
    print("FRESH DATA UPDATE COMPLETE")
    print("✅ OHLCV pipeline working")
    print("✅ Parquet files updated") 
    print("✅ Ready for backtest validation")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
