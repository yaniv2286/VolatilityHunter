"""
Data Loader Factory
Provides unified interface for different data sources (Tiingo or Yahoo Finance)
"""

from src.config import DATA_SOURCE
from src.notifications import log_info

def get_data_loader():
    """
    Get the appropriate data loader based on configuration.
    
    Returns:
        Data loader instance (either Tiingo or YFinance)
    """
    if DATA_SOURCE.lower() == 'yfinance':
        log_info("Using Yahoo Finance as data source")
        from src.yfinance_loader import YFinanceLoader
        return YFinanceLoader()
    else:
        log_info("Using Tiingo as data source")
        return TiingoLoader()

class TiingoLoader:
    """Wrapper for existing Tiingo data loader to match YFinance interface."""
    
    def __init__(self):
        from src.storage import DataStorage
        self.storage = DataStorage()
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """Update stocks using Tiingo API."""
        from src.data_loader import update_all_stocks
        return update_all_stocks(full_refresh=full_refresh, stock_list=stock_list)
    
    def download_nasdaq_tickers(self):
        """Tiingo doesn't provide ticker list, use manual list."""
        from src.config import STOCK_LIST
        return STOCK_LIST
    
    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        """Tiingo doesn't support filtering, return all tickers."""
        import pandas as pd
        return pd.DataFrame([{'ticker': t, 'price': 0, 'avg_volume': 0} for t in tickers])
