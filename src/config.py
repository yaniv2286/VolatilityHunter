"""
VolatilityHunter Configuration Constants
Legacy configuration constants for backward compatibility
"""

import os
from typing import List, Dict, Any
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# API Configuration - read both TIINGO_API_KEY (set in .env) and TIINGO_KEY (legacy)
TIINGO_KEY = os.getenv('TIINGO_API_KEY', '') or os.getenv('TIINGO_KEY', '')
TIINGO_BASE_URL = 'https://api.tiingo.com/tiingo'
BATCH_SIZE = 50

# Stock Universe Configuration
STOCK_UNIVERSE_MODE = "FULL"  # FULL or FILTERED
TICKER_LIST_FILE = "tickers.txt"

# Data Source Configuration
DATA_SOURCE = "TIINGO"

# Stock Filters
TICKER_FILTERS = {
    "min_volume": 1000000,  # Minimum average daily volume
    "min_price": 1.0,      # Minimum stock price
    "max_price": 500.0,    # Maximum stock price (reverse-split filter)
    "exclude_penny_stocks": True,
    "exclude_illiquid": True,
    "exchanges": ["NYSE", "NASDAQ", "AMEX"]  # Supported exchanges
}

# Default Stock List (fallback if tickers.txt doesn't exist)
STOCK_LIST = [
    "AAPL", "MSFT", "GOOGL", "AMZN", "META", "NVDA", "TSLA", "JPM", 
    "JNJ", "V", "PG", "UNH", "HD", "MA", "BAC", "XOM", "CVX", "LLY", 
    "ABBV", "PFE", "KO", "PEP", "TMO", "COST", "ABT", "DHR", "MCD",
    "ACN", "VZ", "ADBE", "NFLX", "CRM", "PYPL", "INTC", "CSCO",
    "CMCSA", "AMD", "TXN", "QCOM", "IBM", "AMGN", "GILD", "MDT",
    "ISRG", "BDX", "REGN", "ATVI", "AVGO", "TXN", "NOW", "MU",
    "CSX", "NSC", "UNP", "KSU", "FDX", "UPS", "LUV", "DAL", "AAL",
    "UAL", "HA", "ALK", "JBLU", "SAVE", "ALK", "MESA", "SKYW"
]

# Trading Configuration
TRADING_MODE = os.environ.get("TRADING_MODE", "PAPER")
RISK_TOLERANCE = os.environ.get("RISK_TOLERANCE", "MEDIUM")
TIME_OFFSET = int(os.environ.get("TIME_OFFSET", "0"))

# Email Configuration
EMAIL_RECIPIENTS = os.environ.get("EMAIL_RECIPIENTS", "").split(",") if os.environ.get("EMAIL_RECIPIENTS") else []

# Risk Management
MAX_POSITIONS = 10
POSITION_SIZE_PERCENT = 0.10  # 10% of portfolio per position
STOP_LOSS_PERCENT = 0.03     # 3% stop loss
TAKE_PROFIT_PERCENT = 0.20   # 20% take profit

# Data Loading
DATA_CACHE_ENABLED = True
DATA_CACHE_DAYS = 7

# Logging
LOG_LEVEL = "INFO"
LOG_TO_FILE = True
LOG_TO_CONSOLE = True

# Tiingo API Configuration
TIINGO_KEY = os.environ.get("TIINGO_API_KEY") or os.environ.get("TIINGO_KEY", "")
TIINGO_BASE_URL = "https://api.tiingo.com/tiingo"

# Data Loading Configuration
BATCH_SIZE = 1  # Number of stocks to process in each batch (individual for Tiingo)
