"""
build_sector_map_v2.py
======================
Alternative approach: Use the existing TiingoLoader.fetch_ticker_metadata() method
from smart_data_loader_factory.py to build the sector map.

This leverages the proven working implementation.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from src.smart_data_loader_factory import TiingoLoader
from concurrent.futures import ThreadPoolExecutor, as_completed

# Paths
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
TICKERS_FILE = ROOT / 'tickers.txt'
SECTOR_MAP_FILE = DATA_DIR / 'sector_map.json'

def load_ticker_universe():
    """Load all tickers from tickers.txt"""
    with open(TICKERS_FILE, 'r') as f:
        tickers = [line.strip().upper() for line in f if line.strip()]
    return tickers

def build_sector_map_from_tiingo(tickers, max_workers=5):
    """
    Build sector map using TiingoLoader.fetch_ticker_metadata()
    
    Args:
        tickers: List of ticker symbols
        max_workers: Number of parallel workers (keep low for metadata API)
    
    Returns:
        dict: {ticker: {name, sector, industry, exchange}}
    """
    loader = TiingoLoader()
    sector_map = {}
    total = len(tickers)
    completed = 0
    errors = 0
    
    print("=" * 80)
    print("BUILDING SECTOR MAP FROM TIINGO METADATA API")
    print("=" * 80)
    print(f"Total tickers: {total}")
    print(f"Parallel workers: {max_workers}")
    print()
    
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # Submit all tasks
        future_to_ticker = {executor.submit(loader.fetch_ticker_metadata, ticker): ticker 
                           for ticker in tickers}
        
        # Process results as they complete
        for future in as_completed(future_to_ticker):
            ticker = future_to_ticker[future]
            completed += 1
            
            try:
                metadata = future.result()
                
                if metadata and metadata.get('sector') != 'Unknown':
                    sector_map[ticker] = {
                        'name': metadata.get('ticker', ticker),
                        'sector': metadata.get('sector', 'Unknown'),
                        'industry': metadata.get('industry', 'Unknown'),
                        'exchange': metadata.get('exchange', 'Unknown')
                    }
                else:
                    errors += 1
                    sector_map[ticker] = {
                        'name': ticker,
                        'sector': 'Unknown',
                        'industry': 'Unknown',
                        'exchange': 'Unknown'
                    }
                
                if completed % 100 == 0:
                    print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - "
                          f"Mapped: {len(sector_map) - errors} | Unknown: {errors}")
            
            except Exception as e:
                errors += 1
                sector_map[ticker] = {
                    'name': ticker,
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'exchange': 'Unknown'
                }
                if completed % 100 == 0:
                    print(f"⚠️  Error on {ticker}: {str(e)[:50]}")
    
    print()
    print("=" * 80)
    print("SECTOR MAP BUILD COMPLETE")
    print("=" * 80)
    print(f"Total tickers processed: {completed}")
    print(f"Successfully mapped: {len(sector_map) - errors}")
    print(f"Errors (assigned to Unknown): {errors}")
    print()
    
    return sector_map

def analyze_sector_distribution(sector_map):
    """Analyze and print sector distribution"""
    from collections import Counter
    
    sectors = [info['sector'] for info in sector_map.values()]
    sector_counts = Counter(sectors)
    
    print("=" * 80)
    print("SECTOR DISTRIBUTION")
    print("=" * 80)
    for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{sector:<30} {count:>4} tickers ({count/len(sector_map)*100:.1f}%)")
    print()

def save_sector_map(sector_map, filepath):
    """Save sector map to JSON file"""
    with open(filepath, 'w') as f:
        json.dump(sector_map, f, indent=2)
    print(f"✅ Sector map saved to: {filepath}")
    print(f"   File size: {filepath.stat().st_size / 1024:.1f} KB")
    print()

def main():
    """Main execution"""
    # Load ticker universe
    print("Loading ticker universe...")
    tickers = load_ticker_universe()
    print(f"✅ Loaded {len(tickers)} tickers from tickers.txt")
    print()
    
    # Build sector map using existing TiingoLoader
    sector_map = build_sector_map_from_tiingo(tickers, max_workers=5)
    
    # Analyze distribution
    analyze_sector_distribution(sector_map)
    
    # Save to file
    save_sector_map(sector_map, SECTOR_MAP_FILE)
    
    print("=" * 80)
    print("SECTOR MAP BUILD SUCCESSFUL")
    print("=" * 80)
    print(f"Real sector mapping is now active for SECTOR_MAX=3 enforcement")
    print(f"The system will use {SECTOR_MAP_FILE} for all sector lookups")
    print()
    print("Next step: Run functional_health_check.py to verify integration")
    print("=" * 80)

if __name__ == '__main__':
    main()
