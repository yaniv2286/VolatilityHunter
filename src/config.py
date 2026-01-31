import os
from dotenv import load_dotenv

load_dotenv()

TIINGO_KEY = os.getenv('TIINGO_KEY')
BUCKET_NAME = os.getenv('BUCKET_NAME')
IS_CLOUD_RUN = os.getenv('IS_CLOUD_RUN', 'False').lower() == 'true'
PORT = int(os.getenv('PORT', 8080))

# Data source: 'tiingo' or 'yfinance'
DATA_SOURCE = os.getenv('DATA_SOURCE', 'tiingo')

# Stock universe mode: 'manual', 'sp500', 'all'
STOCK_UNIVERSE_MODE = os.getenv('STOCK_UNIVERSE_MODE', 'manual')

# Manual stock list (used when STOCK_UNIVERSE_MODE='manual')
STOCK_LIST = [
    'NVDA', 'NFLX', 'PLTR', 'SHOP', 'ZS', 'SPOT', 'CRWD', 'DECK', 
    'META', 'AVGO', 'LRCX', 'CSCO', 'MU', 'AMZN', 'MELI', 'TSLA', 
    'HD', 'KLAC', 'MSFT', 'GOOGL', 'QQQ'
]

# Ticker filtering criteria (used when STOCK_UNIVERSE_MODE='all' or 'sp500')
TICKER_FILTERS = {
    'min_price': float(os.getenv('MIN_STOCK_PRICE', 5.0)),
    'min_volume': int(os.getenv('MIN_STOCK_VOLUME', 500000)),
    'exchanges': ['NYSE', 'NASDAQ', 'AMEX']
}

TIINGO_BASE_URL = 'https://api.tiingo.com/iex'
BATCH_SIZE = 50

STRATEGY_PARAMS = {
    'sma_period': 200,
    'stochastic_k_period': 10,
    'stochastic_d_period': 3,
    'stochastic_smooth': 3,
    'sweet_spot_lower': 32,
    'sweet_spot_upper': 80,
    'min_cagr': 15.0
}

LOCAL_DATA_DIR = 'data'
TICKER_LIST_FILE = 'tickers.txt'
