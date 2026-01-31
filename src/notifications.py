import logging
from datetime import datetime

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
    logger.info(message)

def log_error(message):
    logger.error(message)

def log_warning(message):
    logger.warning(message)

def alert_signal(ticker, signal, price, indicators):
    message = f"[SIGNAL] {ticker}: {signal} at ${price:.2f} | Indicators: {indicators}"
    logger.info(message)
    return message

def alert_error(ticker, error):
    message = f"[ERROR] {ticker}: {error}"
    logger.error(message)
    return message
