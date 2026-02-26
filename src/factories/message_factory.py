"""
Message Factory - Factory for creating messages
"""

import logging
import uuid
from datetime import datetime
from typing import Dict, Any, Optional
from ..interfaces.agent_interface import Message, MessageType
from ..messaging.message_types import MessageFactory

class MessageFactory:
    """Factory for creating messages"""
    
    def __init__(self):
        self.logger = logging.getLogger("message_factory")
        self.message_counter = 0
        
    def create_message(self, message_type: MessageType, sender: str, recipient: str, 
                      data: Dict[str, Any], correlation_id: str = None, 
                      requires_response: bool = False) -> Message:
        """Create basic message"""
        try:
            message = Message(
                message_type=message_type,
                sender=sender,
                recipient=recipient,
                data=data,
                timestamp=datetime.now().isoformat(),
                correlation_id=correlation_id or str(uuid.uuid4()),
                requires_response=requires_response
            )
            
            self.message_counter += 1
            self.logger.debug(f"Created message {message_type} from {sender} to {recipient}")
            return message
            
        except Exception as e:
            self.logger.error(f"Error creating message: {e}")
            raise
            
    def create_response(self, original_message: Message, response_data: Dict[str, Any], 
                       success: bool = True, error: str = None) -> Message:
        """Create response message"""
        try:
            response_type = self._get_response_type(original_message.message_type)
            
            response_data.update({
                "success": success,
                "error": error,
                "original_request_id": original_message.correlation_id
            })
            
            return self.create_message(
                message_type=response_type,
                sender=original_message.recipient,
                recipient=original_message.sender,
                data=response_data,
                correlation_id=original_message.correlation_id,
                requires_response=False
            )
            
        except Exception as e:
            self.logger.error(f"Error creating response message: {e}")
            raise
            
    def create_error_response(self, original_message: Message, error: str) -> Message:
        """Create error response message"""
        return self.create_response(
            original_message=original_message,
            response_data={"error": error},
            success=False,
            error=error
        )
        
    def create_health_check(self, sender: str, recipient: str, check_type: str = "basic") -> Message:
        """Create health check message"""
        return self.create_message(
            message_type=MessageType.HEALTH_CHECK,
            sender=sender,
            recipient=recipient,
            data={"check_type": check_type},
            requires_response=True
        )
        
    def create_shutdown_message(self, sender: str, recipient: str, reason: str = None) -> Message:
        """Create shutdown message"""
        return self.create_message(
            message_type=MessageType.SHUTDOWN,
            sender=sender,
            recipient=recipient,
            data={"reason": reason or "Manual shutdown"},
            requires_response=False
        )
        
    def create_broadcast_message(self, sender: str, message_type: MessageType, 
                               data: Dict[str, Any]) -> Message:
        """Create broadcast message"""
        return self.create_message(
            message_type=message_type,
            sender=sender,
            recipient="broadcast",
            data=data,
            requires_response=False
        )
        
    def _get_response_type(self, request_type: MessageType) -> MessageType:
        """Get response type for request type"""
        response_mapping = {
            MessageType.DATA_REQUEST: MessageType.DATA_RESPONSE,
            MessageType.SIGNAL_REQUEST: MessageType.SIGNAL_RESPONSE,
            MessageType.EXECUTION_REQUEST: MessageType.EXECUTION_RESPONSE,
            MessageType.SYNC_REQUEST: MessageType.SYNC_RESPONSE,
            MessageType.NOTIFICATION_REQUEST: MessageType.NOTIFICATION_RESPONSE,
            MessageType.TEST_REQUEST: MessageType.TEST_RESPONSE,
            MessageType.HEALTH_CHECK: MessageType.HEALTH_CHECK
        }
        
        return response_mapping.get(request_type, MessageType.ERROR)
        
    def get_statistics(self) -> Dict[str, Any]:
        """Get factory statistics"""
        return {
            "messages_created": self.message_counter,
            "timestamp": datetime.now().isoformat()
        }
        
    def reset_counter(self):
        """Reset message counter"""
        self.message_counter = 0
        self.logger.info("Message counter reset")
