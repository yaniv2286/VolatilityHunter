#!/usr/bin/env python3
"""
Functional Health Check with Real Trading
Tests complete trading flow by buying and selling 1 share
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.orchestrator import Orchestrator
from src.config.system_config import SystemConfigManager
from src.config.agent_config import ConfigManager
from src.interfaces.agent_interface import MessageType, Message

class FunctionalHealthCheck:
    """Functional health check with real trading"""
    
    def __init__(self):
        self.logger = logging.getLogger("functional_health_check")
        self.health_check_trade_id = None
        self.original_portfolio = None
        
    async def run_functional_health_check(self) -> Dict[str, Any]:
        """Run functional health check with real trading"""
        try:
            self.logger.info("🚀 Starting Functional Health Check with Real Trading")
            
            # Initialize system
            system_config_manager = SystemConfigManager()
            config_manager = ConfigManager()
            
            orchestrator_config = {
                "config_manager": config_manager,
                "health_check_interval": 60,
                "max_concurrent_workflows": 5,
                "workflow_timeout": 600
            }
            
            orchestrator = Orchestrator(orchestrator_config)
            
            # Register agent types
            await self._register_agent_types(orchestrator)
            
            # Initialize orchestrator
            if not await orchestrator.initialize():
                return {"success": False, "error": "Failed to initialize orchestrator"}
                
            # Start orchestrator
            if not await orchestrator.start():
                return {"success": False, "error": "Failed to start orchestrator"}
            
            # Step 1: Check portfolio sync status
            sync_status = await self._check_portfolio_sync(orchestrator)
            if not sync_status["synced"]:
                return {"success": False, "error": "Portfolio not synchronized", "sync_status": sync_status}
            
            # Step 2: Backup original portfolio
            backup_status = await self._backup_portfolio()
            if not backup_status["success"]:
                return {"success": False, "error": "Failed to backup portfolio"}
            
            # Step 3: Execute functional trade test
            trade_result = await self._execute_health_check_trade(orchestrator)
            if not trade_result["success"]:
                return {"success": False, "error": "Health check trade failed", "trade_result": trade_result}
            
            # Step 4: Verify trade execution
            verification_result = await self._verify_trade_execution()
            if not verification_result["success"]:
                return {"success": False, "error": "Trade verification failed", "verification": verification_result}
            
            # Step 5: Restore portfolio (cleanup)
            cleanup_result = await self._cleanup_health_check()
            if not cleanup_result["success"]:
                return {"success": False, "error": "Cleanup failed", "cleanup": cleanup_result}
            
            # Step 6: Generate comprehensive report
            health_report = {
                "success": True,
                "test_type": "functional_health_check",
                "timestamp": datetime.now().isoformat(),
                "portfolio_sync": sync_status,
                "trade_execution": trade_result,
                "trade_verification": verification_result,
                "cleanup": cleanup_result,
                "overall_status": "HEALTHY",
                "test_summary": {
                    "portfolio_sync": "✅ PASS" if sync_status["synced"] else "❌ FAIL",
                    "trade_execution": "✅ PASS" if trade_result["success"] else "❌ FAIL",
                    "trade_verification": "✅ PASS" if verification_result["success"] else "❌ FAIL",
                    "cleanup": "✅ PASS" if cleanup_result["success"] else "❌ FAIL"
                }
            }
            
            # Stop orchestrator
            await orchestrator.stop()
            
            self.logger.info("🎯 Functional Health Check COMPLETED SUCCESSFULLY!")
            return health_report
            
        except Exception as e:
            self.logger.error(f"Functional health check failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _register_agent_types(self, orchestrator):
        """Register all agent types"""
        try:
            from src.agents.data import DataAgent
            from src.agents.strategy import StrategyAgent
            from src.agents.execution import ExecutionAgent
            from src.agents.sync import SyncAgent
            from src.agents.notification import NotificationAgent
            from src.agents.testing import TestingAgent
            
            orchestrator.agent_factory.register_agent("data", DataAgent)
            orchestrator.agent_factory.register_agent("strategy", StrategyAgent)
            orchestrator.agent_factory.register_agent("execution", ExecutionAgent)
            orchestrator.agent_factory.register_agent("sync", SyncAgent)
            orchestrator.agent_factory.register_agent("notification", NotificationAgent)
            orchestrator.agent_factory.register_agent("testing", TestingAgent)
            
        except Exception as e:
            self.logger.error(f"Error registering agent types: {e}")
    
    async def _check_portfolio_sync(self, orchestrator) -> Dict[str, Any]:
        """Check if TWS and local portfolio are synchronized"""
        try:
            self.logger.info("🔍 Checking portfolio synchronization...")
            
            # Get execution agent for account info
            execution_agent = orchestrator.agents.get('execution_agent')
            if not execution_agent:
                return {"success": False, "synced": False, "error": "Execution agent not found"}
            
            # Get TWS account info
            tws_account_info = await execution_agent.get_account_info()
            
            # Load local portfolio
            portfolio_file = "data/portfolio_sim.json"
            if not os.path.exists(portfolio_file):
                return {"success": False, "synced": False, "error": "Local portfolio file not found"}
            
            with open(portfolio_file, 'r') as f:
                local_portfolio = json.load(f)
            
            # Compare key metrics
            tws_positions = tws_account_info.get('positions', {})
            local_positions = local_portfolio.get('positions', {})
            
            # Check position count
            tws_position_count = len(tws_positions)
            local_position_count = len(local_positions)
            
            # Check if major positions match (allowing for small differences)
            position_match = abs(tws_position_count - local_position_count) <= 1
            
            # Check total value
            tws_total = tws_account_info.get('portfolio_value', 0)
            local_total = local_portfolio.get('total_value', 0)
            value_match = abs(tws_total - local_total) / max(tws_total, local_total) < 0.05  # 5% tolerance
            
            is_synced = position_match and value_match
            
            sync_status = {
                "success": True,
                "synced": is_synced,
                "tws_positions": tws_position_count,
                "local_positions": local_position_count,
                "tws_total_value": tws_total,
                "local_total_value": local_total,
                "position_match": position_match,
                "value_match": value_match,
                "details": f"TWS: {tws_position_count} pos, ${tws_total:,.2f} | Local: {local_position_count} pos, ${local_total:,.2f}"
            }
            
            self.logger.info(f"📊 Portfolio Sync Status: {'✅ SYNCED' if is_synced else '❌ NOT SYNCED'}")
            self.logger.info(f"   {sync_status['details']}")
            
            return sync_status
            
        except Exception as e:
            self.logger.error(f"Portfolio sync check failed: {e}")
            return {"success": False, "synced": False, "error": str(e)}
    
    async def _backup_portfolio(self) -> Dict[str, Any]:
        """Backup original portfolio before health check trade"""
        try:
            self.logger.info("💾 Backing up original portfolio...")
            
            portfolio_file = "data/portfolio_sim.json"
            backup_file = f"data/portfolio_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
            
            if os.path.exists(portfolio_file):
                # Read original portfolio
                with open(portfolio_file, 'r') as f:
                    self.original_portfolio = json.load(f)
                
                # Create backup
                with open(backup_file, 'w') as f:
                    json.dump(self.original_portfolio, f, indent=2)
                
                self.logger.info(f"✅ Portfolio backed up to: {backup_file}")
                return {"success": True, "backup_file": backup_file}
            else:
                return {"success": False, "error": "Portfolio file not found"}
                
        except Exception as e:
            self.logger.error(f"Portfolio backup failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _execute_health_check_trade(self, orchestrator) -> Dict[str, Any]:
        """Execute health check trade (buy 1 share, sell after 1 minute)"""
        try:
            self.logger.info("🔄 Executing Health Check Trade...")
            
            # Choose a liquid stock for testing (use one from current portfolio)
            test_ticker = "AAPL"  # Most liquid stock
            test_quantity = 1
            
            # Get execution agent
            execution_agent = orchestrator.agents.get('execution_agent')
            if not execution_agent:
                return {"success": False, "error": "Execution agent not found"}
            
            # Mark this as a health check trade
            self.health_check_trade_id = f"HEALTH_CHECK_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
            # Step 1: Buy 1 share
            self.logger.info(f"📈 Buying {test_quantity} share of {test_ticker}...")
            
            buy_order = {
                "action": "BUY",
                "ticker": test_ticker,
                "quantity": test_quantity,
                "order_type": "MARKET",
                "time_in_force": "DAY",
                "health_check": True,
                "trade_id": self.health_check_trade_id
            }
            
            buy_result = await execution_agent.place_order(buy_order)
            
            if not buy_result.get('success', False):
                return {"success": False, "error": "Buy order failed", "buy_result": buy_result}
            
            self.logger.info(f"✅ Buy order executed: {buy_result}")
            
            # Step 2: Wait 1 minute
            self.logger.info("⏱️ Waiting 1 minute before selling...")
            await asyncio.sleep(60)
            
            # Step 3: Sell 1 share
            self.logger.info(f"📉 Selling {test_quantity} share of {test_ticker}...")
            
            sell_order = {
                "action": "SELL",
                "ticker": test_ticker,
                "quantity": test_quantity,
                "order_type": "MARKET",
                "time_in_force": "DAY",
                "health_check": True,
                "trade_id": self.health_check_trade_id
            }
            
            sell_result = await execution_agent.place_order(sell_order)
            
            if not sell_result.get('success', False):
                return {"success": False, "error": "Sell order failed", "sell_result": sell_result}
            
            self.logger.info(f"✅ Sell order executed: {sell_result}")
            
            trade_result = {
                "success": True,
                "test_ticker": test_ticker,
                "quantity": test_quantity,
                "buy_order": buy_result,
                "sell_order": sell_result,
                "trade_id": self.health_check_trade_id,
                "execution_time": datetime.now().isoformat()
            }
            
            return trade_result
            
        except Exception as e:
            self.logger.error(f"Health check trade execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _verify_trade_execution(self) -> Dict[str, Any]:
        """Verify that the health check trade was executed properly"""
        try:
            self.logger.info("🔍 Verifying trade execution...")
            
            # Load current portfolio
            portfolio_file = "data/portfolio_sim.json"
            with open(portfolio_file, 'r') as f:
                current_portfolio = json.load(f)
            
            # Check if portfolio was updated (should have trade records)
            trades = current_portfolio.get('trades', [])
            
            # Look for our health check trade
            health_check_trades = [t for t in trades if t.get('trade_id') == self.health_check_trade_id]
            
            if len(health_check_trades) >= 2:
                # Found both buy and sell trades
                buy_trade = health_check_trades[0]
                sell_trade = health_check_trades[1]
                
                verification = {
                    "success": True,
                    "trades_found": len(health_check_trades),
                    "buy_trade": {
                        "ticker": buy_trade.get('ticker'),
                        "quantity": buy_trade.get('quantity'),
                        "price": buy_trade.get('price'),
                        "timestamp": buy_trade.get('timestamp')
                    },
                    "sell_trade": {
                        "ticker": sell_trade.get('ticker'),
                        "quantity": sell_trade.get('quantity'),
                        "price": sell_trade.get('price'),
                        "timestamp": sell_trade.get('timestamp')
                    },
                    "pnl": sell_trade.get('pnl', 0)
                }
                
                self.logger.info(f"✅ Trade verification successful: {verification['pnl']:+.2f} P&L")
                return verification
            else:
                return {
                    "success": False,
                    "error": f"Expected 2 trades, found {len(health_check_trades)}",
                    "trades_found": len(health_check_trades)
                }
                
        except Exception as e:
            self.logger.error(f"Trade verification failed: {e}")
            return {"success": False, "error": str(e)}
    
    async def _cleanup_health_check(self) -> Dict[str, Any]:
        """Clean up health check trade and restore portfolio"""
        try:
            self.logger.info("🧹 Cleaning up health check trade...")
            
            if self.original_portfolio is None:
                return {"success": False, "error": "No original portfolio backup found"}
            
            # Remove health check trades from portfolio
            portfolio_file = "data/portfolio_sim.json"
            with open(portfolio_file, 'r') as f:
                current_portfolio = json.load(f)
            
            # Filter out health check trades
            original_trades = self.original_portfolio.get('trades', [])
            current_trades = current_portfolio.get('trades', [])
            
            # Keep only original trades (remove health check trades)
            cleaned_trades = [t for t in current_trades if t.get('trade_id') != self.health_check_trade_id]
            
            # Restore portfolio state (except for health check trades)
            restored_portfolio = {
                "cash": self.original_portfolio['cash'],
                "positions": current_portfolio.get('positions', {}),  # Keep current positions
                "total_value": current_portfolio.get('total_value', self.original_portfolio['total_value']),
                "last_updated": datetime.now().isoformat(),
                "trades": original_trades,  # Restore original trades
                "sync_source": "health_check_cleanup",
                "health_check_trades_removed": len(current_trades) - len(cleaned_trades)
            }
            
            # Write restored portfolio
            with open(portfolio_file, 'w') as f:
                json.dump(restored_portfolio, f, indent=2)
            
            self.logger.info(f"✅ Cleanup completed: {restored_portfolio['health_check_trades_removed']} health check trades removed")
            
            return {"success": True, "trades_restored": len(original_trades), "health_check_trades_removed": restored_portfolio['health_check_trades_removed']}
            
        except Exception as e:
            self.logger.error(f"Cleanup failed: {e}")
            return {"success": False, "error": str(e)}

async def main():
    """Main entry point"""
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/functional_health_check.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("functional_health_check")
    logger.info("Starting Functional Health Check...")
    
    health_check = FunctionalHealthCheck()
    result = await health_check.run_functional_health_check()
    
    if result["success"]:
        logger.info("🎯 Functional Health Check PASSED!")
        logger.info(f"Status: {result['overall_status']}")
        
        # Print summary
        print("\n" + "="*80)
        print("🎯 FUNCTIONAL HEALTH CHECK RESULTS")
        print("="*80)
        print(f"Overall Status: {result['overall_status']}")
        print(f"Portfolio Sync: {result['test_summary']['portfolio_sync']}")
        print(f"Trade Execution: {result['test_summary']['trade_execution']}")
        print(f"Trade Verification: {result['test_summary']['trade_verification']}")
        print(f"Cleanup: {result['test_summary']['cleanup']}")
        print("="*80)
        print("✅ All systems are FUNCTIONAL and READY for trading!")
        print("="*80)
    else:
        logger.error(f"❌ Functional Health Check FAILED: {result.get('error', 'Unknown error')}")
        print("\n" + "="*80)
        print("❌ FUNCTIONAL HEALTH CHECK FAILED")
        print(f"Error: {result.get('error', 'Unknown error')}")
        print("="*80)
    
    return result

if __name__ == "__main__":
    asyncio.run(main())
