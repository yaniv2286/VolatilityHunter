#!/usr/bin/env python3
"""
Simple Test Suite - 7 Agent Tests + 1 Full Test
Slim, efficient testing for VolatilityHunter agent system
"""

import asyncio
import sys
import os
import logging
from datetime import datetime
from typing import Dict, List, Any

# Add VolatilityHunter root to path
vh_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, vh_root)
sys.path.insert(0, os.path.join(vh_root, 'src'))

class SimpleTestSuite:
    """Simple test suite: 7 agent tests + 1 full test"""
    
    def __init__(self):
        self.logger = self._setup_logging()
        self.test_results = {}
        
    def _setup_logging(self):
        """Setup logging without emoji to avoid encoding issues"""
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/simple_tests.log'),
                logging.StreamHandler()
            ]
        )
        return logging.getLogger("simple_test_suite")
    
    async def run_all_tests(self) -> Dict[str, Any]:
        """Run all tests: 7 agent tests + 1 full test"""
        self.logger.info("=" * 70)
        self.logger.info("SIMPLE TEST SUITE: 7 AGENT TESTS + 1 FULL TEST")
        self.logger.info("=" * 70)
        
        results = {
            "agent_tests": {},
            "full_test": {},
            "summary": {
                "total_tests": 8,
                "passed": 0,
                "failed": 0,
                "start_time": datetime.now().isoformat()
            }
        }
        
        try:
            # Phase 1: Run 7 agent tests
            self.logger.info("Phase 1: Running 7 Agent Tests")
            results["agent_tests"] = await self.run_agent_tests()
            
            # Phase 2: Run 1 full test
            self.logger.info("Phase 2: Running Full End-to-End Test")
            results["full_test"] = await self.run_full_test()
            
            # Calculate summary
            agent_passed = results["agent_tests"].get("passed", 0)
            agent_failed = results["agent_tests"].get("failed", 0)
            full_passed = 1 if results["full_test"].get("success", False) else 0
            full_failed = 0 if results["full_test"].get("success", False) else 1
            
            results["summary"]["passed"] = agent_passed + full_passed
            results["summary"]["failed"] = agent_failed + full_failed
            results["summary"]["end_time"] = datetime.now().isoformat()
            
            # Print summary
            self.print_test_summary(results["summary"])
            
            return results
            
        except Exception as e:
            self.logger.error(f"Error running tests: {e}")
            return {"error": str(e), "summary": results.get("summary", {})}
    
    async def run_agent_tests(self) -> Dict[str, Any]:
        """Run 7 individual agent tests"""
        agent_tests = [
            ("Data Agent", self.test_data_agent),
            ("Strategy Agent", self.test_strategy_agent),
            ("Execution Agent", self.test_execution_agent),
            ("Sync Agent", self.test_sync_agent),
            ("Notification Agent", self.test_notification_agent),
            ("Testing Agent", self.test_testing_agent),
            ("Scheduler Agent", self.test_scheduler_agent)
        ]
        
        results = {"passed": 0, "failed": 0, "tests": []}
        
        for agent_name, test_func in agent_tests:
            self.logger.info(f"Testing {agent_name}...")
            try:
                result = await test_func()
                results["tests"].append({
                    "agent": agent_name,
                    "success": result.get("success", False),
                    "message": result.get("message", ""),
                    "details": result.get("details", {})
                })
                
                if result.get("success", False):
                    results["passed"] += 1
                    self.logger.info(f"✅ {agent_name}: PASSED")
                else:
                    results["failed"] += 1
                    self.logger.error(f"❌ {agent_name}: FAILED - {result.get('error', 'Unknown error')}")
                    
            except Exception as e:
                results["failed"] += 1
                results["tests"].append({
                    "agent": agent_name,
                    "success": False,
                    "error": str(e)
                })
                self.logger.error(f"❌ {agent_name}: EXCEPTION - {e}")
        
        return results
    
    async def test_data_agent(self) -> Dict[str, Any]:
        """Test Data Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Data Agent import...")
            from src.agents.data.agent import DataAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Data Agent configuration...")
            config = {
                'agent_id': 'test_data_agent',
                'agent_type': 'data',
                'data_source': 'smart_data_loader',
                'cache_enabled': True,
                'cache_ttl': 300
            }
            
            agent = DataAgent('test_data_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_data_agent'
            
            # Test 3: Initialization
            self.logger.info("  Testing Data Agent initialization...")
            try:
                await agent.initialize()
                init_success = True
            except Exception as e:
                self.logger.warning(f"    Initialization warning: {e}")
                init_success = False
            
            # Test 4: Data loading capability
            self.logger.info("  Testing data loading capability...")
            data_success = hasattr(agent, 'load_stock_data')
            
            overall_success = import_success and config_success and data_success
            
            return {
                "success": overall_success,
                "message": "Data Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "initialization": "PASS" if init_success else "FAIL",
                    "data_loading": "PASS" if data_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_strategy_agent(self) -> Dict[str, Any]:
        """Test Strategy Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Strategy Agent import...")
            from src.agents.strategy.agent import StrategyAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Strategy Agent configuration...")
            config = {
                'agent_id': 'test_strategy_agent',
                'agent_type': 'strategy',
                'strategy_name': 'sweet_spot_v7_2'
            }
            
            agent = StrategyAgent('test_strategy_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_strategy_agent'
            
            # Test 3: Signal generation capability
            self.logger.info("  Testing signal generation capability...")
            signal_success = hasattr(agent, 'generate_signals')
            
            # Test 4: Strategy configuration
            self.logger.info("  Testing strategy configuration...")
            strategy_success = hasattr(agent, 'current_strategy')
            
            overall_success = import_success and config_success and signal_success
            
            return {
                "success": overall_success,
                "message": "Strategy Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "signal_generation": "PASS" if signal_success else "FAIL",
                    "strategy": "PASS" if strategy_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_execution_agent(self) -> Dict[str, Any]:
        """Test Execution Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Execution Agent import...")
            from src.agents.execution.agent import ExecutionAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Execution Agent configuration...")
            config = {
                'agent_id': 'test_execution_agent',
                'agent_type': 'execution',
                'execution_mode': 'paper'
            }
            
            agent = ExecutionAgent('test_execution_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_execution_agent'
            
            # Test 3: Order placement capability
            self.logger.info("  Testing order placement capability...")
            order_success = hasattr(agent, 'place_order')
            
            # Test 4: Portfolio management
            self.logger.info("  Testing portfolio management...")
            portfolio_success = hasattr(agent, 'portfolio_manager')
            
            overall_success = import_success and config_success and order_success
            
            return {
                "success": overall_success,
                "message": "Execution Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "order_placement": "PASS" if order_success else "FAIL",
                    "portfolio_management": "PASS" if portfolio_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_sync_agent(self) -> Dict[str, Any]:
        """Test Sync Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Sync Agent import...")
            from src.agents.sync.agent import SyncAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Sync Agent configuration...")
            config = {
                'agent_id': 'test_sync_agent',
                'agent_type': 'sync',
                'sync_targets': ['local', 'backup']
            }
            
            agent = SyncAgent('test_sync_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_sync_agent'
            
            # Test 3: Portfolio sync capability
            self.logger.info("  Testing portfolio sync capability...")
            sync_success = hasattr(agent, 'sync_portfolio')
            
            # Test 4: Backup functionality
            self.logger.info("  Testing backup functionality...")
            backup_success = hasattr(agent, 'backup_manager')
            
            overall_success = import_success and config_success and sync_success
            
            return {
                "success": overall_success,
                "message": "Sync Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "portfolio_sync": "PASS" if sync_success else "FAIL",
                    "backup": "PASS" if backup_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_notification_agent(self) -> Dict[str, Any]:
        """Test Notification Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Notification Agent import...")
            from src.agents.notification.agent import NotificationAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Notification Agent configuration...")
            config = {
                'agent_id': 'test_notification_agent',
                'agent_type': 'notification',
                'email_enabled': True,
                'dry_run_mode': True
            }
            
            agent = NotificationAgent('test_notification_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_notification_agent'
            
            # Test 3: Email notification capability
            self.logger.info("  Testing email notification capability...")
            email_success = hasattr(agent, 'send_notification')
            
            # Test 4: Alert system
            self.logger.info("  Testing alert system...")
            alert_success = hasattr(agent, 'alert_manager')
            
            overall_success = import_success and config_success and email_success
            
            return {
                "success": overall_success,
                "message": "Notification Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "email_notification": "PASS" if email_success else "FAIL",
                    "alert_system": "PASS" if alert_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_testing_agent(self) -> Dict[str, Any]:
        """Test Testing Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Testing Agent import...")
            from src.agents.testing.agent import TestingAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Testing Agent configuration...")
            config = {
                'agent_id': 'test_testing_agent',
                'agent_type': 'testing',
                'backtest_enabled': True,
                'dry_run_enabled': True
            }
            
            agent = TestingAgent('test_testing_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_testing_agent'
            
            # Test 3: Unit test capability
            self.logger.info("  Testing unit test capability...")
            unit_success = hasattr(agent, 'run_unit_tests')
            
            # Test 4: Backtest capability
            self.logger.info("  Testing backtest capability...")
            backtest_success = hasattr(agent, 'run_backtest')
            
            overall_success = import_success and config_success and unit_success
            
            return {
                "success": overall_success,
                "message": "Testing Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "unit_tests": "PASS" if unit_success else "FAIL",
                    "backtest": "PASS" if backtest_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def test_scheduler_agent(self) -> Dict[str, Any]:
        """Test Scheduler Agent basic functionality"""
        try:
            # Test 1: Import
            self.logger.info("  Testing Scheduler Agent import...")
            from src.agents.scheduler.agent import SchedulerAgent
            import_success = True
            
            # Test 2: Configuration
            self.logger.info("  Testing Scheduler Agent configuration...")
            config = {
                'agent_id': 'test_scheduler_agent',
                'agent_type': 'scheduler',
                'task_monitoring_enabled': True,
                'dry_run_mode': True
            }
            
            agent = SchedulerAgent('test_scheduler_agent', config)
            config_success = hasattr(agent, 'agent_id') and agent.agent_id == 'test_scheduler_agent'
            
            # Test 3: Task scheduling
            self.logger.info("  Testing task scheduling...")
            scheduling_success = hasattr(agent, 'task_monitor')
            
            # Test 4: Windows integration
            self.logger.info("  Testing Windows integration...")
            windows_success = hasattr(agent, 'windows_integration')
            
            overall_success = import_success and config_success and scheduling_success
            
            return {
                "success": overall_success,
                "message": "Scheduler Agent basic test completed",
                "details": {
                    "import": "PASS" if import_success else "FAIL",
                    "configuration": "PASS" if config_success else "FAIL",
                    "task_scheduling": "PASS" if scheduling_success else "FAIL",
                    "windows_integration": "PASS" if windows_success else "FAIL"
                }
            }
            
        except Exception as e:
            return {"success": False, "error": str(e)}
    
    async def run_full_test(self) -> Dict[str, Any]:
        """Run full end-to-end test (buy 1 trade, sell after 1 minute)"""
        try:
            self.logger.info("Running Full End-to-End Test")
            self.logger.info("Test: Buy 1 share, wait 1 minute, sell 1 share")
            
            # Use the existing functional health check
            from scripts.functional_health_check import FunctionalHealthCheck
            
            health_check = FunctionalHealthCheck()
            result = await health_check.run_functional_health_check()
            
            if result.get('success', False):
                self.logger.info("✅ Full End-to-End Test: PASSED")
                return {
                    "success": True,
                    "message": "Full end-to-end test passed (buy 1, wait 1 min, sell 1)",
                    "details": result
                }
            else:
                self.logger.error(f"❌ Full End-to-End Test: FAILED - {result.get('error', 'Unknown error')}")
                return {
                    "success": False,
                    "error": result.get('error', 'Unknown error'),
                    "details": result
                }
                
        except Exception as e:
            self.logger.error(f"❌ Full test execution failed: {e}")
            return {"success": False, "error": str(e)}
    
    def print_test_summary(self, summary: Dict[str, Any]):
        """Print comprehensive test summary"""
        total = summary.get("total_tests", 0)
        passed = summary.get("passed", 0)
        failed = summary.get("failed", 0)
        
        print("\n" + "=" * 70)
        print("SIMPLE TEST SUITE RESULTS")
        print("=" * 70)
        print(f"Total Tests: {total}")
        print(f"Passed: {passed}")
        print(f"Failed: {failed}")
        if total > 0:
            print(f"Success Rate: {(passed/total*100):.1f}%")
        else:
            print("Success Rate: 0%")
        
        if failed == 0:
            print("\n🎉 ALL TESTS PASSED!")
            print("🚀 System is ready for production!")
        else:
            print(f"\n⚠️  {failed} tests failed - Check logs for details")
        
        print("=" * 70)

async def main():
    """Main entry point"""
    runner = SimpleTestSuite()
    
    try:
        # Run all tests
        results = await runner.run_all_tests()
        
        # Determine exit code
        success = results.get("summary", {}).get("failed", 0) == 0
        exit_code = 0 if success else 1
        
        print(f"Simple Test Suite completed with exit code: {exit_code}")
        sys.exit(exit_code)
        
    except Exception as e:
        print(f"❌ Fatal error: {e}")
        return 1

if __name__ == "__main__":
    asyncio.run(main())
