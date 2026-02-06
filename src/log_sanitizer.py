"""
Log Sanitization and Error Reduction for VolatilityHunter
Implements sanitized logging with API key redaction and error noise reduction
"""

import logging
import re
import sys
from typing import Dict, Any, Optional
from collections import defaultdict

class SanitizedFormatter(logging.Formatter):
    """
    Sanitized logging formatter that redacts sensitive information
    and reduces error noise through intelligent filtering
    """
    
    def __init__(self, fmt=None, datefmt=None):
        super().__init__(fmt, datefmt)
        
        # Patterns to redact sensitive information
        self.redaction_patterns = [
            # API Keys
            (r'(?i)(tiingo[_\s]*key[\'"\s]*:\s*[\'"]\s*[a-zA-Z0-9_-]+[\'"\s]*)', r'\1[REDACTED]'),
            (r'(?i)(tiingo[_\s]*key[\'"\s]*=\s*[\'"]\s*[a-zA-Z0-9_-]+[\'"\s]*)', r'\1[REDACTED]'),
            (r'(?i)(api[_\s]*key[\'"\s]*:\s*[\'"]\s*[a-zA-Z0-9_-]+[\'"\s]*)', r'\1[REDACTED]'),
            (r'(?i)(api[_\s]*key[\'"\s]*=\s*[\'"]\s*[a-zA-Z0-9_-]+[\'"\s]*)', r'\1[REDACTED]'),
            
            # Passwords and tokens
            (r'(?i)(password[\'"\s]*:\s*[\'"]\s*[^\s\'"]+)', r'\1[REDACTED]'),
            (r'(?i)(token[\'"\s]*:\s*[\'"]\s*[^\s\'"]+)', r'\1[REDACTED]'),
            (r'(?i)(secret[\'"\s]*:\s*[\'"]\s*[^\s\'"]+)', r'\1[REDACTED]'),
            (r'(?i)(auth[\'"\s]*:\s*[\'"]\s*[^\s\'"]+)', r'\1[REDACTED]'),
            
            # Email addresses
            (r'(?i)([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})', r'[REDACTED_EMAIL]'),
            
            # File paths with sensitive info
            (r'(?i)(/[uU]sers/[^\s/]+)', r'\1[REDACTED_PATH]'),
            (r'(?i)([hH]ome/[^\s/]+)', r'\1[REDACTED_PATH]'),
            
            # URLs with keys/tokens
            (r'(?i)(key[=][^\s&]+)', r'\1[REDACTED_KEY]'),
            (r'(?i)(token[=][^\s&]+)', r'\1[REDACTED_TOKEN]'),
        ]
        
        # Error suppression tracking
        self.error_counts = defaultdict(int)
        self.max_error_repetitions = 3
        self.suppressed_errors = set()
        
        # Compile regex patterns for performance
        self.compiled_patterns = [(re.compile(pattern, re.IGNORECASE), replacement) 
                                for pattern, replacement in self.redaction_patterns]
    
    def format(self, record):
        """
        Format the log record with sanitization
        """
        # Get the original formatted message
        formatted = super().format(record)
        
        # Apply redaction patterns
        sanitized = formatted
        for pattern, replacement in self.compiled_patterns:
            sanitized = pattern.sub(replacement, sanitized)
        
        # Ensure ASCII-only output
        if sys.version_info[0] >= 3:
            # Python 3.x: handle Unicode properly
            try:
                sanitized = sanitized.encode('ascii', errors='replace').decode('ascii')
            except UnicodeEncodeError:
                sanitized = sanitized.encode('ascii', 'ignore').decode('ascii')
        else:
            # Python 2.x fallback
            sanitized = sanitized.encode('ascii', errors='ignore').decode('ascii')
        
        return sanitized
    
    def track_error(self, error_message: str) -> bool:
        """
        Track error messages for noise reduction
        
        Returns:
            True if error should be logged, False if suppressed
        """
        # Create a normalized error signature for tracking
        error_signature = self._normalize_error_message(error_message)
        
        self.error_counts[error_signature] += 1
        
        # Check if we should suppress this error
        if self.error_counts[error_signature] > self.max_error_repetitions:
            if error_signature not in self.suppressed_errors:
                self.suppressed_errors.add(error_signature)
                # Print summary for newly suppressed error
                count = self.error_counts[error_signature]
                print(f"[REDACTED ERROR] {error_signature} repeated {count} times")
            return False
        
        return True
    
    def _normalize_error_message(self, message: str) -> str:
        """
        Normalize error message for tracking by removing dynamic content
        """
        # Remove timestamps, line numbers, and dynamic values
        normalized = re.sub(r'\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3}', '[TIMESTAMP]', message)
        normalized = re.sub(r'line \d+', '[LINE]', normalized)
        normalized = re.sub(r'\b\d+\.\d+\b', '[NUMBER]', normalized)
        normalized = re.sub(r'\b\d+\b', '[NUMBER]', normalized)
        normalized = re.sub(r'\'[^\']*\'', '[STRING]', normalized)
        normalized = re.sub(r'"[^"]*"', '[STRING]', normalized)
        
        # Remove extra whitespace
        normalized = re.sub(r'\s+', ' ', normalized)
        normalized = normalized.strip()
        
        return normalized
    
    def get_suppression_summary(self) -> Dict[str, Any]:
        """
        Get summary of suppressed errors
        
        Returns:
            Dict with suppression statistics
        """
        return {
            'total_suppressed': len(self.suppressed_errors),
            'suppressed_errors': list(self.suppressed_errors),
            'error_counts': dict(self.error_counts),
            'max_repetitions': self.max_error_repetitions
        }
    
    def reset_tracking(self):
        """Reset error tracking counters"""
        self.error_counts.clear()
        self.suppressed_errors.clear()

# Global formatter instance
sanitized_formatter = SanitizedFormatter()

def get_sanitized_logger(name: str) -> logging.Logger:
    """
    Get a logger with sanitized formatting
    
    Args:
        name: Logger name
        
    Returns:
        Configured logger with sanitized formatter
    """
    logger = logging.getLogger(name)
    
    # Remove existing handlers
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create console handler with sanitized formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(sanitized_formatter)
    
    # Add handler to logger
    logger.addHandler(console_handler)
    logger.setLevel(logging.INFO)
    
    return logger

# Convenience function for error logging with tracking
def log_error_with_tracking(logger: logging.Logger, message: str, *args, **kwargs):
    """
    Log error with noise reduction tracking
    """
    if sanitized_formatter.track_error(message):
        logger.error(message, *args, **kwargs)

# Convenience function for warning logging with tracking
def log_warning_with_tracking(logger: logging.Logger, message: str, *args, **kwargs):
    """
    Log warning with noise reduction tracking
    """
    if sanitized_formatter.track_error(message):
        logger.warning(message, *args, **kwargs)
