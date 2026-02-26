"""
Orchestrator - Main system orchestrator for agent-based architecture
"""

import asyncio
import logging
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import json
import traceback

from .interfaces.agent_interface import AgentInterface, AgentStatus, Message, MessageType, HealthStatus
from .messaging.message_bus import MessageBus
from .factories.agent_factory import AgentFactory
from .factories.message_factory import MessageFactory
from .workflows.workflow_manager import WorkflowManager

class Orchestrator:
    """Main system orchestrator"""
    
    def __init__(self, config: Dict[str, Any]):
        self.logger = logging.getLogger("orchestrator")
        self.config = config
        
        # Core components
        self.message_bus = MessageBus()
        self.agent_factory = AgentFactory()
        self.message_factory = MessageFactory()
        self.workflow_manager = WorkflowManager()
        
        # Agents
        self.agents: Dict[str, AgentInterface] = {}
        
        # System state
        self.running = False
        self.start_time = None
        self.shutdown_requested = False
        self.error_count = 0
        self.last_error = None
        
        # Health monitoring
        self.health_check_interval = config.get("health_check_interval", 60)
        self.last_health_check = None
        
        # Event loop
        self.loop = asyncio.get_event_loop()
        
    async def initialize(self) -> bool:
        """Initialize orchestrator and all agents"""
        try:
            self.logger.info("Initializing orchestrator...")
            
            # Start message bus
            await self.message_bus.start()
            
            # Load and create agents
            await self._load_agents()
            
            # Initialize workflow manager
            await self.workflow_manager.initialize(self.message_bus)
            
            # Register orchestrator message handlers
            self._register_message_handlers()
            
            self.logger.info("Orchestrator initialized successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error initializing orchestrator: {e}")
            self.error_count += 1
            self.last_error = str(e)
            return False
            
    async def start(self) -> bool:
        """Start all agents and begin orchestration"""
        try:
            self.logger.info("Starting orchestrator...")
            self.running = True
            self.start_time = datetime.now()
            
            # Start all agents
            for agent_id, agent in self.agents.items():
                if not await agent.start():
                    self.logger.error(f"Failed to start agent: {agent_id}")
                    return False
                    
            # Start workflow manager
            await self.workflow_manager.start()
            
            # Start health monitoring
            asyncio.create_task(self._health_monitoring_loop())
            
            # Start message processing
            asyncio.create_task(self._message_processing_loop())
            
            self.logger.info("Orchestrator started successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error starting orchestrator: {e}")
            self.error_count += 1
            self.last_error = str(e)
            return False
            
    async def stop(self) -> bool:
        """Stop all agents and shutdown orchestrator"""
        try:
            self.logger.info("Stopping orchestrator...")
            self.shutdown_requested = True
            
            # Stop workflow manager
            await self.workflow_manager.stop()
            
            # Stop all agents
            for agent_id, agent in self.agents.items():
                await agent.stop()
                
            # Stop message bus
            await self.message_bus.stop()
            
            self.running = False
            self.logger.info("Orchestrator stopped successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Error stopping orchestrator: {e}")
            return False
            
    async def add_agent(self, agent: AgentInterface) -> bool:
        """Add agent to orchestrator"""
        try:
            # Subscribe agent to message bus
            message_types = agent.get_capabilities()
            # Convert string capabilities to MessageType enums
            from src.interfaces.agent_interface import MessageType
            enum_message_types = []
            for msg_type in message_types:
                try:
                    enum_message_types.append(MessageType(msg_type))
                except ValueError:
                    # Skip invalid message types
                    self.logger.warning(f"Invalid message type: {msg_type}")
                    continue
            
            if enum_message_types:
                await self.message_bus.subscribe(agent.agent_id, enum_message_types)
            
            # Store agent
            self.agents[agent.agent_id] = agent
            self.logger.info(f"Added agent: {agent.agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error adding agent {agent.agent_id}: {e}")
            return False
            
    async def remove_agent(self, agent_id: str) -> bool:
        """Remove agent from orchestrator"""
        try:
            if agent_id not in self.agents:
                return False
                
            agent = self.agents[agent_id]
            
            # Stop agent
            await agent.stop()
            
            # Unsubscribe from message bus
            message_types = agent.get_capabilities()
            await self.message_bus.unsubscribe(agent_id, message_types)
            
            # Remove agent
            del self.agents[agent_id]
            
            self.logger.info(f"Removed agent: {agent_id}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error removing agent {agent_id}: {e}")
            return False
            
    async def send_message(self, message: Message) -> Optional[Message]:
        """Send message through orchestrator"""
        try:
            if not self.running:
                self.logger.warning("Orchestrator not running")
                return None
                
            return await self.message_bus.send_message(message)
            
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            return None
    
    async def publish_message(self, target_agent: str, message_type: str, data: Dict[str, Any]) -> bool:
        """Publish message to specific agent"""
        try:
            if not self.running:
                self.logger.warning("Orchestrator not running")
                return False
                
            # Create message for specific agent
            from src.interfaces.agent_interface import Message, MessageType
            from datetime import datetime
            import uuid
            
            # Convert string to MessageType enum
            msg_type = MessageType(message_type)
            
            message = Message(
                message_type=msg_type,
                sender="orchestrator",
                recipient=target_agent,
                data=data,
                timestamp=datetime.now().isoformat(),
                correlation_id=str(uuid.uuid4())
            )
            
            # Send message
            result = await self.message_bus.send_message(message)
            return result is not None
            
        except Exception as e:
            self.logger.error(f"Error publishing message to {target_agent}: {e}")
            return False
            
    async def broadcast_message(self, message_type: MessageType, data: Dict[str, Any]) -> bool:
        """Broadcast message to all agents"""
        try:
            message = self.message_factory.create_broadcast_message(
                sender="orchestrator",
                message_type=message_type,
                data=data
            )
            
            return await self.message_bus.publish(message)
            
        except Exception as e:
            self.logger.error(f"Error broadcasting message: {e}")
            return False
            
    async def get_system_status(self) -> Dict[str, Any]:
        """Get overall system status"""
        try:
            agent_statuses = {}
            for agent_id, agent in self.agents.items():
                health = await agent.health_check()
                agent_statuses[agent_id] = {
                    "status": health.status.value,
                    "last_check": health.last_check,
                    "error_count": health.error_count,
                    "uptime": health.uptime
                }
                
            return {
                "orchestrator": {
                    "running": self.running,
                    "start_time": self.start_time.isoformat() if self.start_time else None,
                    "uptime": (datetime.now() - self.start_time).total_seconds() if self.start_time else 0,
                    "error_count": self.error_count,
                    "last_error": self.last_error
                },
                "agents": agent_statuses,
                "message_bus": self.message_bus.get_statistics(),
                "workflow_manager": await self.workflow_manager.get_status()
            }
            
        except Exception as e:
            self.logger.error(f"Error getting system status: {e}")
            return {"error": str(e)}
            
    async def _load_agents(self) -> bool:
        """Load and create all agents"""
        try:
            # Load agent configurations
            agent_configs = self.agent_factory.load_agent_configs()
            
            # Create agents
            self.agents = self.agent_factory.create_all_agents(agent_configs)
            
            # Initialize agents
            for agent_id, agent in self.agents.items():
                if not await agent.initialize():
                    self.logger.error(f"Failed to initialize agent: {agent_id}")
                    return False
                    
                # Add to orchestrator
                await self.add_agent(agent)
                
            self.logger.info(f"Loaded {len(self.agents)} agents")
            return True
            
        except Exception as e:
            self.logger.error(f"Error loading agents: {e}")
            return False
            
    def _register_message_handlers(self):
        """Register orchestrator message handlers"""
        # This would be implemented based on specific message types
        pass
        
    async def _message_processing_loop(self):
        """Main message processing loop"""
        while self.running and not self.shutdown_requested:
            try:
                # Process messages for all agents
                for agent_id, agent in self.agents.items():
                    messages = await self.message_bus.get_messages(agent_id)
                    for message in messages:
                        response = await agent.handle_message(message)
                        if response:
                            await self.message_bus.publish(response)
                            
                await asyncio.sleep(0.1)  # Small delay to prevent busy loop
                
            except Exception as e:
                self.logger.error(f"Error in message processing loop: {e}")
                self.error_count += 1
                self.last_error = str(e)
                await asyncio.sleep(1)
                
    async def _health_monitoring_loop(self):
        """Health monitoring loop"""
        while self.running and not self.shutdown_requested:
            try:
                # Perform health checks
                await self._perform_health_checks()
                
                # Wait for next check
                await asyncio.sleep(self.health_check_interval)
                
            except Exception as e:
                self.logger.error(f"Error in health monitoring loop: {e}")
                await asyncio.sleep(self.health_check_interval)
                
    async def _perform_health_checks(self):
        """Perform health checks on all agents"""
        try:
            for agent_id, agent in self.agents.items():
                health = await agent.health_check()
                
                # Log any issues
                if health.status == AgentStatus.ERROR:
                    self.logger.error(f"Agent {agent_id} in error state: {health.last_error}")
                    
                # Update orchestrator metrics
                self.last_health_check = datetime.now().isoformat()
                
        except Exception as e:
            self.logger.error(f"Error performing health checks: {e}")
            
    def get_agent(self, agent_id: str) -> Optional[AgentInterface]:
        """Get agent by ID"""
        return self.agents.get(agent_id)
        
    def list_agents(self) -> List[str]:
        """List all agent IDs"""
        return list(self.agents.keys())
        
    def get_uptime(self) -> float:
        """Get orchestrator uptime"""
        if self.start_time:
            return (datetime.now() - self.start_time).total_seconds()
        return 0.0
    
    async def get_system_health(self) -> Dict[str, Any]:
        """Get system health status"""
        try:
            agent_health = {}
            for agent_id, agent in self.agents.items():
                agent_health[agent_id] = {
                    "status": "running" if hasattr(agent, 'agent_id') else "error",
                    "last_heartbeat": datetime.now().isoformat()
                }
            
            return {
                "overall_health": "healthy",
                "agents": agent_health,
                "message_bus": "active",
                "timestamp": datetime.now().isoformat()
            }
        except Exception as e:
            return {
                "overall_health": "error",
                "error": str(e),
                "timestamp": datetime.now().isoformat()
            }
