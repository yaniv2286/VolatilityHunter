"""
Clean delisted tickers from tickers.txt
Removes tickers that consistently fail to download data
"""
import os
import sys
from pathlib import Path
from collections import defaultdict
import re

ROOT = Path("d:/GitHub/VolatilityHunter")
LOG_DIR = ROOT / "logs"
TICKERS_FILE = ROOT / "tickers.txt"

def find_delisted_tickers():
    """Scan all trading logs to find tickers that are delisted"""
    delisted = set()
    error_counts = defaultdict(int)
    
    # Scan all trading logs
    for log_file in sorted(LOG_DIR.glob("trading_2026-*.log")):
        with open(log_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Find delisted ticker errors
        for match in re.finditer(r'\$([A-Z]+): possibly delisted', content):
            ticker = match.group(1)
            delisted.add(ticker)
            error_counts[ticker] += 1
    
    return delisted, error_counts

def clean_tickers_file(delisted_tickers):
    """Remove delisted tickers from tickers.txt"""
    if not TICKERS_FILE.exists():
        print(f"❌ tickers.txt not found at {TICKERS_FILE}")
        return
    
    # Read current tickers
    with open(TICKERS_FILE, 'r') as f:
        current_tickers = [line.strip() for line in f if line.strip()]
    
    print(f"Current tickers: {len(current_tickers)}")
    print(f"Delisted tickers to remove: {len(delisted_tickers)}")
    
    # Filter out delisted
    cleaned_tickers = [t for t in current_tickers if t not in delisted_tickers]
    
    print(f"Cleaned tickers: {len(cleaned_tickers)}")
    print(f"Removed: {len(current_tickers) - len(cleaned_tickers)}")
    
    # Backup original
    backup_file = TICKERS_FILE.with_suffix('.txt.backup')
    with open(backup_file, 'w') as f:
        f.write('\n'.join(current_tickers))
    print(f"\n✅ Backup saved to: {backup_file}")
    
    # Write cleaned file
    with open(TICKERS_FILE, 'w') as f:
        f.write('\n'.join(sorted(cleaned_tickers)))
    
    print(f"✅ Cleaned tickers.txt saved")
    
    return current_tickers, cleaned_tickers

def main():
    print("=" * 80)
    print("CLEANING DELISTED TICKERS FROM UNIVERSE")
    print("=" * 80)
    print()
    
    # Find delisted tickers from logs
    print("Scanning trading logs for delisted tickers...")
    delisted, error_counts = find_delisted_tickers()
    
    if not delisted:
        print("✅ No delisted tickers found in logs")
        return
    
    print(f"\nFound {len(delisted)} delisted tickers:")
    print()
    
    # Show top offenders
    sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)
    print("Top 20 most frequent errors:")
    for ticker, count in sorted_errors[:20]:
        print(f"  {ticker}: {count} errors")
    
    print()
    print("All delisted tickers:")
    print(", ".join(sorted(delisted)))
    
    print()
    print("-" * 80)
    
    # Clean the file
    current, cleaned = clean_tickers_file(delisted)
    
    print()
    print("=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Original tickers: {len(current)}")
    print(f"Delisted removed: {len(delisted)}")
    print(f"Final tickers: {len(cleaned)}")
    print(f"Reduction: {len(delisted) / len(current) * 100:.1f}%")
    print()
    print("✅ DONE - tickers.txt has been cleaned")
    print(f"✅ Backup saved to: {TICKERS_FILE.with_suffix('.txt.backup')}")

if __name__ == "__main__":
    main()
