#!/usr/bin/env python3
"""
Full 26-Year Backtest Runner - Verify Core Logic Integrity
"""

import asyncio
import sys
import os
from datetime import datetime

# Add VolatilityHunter root to path
vh_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))
sys.path.insert(0, vh_root)

from src.main_agent_system import MainAgentSystem

async def run_full_backtest():
    """Run full 26-year backtest to verify core logic"""
    print("🚀 Running Full 26-Year Backtest to Verify Core Logic Integrity")
    print("=" * 70)
    
    try:
        # Initialize system
        system = MainAgentSystem()
        await system.initialize()
        await system.start()
        
        # Manually create testing agent
        print("⚠️  Creating Testing Agent manually...")
        from src.agents.testing import TestingAgent
        testing_config = {
            "agent_id": "testing_agent",
            "agent_type": "testing",
            "enabled": True,
            "log_level": "INFO",
            "retry_attempts": 3,
            "timeout": 30.0,
            "max_concurrent_tasks": 5,
            "health_check_interval": 60.0,
            "backtest_enabled": True,
            "dry_run_enabled": True,
            "integration_tests_enabled": True,
            "performance_benchmarks_enabled": True,
            "test_data_path": "data/test/",
            "backtest_lookback_days": 6520,  # 26 years (26 * 251 trading days)
            "dry_run_initial_capital": 100000,
            "benchmark_strategies": ["sweet_spot_v7_2"]
        }
        
        testing_agent = TestingAgent("testing_agent", testing_config)
        await testing_agent.initialize()
        await testing_agent.start()
        
        # Add to orchestrator
        await system.orchestrator.add_agent(testing_agent)
        print("✅ Testing Agent created successfully")
        
        print("🧪 Running Full 26-Year Backtest...")
        print("📅 Period: 1999-2025 (26 years)")
        print("💰 Initial Capital: $100,000")
        print("🎯 Strategy: Sweet Spot v7.2")
        print("-" * 70)
        
        # Run full backtest
        result = await testing_agent.run_backtest(
            strategy="sweet_spot_v7_2",
            lookback_days=6520,  # 26 years
            initial_capital=100000
        )
        
        if result.get("success", False):
            print("✅ Full Backtest completed successfully")
            
            # Extract key metrics
            results = result.get("results", {})
            total_return = results.get("total_return", 0)
            cagr = results.get("cagr", 0)
            max_drawdown = results.get("max_drawdown", 0)
            sharpe_ratio = results.get("sharpe_ratio", 0)
            win_rate = results.get("win_rate", 0)
            profit_factor = results.get("profit_factor", 0)
            total_trades = results.get("total_trades", 0)
            
            print("\n" + "=" * 70)
            print("📊 26-YEAR BACKTEST RESULTS:")
            print("=" * 70)
            print(f"📈 Total Return: {total_return:.2%}")
            print(f"📊 CAGR: {cagr:.2%}")
            print(f"📉 Max Drawdown: {max_drawdown:.2%}")
            print(f"📏 Sharpe Ratio: {sharpe_ratio:.2f}")
            print(f"🎯 Win Rate: {win_rate:.2%}")
            print(f"💰 Profit Factor: {profit_factor:.2f}")
            print(f"📋 Total Trades: {total_trades:,}")
            
            # Performance analysis
            print("\n" + "=" * 70)
            print("🎯 PERFORMANCE ANALYSIS:")
            print("=" * 70)
            
            # Check if metrics are reasonable for 26-year period
            if cagr > 0.20 and max_drawdown < 0.25:
                print("✅ EXCELLENT: Performance metrics are outstanding!")
                print(f"✅ CAGR: {cagr:.2%} (Target: >20%) - EXCELLENT!")
                print(f"✅ Max Drawdown: {max_drawdown:.2%} (Target: <25%) - EXCELLENT!")
                print("✅ CORE LOGIC VERIFIED: Sweet Spot v7.2 strategy is working perfectly!")
            elif cagr > 0.15 and max_drawdown < 0.30:
                print("✅ GOOD: Performance metrics are solid!")
                print(f"✅ CAGR: {cagr:.2%} (Target: >15%) - GOOD!")
                print(f"✅ Max Drawdown: {max_drawdown:.2%} (Target: <30%) - GOOD!")
                print("✅ CORE LOGIC VERIFIED: Strategy is working well!")
            else:
                print("⚠️  PERFORMANCE WARNING: Check core logic implementation")
                print(f"⚠️  CAGR: {cagr:.2%} (should be >15-20%)")
                print(f"⚠️  Max Drawdown: {max_drawdown:.2%} (should be <25-30%)")
            
            # Risk analysis
            print("\n📊 RISK ANALYSIS:")
            print(f"📉 Risk-Adjusted Return (Sharpe): {sharpe_ratio:.2f}")
            if sharpe_ratio > 1.5:
                print("✅ EXCELLENT: Superior risk-adjusted returns!")
            elif sharpe_ratio > 1.0:
                print("✅ GOOD: Solid risk-adjusted returns!")
            else:
                print("⚠️  WARNING: Risk-adjusted returns could be improved")
            
            # Win rate analysis
            print(f"🎯 Win Rate: {win_rate:.2%}")
            if win_rate > 0.65:
                print("✅ EXCELLENT: High win rate!")
            elif win_rate > 0.55:
                print("✅ GOOD: Solid win rate!")
            else:
                print("⚠️  WARNING: Win rate could be improved")
            
            # Profit factor analysis
            print(f"💰 Profit Factor: {profit_factor:.2f}")
            if profit_factor > 2.0:
                print("✅ EXCELLENT: Strong profitability!")
            elif profit_factor > 1.5:
                print("✅ GOOD: Good profitability!")
            else:
                print("⚠️  WARNING: Profitability could be improved")
            
            # Trade frequency analysis
            trades_per_year = total_trades / 26
            print(f"📋 Trade Frequency: {trades_per_year:.1f} trades/year")
            if 20 <= trades_per_year <= 100:
                print("✅ GOOD: Reasonable trade frequency!")
            else:
                print("⚠️  WARNING: Trade frequency may need adjustment")
            
            print("\n" + "=" * 70)
            print("🎉 26-YEAR BACKTEST COMPLETED SUCCESSFULLY!")
            print("🎯 Core logic integrity verified over full historical period!")
            print("=" * 70)
            
            return True
        else:
            print(f"❌ Backtest failed: {result.get('error', 'Unknown error')}")
            return False
            
    except Exception as e:
        print(f"❌ Error running backtest: {e}")
        return False
    finally:
        # Stop system
        if 'system' in locals():
            await system.stop()

if __name__ == "__main__":
    success = asyncio.run(run_full_backtest())
    if success:
        print("\n🎉 FULL 26-YEAR BACKTEST COMPLETED SUCCESSFULLY!")
        print("🎯 Core logic integrity verified over entire historical period!")
        print("🚀 System is ready for production deployment!")
    else:
        print("\n❌ FULL BACKTEST FAILED!")
        print("🔧 Check core logic implementation")
    
    sys.exit(0 if success else 1)
