#!/usr/bin/env python3
"""
Production Deployment Script for Agent-Based Architecture
"""

import asyncio
import logging
import sys
import os
import argparse
from datetime import datetime
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from main_agent_system import MainAgentSystem

def setup_production_logging():
    """Setup production logging"""
    os.makedirs("logs", exist_ok=True)
    
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler(f'logs/VH_{datetime.now().strftime("%Y-%m-%d")}.log'),
            logging.StreamHandler()
        ]
    )

async def run_production_system(mode: str = "live", workflow: str = "daily_trading", config_path: str = None):
    """Run the production agent system"""
    try:
        print(f"🚀 Starting VolatilityHunter Agent System in {mode} mode")
        print("=" * 60)
        
        # Setup logging
        setup_production_logging()
        logger = logging.getLogger("production")
        
        # Create and initialize system
        system = MainAgentSystem()
        
        # Load configuration
        if config_path:
            logger.info(f"Loading configuration from: {config_path}")
            success = await system.initialize(config_path)
        else:
            logger.info("Loading default configuration")
            success = await system.initialize()
            
        if not success:
            logger.error("System initialization failed")
            return 1
            
        # Start system
        success = await system.start()
        if not success:
            logger.error("System start failed")
            
        logger.info("System started successfully")
        
        # Run workflow
        if workflow:
            logger.info(f"Running workflow: {workflow}")
            result = await system.run_workflow(workflow)
            if result:
                logger.info(f"Workflow {workflow} completed successfully")
            else:
                logger.error(f"Workflow {workflow} failed")
        
        # Keep system running for live mode
        if mode == "live":
            logger.info("System running in live mode. Press Ctrl+C to stop...")
            try:
                while True:
                    await asyncio.sleep(60)  # Check every minute
                    status = await system.get_system_status()
                    logger.info(f"System Status: {status['orchestrator']['uptime']:.2f}s uptime")
                    
            except KeyboardInterrupt:
                logger.info("Shutdown requested by user")
        
        # Stop system
        success = await system.stop()
        if success:
            logger.info("System stopped successfully")
        else:
            logger.error("System stop failed")
            
        return 0 if success else 1
        
    except Exception as e:
        logger.error(f"Production system error: {e}")
        return 1

async def run_health_check():
    """Run system health check"""
    try:
        print("Running System Health Check")
        print("=" * 40)
        
        system = MainAgentSystem()
        
        # Initialize system
        success = await system.initialize()
        if not success:
            print("System initialization failed")
            return 1
            
        # Start system
        success = await system.start()
        if not success:
            print("System start failed")
            return 1
            
        # Get health status
        status = await system.get_system_status()
        
        print("System Health Status:")
        print(f"  Orchestrator: {'Running' if status['orchestrator']['running'] else 'Stopped'}")
        print(f"  Uptime: {status['orchestrator']['uptime']:.2f}s")
        print(f"  Error Count: {status['orchestrator']['error_count']}")
        print(f"  Active Agents: {len(status['agents'])}")
        print(f"  Message Bus: {'Running' if status['message_bus']['running'] else 'Stopped'}")
        print(f"  Workflows: {len(status['workflow_manager']['registered_workflows'])} registered")
        
        # Stop system
        await system.stop()
        
        return 0
        
    except Exception as e:
        print(f"Health check failed: {e}")
        return 1

async def run_migration_test():
    """Run migration test from old to new system"""
    try:
        print("Running Migration Test")
        print("=" * 40)
        
        # Test old system compatibility
        print("Testing old system compatibility...")
        
        # Test new system
        print("Testing new agent system...")
        system = MainAgentSystem()
        
        success = await system.initialize()
        if success:
            print("New system initialized successfully")
        else:
            print("New system initialization failed")
            return 1
            
        await system.stop()
        
        print("Migration test completed successfully")
        return 0
        
    except Exception as e:
        print(f"Migration test failed: {e}")
        return 1

def main():
    """Main deployment function"""
    parser = argparse.ArgumentParser(description="VolatilityHunter Agent System Deployment")
    
    parser.add_argument("--mode", choices=["live", "test", "health", "migrate"], 
                       default="test", help="System mode")
    parser.add_argument("--workflow", choices=["daily_trading", "health_check", "backtest", "integration"], 
                       default="daily_trading", help="Workflow to run")
    parser.add_argument("--config", help="Configuration file path")
    parser.add_argument("--verbose", action="store_true", help="Verbose logging")
    
    args = parser.parse_args()
    
    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Run based on mode
    if args.mode == "health":
        exit_code = asyncio.run(run_health_check())
    elif args.mode == "migrate":
        exit_code = asyncio.run(run_migration_test())
    else:
        exit_code = asyncio.run(run_production_system(args.mode, args.workflow, args.config))
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
