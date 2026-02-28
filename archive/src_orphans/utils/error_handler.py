"""
Error Handling Utilities - Comprehensive error handling and recovery
"""

import logging
import traceback
import json
from datetime import datetime
from typing import Dict, Any, Optional, List, Callable
from dataclasses import dataclass
from enum import Enum

class ErrorSeverity(Enum):
    """Error severity levels"""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

@dataclass
class ErrorInfo:
    """Error information structure"""
    error_id: str
    timestamp: datetime
    severity: ErrorSeverity
    error_type: str
    message: str
    traceback: str
    context: Dict[str, Any]
    agent_id: str
    recovered: bool = False
    recovery_attempts: int = 0

class ErrorHandler:
    """Comprehensive error handling and recovery"""
    
    def __init__(self, agent_id: str):
        self.agent_id = agent_id
        self.logger = logging.getLogger(f"error_handler.{agent_id}")
        self.error_history: List[ErrorInfo] = []
        self.recovery_strategies: Dict[str, Callable] = {}
        self.max_error_history = 1000
        self.critical_error_threshold = 5  # Max critical errors before shutdown
        
        # Register default recovery strategies
        self._register_default_strategies()
        
    def handle_error(self, error: Exception, context: Dict[str, Any] = None, 
                    severity: ErrorSeverity = ErrorSeverity.MEDIUM, 
                    error_type: str = None) -> ErrorInfo:
        """Handle error with comprehensive logging and recovery"""
        try:
            # Create error info
            error_info = ErrorInfo(
                error_id=self._generate_error_id(),
                timestamp=datetime.now(),
                severity=severity,
                error_type=error_type or type(error).__name__,
                message=str(error),
                traceback=traceback.format_exc(),
                context=context or {},
                agent_id=self.agent_id
            )
            
            # Log error
            self._log_error(error_info)
            
            # Add to history
            self._add_to_history(error_info)
            
            # Check for critical errors
            if severity == ErrorSeverity.CRITICAL:
                self._handle_critical_error(error_info)
                
            # Attempt recovery
            if self._should_attempt_recovery(error_info):
                self._attempt_recovery(error_info)
                
            return error_info
            
        except Exception as e:
            self.logger.error(f"Error in error handler: {e}")
            # Return minimal error info
            return ErrorInfo(
                error_id="unknown",
                timestamp=datetime.now(),
                severity=ErrorSeverity.HIGH,
                error_type="ErrorHandlerError",
                message=str(e),
                traceback="",
                context={},
                agent_id=self.agent_id
            )
            
    def register_recovery_strategy(self, error_type: str, strategy: Callable):
        """Register a recovery strategy for specific error types"""
        try:
            self.recovery_strategies[error_type] = strategy
            self.logger.info(f"Registered recovery strategy for {error_type}")
            
        except Exception as e:
            self.logger.error(f"Error registering recovery strategy: {e}")
            
    def safe_execute(self, func: Callable, *args, default_return=None, 
                     error_type: str = None, severity: ErrorSeverity = ErrorSeverity.MEDIUM,
                     context: Dict[str, Any] = None, **kwargs) -> Any:
        """Safely execute function with comprehensive error handling"""
        try:
            return func(*args, **kwargs)
            
        except Exception as e:
            error_info = self.handle_error(e, context, severity, error_type)
            
            # Return default value if provided
            if default_return is not None:
                return default_return
                
            # Re-raise if critical
            if severity == ErrorSeverity.CRITICAL:
                raise
                
            return None
            
    def get_error_stats(self) -> Dict[str, Any]:
        """Get error statistics"""
        try:
            if not self.error_history:
                return {
                    "total_errors": 0,
                    "by_severity": {},
                    "by_type": {},
                    "recovery_rate": 0.0,
                    "recent_errors": []
                }
                
            # Count by severity
            by_severity = {}
            for error in self.error_history:
                severity = error.severity.value
                by_severity[severity] = by_severity.get(severity, 0) + 1
                
            # Count by type
            by_type = {}
            for error in self.error_history:
                error_type = error.error_type
                by_type[error_type] = by_type.get(error_type, 0) + 1
                
            # Calculate recovery rate
            recovered = sum(1 for error in self.error_history if error.recovered)
            recovery_rate = recovered / len(self.error_history)
            
            # Recent errors (last 10)
            recent_errors = [
                {
                    "error_id": error.error_id,
                    "timestamp": error.timestamp.isoformat(),
                    "severity": error.severity.value,
                    "error_type": error.error_type,
                    "message": error.message,
                    "recovered": error.recovered
                }
                for error in self.error_history[-10:]
            ]
            
            return {
                "total_errors": len(self.error_history),
                "by_severity": by_severity,
                "by_type": by_type,
                "recovery_rate": recovery_rate,
                "recent_errors": recent_errors
            }
            
        except Exception as e:
            self.logger.error(f"Error getting error stats: {e}")
            return {"error": str(e)}
            
    def _generate_error_id(self) -> str:
        """Generate unique error ID"""
        try:
            import uuid
            return str(uuid.uuid4())[:8]
            
        except Exception:
            return f"error_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
            
    def _log_error(self, error_info: ErrorInfo):
        """Log error with appropriate level"""
        try:
            log_message = f"[{error_info.severity.value.upper()}] {error_info.error_type}: {error_info.message}"
            
            if error_info.severity == ErrorSeverity.CRITICAL:
                self.logger.critical(log_message)
            elif error_info.severity == ErrorSeverity.HIGH:
                self.logger.error(log_message)
            elif error_info.severity == ErrorSeverity.MEDIUM:
                self.logger.warning(log_message)
            else:
                self.logger.info(log_message)
                
            # Log traceback for debugging
            if error_info.traceback:
                self.logger.debug(f"Traceback for {error_info.error_id}:\n{error_info.traceback}")
                
        except Exception as e:
            self.logger.error(f"Error logging error: {e}")
            
    def _add_to_history(self, error_info: ErrorInfo):
        """Add error to history with size limit"""
        try:
            self.error_history.append(error_info)
            
            # Maintain history size limit
            if len(self.error_history) > self.max_error_history:
                self.error_history = self.error_history[-self.max_error_history:]
                
        except Exception as e:
            self.logger.error(f"Error adding to history: {e}")
            
    def _handle_critical_error(self, error_info: ErrorInfo):
        """Handle critical errors"""
        try:
            critical_count = sum(1 for error in self.error_history 
                              if error.severity == ErrorSeverity.CRITICAL)
            
            if critical_count >= self.critical_error_threshold:
                self.logger.critical(
                    f"Critical error threshold reached ({critical_count}). "
                    f"Agent {self.agent_id} should be shutdown."
                )
                
                # This would trigger agent shutdown
                self._trigger_emergency_shutdown()
                
        except Exception as e:
            self.logger.error(f"Error handling critical error: {e}")
            
    def _should_attempt_recovery(self, error_info: ErrorInfo) -> bool:
        """Determine if recovery should be attempted"""
        try:
            # Don't attempt recovery for certain error types
            no_recovery_types = ["KeyboardInterrupt", "SystemExit", "MemoryError"]
            if error_info.error_type in no_recovery_types:
                return False
                
            # Don't attempt recovery too many times
            if error_info.recovery_attempts >= 3:
                return False
                
            # Attempt recovery for recoverable errors
            recoverable_types = ["ConnectionError", "TimeoutError", "NetworkError"]
            if error_info.error_type in recoverable_types:
                return True
                
            # Check if we have a recovery strategy
            if error_info.error_type in self.recovery_strategies:
                return True
                
            return False
            
        except Exception:
            return False
            
    def _attempt_recovery(self, error_info: ErrorInfo):
        """Attempt error recovery"""
        try:
            self.logger.info(f"Attempting recovery for {error_info.error_id}")
            
            # Increment recovery attempts
            error_info.recovery_attempts += 1
            
            # Try specific recovery strategy
            if error_info.error_type in self.recovery_strategies:
                strategy = self.recovery_strategies[error_info.error_type]
                success = strategy(error_info)
                
                if success:
                    error_info.recovered = True
                    self.logger.info(f"Recovery successful for {error_info.error_id}")
                else:
                    self.logger.warning(f"Recovery failed for {error_info.error_id}")
                    
            # Try generic recovery
            else:
                success = self._generic_recovery(error_info)
                
                if success:
                    error_info.recovered = True
                    self.logger.info(f"Generic recovery successful for {error_info.error_id}")
                else:
                    self.logger.warning(f"Generic recovery failed for {error_info.error_id}")
                    
        except Exception as e:
            self.logger.error(f"Error in recovery attempt: {e}")
            
    def _generic_recovery(self, error_info: ErrorInfo) -> bool:
        """Generic recovery strategy"""
        try:
            # This would implement generic recovery logic
            # For now, just log the attempt
            self.logger.info(f"Generic recovery attempted for {error_info.error_type}")
            return False
            
        except Exception:
            return False
            
    def _trigger_emergency_shutdown(self):
        """Trigger emergency shutdown"""
        try:
            self.logger.critical(f"Triggering emergency shutdown for agent {self.agent_id}")
            # This would trigger the actual shutdown process
            # Implementation depends on the agent system
            
        except Exception as e:
            self.logger.error(f"Error triggering emergency shutdown: {e}")
            
    def _register_default_strategies(self):
        """Register default recovery strategies"""
        try:
            # Connection recovery
            self.register_recovery_strategy("ConnectionError", self._recover_connection)
            
            # Timeout recovery
            self.register_recovery_strategy("TimeoutError", self._recover_timeout)
            
            # Network recovery
            self.register_recovery_strategy("NetworkError", self._recover_network)
            
        except Exception as e:
            self.logger.error(f"Error registering default strategies: {e}")
            
    def _recover_connection(self, error_info: ErrorInfo) -> bool:
        """Recover from connection errors"""
        try:
            self.logger.info("Attempting connection recovery")
            # This would implement actual connection recovery logic
            return False
            
        except Exception:
            return False
            
    def _recover_timeout(self, error_info: ErrorInfo) -> bool:
        """Recover from timeout errors"""
        try:
            self.logger.info("Attempting timeout recovery")
            # This would implement actual timeout recovery logic
            return False
            
        except Exception:
            return False
            
    def _recover_network(self, error_info: ErrorInfo) -> bool:
        """Recover from network errors"""
        try:
            self.logger.info("Attempting network recovery")
            # This would implement actual network recovery logic
            return False
            
        except Exception:
            return False

class CircuitBreaker:
    """Circuit breaker pattern to prevent cascading failures"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = None
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
        
    def call(self, func: Callable, *args, **kwargs):
        """Execute function with circuit breaker protection"""
        try:
            if self.state == "OPEN":
                if datetime.now() - self.last_failure_time > timedelta(seconds=self.recovery_timeout):
                    self.state = "HALF_OPEN"
                else:
                    raise Exception("Circuit breaker is OPEN")
                    
            if self.state == "HALF_OPEN":
                # Allow one call to test the waters
                self.state = "CLOSED"
                
            result = func(*args, **kwargs)
            
            # Success - reset circuit breaker
            if self.state == "HALF_OPEN":
                self.state = "CLOSED"
                self.failure_count = 0
                
            return result
            
        except Exception as e:
            self.failure_count += 1
            self.last_failure_time = datetime.now()
            
            if self.failure_count >= self.failure_threshold:
                self.state = "OPEN"
                
            raise e
