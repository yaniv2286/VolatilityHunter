import logging
from datetime import datetime
import re

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

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('volatility_hunter.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger('VolatilityHunter')

def log_info(message):
    ascii_message = ensure_ascii(str(message))
    logger.info(ascii_message)

def log_error(message):
    ascii_message = ensure_ascii(str(message))
    logger.error(ascii_message)

def log_warning(message):
    ascii_message = ensure_ascii(str(message))
    logger.warning(ascii_message)

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
