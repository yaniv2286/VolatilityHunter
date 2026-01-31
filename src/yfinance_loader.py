"""
Yahoo Finance Data Loader
Provides unlimited free access to US stock data
"""

import yfinance as yf
import pandas as pd
import requests
from datetime import datetime, timedelta
from src.notifications import log_info, log_error, log_warning
from src.storage import DataStorage
import time

class YFinanceLoader:
    """Handles data loading from Yahoo Finance."""
    
    def __init__(self):
        self.storage = DataStorage()
    
    def download_nasdaq_tickers(self):
        """Download complete list of US stock tickers."""
        try:
            log_info("Downloading NASDAQ ticker list...")
            url = "https://raw.githubusercontent.com/rreichel3/US-Stock-Symbols/main/all/all_tickers.txt"
            
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                tickers = response.text.strip().split('\n')
                tickers = [t.strip() for t in tickers if t.strip()]
                log_info(f"Downloaded {len(tickers)} tickers")
                return tickers
            else:
                log_error(f"Failed to download tickers: {response.status_code}")
                return []
        except Exception as e:
            log_error(f"Error downloading tickers: {e}")
            return []
    
    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        """
        Filter tickers by price and volume criteria.
        
        Args:
            tickers: List of ticker symbols
            min_price: Minimum stock price
            min_volume: Minimum average daily volume
            batch_size: Number of stocks to fetch per batch
            
        Returns:
            DataFrame with filtered stocks
        """
        log_info(f"Filtering {len(tickers)} tickers (Price>${min_price}, Volume>{min_volume:,})...")
        
        results = []
        total_batches = (len(tickers) + batch_size - 1) // batch_size
        
        for i in range(0, len(tickers), batch_size):
            batch = tickers[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            log_info(f"Processing batch {batch_num}/{total_batches} ({len(batch)} stocks)...")
            
            try:
                # Download last 5 days to get current price and volume
                data = yf.download(batch, period='5d', progress=False, threads=True)
                
                if isinstance(data.columns, pd.MultiIndex):
                    # Multiple tickers
                    for ticker in batch:
                        try:
                            if ticker in data['Close'].columns:
                                close_prices = data['Close'][ticker].dropna()
                                volumes = data['Volume'][ticker].dropna()
                                
                                if len(close_prices) > 0 and len(volumes) > 0:
                                    latest_price = close_prices.iloc[-1]
                                    avg_volume = volumes.mean()
                                    
                                    if latest_price > min_price and avg_volume > min_volume:
                                        results.append({
                                            'ticker': ticker,
                                            'price': latest_price,
                                            'avg_volume': avg_volume
                                        })
                        except:
                            pass
                else:
                    # Single ticker
                    if len(data) > 0:
                        latest_price = data['Close'].iloc[-1]
                        avg_volume = data['Volume'].mean()
                        
                        if latest_price > min_price and avg_volume > min_volume:
                            results.append({
                                'ticker': batch[0],
                                'price': latest_price,
                                'avg_volume': avg_volume
                            })
                
                # Small delay to be respectful
                time.sleep(0.5)
                
            except Exception as e:
                log_warning(f"Error processing batch {batch_num}: {e}")
        
        df = pd.DataFrame(results)
        log_info(f"Filtered to {len(df)} stocks meeting criteria")
        
        return df
    
    def download_historical_data(self, ticker, period='2y'):
        """
        Download historical data for a single ticker.
        
        Args:
            ticker: Stock symbol
            period: Time period (e.g., '2y', '1y', '6mo')
            
        Returns:
            DataFrame with OHLCV data
        """
        try:
            data = yf.download(ticker, period=period, progress=False)
            
            if len(data) == 0:
                log_warning(f"No data returned for {ticker}")
                return None
            
            # Rename columns to match expected format
            data = data.reset_index()
            data = data.rename(columns={
                'Date': 'date',
                'Open': 'Open',
                'High': 'High',
                'Low': 'Low',
                'Close': 'Close',
                'Volume': 'Volume'
            })
            
            # Select only needed columns
            data = data[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
            
            # Drop any NaN rows
            data = data.dropna(subset=['Close', 'High', 'Low', 'Open'])
            
            return data
            
        except Exception as e:
            log_error(f"Error downloading {ticker}: {e}")
            return None
    
    def download_batch(self, tickers, period='2y'):
        """
        Download historical data for multiple tickers in parallel.
        
        Args:
            tickers: List of ticker symbols
            period: Time period
            
        Returns:
            Dictionary of {ticker: DataFrame}
        """
        log_info(f"Downloading {len(tickers)} stocks with period={period}...")
        
        results = {}
        
        try:
            # Download all tickers at once (yfinance handles parallelization)
            data = yf.download(tickers, period=period, progress=False, threads=True, group_by='ticker')
            
            if isinstance(data.columns, pd.MultiIndex):
                # Multiple tickers
                for ticker in tickers:
                    try:
                        if ticker in data.columns.get_level_values(0):
                            ticker_data = data[ticker].copy()
                            ticker_data = ticker_data.reset_index()
                            ticker_data = ticker_data.rename(columns={'Date': 'date'})
                            
                            # Ensure column names are correct
                            ticker_data = ticker_data[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                            ticker_data = ticker_data.dropna(subset=['Close', 'High', 'Low', 'Open'])
                            
                            if len(ticker_data) > 0:
                                results[ticker] = ticker_data
                    except Exception as e:
                        log_warning(f"Error processing {ticker}: {e}")
            else:
                # Single ticker
                ticker = tickers[0]
                ticker_data = data.copy()
                ticker_data = ticker_data.reset_index()
                ticker_data = ticker_data.rename(columns={'Date': 'date'})
                ticker_data = ticker_data[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                ticker_data = ticker_data.dropna(subset=['Close', 'High', 'Low', 'Open'])
                
                if len(ticker_data) > 0:
                    results[ticker] = ticker_data
            
            log_info(f"Successfully downloaded {len(results)}/{len(tickers)} stocks")
            
        except Exception as e:
            log_error(f"Error in batch download: {e}")
        
        return results
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """
        Update historical data for all stocks in the list.
        
        Args:
            stock_list: List of ticker symbols
            full_refresh: If True, download 2 years; if False, download last 7 days
            batch_size: Number of stocks per batch
            
        Returns:
            Dictionary with update results
        """
        period = '2y' if full_refresh else '7d'
        log_info(f"Starting {'full' if full_refresh else 'incremental'} update for {len(stock_list)} stocks")
        
        updated_count = 0
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            log_info(f"Batch {batch_num}/{total_batches}: {len(batch)} stocks")
            
            # Download batch
            batch_data = self.download_batch(batch, period=period)
            
            # Save each stock
            for ticker, new_df in batch_data.items():
                try:
                    if full_refresh:
                        # Full refresh - just save new data
                        self.storage.save_data(new_df, ticker)
                    else:
                        # Incremental - merge with existing
                        existing_df = self.storage.load_data(ticker)
                        if existing_df is not None:
                            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                            combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
                            combined_df = combined_df.sort_values('date').reset_index(drop=True)
                            self.storage.save_data(combined_df, ticker)
                        else:
                            self.storage.save_data(new_df, ticker)
                    
                    updated_count += 1
                except Exception as e:
                    log_error(f"Error saving {ticker}: {e}")
        
        log_info(f"Update complete: {updated_count}/{len(stock_list)} stocks updated")
        
        return {
            'success': True,
            'updated': updated_count,
            'total': len(stock_list),
            'timestamp': datetime.now().isoformat()
        }
