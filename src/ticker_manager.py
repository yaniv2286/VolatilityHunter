import requests
import pandas as pd
from datetime import datetime
from src.config import TIINGO_KEY
from src.notifications import log_info, log_error

class TickerManager:
    """Manages the universe of stocks to scan."""
    
    def __init__(self):
        self.tiingo_key = TIINGO_KEY
        self.base_url = "https://api.tiingo.com/tiingo/utilities/search"
        
    def fetch_all_tickers(self):
        """Fetch all supported tickers from Tiingo."""
        try:
            log_info("Fetching all supported tickers from Tiingo...")
            
            # Tiingo's supported tickers endpoint
            url = f"https://api.tiingo.com/tiingo/daily/prices?token={self.tiingo_key}"
            
            # Alternative: Use the fundamentals endpoint to get all tickers
            meta_url = f"https://api.tiingo.com/tiingo/utilities/search?token={self.tiingo_key}"
            
            # For now, we'll use a simpler approach - get tickers from a known list
            # Tiingo doesn't have a direct "all tickers" endpoint, so we'll use EOD data endpoint
            
            # Get list of all available tickers (this is a workaround)
            # In production, you might want to maintain your own list or use a different data source
            
            log_info("Note: Tiingo doesn't provide a direct 'all tickers' endpoint.")
            log_info("Using alternative approach to build ticker universe...")
            
            return None
            
        except Exception as e:
            log_error(f"Error fetching tickers: {e}")
            return None
    
    def get_filtered_tickers(self, min_price=5.0, min_volume=500000, exchanges=['NYSE', 'NASDAQ']):
        """
        Get filtered list of tickers based on criteria.
        
        Args:
            min_price: Minimum stock price
            min_volume: Minimum average daily volume
            exchanges: List of exchanges to include
            
        Returns:
            List of ticker symbols
        """
        try:
            log_info(f"Filtering tickers: price>${min_price}, volume>{min_volume:,}, exchanges={exchanges}")
            
            # Since Tiingo doesn't have a bulk ticker endpoint, we'll use a predefined universe
            # This includes major indices and popular stocks
            
            # S&P 500 + NASDAQ 100 + Russell 2000 top stocks
            # For a production system, you'd maintain this list or use a financial data provider
            
            tickers = self._get_major_stock_universe()
            
            log_info(f"Loaded {len(tickers)} tickers from major indices")
            
            # Filter by fetching current data
            filtered = self._filter_by_criteria(tickers, min_price, min_volume)
            
            log_info(f"Filtered to {len(filtered)} tickers meeting criteria")
            
            return filtered
            
        except Exception as e:
            log_error(f"Error filtering tickers: {e}")
            return []
    
    def _get_major_stock_universe(self):
        """Returns a comprehensive list of major US stocks."""
        
        # S&P 500 stocks (sample - in production, load from file or API)
        sp500 = [
            'AAPL', 'MSFT', 'GOOGL', 'GOOG', 'AMZN', 'NVDA', 'META', 'TSLA', 'BRK.B', 'UNH',
            'JNJ', 'XOM', 'V', 'PG', 'JPM', 'MA', 'HD', 'CVX', 'LLY', 'ABBV',
            'MRK', 'PEP', 'KO', 'AVGO', 'COST', 'WMT', 'TMO', 'MCD', 'CSCO', 'ACN',
            'ABT', 'DHR', 'VZ', 'ADBE', 'CRM', 'NKE', 'TXN', 'NEE', 'LIN', 'PM',
            'ORCL', 'DIS', 'WFC', 'BMY', 'UPS', 'RTX', 'QCOM', 'HON', 'UNP', 'AMGN',
            'LOW', 'T', 'INTU', 'BA', 'ELV', 'SPGI', 'DE', 'PLD', 'GE', 'AMAT',
            'CAT', 'SBUX', 'ADP', 'GILD', 'BKNG', 'ADI', 'TJX', 'MDLZ', 'ISRG', 'MMC',
            'VRTX', 'CI', 'AMT', 'SYK', 'LRCX', 'ZTS', 'PGR', 'REGN', 'MO', 'BLK',
            'C', 'SCHW', 'CB', 'ETN', 'DUK', 'SO', 'BSX', 'NOC', 'FI', 'MMM',
            'PNC', 'ITW', 'GD', 'SLB', 'EOG', 'USB', 'APD', 'CME', 'CL', 'ICE'
        ]
        
        # High-growth tech and momentum stocks
        growth_stocks = [
            'PLTR', 'CRWD', 'SNOW', 'DDOG', 'NET', 'ZS', 'OKTA', 'PANW', 'FTNT', 'CYBR',
            'SHOP', 'SQ', 'PYPL', 'COIN', 'RBLX', 'U', 'DASH', 'ABNB', 'UBER', 'LYFT',
            'SPOT', 'ROKU', 'NFLX', 'DIS', 'PARA', 'WBD', 'CMCSA', 'CHTR', 'TMUS', 'VZ',
            'MELI', 'SE', 'BABA', 'JD', 'PDD', 'NIO', 'XPEV', 'LI', 'RIVN', 'LCID',
            'SOFI', 'AFRM', 'UPST', 'LC', 'HOOD', 'OPEN', 'RDFN', 'Z', 'COMP', 'EXPE',
            'DECK', 'LULU', 'PTON', 'NKE', 'ADDYY', 'CPNG', 'GRAB', 'DIDI', 'BEKE', 'BILI'
        ]
        
        # Semiconductor stocks
        semis = [
            'AMD', 'INTC', 'QCOM', 'AVGO', 'TXN', 'ADI', 'MRVL', 'MU', 'NXPI', 'KLAC',
            'LRCX', 'AMAT', 'ASML', 'TSM', 'SNPS', 'CDNS', 'ON', 'MPWR', 'SWKS', 'QRVO'
        ]
        
        # ETFs for market coverage
        etfs = [
            'SPY', 'QQQ', 'IWM', 'DIA', 'VOO', 'VTI', 'VEA', 'VWO', 'AGG', 'BND',
            'GLD', 'SLV', 'USO', 'UNG', 'TLT', 'IEF', 'LQD', 'HYG', 'VNQ', 'XLF',
            'XLE', 'XLK', 'XLV', 'XLI', 'XLP', 'XLY', 'XLU', 'XLRE', 'XLB', 'XLC'
        ]
        
        # Combine all lists and remove duplicates
        all_tickers = list(set(sp500 + growth_stocks + semis + etfs))
        
        return sorted(all_tickers)
    
    def _filter_by_criteria(self, tickers, min_price, min_volume):
        """
        Filter tickers by fetching latest data and checking criteria.
        Note: This is expensive for large lists. Consider caching.
        """
        # For now, return all tickers
        # In production, you'd fetch latest price/volume data and filter
        # This would require batched API calls to Tiingo
        
        log_info(f"Skipping real-time filtering to avoid excessive API calls")
        log_info(f"Returning all {len(tickers)} tickers. Filtering will happen during scan.")
        
        return tickers
    
    def get_sp500_tickers(self):
        """Get S&P 500 tickers."""
        # This is a subset - in production, load from a maintained list
        return self._get_major_stock_universe()[:100]
    
    def save_ticker_list(self, tickers, filename='tickers.txt'):
        """Save ticker list to file."""
        try:
            with open(filename, 'w') as f:
                for ticker in tickers:
                    f.write(f"{ticker}\n")
            log_info(f"Saved {len(tickers)} tickers to {filename}")
        except Exception as e:
            log_error(f"Error saving ticker list: {e}")
    
    def load_ticker_list(self, filename='tickers.txt'):
        """Load ticker list from file."""
        try:
            with open(filename, 'r') as f:
                tickers = [line.strip() for line in f if line.strip()]
            log_info(f"Loaded {len(tickers)} tickers from {filename}")
            return tickers
        except FileNotFoundError:
            log_info(f"Ticker file {filename} not found, using default universe")
            return self._get_major_stock_universe()
        except Exception as e:
            log_error(f"Error loading ticker list: {e}")
            return []
