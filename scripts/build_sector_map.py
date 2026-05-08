"""
build_sector_map.py
===================
Fetch real sector data from Tiingo metadata API for all tickers in the universe.
Saves to data/sector_map.json for 100% autonomous sector capping enforcement.

CRITICAL: This script ensures SECTOR_MAX=3 uses real GICS sectors, not meaningless
first-letter bucketing.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
import requests
import urllib3
from pathlib import Path
from src.config import TIINGO_KEY
from concurrent.futures import ThreadPoolExecutor, as_completed
import time

# Disable SSL warnings for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

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

def fetch_ticker_metadata(ticker):
    """
    Fetch metadata for a single ticker from Tiingo.
    Returns: (ticker, sector_data_dict) or (ticker, None) on error
    """
    url = f"https://api.tiingo.com/tiingo/meta/{ticker}"
    params = {'token': TIINGO_KEY}
    headers = {'Content-Type': 'application/json'}
    
    try:
        response = requests.get(url, params=params, headers=headers, timeout=10, verify=False)
        if response.status_code == 200:
            data = response.json()
            # Extract relevant sector/industry info
            sector_info = {
                'name': data.get('name', 'Unknown'),
                'sector': data.get('sector', 'Unknown'),
                'industry': data.get('industry', 'Unknown'),
                'exchange': data.get('exchangeCode', 'Unknown')
            }
            return (ticker, sector_info)
        else:
            print(f"⚠️  {ticker}: HTTP {response.status_code}")
            return (ticker, None)
    except Exception as e:
        print(f"⚠️  {ticker}: {str(e)[:50]}")
        return (ticker, None)

def build_sector_map(tickers, max_workers=10):
    """
    Fetch sector metadata for all tickers using parallel requests.
    
    Args:
        tickers: List of ticker symbols
        max_workers: Number of parallel workers
    
    Returns:
        dict: {ticker: {name, sector, industry, exchange}}
    """
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
        future_to_ticker = {executor.submit(fetch_ticker_metadata, ticker): ticker 
                           for ticker in tickers}
        
        # Process results as they complete
        for future in as_completed(future_to_ticker):
            ticker, sector_info = future.result()
            completed += 1
            
            if sector_info:
                sector_map[ticker] = sector_info
                if completed % 100 == 0:
                    print(f"Progress: {completed}/{total} ({completed/total*100:.1f}%) - "
                          f"Mapped: {len(sector_map)} | Errors: {errors}")
            else:
                errors += 1
                # Assign to Unknown sector with warning
                sector_map[ticker] = {
                    'name': 'Unknown',
                    'sector': 'Unknown',
                    'industry': 'Unknown',
                    'exchange': 'Unknown'
                }
    
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
    if not TIINGO_KEY:
        print("❌ ERROR: TIINGO_API_KEY not found in environment")
        print("   Please ensure .env file contains TIINGO_API_KEY")
        sys.exit(1)
    
    # Load ticker universe
    print("Loading ticker universe...")
    tickers = load_ticker_universe()
    print(f"✅ Loaded {len(tickers)} tickers from tickers.txt")
    print()
    
    # Build sector map
    sector_map = build_sector_map(tickers, max_workers=10)
    
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
