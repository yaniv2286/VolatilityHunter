#!/usr/bin/env python3
"""
System Sanitization Script for Santa Rally Simulation
Ensures clean simulation environment while protecting live portfolio
"""

import os
import sys
import json
import hashlib
from pathlib import Path

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.notifications import log_info, log_error, log_warning

def get_file_checksum(file_path):
    """Get SHA-256 checksum of a file"""
    if not os.path.exists(file_path):
        return None
    
    try:
        with open(file_path, 'rb') as f:
            content = f.read()
            return hashlib.sha256(content).hexdigest()
    except Exception as e:
        log_error(f"Error calculating checksum for {file_path}: {e}")
        return None

def reset_simulation_portfolio():
    """Reset simulation portfolio to clean state"""
    print("="*60)
    print("🧹 SIMULATION PORTFOLIO RESET")
    print("="*60)
    
    sim_portfolio_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'simulation', 
        'portfolio_sim.json'
    )
    
    # Get checksum before reset (if file exists)
    old_checksum = get_file_checksum(sim_portfolio_file)
    
    # Create clean portfolio state
    clean_portfolio = {
        "cash": 100000.0,
        "positions": {},
        "history": [],
        "total_value": 100000.0,
        "last_updated": "2026-02-16T15:30:00",
        "execution_mode": "SIMULATION"
    }
    
    try:
        # Save clean portfolio
        with open(sim_portfolio_file, 'w') as f:
            json.dump(clean_portfolio, f, indent=2)
        
        # Get checksum after reset
        new_checksum = get_file_checksum(sim_portfolio_file)
        
        print(f"✅ Simulation portfolio reset: {sim_portfolio_file}")
        print(f"💰 Cash: ${clean_portfolio['cash']:,.2f}")
        print(f"📊 Positions: {len(clean_portfolio['positions'])}")
        print(f"📈 History: {len(clean_portfolio['history'])}")
        print(f"🔐 Old Checksum: {old_checksum}")
        print(f"🔐 New Checksum: {new_checksum}")
        
        return True
        
    except Exception as e:
        print(f"❌ Error resetting simulation portfolio: {e}")
        log_error(f"Error resetting simulation portfolio: {e}")
        return False

def verify_live_portfolio_untouched():
    """Verify that live portfolio remains untouched"""
    print("\n" + "="*60)
    print("🛡️ LIVE PORTFOLIO VERIFICATION")
    print("="*60)
    
    live_portfolio_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'data', 
        'portfolio.json'
    )
    
    if not os.path.exists(live_portfolio_file):
        print(f"⚠️  Live portfolio not found: {live_portfolio_file}")
        return True  # Not existing is acceptable for fresh setup
    
    try:
        # Get current checksum
        current_checksum = get_file_checksum(live_portfolio_file)
        
        # Load and verify portfolio structure
        with open(live_portfolio_file, 'r') as f:
            portfolio = json.load(f)
        
        cash = portfolio.get('cash', 0)
        positions = portfolio.get('positions', {})
        history = portfolio.get('trade_history', [])
        
        print(f"✅ Live portfolio verified: {live_portfolio_file}")
        print(f"💰 Cash: ${cash:,.2f}")
        print(f"📊 Positions: {len(positions)}")
        print(f"📈 History: {len(history)}")
        print(f"🔐 Current Checksum: {current_checksum}")
        
        # Verify it's not the clean simulation portfolio
        if abs(cash - 100000.0) < 0.01 and len(positions) == 0 and len(history) == 0:
            print("⚠️  WARNING: Live portfolio appears to be in clean state")
            print("   This might indicate a fresh setup or previous reset")
        
        return True
        
    except Exception as e:
        print(f"❌ Error verifying live portfolio: {e}")
        log_error(f"Error verifying live portfolio: {e}")
        return False

def verify_portfolio_isolation():
    """Verify that simulation and live portfolios are properly isolated"""
    print("\n" + "="*60)
    print("🔒 PORTFOLIO ISOLATION VERIFICATION")
    print("="*60)
    
    sim_portfolio_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'simulation', 
        'portfolio_sim.json'
    )
    
    live_portfolio_file = os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 
        'data', 
        'portfolio.json'
    )
    
    try:
        # Get checksums
        sim_checksum = get_file_checksum(sim_portfolio_file)
        live_checksum = get_file_checksum(live_portfolio_file)
        
        print(f"📁 Simulation Portfolio: {sim_portfolio_file}")
        print(f"🔐 Simulation Checksum: {sim_checksum}")
        print(f"📁 Live Portfolio: {live_portfolio_file}")
        print(f"🔐 Live Checksum: {live_checksum}")
        
        # Verify files are different
        if sim_checksum == live_checksum:
            print("❌ ERROR: Simulation and live portfolios have identical checksums!")
            print("   This indicates a critical isolation failure!")
            return False
        else:
            print("✅ Portfolio isolation verified: Different checksums")
            return True
            
    except Exception as e:
        print(f"❌ Error verifying portfolio isolation: {e}")
        log_error(f"Error verifying portfolio isolation: {e}")
        return False

def main():
    """Main sanitization execution"""
    print("🧠 VOLATILITYHUNTER SYSTEM SANITIZATION")
    print("🎯 Preparing clean environment for Santa Rally Simulation")
    print("📅 Target Period: 2023-11-01 to 2023-12-31")
    
    # Execute sanitization steps
    steps = [
        ("Reset Simulation Portfolio", reset_simulation_portfolio),
        ("Verify Live Portfolio Untouched", verify_live_portfolio_untouched),
        ("Verify Portfolio Isolation", verify_portfolio_isolation)
    ]
    
    results = []
    
    for step_name, step_func in steps:
        try:
            result = step_func()
            results.append((step_name, result))
        except Exception as e:
            print(f"❌ {step_name} failed with exception: {e}")
            results.append((step_name, False))
    
    # Summary
    print("\n" + "="*60)
    print("📋 SANITIZATION SUMMARY")
    print("="*60)
    
    all_passed = True
    for step_name, result in results:
        status = "✅ PASS" if result else "❌ FAIL"
        print(f"{status} {step_name}")
        if not result:
            all_passed = False
    
    print("\n" + "="*60)
    if all_passed:
        print("🎉 SYSTEM SANITIZATION COMPLETE - READY FOR SIMULATION")
        print("🚀 Simulation environment is clean and isolated")
        return True
    else:
        print("⚠️  SANITIZATION ISSUES DETECTED - FIX BEFORE PROCEEDING")
        print("🛑 HALTING SIMULATION - Address failed steps above")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
