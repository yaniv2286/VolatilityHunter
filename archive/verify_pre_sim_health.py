#!/usr/bin/env python3
"""
Pre-Simulation Health Verification Script
Validates system readiness for Santa Rally Simulation (2023-11-01 to 2023-12-31)
"""

import os
import sys
import json
import pandas as pd
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.storage import DataStorage
from src.notifications import log_info, log_error, log_warning

def check_portfolio_cleanliness():
    """Verify simulation portfolio is clean with $100,000 cash"""
    print("="*60)
    print("🔍 PORTFOLIO CLEANLINESS CHECK")
    print("="*60)
    
    sim_portfolio_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'simulation', 
        'portfolio_sim.json'
    )
    
    print(f"Checking: {sim_portfolio_file}")
    
    if not os.path.exists(sim_portfolio_file):
        print("❌ Simulation portfolio file does not exist")
        return False
    
    try:
        with open(sim_portfolio_file, 'r') as f:
            portfolio = json.load(f)
        
        cash = portfolio.get('cash', 0)
        positions = portfolio.get('positions', {})
        trade_history = portfolio.get('trade_history', [])
        
        print(f"💰 Cash: ${cash:,.2f}")
        print(f"📊 Positions: {len(positions)}")
        print(f"📈 Trade History: {len(trade_history)}")
        
        # Check if portfolio is clean
        is_clean = (
            abs(cash - 100000.0) < 0.01 and  # $100,000 cash
            len(positions) == 0 and           # No positions
            len(trade_history) == 0          # No trade history
        )
        
        if is_clean:
            print("✅ Portfolio is CLEAN - Ready for simulation")
            return True
        else:
            print("❌ Portfolio is NOT CLEAN - Needs reset")
            return False
            
    except Exception as e:
        print(f"❌ Error reading portfolio: {e}")
        return False

def check_critical_parquet_files():
    """Verify AAPL, NVDA, MSFT parquet files are readable"""
    print("\n" + "="*60)
    print("🔍 CRITICAL PARQUET FILES CHECK")
    print("="*60)
    
    critical_tickers = ['AAPL', 'NVDA', 'MSFT']
    storage = DataStorage()
    
    all_readable = True
    
    for ticker in critical_tickers:
        try:
            print(f"📄 Checking {ticker}...")
            
            # Try to load data
            df = storage.load_data(ticker)
            
            if df is None or df.empty:
                print(f"❌ {ticker}: No data available")
                all_readable = False
                continue
            
            # Check data quality
            required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                print(f"❌ {ticker}: Missing columns: {missing_columns}")
                all_readable = False
                continue
            
            # Check date range
            df['date'] = pd.to_datetime(df['date'])
            date_range = f"{df['date'].min().date()} to {df['date'].max().date()}"
            row_count = len(df)
            
            print(f"✅ {ticker}: {row_count:,} rows, {date_range}")
            
        except Exception as e:
            print(f"❌ {ticker}: Error loading - {e}")
            all_readable = False
    
    return all_readable

def check_unified_engine_configuration():
    """Verify Unified Engine simulation configuration"""
    print("\n" + "="*60)
    print("🔍 UNIFIED ENGINE CONFIGURATION CHECK")
    print("="*60)
    
    try:
        # Test main_unified.py import
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        
        # Check if main_unified.py exists and is readable
        main_unified_path = os.path.join(
            os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
            'main_unified.py'
        )
        
        if not os.path.exists(main_unified_path):
            print("❌ main_unified.py not found")
            return False
        
        print(f"✅ main_unified.py found: {main_unified_path}")
        
        # Try to import and check DataLoaderFactory
        import importlib.util
        spec = importlib.util.spec_from_file_location("main_unified", main_unified_path)
        main_module = importlib.util.module_from_spec(spec)
        
        # Check for key classes
        with open(main_unified_path, 'r') as f:
            content = f.read()
        
        checks = {
            'DataLoaderFactory': 'DataLoaderFactory' in content,
            'PortfolioManagerFactory': 'PortfolioManagerFactory' in content,
            'SimulatedParquetLoader': 'SimulatedParquetLoader' in content,
            'mode sim': "mode == 'sim'" in content
        }
        
        for check_name, result in checks.items():
            status = "✅" if result else "❌"
            print(f"{status} {check_name}: {'Found' if result else 'Missing'}")
        
        return all(checks.values())
        
    except Exception as e:
        print(f"❌ Error checking Unified Engine: {e}")
        return False

def count_parquet_universe():
    """Count total parquet files in data directory"""
    print("\n" + "="*60)
    print("🔍 PARQUET UNIVERSE SIZE CHECK")
    print("="*60)
    
    data_dir = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'data'
    )
    
    if not os.path.exists(data_dir):
        print("❌ Data directory does not exist")
        return False
    
    parquet_files = [f for f in os.listdir(data_dir) if f.endswith('.parquet')]
    parquet_count = len(parquet_files)
    
    print(f"📊 Total parquet files: {parquet_count:,}")
    
    # Check minimum threshold
    if parquet_count < 2000:
        print(f"❌ Insufficient parquet files: {parquet_count} < 2000")
        return False
    else:
        print(f"✅ Sufficient parquet universe: {parquet_count:,} files")
        return True

def main():
    """Main health verification"""
    print("🧠 SANTA RALLY SIMULATION - PRE-HEALTH VERIFICATION")
    print("📅 Simulation Period: 2023-11-01 to 2023-12-31")
    print("🎯 Following Strict Operational Protocol")
    
    # Run all health checks
    checks = [
        ("Portfolio Cleanliness", check_portfolio_cleanliness),
        ("Critical Parquet Files", check_critical_parquet_files),
        ("Unified Engine Configuration", check_unified_engine_configuration),
        ("Parquet Universe Size", count_parquet_universe)
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            result = check_func()
            results.append((check_name, result))
        except Exception as e:
            print(f"❌ {check_name} failed with exception: {e}")
            results.append((check_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📋 HEALTH VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for check_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {check_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 ALL HEALTH CHECKS PASSED - READY FOR SIMULATION")
        print("🚀 Proceeding to Phase 2: Debug Logging Enhancement")
        return True
    else:
        print("⚠️  HEALTH CHECKS FAILED - FIX ISSUES BEFORE PROCEEDING")
        print("🛑 HALTING SIMULATION - Address failed checks above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
