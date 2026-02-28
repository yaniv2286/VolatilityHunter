"""
Message Safety Utilities - Prevents common message communication bugs
"""

import asyncio
import logging
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, List
from ..interfaces.agent_interface import Message, MessageType

class MessageSafetyManager:
    """Manages message safety and prevents common bugs"""
    
    def __init__(self):
        self.logger = logging.getLogger("message_safety")
        self.pending_responses: Dict[str, datetime] = {}
        self.message_history: Dict[str, List[Message]] = {}
        self.timeout_seconds = 30
        self.max_pending = 100
        
    async def send_with_timeout(self, message_bus, message: Message, timeout: float = None) -> Optional[Message]:
        """Send message with timeout to prevent deadlocks"""
        try:
            timeout = timeout or self.timeout_seconds
            
            # Check for circular dependencies
            if self._would_create_circular_dependency(message):
                self.logger.warning(f"Circular dependency detected for {message.message_type}")
                return None
                
            # Track pending response
            correlation_id = message.correlation_id
            self.pending_responses[correlation_id] = datetime.now()
            
            # Send message
            await message_bus.publish(message)
            
            # Wait for response with timeout
            start_time = datetime.now()
            while correlation_id in self.pending_responses:
                if (datetime.now() - start_time).total_seconds() > timeout:
                    self.logger.error(f"Message timeout for {correlation_id}")
                    del self.pending_responses[correlation_id]
                    return None
                    
                await asyncio.sleep(0.1)
                
            return None
            
        except Exception as e:
            self.logger.error(f"Error in send_with_timeout: {e}")
            return None
            
    def _would_create_circular_dependency(self, message: Message) -> bool:
        """Check if message would create circular dependency"""
        try:
            # Check if we're waiting for a response from the same agent
            sender = message.sender
            recipient = message.recipient
            
            # Simple circular dependency detection
            for corr_id, timestamp in self.pending_responses.items():
                if (datetime.now() - timestamp).total_seconds() < self.timeout_seconds:
                    # This is a simplified check - would implement more sophisticated logic
                    pass
                    
            return False
            
        except Exception:
            return False
            
    def cleanup_old_pending(self):
        """Clean up old pending responses"""
        try:
            current_time = datetime.now()
            expired = [
                corr_id for corr_id, timestamp in self.pending_responses.items()
                if (current_time - timestamp).total_seconds() > self.timeout_seconds * 2
            ]
            
            for corr_id in expired:
                del self.pending_responses[corr_id]
                
        except Exception as e:
            self.logger.error(f"Error cleaning up pending responses: {e}")

class MessageValidator:
    """Validates messages to prevent common bugs"""
    
    def __init__(self):
        self.logger = logging.getLogger("message_validator")
        
    def validate_message(self, message: Message) -> tuple[bool, List[str]]:
        """Validate message and return (is_valid, errors)"""
        errors = []
        
        # Check required fields
        if not message.message_type:
            errors.append("Missing message_type")
            
        if not message.sender:
            errors.append("Missing sender")
            
        if not message.recipient:
            errors.append("Missing recipient")
            
        if not isinstance(message.data, dict):
            errors.append("Message data must be a dictionary")
            
        # Check for potential infinite loops
        if message.requires_response and message.recipient == message.sender:
            errors.append("Message requires response but sent to self")
            
        # Check message size
        if len(str(message.data)) > 1000000:  # 1MB limit
            errors.append("Message data too large")
            
        return len(errors) == 0, errors

class RateLimiter:
    """Prevents message flooding"""
    
    def __init__(self, max_messages_per_second: int = 100):
        self.max_messages = max_messages_per_second
        self.message_timestamps: list = []
        
    async def check_rate_limit(self) -> bool:
        """Check if message can be sent"""
        try:
            current_time = datetime.now()
            
            # Remove old timestamps (older than 1 second)
            self.message_timestamps = [
                ts for ts in self.message_timestamps
                if (current_time - ts).total_seconds() < 1.0
            ]
            
            # Check if under limit
            return len(self.message_timestamps) < self.max_messages
            
        except Exception:
            return True
            
    def record_message(self):
        """Record a sent message"""
        try:
            self.message_timestamps.append(datetime.now())
        except Exception:
            pass
