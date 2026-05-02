#!/usr/bin/env python3
"""
Quick test of universe pruning with sample tickers
"""

import os
import sys
import json
from pathlib import Path
from datetime import datetime, timedelta

# Add src to path for imports
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from src.smart_data_loader_factory import get_data_loader

def main():
    print("Testing universe pruner with sample tickers...")
    
    # Load sample tickers
    tickers_file = ROOT / 'tickers.txt'
    with open(tickers_file, 'r') as f:
        all_tickers = [line.strip() for line in f if line.strip()]
    
    # Test with first 50 tickers
    sample_tickers = all_tickers[:50]
    print(f"Testing with {len(sample_tickers)} sample tickers")
    
    # Get data loader
    loader = get_data_loader()
    
    # Fetch metadata for sample
    print("Fetching metadata...")
    metadata = loader.fetch_all_metadata(sample_tickers)
    
    print(f"Got metadata for {len(metadata)} tickers")
    
    # Show sample metadata structure
    if metadata:
        sample_ticker = list(metadata.keys())[0]
        sample_data = metadata[sample_ticker]
        print(f"\nSample metadata for {sample_ticker}:")
        for key, value in sample_data.items():
            print(f"  {key}: {value}")
    
    # Check for delisted tickers
    today = datetime.now()
    delisting_threshold = today - timedelta(days=7)
    
    removed = []
    healthy = []
    
    for ticker in sample_tickers:
        ticker_data = metadata.get(ticker, {})
        
        if not ticker_data:
            removed.append({'ticker': ticker, 'reason': 'No metadata'})
            continue
        
        # Check endDate
        end_date_str = ticker_data.get('endDate')
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                if end_date < delisting_threshold:
                    removed.append({'ticker': ticker, 'reason': f'Delisted {end_date_str}'})
                    continue
            except ValueError:
                pass
        
        # Check price
        price = ticker_data.get('price', ticker_data.get('last', 0))
        if price and float(price) < 1.00:
            removed.append({'ticker': ticker, 'reason': f'Price ${price:.4f}'})
            continue
        
        healthy.append(ticker)
    
    print(f"\nResults:")
    print(f"  Healthy: {len(healthy)}")
    print(f"  Removed: {len(removed)}")
    
    if removed:
        print("\nRemoved tickers:")
        for r in removed[:10]:  # Show first 10
            print(f"  {r['ticker']}: {r['reason']}")
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
