"""
Configuration package for VolatilityHunter agent system
"""

# Import all constants from config.py for backward compatibility
try:
    from .config import *
except ImportError:
    # If config.py doesn't exist, define basic constants
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    # API Configuration
    TIINGO_KEY = os.getenv('TIINGO_KEY', '')
    TIINGO_BASE_URL = 'https://api.tiingo.com/tiingo'
    BATCH_SIZE = 50
    
    # Stock Universe Configuration
    STOCK_UNIVERSE_MODE = "FULL"
    TICKER_LIST_FILE = "tickers.txt"
    DATA_SOURCE = "TIINGO"
    
    # Default Stock List
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
