import logging
from datetime import datetime
import re
import os
from src.log_sanitizer import SanitizedFormatter

# ASCII-only logging for Task Scheduler compatibility
def ensure_ascii(message):
    """Convert message to ASCII-only for Task Scheduler compatibility."""
    # Replace common Unicode characters with ASCII equivalents
    replacements = {
        '→': '->',
        '←': '<-',
        '↑': '^',
        '↓': 'v',
        '≥': '>=',
        '≤': '<=',
        '≠': '!=',
        '±': '+/-',
        '×': 'x',
        '÷': '/',
        '°': 'deg',
        '™': '(TM)',
        '®': '(R)',
        '©': '(C)',
        '…': '...',
        '"': '"',
        '"': '"',
        ''': "'",
        ''': "'",
        '–': '-',
        '—': '--',
        '•': '*',
        '·': '*',
        '€': 'EUR',
        '£': 'GBP',
        '¥': 'JPY',
        '₹': 'INR',
        '©': '(C)',
        '®': '(R)',
        '™': '(TM)'
    }
    
    # Apply replacements
    for unicode_char, ascii_char in replacements.items():
        message = message.replace(unicode_char, ascii_char)
    
    # Remove any remaining non-ASCII characters
    ascii_message = re.sub(r'[^\x00-\x7F]+', '', message)
    return ascii_message

def setup_logging():
    """Setup logging with daily log files and append mode"""
    # Configure logging with sanitized formatter
    logger = logging.getLogger('VolatilityHunter')
    logger.setLevel(logging.INFO)
    
    # Remove existing handlers to avoid duplicates
    for handler in logger.handlers[:]:
        logger.removeHandler(handler)
    
    # Create logs directory if it doesn't exist
    logs_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(logs_dir, exist_ok=True)
    
    # Daily log file with append mode
    today = datetime.now().strftime('%Y-%m-%d')
    log_file = os.path.join(logs_dir, f'VH_{today}.log')
    
    # Create file handler with APPEND mode and sanitized formatter
    file_handler = logging.FileHandler(log_file, mode='a', encoding='utf-8')
    file_handler.setFormatter(SanitizedFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Create console handler with sanitized formatter
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(SanitizedFormatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s'))
    
    # Add handlers to logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    
    return logger

# Initialize logging immediately
logger = setup_logging()

def log_info(message):
    ascii_message = ensure_ascii(str(message))
    logger.info(ascii_message)

def log_error(message):
    from src.log_sanitizer import log_error_with_tracking
    ascii_message = ensure_ascii(str(message))
    log_error_with_tracking(logger, ascii_message)

def log_warning(message):
    from src.log_sanitizer import log_warning_with_tracking
    ascii_message = ensure_ascii(str(message))
    log_warning_with_tracking(logger, ascii_message)

def alert_signal(ticker, signal, price, indicators):
    message = f"[SIGNAL] {ticker}: {signal} at ${price:.2f} | Indicators: {indicators}"
    ascii_message = ensure_ascii(message)
    logger.info(ascii_message)
    return ascii_message

def alert_error(ticker, error):
    message = f"[ERROR] {ticker}: {error}"
    ascii_message = ensure_ascii(message)
    logger.error(ascii_message)
    return ascii_message
