#!/usr/bin/env python3
"""
Portfolio Synchronization Script
Syncs TWS portfolio with local portfolio file
"""

import asyncio
import sys
import os
import json
import logging
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.orchestrator import Orchestrator
from src.config.system_config import SystemConfigManager
from src.config.agent_config import ConfigManager
from src.interfaces.agent_interface import MessageType, Message

async def _register_agent_types(orchestrator):
    """Register all agent types with the factory"""
    try:
        from src.agents.data import DataAgent
        from src.agents.strategy import StrategyAgent
        from src.agents.execution import ExecutionAgent
        from src.agents.sync import SyncAgent
        from src.agents.notification import NotificationAgent
        from src.agents.testing import TestingAgent
        
        # Register agent types
        orchestrator.agent_factory.register_agent("data", DataAgent)
        orchestrator.agent_factory.register_agent("strategy", StrategyAgent)
        orchestrator.agent_factory.register_agent("execution", ExecutionAgent)
        orchestrator.agent_factory.register_agent("sync", SyncAgent)
        orchestrator.agent_factory.register_agent("notification", NotificationAgent)
        orchestrator.agent_factory.register_agent("testing", TestingAgent)
        
    except Exception as e:
        logger = logging.getLogger("portfolio_sync")
        logger.error(f"Error registering agent types: {e}")

async def run_portfolio_sync():
    """Run portfolio synchronization"""
    
    # Setup logging
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('logs/portfolio_sync.log'),
            logging.StreamHandler()
        ]
    )
    
    logger = logging.getLogger("portfolio_sync")
    logger.info("Starting Portfolio Synchronization...")
    
    try:
        # Initialize system
        system_config_manager = SystemConfigManager()
        config_manager = ConfigManager()
        
        # Create orchestrator
        orchestrator_config = {
            "config_manager": config_manager,
            "health_check_interval": 60,
            "max_concurrent_workflows": 5,
            "workflow_timeout": 600
        }
        
        orchestrator = Orchestrator(orchestrator_config)
        
        # Register agent types
        await _register_agent_types(orchestrator)
        
        # Initialize orchestrator
        if not await orchestrator.initialize():
            logger.error("Failed to initialize orchestrator")
            return False
            
        # Start orchestrator
        if not await orchestrator.start():
            logger.error("Failed to start orchestrator")
            return False
            
        logger.info("Agent system started successfully")
        
        # Get sync agent
        sync_agent = orchestrator.agents.get('sync_agent')
        if not sync_agent:
            logger.error("Sync agent not found")
            return False
            
        logger.info("Sync agent found, starting synchronization...")
        
        # Trigger portfolio sync
        from src.messaging.message_bus import MessageBus
        message_bus = orchestrator.message_bus
        
        # Create sync request
        from datetime import datetime
        sync_message = Message(
            message_type=MessageType.SYNC_REQUEST,
            sender="portfolio_sync_script",
            recipient="sync_agent",
            data={
                "sync_type": "portfolio",
                "target": "both",  # Sync both TWS and local
                "force_sync": True,
                "reconcile": True
            },
            timestamp=datetime.now().isoformat()
        )
        
        # Send sync request
        response = await message_bus.send_message(sync_message)
        
        if response and response.get('success'):
            logger.info("Portfolio synchronization completed successfully")
            
            # Show sync results
            sync_data = response.get('data', {})
            logger.info(f"Sync Results: {sync_data}")
            
            # Check local portfolio file
            portfolio_file = "data/portfolio_sim.json"
            if os.path.exists(portfolio_file):
                with open(portfolio_file, 'r') as f:
                    portfolio = json.load(f)
                    
                logger.info("Local Portfolio State:")
                logger.info(f"  Cash: ${portfolio.get('cash', 0):,.2f}")
                logger.info(f"  Positions: {len(portfolio.get('positions', {}))}")
                logger.info(f"  Total Value: ${portfolio.get('total_value', 0):,.2f}")
                logger.info(f"  Last Updated: {portfolio.get('last_updated', 'Unknown')}")
                
                # Show positions
                positions = portfolio.get('positions', {})
                if positions:
                    logger.info("Current Positions:")
                    for ticker, pos in positions.items():
                        quantity = pos.get('quantity', 0)
                        avg_price = pos.get('avg_price', 0)
                        last_price = pos.get('last_price', 0)
                        value = pos.get('value', 0)
                        pnl = value - (quantity * avg_price)
                        
                        logger.info(f"  {ticker}: {quantity} shares @ ${avg_price:.2f} | "
                                   f"Current: ${last_price:.2f} | Value: ${value:,.2f} | P&L: ${pnl:+,.2f}")
            
        else:
            logger.error(f"Portfolio synchronization failed: {response}")
            return False
            
        # Stop orchestrator
        await orchestrator.stop()
        logger.info("Portfolio synchronization completed")
        return True
        
    except Exception as e:
        logger.error(f"Error during portfolio synchronization: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(run_portfolio_sync())
    sys.exit(0 if success else 1)
