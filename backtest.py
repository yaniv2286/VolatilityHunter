#!/usr/bin/env python3
"""
VolatilityHunter Backtesting Script
Manual execution of historical performance analysis
"""

import os
import sys

# Path Force Fix - ensures we can find config.json, data/, and src/ modules
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)

from datetime import datetime

from src.backtest_engine import BacktestEngine
from src.notifications import log_info, log_error

def main():
    """Main backtesting execution."""
    print("="*60)
    print("VOLATILITYHUNTER BACKTESTING ENGINE")
    print("="*60)
    print(f"[START] Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    try:
        # Initialize backtest engine
        log_info("Initializing backtest engine...")
        engine = BacktestEngine(initial_capital=100000, max_positions=10)
        
        # Run backtest with hardcoded date range
        log_info("Starting backtest...")
        results = engine.run_backtest(start_date="2024-01-01")
        
        # Generate and display report
        report = engine.generate_report()
        print("\n[BACKTEST RESULTS]")
        print("="*60)
        print(report)
        print("="*60)
        
        log_info("Backtest completed successfully")
        
    except Exception as e:
        print(f"\n[ERROR] Backtest failed: {e}")
        log_error(f"Backtest execution failed: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
