"""
Smart Data Loader Factory
Intelligently switches between Tiingo and Yahoo Finance based on configuration and availability
"""

import os
from src.config import TIINGO_KEY
from src.notifications import log_info, log_warning, log_error

def get_data_loader():
    """
    Smart data loader selection with intelligent fallback.
    
    Priority Order:
    1. Use Tiingo if key exists and explicitly requested
    2. Use Yahoo Finance if explicitly requested
    3. Default to Tiingo if key available (you're paying for it!)
    4. Fallback to Yahoo Finance if Tiingo fails
    
    Returns:
        Data loader instance with fallback capability
    """
    data_source = os.getenv('VH_DATA_SOURCE', 'tiingo').lower()
    
    # Check if user explicitly wants Yahoo Finance
    if data_source == 'yfinance':
        log_info("User explicitly requested Yahoo Finance data source")
        return YFinanceLoader()
    
    # Check if user explicitly wants Tiingo
    elif data_source == 'tiingo':
        if TIINGO_KEY and TIINGO_KEY.strip():
            log_info("User explicitly requested Tiingo data source")
            return TiingoLoader()
        else:
            log_warning("Tiingo requested but no API key found, falling back to Yahoo Finance")
            return YFinanceLoader()
    
    # Default behavior: Use Tiingo if you're paying for it
    else:
        if TIINGO_KEY and TIINGO_KEY.strip():
            log_info("Default: Using Tiingo (you're paying for it!)")
            return TiingoLoader()
        else:
            log_info("Default: No Tiingo key found, using Yahoo Finance")
            return YFinanceLoader()

class SmartDataLoader:
    """
    Smart data loader with automatic fallback capability
    """
    
    def __init__(self):
        self.primary_loader = None
        self.fallback_loader = None
        self.using_fallback = False
        
        # Determine primary and fallback loaders
        if TIINGO_KEY and TIINGO_KEY.strip():
            self.primary_loader = TiingoLoader()
            self.fallback_loader = YFinanceLoader()
            log_info("Smart loader: Primary=Tiingo, Fallback=Yahoo Finance")
        else:
            self.primary_loader = YFinanceLoader()
            log_info("Smart loader: Primary=Yahoo Finance (no Tiingo key)")
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """
        Update stocks with automatic fallback on failure
        """
        try:
            if self.using_fallback:
                log_info("Using fallback loader (Yahoo Finance)")
                return self.fallback_loader.update_all_stocks(stock_list, full_refresh, batch_size)
            else:
                log_info("Using primary loader (Tiingo)")
                result = self.primary_loader.update_all_stocks(stock_list, full_refresh, batch_size)
                
                # Check if Tiingo call was successful
                if result and result.get('success', False):
                    return result
                else:
                    log_warning("Tiingo failed, switching to Yahoo Finance fallback")
                    self.using_fallback = True
                    return self.fallback_loader.update_all_stocks(stock_list, full_refresh, batch_size)
                    
        except Exception as e:
            log_error(f"Primary loader failed: {e}")
            if not self.using_fallback and self.fallback_loader:
                log_warning("Switching to Yahoo Finance fallback")
                self.using_fallback = True
                return self.fallback_loader.update_all_stocks(stock_list, full_refresh, batch_size)
            else:
                raise e
    
    def get_data_source_info(self):
        """Get information about current data source"""
        if self.using_fallback:
            return {
                'source': 'Yahoo Finance (Fallback)',
                'reason': 'Tiingo failed or unavailable',
                'key_available': bool(TIINGO_KEY and TIINGO_KEY.strip())
            }
        else:
            if self.primary_loader and hasattr(self.primary_loader, '__class__') and 'Tiingo' in self.primary_loader.__class__.__name__:
                return {
                    'source': 'Tiingo (Primary)',
                    'reason': 'You\'re paying for it!',
                    'key_available': True
                }
            else:
                return {
                    'source': 'Yahoo Finance (Primary)',
                    'reason': 'No Tiingo API key',
                    'key_available': False
                }

# Keep existing classes for compatibility
class TiingoLoader:
    """Wrapper for existing Tiingo data loader to match YFinance interface."""
    
    def __init__(self):
        from src.storage import DataStorage
        self.storage = DataStorage()
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """Update stocks using Tiingo API."""
        try:
            from src.data_loader import update_all_stocks
            return update_all_stocks(full_refresh=full_refresh, stock_list=stock_list)
        except Exception as e:
            log_error(f"Tiingo data update failed: {e}")
            return {'success': False, 'error': str(e), 'updated': 0, 'total': len(stock_list)}
    
    def download_nasdaq_tickers(self):
        """Tiingo doesn't provide ticker list, use manual list."""
        from src.config import STOCK_LIST
        return STOCK_LIST
    
    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        """Tiingo doesn't support filtering, return all tickers."""
        import pandas as pd
        return pd.DataFrame([{'ticker': t, 'price': 0, 'avg_volume': 0} for t in tickers])

class YFinanceLoader:
    """Wrapper for YFinance loader (imported from existing module)"""
    
    def __init__(self):
        # Import here to avoid circular dependencies
        from src.yfinance_loader import YFinanceLoader as YFLoader
        self.loader = YFLoader()
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """Update stocks using Yahoo Finance API."""
        try:
            return self.loader.update_all_stocks(stock_list, full_refresh, batch_size)
        except Exception as e:
            log_error(f"Yahoo Finance data update failed: {e}")
            return {'success': False, 'error': str(e), 'updated': 0, 'total': len(stock_list)}
    
    def download_nasdaq_tickers(self):
        """Get ticker list from Yahoo Finance."""
        return self.loader.download_nasdaq_tickers()
    
    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        """Filter tickers using Yahoo Finance."""
        return self.loader.filter_tickers_by_criteria(tickers, min_price, min_volume, batch_size)

def get_smart_data_loader():
    """
    Get the smart data loader with automatic fallback capability
    
    Returns:
        SmartDataLoader instance with Tiingo/Yahoo Finance fallback
    """
    return SmartDataLoader()

# Legacy compatibility
def get_data_loader():
    """Legacy function - now uses smart loader"""
    return get_smart_data_loader()
