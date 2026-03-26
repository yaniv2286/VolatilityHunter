"""
VolatilityHunter Log Sanitizer
Enhanced logging with tracking and error context
"""

import logging
import sys
import traceback
from datetime import datetime
from typing import Optional

# Enhanced logger with tracking
def setup_enhanced_logging(name: str, log_file: Optional[str] = None) -> logging.Logger:
    """Setup enhanced logging with tracking"""
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

# Global enhanced logger
enhanced_logger = setup_enhanced_logging("VolatilityHunter_Enhanced")

def log_error_with_tracking(message: str) -> None:
    """Log error with full traceback tracking"""
    enhanced_logger.error(f"TRACKED ERROR: {message}")
    enhanced_logger.error(f"TRACEBACK: {traceback.format_exc()}")

def log_warning_with_tracking(message: str) -> None:
    """Log warning with context tracking"""
    enhanced_logger.warning(f"TRACKED WARNING: {message}")
    enhanced_logger.warning(f"CONTEXT: {datetime.now().isoformat()}")

def log_info_with_tracking(message: str) -> None:
    """Log info with tracking"""
    enhanced_logger.info(f"TRACKED INFO: {message}")

def log_debug_with_tracking(message: str) -> None:
    """Log debug with tracking"""
    enhanced_logger.debug(f"TRACKED DEBUG: {message}")
