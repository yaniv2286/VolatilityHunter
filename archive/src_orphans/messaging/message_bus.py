"""
Message Bus - Core message bus implementation for agent communication
"""

import asyncio
import logging
from typing import Dict, List, Optional, Callable
from collections import defaultdict, deque
from datetime import datetime
import json
import uuid
from ..interfaces.message_interface import MessageBusInterface, TopicManagerInterface
from ..interfaces.agent_interface import Message, MessageType

class MessageBus(MessageBusInterface):
    """Core message bus implementation"""
    
    def __init__(self, max_history: int = 1000):
        self.logger = logging.getLogger("message_bus")
        self.max_history = max_history
        
        # Agent subscriptions
        self.subscriptions: Dict[MessageType, List[str]] = defaultdict(list)
        self.agent_subscriptions: Dict[str, List[MessageType]] = defaultdict(list)
        
        # Message queues
        self.message_queues: Dict[str, deque] = defaultdict(lambda: deque(maxlen=100))
        self.message_history: deque = deque(maxlen=max_history)
        
        # Message handlers
        self.message_handlers: Dict[str, Callable] = {}
        
        # Statistics
        self.message_count = 0
        self.error_count = 0
        
        # Event loop
        self.loop = asyncio.get_event_loop()
        self.running = False
        
    async def start(self):
        """Start message bus"""
        self.running = True
        self.logger.info("Message bus started")
        
    async def stop(self):
        """Stop message bus"""
        self.running = False
        self.logger.info("Message bus stopped")
        
    async def publish(self, message: Message) -> bool:
        """Publish message to bus"""
        try:
            if not self.running:
                self.logger.warning("Message bus not running")
                return False
                
            # Validate message
            if not self._validate_message(message):
                self.error_count += 1
                return False
                
            # Add timestamp if not present
            if not message.timestamp:
                message.timestamp = datetime.now().isoformat()
                
            # Add correlation ID if not present
            if not message.correlation_id:
                message.correlation_id = str(uuid.uuid4())
                
            # Store in history
            self.message_history.append(message)
            self.message_count += 1
            
            # Route to subscribers
            await self._route_message(message)
            
            self.logger.debug(f"Published message {message.message_type} from {message.sender}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error publishing message: {e}")
            self.error_count += 1
            return False
            
    async def subscribe(self, agent_id: str, message_types: List[MessageType]) -> bool:
        """Subscribe to message types"""
        try:
            for message_type in message_types:
                if agent_id not in self.subscriptions[message_type]:
                    self.subscriptions[message_type].append(agent_id)
                    self.agent_subscriptions[agent_id].append(message_type)
                    
            self.logger.info(f"Agent {agent_id} subscribed to {[mt.value for mt in message_types]}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error subscribing agent {agent_id}: {e}")
            return False
            
    async def unsubscribe(self, agent_id: str, message_types: List[MessageType]) -> bool:
        """Unsubscribe from message types"""
        try:
            for message_type in message_types:
                if agent_id in self.subscriptions[message_type]:
                    self.subscriptions[message_type].remove(agent_id)
                    self.agent_subscriptions[agent_id].remove(message_type)
                    
            self.logger.info(f"Agent {agent_id} unsubscribed from {[mt.value for mt in message_types]}")
            return True
            
        except Exception as e:
            self.logger.error(f"Error unsubscribing agent {agent_id}: {e}")
            return False
            
    async def send_message(self, message: Message) -> Optional[Message]:
        """Send message to specific recipient"""
        try:
            if not self.running:
                self.logger.warning("Message bus not running")
                return None
                
            # Validate message
            if not self._validate_message(message):
                self.error_count += 1
                return None
                
            # Add timestamp and correlation ID
            if not message.timestamp:
                message.timestamp = datetime.now().isoformat()
            if not message.correlation_id:
                message.correlation_id = str(uuid.uuid4())
                
            # Store in history
            self.message_history.append(message)
            self.message_count += 1
            
            # Send to specific recipient
            if message.recipient in self.message_queues:
                self.message_queues[message.recipient].append(message)
                self.logger.debug(f"Sent message {message.message_type} to {message.recipient}")
                return message
            else:
                self.logger.warning(f"Recipient {message.recipient} not found")
                return None
                
        except Exception as e:
            self.logger.error(f"Error sending message: {e}")
            self.error_count += 1
            return None
            
    def get_message_history(self, agent_id: str, limit: int = 100) -> List[Message]:
        """Get message history for agent"""
        try:
            # Filter messages for agent
            agent_messages = []
            count = 0
            
            # Check from newest to oldest
            for message in reversed(self.message_history):
                if message.sender == agent_id or message.recipient == agent_id:
                    agent_messages.append(message)
                    count += 1
                    if count >= limit:
                        break
                        
            return list(reversed(agent_messages))
            
        except Exception as e:
            self.logger.error(f"Error getting message history for {agent_id}: {e}")
            return []
            
    async def get_messages(self, agent_id: str) -> List[Message]:
        """Get pending messages for agent"""
        try:
            messages = list(self.message_queues[agent_id])
            self.message_queues[agent_id].clear()
            return messages
            
        except Exception as e:
            self.logger.error(f"Error getting messages for {agent_id}: {e}")
            return []
            
    async def _route_message(self, message: Message):
        """Route message to subscribers"""
        try:
            # Get subscribers for message type
            subscribers = self.subscriptions.get(message.message_type, [])
            
            # Send to all subscribers
            for subscriber in subscribers:
                if subscriber != message.sender:  # Don't send back to sender
                    self.message_queues[subscriber].append(message)
                    
        except Exception as e:
            self.logger.error(f"Error routing message: {e}")
            self.error_count += 1
            
    def _validate_message(self, message: Message) -> bool:
        """Validate message structure"""
        try:
            # Check required fields
            if not message.message_type:
                return False
            if not message.sender:
                return False
            if not message.recipient:
                return False
            if not isinstance(message.data, dict):
                return False
                
            return True
            
        except Exception:
            return False
            
    def get_statistics(self) -> Dict[str, any]:
        """Get message bus statistics"""
        return {
            "message_count": self.message_count,
            "error_count": self.error_count,
            "active_subscriptions": len(self.subscriptions),
            "connected_agents": len(self.agent_subscriptions),
            "running": self.running,
            "history_size": len(self.message_history)
        }
        
    def get_subscribers(self, message_type: MessageType) -> List[str]:
        """Get subscribers for message type"""
        return self.subscriptions.get(message_type, []).copy()
        
    def get_agent_subscriptions(self, agent_id: str) -> List[MessageType]:
        """Get agent's subscriptions"""
        return self.agent_subscriptions.get(agent_id, []).copy()
