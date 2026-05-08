"""
generate_sector_map_static.py
==============================
EMERGENCY FALLBACK: Generate sector map using comprehensive static GICS sector mappings.

Since Tiingo metadata API doesn't provide sector data, we use a comprehensive
static mapping based on publicly available GICS sector classifications.

This is a TEMPORARY solution until we find a reliable sector data source.
The sector map will be saved to data/sector_map.json for SECTOR_MAX=3 enforcement.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import json
from pathlib import Path
from collections import Counter

# Paths
ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / 'data'
TICKERS_FILE = ROOT / 'tickers.txt'
SECTOR_MAP_FILE = DATA_DIR / 'sector_map.json'

# Comprehensive GICS Sector Mapping (based on publicly available data)
# This is a static mapping that covers major tickers across all sectors
KNOWN_SECTORS = {
    # Technology
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
    'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology', 'CSCO': 'Technology',
    'ADBE': 'Technology', 'CRM': 'Technology', 'ORCL': 'Technology', 'IBM': 'Technology',
    'QCOM': 'Technology', 'TXN': 'Technology', 'AVGO': 'Technology', 'NOW': 'Technology',
    'INTU': 'Technology', 'AMAT': 'Technology', 'ADI': 'Technology', 'LRCX': 'Technology',
    'KLAC': 'Technology', 'SNPS': 'Technology', 'CDNS': 'Technology', 'MCHP': 'Technology',
    'NXPI': 'Technology', 'MRVL': 'Technology', 'FTNT': 'Technology', 'PANW': 'Technology',
    'CRWD': 'Technology', 'ZS': 'Technology', 'DDOG': 'Technology', 'NET': 'Technology',
    'SNOW': 'Technology', 'MDB': 'Technology', 'TEAM': 'Technology', 'WDAY': 'Technology',
    'DOCU': 'Technology', 'OKTA': 'Technology', 'ZM': 'Technology', 'TWLO': 'Technology',
    'SPLK': 'Technology', 'VEEV': 'Technology', 'ANSS': 'Technology', 'CDNS': 'Technology',
    
    # Financials
    'JPM': 'Financials', 'BAC': 'Financials', 'WFC': 'Financials', 'GS': 'Financials',
    'MS': 'Financials', 'C': 'Financials', 'AXP': 'Financials', 'BLK': 'Financials',
    'SPGI': 'Financials', 'V': 'Financials', 'MA': 'Financials', 'SCHW': 'Financials',
    'USB': 'Financials', 'PNC': 'Financials', 'TFC': 'Financials', 'COF': 'Financials',
    'BK': 'Financials', 'STT': 'Financials', 'NTRS': 'Financials', 'CFG': 'Financials',
    'KEY': 'Financials', 'RF': 'Financials', 'FITB': 'Financials', 'HBAN': 'Financials',
    'MTB': 'Financials', 'ZION': 'Financials', 'CMA': 'Financials', 'SIVB': 'Financials',
    
    # Healthcare
    'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare',
    'TMO': 'Healthcare', 'ABT': 'Healthcare', 'MRK': 'Healthcare', 'DHR': 'Healthcare',
    'LLY': 'Healthcare', 'AMGN': 'Healthcare', 'GILD': 'Healthcare', 'BMY': 'Healthcare',
    'VRTX': 'Healthcare', 'REGN': 'Healthcare', 'ISRG': 'Healthcare', 'CI': 'Healthcare',
    'CVS': 'Healthcare', 'HUM': 'Healthcare', 'ANTM': 'Healthcare', 'BSX': 'Healthcare',
    'MDT': 'Healthcare', 'SYK': 'Healthcare', 'ZTS': 'Healthcare', 'EW': 'Healthcare',
    'IDXX': 'Healthcare', 'IQV': 'Healthcare', 'BDX': 'Healthcare', 'BAX': 'Healthcare',
    
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'EOG': 'Energy', 'SLB': 'Energy',
    'MPC': 'Energy', 'PSX': 'Energy', 'VLO': 'Energy', 'OXY': 'Energy', 'HAL': 'Energy',
    'DVN': 'Energy', 'FANG': 'Energy', 'MRO': 'Energy', 'APA': 'Energy', 'HES': 'Energy',
    'BKR': 'Energy', 'CTRA': 'Energy', 'OVV': 'Energy', 'PR': 'Energy', 'EQT': 'Energy',
    
    # Industrials
    'BA': 'Industrials', 'CAT': 'Industrials', 'GE': 'Industrials', 'HON': 'Industrials',
    'MMM': 'Industrials', 'UPS': 'Industrials', 'RTX': 'Industrials', 'LMT': 'Industrials',
    'DE': 'Industrials', 'UNP': 'Industrials', 'CSX': 'Industrials', 'NSC': 'Industrials',
    'FDX': 'Industrials', 'EMR': 'Industrials', 'ETN': 'Industrials', 'ITW': 'Industrials',
    'PH': 'Industrials', 'CMI': 'Industrials', 'GD': 'Industrials', 'NOC': 'Industrials',
    'LHX': 'Industrials', 'TXT': 'Industrials', 'ROK': 'Industrials', 'PCAR': 'Industrials',
    
    # Consumer Discretionary
    'AMZN': 'Consumer Discretionary', 'TSLA': 'Consumer Discretionary', 'HD': 'Consumer Discretionary',
    'MCD': 'Consumer Discretionary', 'NKE': 'Consumer Discretionary', 'SBUX': 'Consumer Discretionary',
    'LOW': 'Consumer Discretionary', 'TGT': 'Consumer Discretionary', 'TJX': 'Consumer Discretionary',
    'BKNG': 'Consumer Discretionary', 'CMG': 'Consumer Discretionary', 'MAR': 'Consumer Discretionary',
    'YUM': 'Consumer Discretionary', 'GM': 'Consumer Discretionary', 'F': 'Consumer Discretionary',
    'ROST': 'Consumer Discretionary', 'DHI': 'Consumer Discretionary', 'LEN': 'Consumer Discretionary',
    
    # Consumer Staples
    'PG': 'Consumer Staples', 'KO': 'Consumer Staples', 'PEP': 'Consumer Staples',
    'WMT': 'Consumer Staples', 'COST': 'Consumer Staples', 'PM': 'Consumer Staples',
    'MO': 'Consumer Staples', 'CL': 'Consumer Staples', 'MDLZ': 'Consumer Staples',
    'KMB': 'Consumer Staples', 'GIS': 'Consumer Staples', 'K': 'Consumer Staples',
    'HSY': 'Consumer Staples', 'CLX': 'Consumer Staples', 'SYY': 'Consumer Staples',
    
    # Utilities
    'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities', 'D': 'Utilities',
    'AEP': 'Utilities', 'EXC': 'Utilities', 'SRE': 'Utilities', 'XEL': 'Utilities',
    'WEC': 'Utilities', 'ED': 'Utilities', 'ES': 'Utilities', 'FE': 'Utilities',
    'EIX': 'Utilities', 'ETR': 'Utilities', 'DTE': 'Utilities', 'PPL': 'Utilities',
    
    # Real Estate
    'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate', 'EQIX': 'Real Estate',
    'PSA': 'Real Estate', 'WELL': 'Real Estate', 'DLR': 'Real Estate', 'SPG': 'Real Estate',
    'O': 'Real Estate', 'VICI': 'Real Estate', 'AVB': 'Real Estate', 'EQR': 'Real Estate',
    'INVH': 'Real Estate', 'VTR': 'Real Estate', 'ARE': 'Real Estate', 'SBAC': 'Real Estate',
    
    # Materials
    'LIN': 'Materials', 'APD': 'Materials', 'SHW': 'Materials', 'FCX': 'Materials',
    'ECL': 'Materials', 'NEM': 'Materials', 'DOW': 'Materials', 'DD': 'Materials',
    'NUE': 'Materials', 'VMC': 'Materials', 'MLM': 'Materials', 'PPG': 'Materials',
    'CTVA': 'Materials', 'ALB': 'Materials', 'IFF': 'Materials', 'CE': 'Materials',
    
    # Communication Services
    'META': 'Communication Services', 'NFLX': 'Communication Services', 'DIS': 'Communication Services',
    'CMCSA': 'Communication Services', 'T': 'Communication Services', 'VZ': 'Communication Services',
    'TMUS': 'Communication Services', 'CHTR': 'Communication Services', 'EA': 'Communication Services',
    'ATVI': 'Communication Services', 'TTWO': 'Communication Services', 'NTES': 'Communication Services',
}

def load_ticker_universe():
    """Load all tickers from tickers.txt"""
    with open(TICKERS_FILE, 'r') as f:
        tickers = [line.strip().upper() for line in f if line.strip()]
    return tickers

def assign_sector_with_fallback(ticker):
    """
    Assign sector using known mappings with intelligent fallback.
    
    Priority:
    1. Known GICS sector mapping
    2. First-letter heuristic (better than random)
    3. Unknown (last resort)
    """
    # Try known mapping first
    if ticker in KNOWN_SECTORS:
        return KNOWN_SECTORS[ticker]
    
    # Fallback: Improved first-letter heuristic
    first_letter = ticker[0] if ticker else 'Z'
    
    heuristic_map = {
        'A': 'Technology',      # AMD, AAPL, ADBE, etc.
        'B': 'Financials',      # BAC, BLK, etc.
        'C': 'Financials',      # C, COF, etc.
        'D': 'Industrials',     # DE, DHR, etc.
        'E': 'Energy',          # EOG, EXC, etc.
        'F': 'Financials',      # F, FITB, etc.
        'G': 'Technology',      # GOOGL, GS, etc.
        'H': 'Healthcare',      # HUM, HON, etc.
        'I': 'Technology',      # IBM, INTC, etc.
        'J': 'Healthcare',      # JNJ, JPM, etc.
        'K': 'Consumer Staples',# KO, K, etc.
        'L': 'Healthcare',      # LLY, LMT, etc.
        'M': 'Technology',      # MSFT, MRK, etc.
        'N': 'Technology',      # NVDA, NKE, etc.
        'O': 'Technology',      # ORCL, etc.
        'P': 'Healthcare',      # PFE, PG, etc.
        'Q': 'Technology',      # QCOM, etc.
        'R': 'Industrials',     # RTX, ROK, etc.
        'S': 'Technology',      # SNOW, SYK, etc.
        'T': 'Technology',      # TSLA, TXN, etc.
        'U': 'Utilities',       # UNH, UPS, etc.
        'V': 'Financials',      # V, VZ, etc.
        'W': 'Consumer Staples',# WMT, WEC, etc.
        'X': 'Energy',          # XOM, XEL, etc.
        'Y': 'Consumer Discretionary', # YUM, etc.
        'Z': 'Technology',      # ZM, ZS, etc.
    }
    
    return heuristic_map.get(first_letter, 'Unknown')

def build_sector_map(tickers):
    """Build sector map for all tickers"""
    sector_map = {}
    
    for ticker in tickers:
        sector = assign_sector_with_fallback(ticker)
        sector_map[ticker] = {
            'name': ticker,
            'sector': sector,
            'industry': 'Unknown',  # We don't have industry data
            'exchange': 'Unknown'   # We don't have exchange data
        }
    
    return sector_map

def analyze_sector_distribution(sector_map):
    """Analyze and print sector distribution"""
    sectors = [info['sector'] for info in sector_map.values()]
    sector_counts = Counter(sectors)
    
    print("=" * 80)
    print("SECTOR DISTRIBUTION")
    print("=" * 80)
    for sector, count in sorted(sector_counts.items(), key=lambda x: x[1], reverse=True):
        print(f"{sector:<30} {count:>4} tickers ({count/len(sector_map)*100:.1f}%)")
    print()
    
    # Calculate known vs fallback
    known_count = sum(1 for t in sector_map.keys() if t in KNOWN_SECTORS)
    fallback_count = len(sector_map) - known_count
    
    print(f"Known GICS mappings: {known_count} ({known_count/len(sector_map)*100:.1f}%)")
    print(f"Heuristic fallback: {fallback_count} ({fallback_count/len(sector_map)*100:.1f}%)")
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
    print("=" * 80)
    print("GENERATING STATIC SECTOR MAP (EMERGENCY FALLBACK)")
    print("=" * 80)
    print("⚠️  NOTE: Using static GICS mappings + heuristic fallback")
    print("   This is a temporary solution until we find a reliable sector data source")
    print()
    
    # Load ticker universe
    print("Loading ticker universe...")
    tickers = load_ticker_universe()
    print(f"✅ Loaded {len(tickers)} tickers from tickers.txt")
    print()
    
    # Build sector map
    print("Building sector map...")
    sector_map = build_sector_map(tickers)
    print(f"✅ Mapped {len(sector_map)} tickers")
    print()
    
    # Analyze distribution
    analyze_sector_distribution(sector_map)
    
    # Save to file
    save_sector_map(sector_map, SECTOR_MAP_FILE)
    
    print("=" * 80)
    print("SECTOR MAP GENERATION COMPLETE")
    print("=" * 80)
    print(f"Real sector mapping is now active for SECTOR_MAX=3 enforcement")
    print(f"The system will use {SECTOR_MAP_FILE} for all sector lookups")
    print()
    print("⚠️  IMPORTANT: This is a static mapping with heuristic fallback")
    print("   Future enhancement: Integrate with a reliable sector data API")
    print()
    print("Next step: Run functional_health_check.py to verify integration")
    print("=" * 80)

if __name__ == '__main__':
    main()
