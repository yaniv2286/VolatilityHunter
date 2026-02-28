"""
Message Interface - Message handling and communication interfaces
"""

from abc import ABC, abstractmethod
from typing import Dict, Any, List, Callable, Optional
from .agent_interface import Message, MessageType
import asyncio
import logging

class MessageHandlerInterface(ABC):
    """Interface for message handlers"""
    
    @abstractmethod
    async def handle(self, message: Message) -> Optional[Message]:
        """Handle incoming message"""
        pass
    
    @abstractmethod
    def can_handle(self, message_type: MessageType) -> bool:
        """Check if handler can handle message type"""
        pass

class MessageBusInterface(ABC):
    """Interface for message bus"""
    
    @abstractmethod
    async def publish(self, message: Message) -> bool:
        """Publish message to bus"""
        pass
    
    @abstractmethod
    async def subscribe(self, agent_id: str, message_types: List[MessageType]) -> bool:
        """Subscribe to message types"""
        pass
    
    @abstractmethod
    async def unsubscribe(self, agent_id: str, message_types: List[MessageType]) -> bool:
        """Unsubscribe from message types"""
        pass
    
    @abstractmethod
    async def send_message(self, message: Message) -> Optional[Message]:
        """Send message to specific recipient"""
        pass
    
    @abstractmethod
    def get_message_history(self, agent_id: str, limit: int = 100) -> List[Message]:
        """Get message history for agent"""
        pass

class TopicManagerInterface(ABC):
    """Interface for topic management"""
    
    @abstractmethod
    def create_topic(self, topic_name: str) -> bool:
        """Create new topic"""
        pass
    
    @abstractmethod
    def delete_topic(self, topic_name: str) -> bool:
        """Delete topic"""
        pass
    
    @abstractmethod
    def list_topics(self) -> List[str]:
        """List all topics"""
        pass
    
    @abstractmethod
    def get_topic_subscribers(self, topic_name: str) -> List[str]:
        """Get subscribers for topic"""
        pass

class MessageFilterInterface(ABC):
    """Interface for message filtering"""
    
    @abstractmethod
    def should_process(self, message: Message) -> bool:
        """Determine if message should be processed"""
        pass
    
    @abstractmethod
    def filter_message(self, message: Message) -> Message:
        """Filter message content"""
        pass

class MessageSerializerInterface(ABC):
    """Interface for message serialization"""
    
    @abstractmethod
    def serialize(self, message: Message) -> str:
        """Serialize message to string"""
        pass
    
    @abstractmethod
    def deserialize(self, data: str) -> Message:
        """Deserialize message from string"""
        pass

class MessageValidatorInterface(ABC):
    """Interface for message validation"""
    
    @abstractmethod
    def validate(self, message: Message) -> bool:
        """Validate message structure and content"""
        pass
    
    @abstractmethod
    def get_validation_errors(self, message: Message) -> List[str]:
        """Get validation errors for message"""
        pass
