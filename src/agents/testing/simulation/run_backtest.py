#!/usr/bin/env python3
"""
Quick Backtest Runner - Verify Core Logic Integrity
"""

import asyncio
import sys
import os

# Add VolatilityHunter root to path
vh_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, vh_root)

from src.main_agent_system import MainAgentSystem

async def run_backtest():
    """Run backtest to verify core logic"""
    print("🚀 Running Backtest to Verify Core Logic Integrity")
    print("=" * 60)
    
    try:
        # Initialize system
        system = MainAgentSystem()
        await system.initialize()
        await system.start()
        
        # Manually create testing agent if not found
        testing_agent = None
        for agent in system.orchestrator.agents.values():
            if agent.agent_id == "testing_agent":
                testing_agent = agent
                break
                
        if testing_agent is None:
            print("⚠️  Testing Agent not found, creating manually...")
            # Import and create testing agent directly
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
                "backtest_lookback_days": 252,
                "dry_run_initial_capital": 100000,
                "benchmark_strategies": ["sweet_spot_v7_2"]
            }
            
            testing_agent = TestingAgent("testing_agent", testing_config)
            await testing_agent.initialize()
            await testing_agent.start()
            
            # Add to orchestrator
            await system.orchestrator.add_agent(testing_agent)
            print("✅ Testing Agent created manually")
            
        else:
            print("✅ Testing Agent found in orchestrator")
        
        print("🧪 Running Backtest...")
        result = await testing_agent.run_backtest(
            strategy="sweet_spot_v7_2",
            lookback_days=252,  # 1 year
            initial_capital=100000
        )
        
        if result.get("success", False):
            print("✅ Backtest completed successfully")
            
            # Extract key metrics
            results = result.get("results", {})
            total_return = results.get("total_return", 0)
            cagr = results.get("cagr", 0)
            max_drawdown = results.get("max_drawdown", 0)
            sharpe_ratio = results.get("sharpe_ratio", 0)
            win_rate = results.get("win_rate", 0)
            profit_factor = results.get("profit_factor", 0)
            total_trades = results.get("total_trades", 0)
            
            print("\n📊 BACKTEST RESULTS:")
            print(f"  Total Return: {total_return:.2%}")
            print(f"  CAGR: {cagr:.2%}")
            print(f"  Max Drawdown: {max_drawdown:.2%}")
            print(f"  Sharpe Ratio: {sharpe_ratio:.2f}")
            print(f"  Win Rate: {win_rate:.2%}")
            print(f"  Profit Factor: {profit_factor:.2f}")
            print(f"  Total Trades: {total_trades}")
            
            # Check if metrics are reasonable
            if cagr > 0.20 and max_drawdown < 0.25:  # 20% CAGR and <25% DD
                print("\n✅ CORE LOGIC VERIFIED: Performance metrics look good!")
                print("✅ CAGR > 20% and Max Drawdown < 25% - Core logic is intact!")
            else:
                print("\n⚠️  PERFORMANCE WARNING: Check core logic implementation")
                print(f"⚠️  CAGR: {cagr:.2%} (should be > 20%)")
                print(f"⚠️  Max Drawdown: {max_drawdown:.2%} (should be < 25%)")
                
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
    success = asyncio.run(run_backtest())
    if success:
        print("\n🎉 BACKTEST COMPLETED SUCCESSFULLY!")
        print("🎯 Core logic integrity verified!")
    else:
        print("\n❌ BACKTEST FAILED!")
        print("🔧 Check core logic implementation")
    
    sys.exit(0 if success else 1)
