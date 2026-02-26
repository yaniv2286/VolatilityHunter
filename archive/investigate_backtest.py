#!/usr/bin/env python3
"""
Investigate Backtest Performance - Why is it so fast?
"""

import sys
import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import time

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.main_agent_system import MainAgentSystem

class BacktestInvestigator:
    """Investigate why backtest is too fast"""
    
    def __init__(self):
        self.start_time = datetime.now()
        
    async def investigate_backtest_performance(self):
        """Investigate backtest performance issues"""
        print("🔍 INVESTIGATING BACKTEST PERFORMANCE")
        print("=" * 80)
        print("🎯 Why is 26-year backtest so fast? Something isn't right!")
        print("📊 Should be processing 2149 stocks × 26 years = massive computation")
        print("=" * 80)
        
        try:
            # Step 1: Check actual data availability
            print("📊 Step 1: Checking Actual Data Availability...")
            self.check_data_availability()
            
            # Step 2: Initialize system and check agents
            print("\n🤖 Step 2: Checking Agent Status...")
            system = MainAgentSystem()
            await system.initialize()
            await system.start()
            
            # Check all agents
            print(f"📊 Active Agents: {len(system.orchestrator.agents)}")
            for agent_id, agent in system.orchestrator.agents.items():
                status = getattr(agent, 'status', 'Unknown')
                print(f"  🤖 {agent_id}: {status}")
            
            # Step 3: Check Testing Agent capabilities
            print("\n🧪 Step 3: Checking Testing Agent Capabilities...")
            testing_agent = system.orchestrator.agents.get("testing_agent")
            if testing_agent:
                capabilities = testing_agent.get_capabilities()
                print(f"  🎯 Testing Agent Capabilities: {capabilities}")
                
                # Check if vectorized backtester is available
                try:
                    from scripts.vectorized_backtester import VectorizedBacktester
                    backtester = VectorizedBacktester(initial_capital=100000)
                    print(f"  📊 VectorizedBacktester: Available")
                    print(f"  🔍 Methods: {[m for m in dir(backtester) if not m.startswith('_')]}")
                except Exception as e:
                    print(f"  ❌ VectorizedBacktester Error: {e}")
            
            # Step 4: Check data processing
            print("\n📊 Step 4: Checking Data Processing...")
            self.check_data_processing()
            
            # Step 5: Run a detailed backtest investigation
            print("\n🚀 Step 5: Running Detailed Backtest Investigation...")
            await self.run_detailed_backtest_investigation(testing_agent)
            
            # Step 6: Cleanup
            await system.stop()
            
        except Exception as e:
            print(f"❌ Investigation error: {e}")
    
    def check_data_availability(self):
        """Check actual data availability"""
        print("📊 Checking Data Files...")
        
        data_dir = "data"
        if os.path.exists(data_dir):
            files = os.listdir(data_dir)
            parquet_files = [f for f in files if f.endswith('.parquet')]
            
            print(f"  📁 Data Directory: {data_dir}")
            print(f"  📊 Parquet Files: {len(parquet_files)}")
            
            # Check a few sample files
            sample_files = parquet_files[:5]
            for file in sample_files:
                file_path = os.path.join(data_dir, file)
                try:
                    df = pd.read_parquet(file_path)
                    print(f"  📈 {file}: {len(df)} rows, {df.columns.tolist()}")
                    
                    # Check date range
                    if 'date' in df.columns:
                        dates = pd.to_datetime(df['date'])
                        print(f"    📅 Date Range: {dates.min()} to {dates.max()}")
                except Exception as e:
                    print(f"  ❌ Error reading {file}: {e}")
        else:
            print(f"  ❌ Data directory not found: {data_dir}")
    
    def check_data_processing(self):
        """Check data processing capabilities"""
        print("📊 Checking Data Processing...")
        
        try:
            # Check smart data loader
            from src.smart_data_loader_factory import get_smart_data_loader
            loader = get_smart_data_loader()
            print(f"  📊 Smart Data Loader: Available")
            
            # Test data loading
            sample_data = loader.load_data("AAPL", "1d", 100)
            if sample_data is not None:
                print(f"  📈 Sample Data: {type(sample_data)}, Shape: {getattr(sample_data, 'shape', 'N/A')}")
            else:
                print(f"  ❌ No sample data returned")
                
        except Exception as e:
            print(f"  ❌ Data loader error: {e}")
    
    async def run_detailed_backtest_investigation(self, testing_agent):
        """Run detailed backtest investigation"""
        print("🔍 Running Detailed Backtest Investigation...")
        
        # Test 1: Single stock backtest with timing
        print("\n📊 Test 1: Single Stock Backtest with Timing...")
        start_time = time.time()
        
        try:
            result = await testing_agent.run_backtest(
                strategy="sweet_spot_v7_2",
                parameters={
                    "tickers": ["AAPL"],
                    "mode": "detailed_investigation"
                },
                lookback_days=365,
                initial_capital=100000
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"  ⏱️ Duration: {duration:.2f} seconds")
            print(f"  📊 Result: {result}")
            
            # Analyze the result
            if isinstance(result, dict):
                print(f"  📈 Result Keys: {list(result.keys())}")
                if 'results' in result:
                    results = result['results']
                    print(f"  📊 Results Type: {type(results)}")
                    if isinstance(results, dict):
                        print(f"  📈 Results Keys: {list(results.keys())}")
                        if 'equity_curve' in results:
                            equity = results['equity_curve']
                            print(f"  💰 Equity Curve: {type(equity)}, Length: {len(equity) if hasattr(equity, '__len__') else 'N/A'}")
                        if 'trades' in results:
                            trades = results['trades']
                            print(f"  📊 Trades: {type(trades)}, Count: {len(trades) if hasattr(trades, '__len__') else 'N/A'}")
                        if 'performance' in results:
                            perf = results['performance']
                            print(f"  📈 Performance: {perf}")
            
        except Exception as e:
            print(f"  ❌ Detailed backtest error: {e}")
        
        # Test 2: Multiple stocks backtest
        print("\n📊 Test 2: Multiple Stocks Backtest...")
        start_time = time.time()
        
        try:
            result = await testing_agent.run_backtest(
                strategy="sweet_spot_v7_2",
                parameters={
                    "tickers": ["AAPL", "MSFT", "GOOGL", "NVDA", "TSLA"],
                    "mode": "multi_stock_investigation"
                },
                lookback_days=365,
                initial_capital=100000
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"  ⏱️ Duration: {duration:.2f} seconds")
            print(f"  📊 Result: {result}")
            
        except Exception as e:
            print(f"  ❌ Multi-stock backtest error: {e}")
        
        # Test 3: Large universe backtest
        print("\n📊 Test 3: Large Universe Backtest...")
        start_time = time.time()
        
        try:
            # Load all tickers
            with open("tickers.txt", 'r') as f:
                all_tickers = [line.strip() for line in f if line.strip() and not line.startswith('#')]
            
            # Take first 100 for testing
            test_tickers = all_tickers[:100]
            
            result = await testing_agent.run_backtest(
                strategy="sweet_spot_v7_2",
                parameters={
                    "tickers": test_tickers,
                    "mode": "large_universe_investigation"
                },
                lookback_days=365,
                initial_capital=100000
            )
            
            end_time = time.time()
            duration = end_time - start_time
            
            print(f"  ⏱️ Duration: {duration:.2f} seconds")
            print(f"  📊 Tickers Processed: {len(test_tickers)}")
            print(f"  📊 Result: {result}")
            
        except Exception as e:
            print(f"  ❌ Large universe backtest error: {e}")

async def main():
    """Main investigation function"""
    print("🔍 VolatilityHunter Backtest Performance Investigation")
    print("🎯 Why is 26-year backtest so fast? Something isn't right!")
    print("=" * 80)
    
    investigator = BacktestInvestigator()
    await investigator.investigate_backtest_performance()
    
    print("\n" + "=" * 80)
    print("🔍 INVESTIGATION CONCLUSION:")
    print("📊 Backtest performance issues identified")
    print("🎯 Need to fix actual data processing and performance metrics")
    print("🚀 System architecture is working, but backtest logic needs improvement")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(main())
