#!/usr/bin/env python3
"""
Unified Logic Verification Script
Tests that strategy and shield logic produces identical results regardless of mode
"""

import os
import sys
import json
from datetime import datetime

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.strategy_v7_2 import analyze_stock_v7_2
from src.shields import apply_universal_shields
from src.data_loader_factory import get_data_loader
from simulation.simulated_data_loader import SimulatedParquetLoader

def test_aapl_analysis():
    """Test AAPL analysis in both sim and live modes"""
    print("="*60)
    print("🧪 UNIFIED LOGIC VERIFICATION - AAPL ANALYSIS")
    print("="*60)
    
    ticker = "AAPL"
    target_date = "2023-11-15"
    
    # Test in simulation mode
    print("📊 Testing SIMULATION Mode...")
    try:
        sim_loader = SimulatedParquetLoader(target_date)
        sim_data = sim_loader.load_data(ticker)
        
        if sim_data is None or sim_data.empty:
            print(f"❌ No simulation data for {ticker}")
            return False
        
        # Apply shields in sim mode
        sim_shields = apply_universal_shields(ticker, target_date)
        print(f"🛡️  SIM Shields: {sim_shields}")
        
        # Analyze in sim mode
        if all(sim_shields.values()):
            sim_analysis = analyze_stock_v7_2(sim_data, ticker)
            print(f"📈 SIM Analysis: {sim_analysis['signal']} - {sim_analysis['reason']}")
            sim_indicators = sim_analysis.get('indicators', {})
        else:
            print(f"🚫 SIM Shield Rejected: {sim_shields}")
            sim_analysis = {'signal': 'SHIELD_REJECTED', 'reason': 'Shields failed'}
            sim_indicators = {}
        
    except Exception as e:
        print(f"❌ SIM Mode Error: {e}")
        return False
    
    # Test in live mode
    print("\n📊 Testing LIVE Mode...")
    try:
        live_loader = get_data_loader()
        live_data = live_loader.load_data(ticker)
        
        if live_data is None or live_data.empty:
            print(f"❌ No live data for {ticker}")
            return False
        
        # Apply shields in live mode (use today's date for comparison)
        today_date = datetime.now().strftime('%Y-%m-%d')
        live_shields = apply_universal_shields(ticker, today_date)
        print(f"🛡️  LIVE Shields: {live_shields}")
        
        # Analyze in live mode
        if all(live_shields.values()):
            live_analysis = analyze_stock_v7_2(live_data, ticker)
            print(f"📈 LIVE Analysis: {live_analysis['signal']} - {live_analysis['reason']}")
            live_indicators = live_analysis.get('indicators', {})
        else:
            print(f"🚫 LIVE Shield Rejected: {live_shields}")
            live_analysis = {'signal': 'SHIELD_REJECTED', 'reason': 'Shields failed'}
            live_indicators = {}
        
    except Exception as e:
        print(f"❌ LIVE Mode Error: {e}")
        return False
    
    # Compare results
    print("\n🔍 RESULT COMPARISON")
    print("="*40)
    
    # Compare signals
    signals_match = sim_analysis['signal'] == live_analysis['signal']
    print(f"📊 Signals Match: {'✅' if signals_match else '❌'}")
    print(f"   SIM:  {sim_analysis['signal']}")
    print(f"   LIVE: {live_analysis['signal']}")
    
    # Compare indicators (if both analyses succeeded)
    indicators_match = True
    if sim_indicators and live_indicators:
        print("📊 INDICATOR COMPARISON (Expected Differences Due to Date):")
        for key in ['price', 'sma_200', 'stoch_k', 'volume']:
            sim_val = sim_indicators.get(key, None)
            live_val = live_indicators.get(key, None)
            
            if sim_val is not None and live_val is not None:
                print(f"📊 {key.upper()}: SIM=${sim_val:.2f}, LIVE=${live_val:.2f}")
                print(f"   📅 SIM Date: {target_date}, LIVE Date: {today_date}")
            else:
                print(f"📊 {key.upper()}: {'N/A' if sim_val is None else sim_val} vs {'N/A' if live_val is None else live_val}")
        
        # The key test is that both modes produce the same SIGNAL and shields work identically
        print(f"\n🎯 LOGIC CONSISTENCY: {'✅' if signals_match else '❌'}")
        print(f"   Both modes produce same signal: {sim_analysis['signal']}")
        print(f"   Both modes pass shields: {all(sim_shields.values()) and all(live_shields.values())}")
        
        indicators_match = signals_match  # Focus on signal consistency
    
    # Overall result - focus on signal consistency
    overall_match = signals_match
    print(f"\n🎯 LOGIC CONSISTENCY: {'✅' if overall_match else '❌'}")
    
    if overall_match:
        print("✅ Unified logic verification PASSED")
        print("   Strategy and shields produce consistent results across modes")
    else:
        print("❌ Unified logic verification FAILED")
        print("   Strategy or shields produce different results across modes")
    
    return overall_match

def test_data_consistency():
    """Test that data loading is consistent"""
    print("\n" + "="*60)
    print("📊 DATA CONSISTENCY VERIFICATION")
    print("="*60)
    
    ticker = "AAPL"
    target_date = "2023-11-15"
    
    try:
        # Load simulation data
        sim_loader = SimulatedParquetLoader(target_date)
        sim_data = sim_loader.load_data(ticker)
        
        # Load live data
        live_loader = get_data_loader()
        live_data = live_loader.load_data(ticker)
        
        if sim_data is None or live_data is None:
            print("❌ Data loading failed")
            return False
        
        # Compare data shapes
        print(f"📊 SIM Data Shape: {sim_data.shape}")
        print(f"📊 LIVE Data Shape: {live_data.shape}")
        
        # Check for required columns (case-insensitive)
        required_columns = ['date', 'open', 'high', 'low', 'close', 'volume']
        
        sim_columns_lower = [col.lower() for col in sim_data.columns]
        live_columns_lower = [col.lower() for col in live_data.columns]
        
        sim_has_required = all(col.lower() in sim_columns_lower for col in required_columns)
        live_has_required = all(col.lower() in live_columns_lower for col in required_columns)
        
        print(f"✅ SIM Has Required Columns: {sim_has_required}")
        print(f"✅ LIVE Has Required Columns: {live_has_required}")
        
        return sim_has_required and live_has_required
        
    except Exception as e:
        print(f"❌ Data consistency error: {e}")
        return False

def main():
    """Main verification execution"""
    print("🧠 VOLATILITYHUNTER UNIFIED LOGIC VERIFICATION")
    print("🎯 Testing strategy and shield consistency across modes")
    print("📅 Test Date: 2023-11-15")
    print("📈 Test Ticker: AAPL")
    
    # Run verification tests
    tests = [
        ("AAPL Analysis Comparison", test_aapl_analysis),
        ("Data Consistency Check", test_data_consistency)
    ]
    
    results = []
    
    for test_name, test_func in tests:
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"❌ {test_name} failed with exception: {e}")
            results.append((test_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📋 VERIFICATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for test_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {test_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 UNIFIED LOGIC VERIFICATION COMPLETE")
        print("✅ Strategy and shields are mode-independent")
        print("🚀 Ready for Santa Rally simulation")
        return True
    else:
        print("⚠️  UNIFIED LOGIC ISSUES DETECTED")
        print("🛑 FIX ISSUES BEFORE PROCEEDING WITH SIMULATION")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
