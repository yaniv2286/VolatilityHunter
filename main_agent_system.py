"""
Main Agent System - New main entry point for agent-based architecture - V10.0
"""

import asyncio
import logging
import argparse
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional

# Add src to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.orchestrator import Orchestrator
from src.config.system_config import SystemConfigManager
from src.config.agent_config import ConfigManager

class MainAgentSystem:
    """Main agent system entry point"""
    
    def __init__(self):
        self.logger = logging.getLogger("main_agent_system")
        self.orchestrator: Optional[Orchestrator] = None
        self.system_config_manager = SystemConfigManager()
        self.config_manager = ConfigManager()
        self.running = False
        
    async def initialize(self, config_path: str = None) -> bool:
        """Initialize the agent system"""
        try:
            self.logger.info("Initializing VolatilityHunter Agent System...")
            
            # Load system configuration
            system_config = self.system_config_manager.load_system_config(config_path)
            if not self.system_config_manager.validate_config():
                self.logger.error("Invalid system configuration")
                return False
                
            # Create directories
            if not self.system_config_manager.create_directories():
                self.logger.error("Failed to create required directories")
                return False
                
            # Initialize orchestrator
            orchestrator_config = {
                "config_manager": self.config_manager,
                "health_check_interval": system_config.get("orchestrator", {}).get("health_check_interval", 60),
                "max_concurrent_workflows": system_config.get("orchestrator", {}).get("max_concurrent_workflows", 5),
                "workflow_timeout": system_config.get("orchestrator", {}).get("workflow_timeout", 600)
            }
            
            self.orchestrator = Orchestrator(orchestrator_config)
            
            # Register agent types
            self._register_agent_types()
            
            # Initialize orchestrator
            if not await self.orchestrator.initialize():
                self.logger.error("Failed to initialize orchestrator")
                return False
                
            self.logger.info("Agent system initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing agent system: {e}")
            return False
            
    def _register_agent_types(self):
        """Register all agent types with the factory"""
        try:
            from src.agents.data import DataAgent
            from src.agents.strategy import StrategyAgent
            from src.agents.execution import ExecutionAgent
            from src.agents.sync import SyncAgent
            from src.agents.notification import NotificationAgent
            from src.agents.testing import TestingAgent
            
            # Register agent types
            self.orchestrator.agent_factory.register_agent("data", DataAgent)
            self.orchestrator.agent_factory.register_agent("strategy", StrategyAgent)
            self.orchestrator.agent_factory.register_agent("execution", ExecutionAgent)
            self.orchestrator.agent_factory.register_agent("sync", SyncAgent)
            self.orchestrator.agent_factory.register_agent("notification", NotificationAgent)
            self.orchestrator.agent_factory.register_agent("testing", TestingAgent)
            
            self.logger.info("Registered all agent types")
            
        except Exception as e:
            self.logger.error(f"Error registering agent types: {e}")
            
    async def start(self) -> bool:
        """Start the agent system"""
        try:
            self.logger.info("Starting VolatilityHunter Agent System...")
            
            if not self.orchestrator:
                self.logger.error("Orchestrator not initialized")
                return False
                
            # Start orchestrator
            if not await self.orchestrator.start():
                self.logger.error("Failed to start orchestrator")
                return False
                
            self.running = True
            self.logger.info("Agent system started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting agent system: {e}")
            return False
            
    async def stop(self) -> bool:
        """Stop the agent system"""
        try:
            self.logger.info("Stopping VolatilityHunter Agent System...")
            
            if self.orchestrator:
                await self.orchestrator.stop()
                
            self.running = False
            self.logger.info("Agent system stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping agent system: {e}")
            return False
            
    async def run_workflow(self, workflow_name: str, parameters: Dict[str, Any] = None) -> str:
        """Run a specific workflow"""
        try:
            if not self.orchestrator:
                raise ValueError("Orchestrator not initialized")
                
            from src.workflows.workflow_manager import WorkflowManager
            workflow_manager = WorkflowManager()
            await workflow_manager.initialize(self.orchestrator.message_bus)
            
            workflow_id = await workflow_manager.execute_workflow(workflow_name, parameters or {})
            return workflow_id
            
        except Exception as e:
            self.logger.error(f"Error running workflow {workflow_name}: {e}")
            raise
            
    async def get_system_status(self) -> Dict[str, Any]:
        """Get system status"""
        try:
            if self.orchestrator:
                return await self.orchestrator.get_system_status()
            else:
                return {"error": "System not initialized"}
                
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
            
    async def shutdown(self):
        """Shutdown the system"""
        try:
            await self.stop()
            self.logger.info("VolatilityHunter Agent System shutdown complete")
            
        except Exception as e:
            self.logger.error(f"Error during shutdown: {e}")

async def main():
    """Main entry point"""
    try:
        # Setup logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler('logs/agent_system.log'),
                logging.StreamHandler()
            ]
        )
        
        logger = logging.getLogger("main")
        logger.info("VolatilityHunter Agent System Starting...")
        
        # Parse command line arguments
        parser = argparse.ArgumentParser(description='VolatilityHunter Agent System')
        parser.add_argument('--config', type=str, help='Configuration file path')
        parser.add_argument('--workflow', type=str, help='Workflow to run')
        parser.add_argument('--mode', type=str, default='live', help='Execution mode')
        args = parser.parse_args()
        
        # Create and initialize system
        system = MainAgentSystem()
        
        # Initialize
        if not await system.initialize(args.config):
            logger.error("Failed to initialize system")
            return 1
            
        # Start system
        if not await system.start():
            logger.error("Failed to start system")
            return 1
            
        try:
            # Run workflow if specified
            if args.workflow:
                logger.info(f"Running workflow: {args.workflow}")
                workflow_id = await system.run_workflow(args.workflow)
                logger.info(f"Workflow started with ID: {workflow_id}")
                
                # Wait for workflow completion
                # This would implement actual workflow monitoring
                await asyncio.sleep(60)
                
            else:
                # Run default daily trading workflow
                logger.info("Running daily trading workflow")
                workflow_id = await system.run_workflow("daily_trading")
                logger.info(f"Daily trading workflow started with ID: {workflow_id}")
                
                # Wait for completion
                await asyncio.sleep(300)  # 5 minutes
                
        except KeyboardInterrupt:
            logger.info("Received interrupt signal")
            
        except Exception as e:
            logger.error(f"Error during execution: {e}")
            return 1
            
        finally:
            # Shutdown
            await system.shutdown()
            
        return 0
        
    except Exception as e:
        logging.getLogger("main").error(f"Fatal error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
