"""
VolatilityHunter Notification System
Centralized logging and notification utilities
"""

import logging
import sys
from datetime import datetime
from typing import Optional

# Configure logging
def setup_logging(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """Setup logging configuration"""
    logger = logging.getLogger(name)
    logger.setLevel(logging.INFO)
    
    # Clear existing handlers
    logger.handlers.clear()
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)
    console_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)
    
    # File handler (if specified)
    if log_file:
        file_handler = logging.FileHandler(log_file)
        file_handler.setLevel(logging.INFO)
        file_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        file_handler.setFormatter(file_formatter)
        logger.addHandler(file_handler)
    
    return logger

# Global logger instance
logger = setup_logging("VolatilityHunter")

def log_info(message: str) -> None:
    """Log info message"""
    logger.info(message)

def log_warning(message: str) -> None:
    """Log warning message"""
    logger.warning(message)

def log_error(message: str) -> None:
    """Log error message"""
    logger.error(message)

def log_debug(message: str) -> None:
    """Log debug message"""
    logger.debug(message)

def log_critical(message: str) -> None:
    """Log critical message"""
    logger.critical(message)
