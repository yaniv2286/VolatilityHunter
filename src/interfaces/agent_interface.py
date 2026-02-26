"""
Agent Interface - Base interface for all VolatilityHunter agents
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Optional
from enum import Enum
from dataclasses import dataclass
import logging

class AgentStatus(Enum):
    """Agent status enumeration"""
    INITIALIZING = "initializing"
    READY = "ready"
    RUNNING = "running"
    PAUSED = "paused"
    ERROR = "error"
    SHUTDOWN = "shutdown"

class MessageType(Enum):
    """Message type enumeration"""
    DATA_REQUEST = "data_request"
    DATA_RESPONSE = "data_response"
    SIGNAL_REQUEST = "signal_request"
    SIGNAL_RESPONSE = "signal_response"
    EXECUTION_REQUEST = "execution_request"
    EXECUTION_RESPONSE = "execution_response"
    SYNC_REQUEST = "sync_request"
    SYNC_RESPONSE = "sync_response"
    NOTIFICATION_REQUEST = "notification_request"
    NOTIFICATION_RESPONSE = "notification_response"
    TEST_REQUEST = "test_request"
    TEST_RESPONSE = "test_response"
    HEALTH_CHECK = "health_check"
    ERROR = "error"
    SHUTDOWN = "shutdown"

@dataclass
class Message:
    """Message structure for agent communication"""
    message_type: MessageType
    sender: str
    recipient: str
    data: Dict[str, Any]
    timestamp: str
    correlation_id: Optional[str] = None
    requires_response: bool = False

@dataclass
class HealthStatus:
    """Health status for agents"""
    agent_id: str
    status: AgentStatus
    last_check: str
    cpu_usage: float
    memory_usage: float
    error_count: int
    last_error: Optional[str] = None
    uptime: float = 0.0

class AgentInterface(ABC):
    """Base interface for all agents"""
    
    def __init__(self, agent_id: str, config: Dict[str, Any]):
        self.agent_id = agent_id
        self.config = config
        self.status = AgentStatus.INITIALIZING
        self.logger = logging.getLogger(f"agent.{agent_id}")
        self.message_handlers = {}
        self.start_time = None
        self.error_count = 0
        self.last_error = None
        
    @abstractmethod
    async def initialize(self) -> bool:
        """Initialize the agent"""
        pass
    
    @abstractmethod
    async def start(self) -> bool:
        """Start the agent"""
        pass
    
    @abstractmethod
    async def stop(self) -> bool:
        """Stop the agent"""
        pass
    
    @abstractmethod
    async def process_message(self, message: Message) -> Optional[Message]:
        """Process incoming message"""
        pass
    
    @abstractmethod
    async def health_check(self) -> HealthStatus:
        """Perform health check"""
        pass
    
    @abstractmethod
    def get_capabilities(self) -> List[str]:
        """Get agent capabilities"""
        pass
    
    def register_message_handler(self, message_type: MessageType, handler):
        """Register message handler"""
        self.message_handlers[message_type] = handler
    
    async def handle_message(self, message: Message) -> Optional[Message]:
        """Handle incoming message with registered handler"""
        handler = self.message_handlers.get(message.message_type)
        if handler:
            try:
                return await handler(message)
            except Exception as e:
                self.logger.error(f"Error handling message {message.message_type}: {e}")
                self.error_count += 1
                self.last_error = str(e)
                return Message(
                    message_type=MessageType.ERROR,
                    sender=self.agent_id,
                    recipient=message.sender,
                    data={"error": str(e), "original_message": message},
                    timestamp=self._get_timestamp(),
                    correlation_id=message.correlation_id
                )
        else:
            self.logger.warning(f"No handler for message type: {message.message_type}")
            return None
    
    def _get_timestamp(self) -> str:
        """Get current timestamp"""
        from datetime import datetime
        return datetime.now().isoformat()
    
    def update_status(self, status: AgentStatus):
        """Update agent status"""
        self.status = status
        self.logger.info(f"Agent {self.agent_id} status changed to {status.value}")
    
    def get_agent_info(self) -> Dict[str, Any]:
        """Get agent information"""
        return {
            "agent_id": self.agent_id,
            "status": self.status.value,
            "config": self.config,
            "capabilities": self.get_capabilities(),
            "error_count": self.error_count,
            "last_error": self.last_error
        }
