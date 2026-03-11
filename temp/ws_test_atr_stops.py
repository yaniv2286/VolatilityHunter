"""
Test ATR-based volatility stops on current positions
"""
import os
import sys
from pathlib import Path
import pandas as pd
import json

ROOT = Path("d:/GitHub/VolatilityHunter")
sys.path.insert(0, str(ROOT))

from src.strategy_engine import get_params, load_and_prepare

def test_atr_stops():
    """Test ATR-based stops on current positions"""
    
    # Load portfolio
    portfolio_file = ROOT / "data" / "portfolio.json"
    with open(portfolio_file, 'r') as f:
        portfolio = json.load(f)
    
    positions = portfolio.get('positions', {})
    
    if not positions:
        print("No open positions to test")
        return
    
    print("=" * 80)
    print("ATR-BASED VOLATILITY STOP ANALYSIS")
    print("=" * 80)
    print()
    
    # Get v8.1 parameters
    params = get_params('v8.1')
    HARD_STOP_PCT = params['HARD_STOP_PCT']
    ATR_STOP_MULT = params['ATR_STOP_MULT']
    
    print(f"Configuration:")
    print(f"  Fixed Hard Stop: {HARD_STOP_PCT:.1%}")
    print(f"  ATR Multiplier: {ATR_STOP_MULT}x")
    print()
    
    print("CURRENT POSITIONS:")
    print("-" * 80)
    print(f"{'Ticker':<8} {'Entry':<10} {'Current':<10} {'ATR':<8} {'Fixed Stop':<12} {'ATR Stop':<12} {'Diff':<8}")
    print("-" * 80)
    
    for ticker, pos in positions.items():
        entry_price = pos.get('entry_price', 0)
        
        # Load data to get current price and ATR
        parquet_file = ROOT / "data" / f"{ticker}.parquet"
        if not parquet_file.exists():
            print(f"{ticker:<8} No data file found")
            continue
        
        df = load_and_prepare(parquet_file)
        if df is None or df.empty:
            print(f"{ticker:<8} Failed to load data")
            continue
        
        last = df.iloc[-1]
        current_price = last.get('adjClose', last.get('Close', last.get('close', 0)))
        atr = last.get('atr', 0)
        
        # Calculate stops
        fixed_stop_price = entry_price * (1 - HARD_STOP_PCT)
        
        if atr > 0:
            atr_stop_distance = ATR_STOP_MULT * atr
            atr_stop_pct = atr_stop_distance / entry_price
            atr_stop_price = entry_price - atr_stop_distance
            diff_pct = atr_stop_pct - HARD_STOP_PCT
            
            print(f"{ticker:<8} ${entry_price:<9.2f} ${current_price:<9.2f} ${atr:<7.2f} "
                  f"${fixed_stop_price:<11.2f} ${atr_stop_price:<11.2f} {diff_pct:>+7.1%}")
        else:
            print(f"{ticker:<8} ${entry_price:<9.2f} ${current_price:<9.2f} N/A      "
                  f"${fixed_stop_price:<11.2f} N/A          N/A")
    
    print()
    print("=" * 80)
    print("INTERPRETATION:")
    print("=" * 80)
    print()
    print("ATR Stop vs Fixed Stop:")
    print("  • Positive Diff: ATR stop is WIDER (more room for volatility)")
    print("  • Negative Diff: ATR stop is TIGHTER (less volatile stock)")
    print()
    print("Benefits of ATR-based stops:")
    print("  ✅ High volatility stocks get wider stops (avoid false exits)")
    print("  ✅ Low volatility stocks get tighter stops (better protection)")
    print("  ✅ Adapts to each stock's personality")
    print("  ✅ More sophisticated risk management")
    print()
    print("Example:")
    print("  • Stock with ATR=$5, Entry=$100:")
    print("    - Fixed 8% stop: $92.00")
    print("    - ATR 2.5x stop: $87.50 (12.5% - wider for volatile stock)")
    print()
    print("  • Stock with ATR=$2, Entry=$100:")
    print("    - Fixed 8% stop: $92.00")
    print("    - ATR 2.5x stop: $95.00 (5% - tighter for stable stock)")
    
    print()

if __name__ == "__main__":
    test_atr_stops()
