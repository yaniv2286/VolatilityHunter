"""
Yahoo Finance Data Loader
Provides unlimited free access to US stock data with optimized bulk downloading
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
    
    def download_batch(self, tickers, period='2y', max_retries=2):
        """
        Download historical data for multiple tickers using optimized bulk download.
        
        Args:
            tickers: List of ticker symbols
            period: Time period
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary of {ticker: DataFrame}
        """
        log_info(f"Bulk downloading {len(tickers)} stocks with period={period}...")
        
        results = {}
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use conservative bulk download without custom session
                start_time = time.time()
                data = yf.download(
                    tickers, 
                    period=period, 
                    progress=False, 
                    threads=5  # Reduced threading to avoid rate limits
                )
                
                download_time = time.time() - start_time
                log_info(f"Bulk download completed in {download_time:.2f} seconds")
                
                if isinstance(data.columns, pd.MultiIndex):
                    # Multiple tickers - process efficiently
                    for ticker in tickers:
                        try:
                            if ticker in data.columns.get_level_values(0):
                                ticker_data = data[ticker].copy()
                                ticker_data = ticker_data.reset_index()
                                ticker_data = ticker_data.rename(columns={'Date': 'date'})
                                
                                # Ensure column names are correct and drop NaN
                                ticker_data = ticker_data[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                                ticker_data = ticker_data.dropna(subset=['Close', 'High', 'Low', 'Open'])
                                
                                if len(ticker_data) > 0:
                                    results[ticker] = ticker_data
                            else:
                                log_warning(f"No data returned for {ticker}")
                        except Exception as e:
                            log_warning(f"Error processing {ticker}: {e}")
                else:
                    # Single ticker case
                    ticker = tickers[0]
                    ticker_data = data.copy()
                    ticker_data = ticker_data.reset_index()
                    ticker_data = ticker_data.rename(columns={'Date': 'date'})
                    ticker_data = ticker_data[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                    ticker_data = ticker_data.dropna(subset=['Close', 'High', 'Low', 'Open'])
                    
                    if len(ticker_data) > 0:
                        results[ticker] = ticker_data
                
                log_info(f"Successfully processed {len(results)}/{len(tickers)} stocks")
                return results
                
            except Exception as e:
                retry_count += 1
                if "Rate limit" in str(e) or "Too many requests" in str(e):
                    log_warning(f"Rate limit hit (attempt {retry_count}/{max_retries}): {e}")
                    if retry_count < max_retries:
                        log_info(f"Waiting 5 seconds before retry...")
                        time.sleep(5)
                    else:
                        log_error(f"Max retries reached for bulk download")
                        return results
                else:
                    log_error(f"Error in bulk download (attempt {retry_count}/{max_retries}): {e}")
                    if retry_count < max_retries:
                        log_info(f"Waiting 5 seconds before retry...")
                        time.sleep(5)
                    else:
                        log_error(f"Max retries reached for bulk download")
                        return results
        
        return results
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """
        Update historical data for all stocks using production batching for 2,150 stocks.
        
        Args:
            stock_list: List of ticker symbols (2,150 stocks)
            full_refresh: If True, download 2 years; if False, download last 7 days
            batch_size: Number of stocks per batch (50 for high-volume processing)
            
        Returns:
            Dictionary with update results
        """
        period = '2y' if full_refresh else '7d'
        log_info(f"Starting production batch update for {len(stock_list)} stocks with batch_size={batch_size}")
        
        start_time = time.time()
        updated_count = 0
        
        # Process in production batches with 10-second delays
        total_batches = (len(stock_list) + batch_size - 1) // batch_size
        
        for i in range(0, len(stock_list), batch_size):
            batch = stock_list[i:i+batch_size]
            batch_num = i // batch_size + 1
            
            log_info(f"Processing production batch {batch_num}/{total_batches}: {len(batch)} stocks")
            
            # Download batch with production retry mechanism
            batch_data = self.download_production_batch(batch, period=period, max_retries=2)
            
            # Save each stock's data with local persistence fallback
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
            
            # 10-second delay between batches to prevent YFRateLimitError
            if batch_num < total_batches:
                log_info("Production delay: Waiting 10 seconds before next batch...")
                time.sleep(10)
        
        total_time = time.time() - start_time
        log_info(f"Production batch update complete: {updated_count}/{len(stock_list)} stocks updated in {total_time:.2f} seconds")
        
        return {
            'success': True,
            'updated': updated_count,
            'total': len(stock_list),
            'timestamp': datetime.now().isoformat(),
            'download_time_seconds': total_time
        }
    
    def download_production_batch(self, tickers, period='7d', max_retries=2):
        """
        Download historical data for a production batch with high-volume API handling.
        
        Args:
            tickers: List of ticker symbols (up to 50)
            period: Time period
            max_retries: Maximum number of retry attempts
            
        Returns:
            Dictionary of {ticker: DataFrame}
        """
        log_info(f"Production batch downloading {len(tickers)} stocks with period={period}...")
        
        results = {}
        retry_count = 0
        
        while retry_count < max_retries:
            try:
                # Use production batch download with optimal settings
                start_time = time.time()
                data = yf.download(
                    tickers, 
                    period=period, 
                    progress=False, 
                    threads=True,
                    group_by='ticker'  # Group by ticker for efficient processing
                )
                
                download_time = time.time() - start_time
                log_info(f"Production batch download completed in {download_time:.2f} seconds")
                
                if data.empty:
                    log_warning(f"Production batch returned empty data (attempt {retry_count + 1}/{max_retries + 1})")
                    if retry_count < max_retries:
                        log_info("Production retry: Waiting 5 seconds before retry...")
                        time.sleep(5)
                        retry_count += 1
                        continue
                    else:
                        log_error(f"Production batch failed after max retries")
                        return results
                
                # Process each ticker in the batch with local persistence fallback
                for ticker in tickers:
                    try:
                        if ticker in data:
                            ticker_data = data[ticker]
                            if not ticker_data.empty:
                                results[ticker] = ticker_data
                            else:
                                # Use local persistence fallback
                                local_data = self._local_persistence_fallback(ticker)
                                if local_data is not None:
                                    results[ticker] = local_data
                                    log_info(f"[LOCAL FALLBACK] {ticker}: Used last known local price")
                        else:
                            # Use local persistence fallback
                            local_data = self._local_persistence_fallback(ticker)
                            if local_data is not None:
                                results[ticker] = local_data
                                log_info(f"[LOCAL FALLBACK] {ticker}: Used last known local price")
                    except Exception as e:
                        log_error(f"Error processing {ticker}: {e}")
                
                return results
                
            except Exception as e:
                log_error(f"Production batch error (attempt {retry_count + 1}/{max_retries + 1}): {e}")
                if retry_count < max_retries:
                    log_info("Production retry: Waiting 5 seconds before retry...")
                    time.sleep(5)
                    retry_count += 1
                else:
                    log_error(f"Production batch failed after max retries")
                    break
        
        return results
    
    def _local_persistence_fallback(self, ticker):
        """
        Production local persistence fallback - use last known price from local data.
        
        Args:
            ticker: Ticker symbol
            
        Returns:
            DataFrame with local data or None if not found
        """
        try:
            # Try to load from local storage
            local_data = self.storage.load_data(ticker)
            if local_data is not None and len(local_data) > 0:
                # Return the local data for continued processing
                return local_data
            else:
                # Silent fail - no local data available
                return None
        except Exception as e:
            # Only log actual errors, not missing data
            log_error(f"[LOCAL ERROR] {ticker}: Error accessing local data: {e}")
            return None
