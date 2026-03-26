"""
Production Data Loader Factory - Tiingo Professional API Only
100% Tiingo integration - No Yahoo Finance, No Fallback Logic
"""

import os
import requests
import pandas as pd
import urllib3
from datetime import datetime, timedelta
from src.config import TIINGO_KEY
from src.notifications import log_info, log_warning, log_error
from src.log_sanitizer import log_error_with_tracking

# Disable SSL warnings for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

def get_data_loader():
    """
    Production data loader - Tiingo Professional API only.
    100% free of Yahoo Finance and fallback logic.
    
    Returns:
        TiingoLoader instance using TIINGO_API_KEY
    """
    log_info("Production: Using Tiingo Professional API - No Fallback Logic")
    return TiingoLoader()

class TiingoLoader:
    """
    Tiingo Professional API data loader.
    Bulk metadata endpoint for efficient data fetching.
    """
    
    def __init__(self):
        from src.storage import DataStorage
        self.storage = DataStorage()
        self.api_key = TIINGO_KEY
        if not self.api_key:
            log_error("TIINGO_API_KEY not found in environment")
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """
        Update stocks using Tiingo Bulk Metadata API.
        3 requests for 2,147 tickers (1000 per request).
        No Yahoo Finance, no fallback logic.
        """
        if not self.api_key:
            log_error("Cannot update stocks: TIINGO_API_KEY missing")
            return {'success': False, 'error': 'TIINGO_API_KEY missing', 'updated': 0, 'total': len(stock_list)}
        
        try:
            log_info(f"Production: Fetching latest prices for {len(stock_list)} tickers via Tiingo Bulk Metadata API")
            
            # Use Tiingo IEX endpoint for real-time prices
            url = "https://api.tiingo.com/iex"
            
            # Split into chunks of 100 (hard limit to avoid 502 Bad Gateway)
            chunk_size = 100
            all_prices = {}
            updated_count = 0
            
            for i in range(0, len(stock_list), chunk_size):
                chunk = stock_list[i:i + chunk_size]
                
                params = {
                    'tickers': ','.join(chunk),
                    'token': self.api_key  # Tiingo uses token as query parameter
                }
                headers = {
                    'Content-Type': 'application/json'
                }
                
                response = requests.get(url, params=params, headers=headers, timeout=60, verify=False)
                response.raise_for_status()
                
                data = response.json()
                
                # Process IEX response format
                for ticker_data in data:
                    if 'ticker' in ticker_data:
                        ticker = ticker_data['ticker']
                        # Use tngoLast if last is null (real-time price)
                        latest_price = ticker_data.get('tngoLast') or ticker_data.get('last')
                        volume = ticker_data.get('volume', 0)
                        
                        if latest_price and latest_price > 0:
                            all_prices[ticker] = {
                                'price': latest_price,
                                'volume': volume,
                                'date': datetime.now().strftime('%Y-%m-%d')
                            }
                            updated_count += 1
                            if updated_count <= 10:  # Log first 10 for verification
                                log_info(f"Got price for {ticker}: ${latest_price:.2f} (vol: {volume:,})")
                
                # Small delay between chunks (22 small batches for 2,147 tickers)
                if i + chunk_size < len(stock_list):
                    import time
                    time.sleep(1.0)  # Respectful delay between requests
            
            log_info(f"Production: Successfully fetched {updated_count}/{len(stock_list)} ticker prices in {len(stock_list)//chunk_size + 1} requests (100 tickers each)")
            
            # Return prices directly (trading loop will use them)
            return {'success': True, 'updated': updated_count, 'total': len(stock_list), 'prices': {k: v['price'] for k, v in all_prices.items()},
                'metadata': all_prices}
            
        except requests.exceptions.RequestException as e:
            log_error(f"Tiingo Bulk API request failed: {e}")
            return {'success': False, 'error': f'API request failed: {e}', 'updated': 0, 'total': len(stock_list)}
        except Exception as e:
            log_error_with_tracking(f"Tiingo bulk update failed: {e}")
            return {'success': False, 'error': str(e), 'updated': 0, 'total': len(stock_list)}
    
    def download_nasdaq_tickers(self):
        """Tiingo doesn't provide ticker list, use manual list."""
        from src.config import STOCK_LIST
        return STOCK_LIST
    
    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        """Tiingo doesn't support filtering, return all tickers."""
        return pd.DataFrame([{'ticker': t, 'price': 0, 'avg_volume': 0} for t in tickers])
