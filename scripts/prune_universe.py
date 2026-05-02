#!/usr/bin/env python3
"""
Universe Pruner - Step 1 of Infrastructure Audit
Removes delisted, illiquid, and dead tickers from the universe.

Exit Code 0 = success
Exit Code 1 = API failure or critical error (No Silent Failures)
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
from src.notifications import log_info, log_error, log_warning

def main():
    print("=" * 60)
    print("VOLATILITYHUNTER UNIVERSE PRUNER")
    print("Removing dead tickers from the trading universe")
    print("=" * 60)
    
    # Load current tickers
    tickers_file = ROOT / 'tickers.txt'
    if not tickers_file.exists():
        log_error(f"ERROR: {tickers_file} not found")
        return 1
    
    with open(tickers_file, 'r') as f:
        tickers = [line.strip() for line in f if line.strip()]
    
    print(f"Loaded {len(tickers)} tickers from tickers.txt")
    
    # Get data loader
    try:
        loader = get_data_loader()
        print("Tiingo API connection established")
    except Exception as e:
        log_error(f"Failed to connect to Tiingo API: {e}")
        return 1
    
    # Fetch metadata for all tickers
    print(f"\nFetching metadata for {len(tickers)} tickers...")
    try:
        metadata = loader.fetch_all_metadata(tickers)
        print(f"Successfully fetched metadata for {len(metadata)} tickers")
    except Exception as e:
        log_error(f"Failed to fetch metadata: {e}")
        return 1
    
    # Analyze and filter tickers
    healthy_tickers = []
    removed_tickers = []
    
    # Date threshold for delisting detection
    today = datetime.now()
    delisting_threshold = today - timedelta(days=7)  # More than 7 days ago = likely delisted
    
    print(f"\nAnalyzing ticker health (delisting threshold: {delisting_threshold.strftime('%Y-%m-%d')})...")
    
    for ticker in tickers:
        ticker_data = metadata.get(ticker, {})
        
        # Check if ticker has metadata
        if not ticker_data:
            removed_tickers.append({
                'ticker': ticker,
                'reason': 'No metadata available'
            })
            continue
        
        # Check endDate for delisting
        end_date_str = ticker_data.get('endDate')
        if end_date_str:
            try:
                end_date = datetime.strptime(end_date_str, '%Y-%m-%d')
                if end_date < delisting_threshold:
                    removed_tickers.append({
                        'ticker': ticker,
                        'reason': f'Delisted on {end_date_str}'
                    })
                    continue
            except ValueError:
                pass  # Invalid date format, treat as healthy
        
        # Check price (filter OTC penny stocks)
        price = ticker_data.get('price', ticker_data.get('last', 0))
        if price and float(price) < 1.00:
            removed_tickers.append({
                'ticker': ticker,
                'reason': f'Price too low: ${price:.4f}'
            })
            continue
        
        # Check if ticker is actively trading
        start_date_str = ticker_data.get('startDate')
        if start_date_str:
            try:
                start_date = datetime.strptime(start_date_str, '%Y-%m-%d')
                # If start date is in future, something is wrong
                if start_date > today:
                    removed_tickers.append({
                        'ticker': ticker,
                        'reason': f'Start date in future: {start_date_str}'
                    })
                    continue
            except ValueError:
                pass
        
        # Ticker passed all checks - keep it
        healthy_tickers.append(ticker)
    
    # Summary
    print(f"\n" + "=" * 60)
    print("UNIVERSE PRUNING SUMMARY")
    print("=" * 60)
    print(f"Original tickers: {len(tickers)}")
    print(f"Healthy tickers:  {len(healthy_tickers)}")
    print(f"Removed tickers:  {len(removed_tickers)}")
    print(f"Survival rate:    {len(healthy_tickers)/len(tickers)*100:.1f}%")
    
    if len(removed_tickers) > 0:
        print(f"\nTop 10 removal reasons:")
        reason_counts = {}
        for removal in removed_tickers:
            reason = removal['reason']
            reason_counts[reason] = reason_counts.get(reason, 0) + 1
        
        for reason, count in sorted(reason_counts.items(), key=lambda x: x[1], reverse=True)[:10]:
            print(f"  {reason}: {count} tickers")
    
    # Archive removed tickers
    if removed_tickers:
        timestamp = datetime.now().strftime('%Y%m%d')
        archive_file = ROOT / 'logs' / f'delisted_tickers_{timestamp}.txt'
        archive_file.parent.mkdir(exist_ok=True)
        
        with open(archive_file, 'w') as f:
            f.write(f"# VolatilityHunter Universe Pruning - {datetime.now().isoformat()}\n")
            f.write(f"# Removed {len(removed_tickers)} tickers from universe\n")
            f.write(f"# Format: TICKER | REASON\n")
            f.write("\n")
            for removal in removed_tickers:
                f.write(f"{removal['ticker']} | {removal['reason']}\n")
        
        print(f"\nArchived removed tickers to: {archive_file}")
    
    # Update tickers.txt with healthy tickers only
    if len(healthy_tickers) != len(tickers):
        # Create backup of original
        backup_file = tickers_file.with_suffix('.txt.backup')
        with open(backup_file, 'w') as f:
            with open(tickers_file, 'r') as original:
                f.write(original.read())
        print(f"Backed up original to: {backup_file}")
        
        # Write new healthy ticker list
        with open(tickers_file, 'w') as f:
            for ticker in sorted(healthy_tickers):
                f.write(f"{ticker}\n")
        
        print(f"Updated tickers.txt with {len(healthy_tickers)} healthy tickers")
    else:
        print("\nNo tickers removed - universe already healthy")
    
    print("\n" + "=" * 60)
    print("UNIVERSE PRUNING COMPLETE")
    if len(removed_tickers) > 0:
        print(f"✅ Purged {len(removed_tickers)} ghost tickers from universe")
    else:
        print("✅ Universe already clean - no purges needed")
    print("✅ Ticker universe is now healthy and tradeable")
    print("=" * 60)
    
    return 0

if __name__ == '__main__':
    sys.exit(main())
