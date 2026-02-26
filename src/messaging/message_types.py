"""
Message Types - Message type definitions and utilities
"""

from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field
from enum import Enum
from datetime import datetime
import json
from ..interfaces.agent_interface import MessageType

# Message data structures
@dataclass
class DataRequest:
    """Data request message data"""
    ticker: str
    date_range: str
    data_type: str = "price"
    fields: List[str] = field(default_factory=lambda: ["open", "high", "low", "close", "volume"])
    
@dataclass
class DataResponse:
    """Data response message data"""
    ticker: str
    data: Dict[str, Any]
    success: bool
    error: Optional[str] = None
    
@dataclass
class SignalRequest:
    """Signal request message data"""
    tickers: List[str]
    strategy: str = "sweet_spot_v7_2"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class SignalResponse:
    """Signal response message data"""
    signals: List[Dict[str, Any]]
    strategy: str
    timestamp: str
    success: bool
    error: Optional[str] = None
    
@dataclass
class ExecutionRequest:
    """Execution request message data"""
    ticker: str
    action: str  # "buy" or "sell"
    quantity: int
    order_type: str = "market"
    price: Optional[float] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class ExecutionResponse:
    """Execution response message data"""
    order_id: str
    ticker: str
    action: str = ""
    quantity: int = 0
    status: str = ""
    price: Optional[float] = None
    timestamp: str = ""
    success: bool = False
    error: Optional[str] = None
    
@dataclass
class SyncRequest:
    """Sync request message data"""
    sync_type: str  # "portfolio", "positions", "account"
    target: str  # "tws", "local", "both"
    parameters: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class SyncResponse:
    """Sync response message data"""
    sync_type: str
    target: str
    status: str
    synced_items: int
    timestamp: str
    success: bool
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class NotificationRequest:
    """Notification request message data"""
    notification_type: str  # "email", "alert", "log"
    recipients: List[str] = field(default_factory=list)
    subject: Optional[str] = None
    body: Optional[str] = None
    data: Dict[str, Any] = field(default_factory=dict)
    priority: str = "normal"  # "low", "normal", "high", "urgent"
    
@dataclass
class NotificationResponse:
    """Notification response message data"""
    notification_type: str
    status: str
    recipients: List[str]
    timestamp: str
    success: bool
    error: Optional[str] = None
    details: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class TestRequest:
    """Test request message data"""
    test_type: str  # "backtest", "dry_run", "integration", "performance"
    parameters: Dict[str, Any] = field(default_factory=dict)
    config: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class TestResponse:
    """Test response message data"""
    test_type: str
    status: str
    results: Dict[str, Any]
    timestamp: str
    success: bool
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)
    
@dataclass
class HealthCheckRequest:
    """Health check request message data"""
    check_type: str = "basic"  # "basic", "detailed", "full"
    components: List[str] = field(default_factory=list)
    
@dataclass
class HealthCheckResponse:
    """Health check response message data"""
    agent_id: str
    status: str
    checks: Dict[str, Any]
    timestamp: str
    success: bool
    error: Optional[str] = None
    metrics: Dict[str, Any] = field(default_factory=dict)

class MessageFactory:
    """Factory for creating messages"""
    
    @staticmethod
    def create_data_request(sender: str, recipient: str, request: DataRequest) -> Dict[str, Any]:
        """Create data request message"""
        return {
            "message_type": MessageType.DATA_REQUEST,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "ticker": request.ticker,
                "date_range": request.date_range,
                "data_type": request.data_type,
                "fields": request.fields
            },
            "timestamp": datetime.now().isoformat(),
            "requires_response": True
        }
    
    @staticmethod
    def create_data_response(sender: str, recipient: str, response: DataResponse, correlation_id: str = None) -> Dict[str, Any]:
        """Create data response message"""
        return {
            "message_type": MessageType.DATA_RESPONSE,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "ticker": response.ticker,
                "data": response.data,
                "success": response.success,
                "error": response.error
            },
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_id,
            "requires_response": False
        }
    
    @staticmethod
    def create_signal_request(sender: str, recipient: str, request: SignalRequest) -> Dict[str, Any]:
        """Create signal request message"""
        return {
            "message_type": MessageType.SIGNAL_REQUEST,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "tickers": request.tickers,
                "strategy": request.strategy,
                "parameters": request.parameters
            },
            "timestamp": datetime.now().isoformat(),
            "requires_response": True
        }
    
    @staticmethod
    def create_signal_response(sender: str, recipient: str, response: SignalResponse, correlation_id: str = None) -> Dict[str, Any]:
        """Create signal response message"""
        return {
            "message_type": MessageType.SIGNAL_RESPONSE,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "signals": response.signals,
                "strategy": response.strategy,
                "timestamp": response.timestamp,
                "success": response.success,
                "error": response.error
            },
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_id,
            "requires_response": False
        }
    
    @staticmethod
    def create_execution_request(sender: str, recipient: str, request: ExecutionRequest) -> Dict[str, Any]:
        """Create execution request message"""
        return {
            "message_type": MessageType.EXECUTION_REQUEST,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "ticker": request.ticker,
                "action": request.action,
                "quantity": request.quantity,
                "order_type": request.order_type,
                "price": request.price,
                "parameters": request.parameters
            },
            "timestamp": datetime.now().isoformat(),
            "requires_response": True
        }
    
    @staticmethod
    def create_execution_response(sender: str, recipient: str, response: ExecutionResponse, correlation_id: str = None) -> Dict[str, Any]:
        """Create execution response message"""
        return {
            "message_type": MessageType.EXECUTION_RESPONSE,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "order_id": response.order_id,
                "ticker": response.ticker,
                "action": response.action,
                "quantity": response.quantity,
                "status": response.status,
                "price": response.price,
                "timestamp": response.timestamp,
                "success": response.success,
                "error": response.error
            },
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_id,
            "requires_response": False
        }
    
    @staticmethod
    def create_test_request(sender: str, recipient: str, request: TestRequest) -> Dict[str, Any]:
        """Create test request message"""
        return {
            "message_type": MessageType.TEST_REQUEST,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "test_type": request.test_type,
                "parameters": request.parameters,
                "config": request.config
            },
            "timestamp": datetime.now().isoformat(),
            "requires_response": True
        }
    
    @staticmethod
    def create_test_response(sender: str, recipient: str, response: TestResponse, correlation_id: str = None) -> Dict[str, Any]:
        """Create test response message"""
        return {
            "message_type": MessageType.TEST_RESPONSE,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "test_type": response.test_type,
                "status": response.status,
                "results": response.results,
                "timestamp": response.timestamp,
                "success": response.success,
                "error": response.error,
                "metrics": response.metrics
            },
            "timestamp": datetime.now().isoformat(),
            "correlation_id": correlation_id,
            "requires_response": False
        }
    
    @staticmethod
    def create_health_check(sender: str, recipient: str, request: HealthCheckRequest) -> Dict[str, Any]:
        """Create health check message"""
        return {
            "message_type": MessageType.HEALTH_CHECK,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "check_type": request.check_type,
                "components": request.components
            },
            "timestamp": datetime.now().isoformat(),
            "requires_response": True
        }
    
    @staticmethod
    def create_error_message(sender: str, recipient: str, error: str, original_message: Dict[str, Any] = None) -> Dict[str, Any]:
        """Create error message"""
        return {
            "message_type": MessageType.ERROR,
            "sender": sender,
            "recipient": recipient,
            "data": {
                "error": error,
                "original_message": original_message
            },
            "timestamp": datetime.now().isoformat(),
            "requires_response": False
        }
