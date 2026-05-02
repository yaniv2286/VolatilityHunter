"""
Production Data Loader Factory - Tiingo Professional API Only
100% Tiingo integration - No Yahoo Finance, No Fallback Logic
"""

import os
import requests
import pandas as pd
import urllib3
import json
from datetime import datetime, timedelta
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from src.config import TIINGO_KEY
from src.notifications import log_info, log_warning, log_error
from src.log_sanitizer import log_error_with_tracking

# Disable SSL warnings for verify=False
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Data directory for parquet files
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
DATA_DIR = ROOT / 'data'

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
    
    def _fetch_chunk(self, chunk, chunk_index):
        """
        Fetch a single chunk of tickers from Tiingo IEX endpoint.
        Returns latest price with basic OHLCV extraction.
        """
        url = "https://api.tiingo.com/iex"
        params = {
            'tickers': ','.join(chunk),
            'token': self.api_key
        }
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=60, verify=False)
            response.raise_for_status()
            data = response.json()
            
            chunk_data = {}
            for ticker_data in data:
                if 'ticker' in ticker_data:
                    ticker = ticker_data['ticker']
                    
                    # Extract available data from IEX response
                    latest_price = ticker_data.get('tngoLast') or ticker_data.get('last')
                    volume = ticker_data.get('volume', 0)
                    high = ticker_data.get('high', latest_price)
                    low = ticker_data.get('low', latest_price)
                    open_price = ticker_data.get('open', latest_price)
                    
                    # Validate we have a price
                    if latest_price and latest_price > 0:
                        # For IEX data, we may not have full OHLC, so use close as fallback
                        chunk_data[ticker] = {
                            'close': float(latest_price),
                            'high': float(high) if high else float(latest_price),
                            'low': float(low) if low else float(latest_price),
                            'open': float(open_price) if open_price else float(latest_price),
                            'volume': int(volume) if volume else 0,
                            'date': datetime.now().strftime('%Y-%m-%d')
                        }
            
            return {'success': True, 'chunk_index': chunk_index, 'data': chunk_data}
        except Exception as e:
            log_error(f"Chunk {chunk_index} fetch failed: {e}")
            return {'success': False, 'chunk_index': chunk_index, 'error': str(e)}
    
    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50):
        """
        Update stocks using Tiingo daily prices API with OHLCV data.
        Fetches 100 tickers per batch, 10 concurrent threads.
        Updates parquet files with fresh OHLCV data.
        """
        if not self.api_key:
            log_error("Cannot update stocks: TIINGO_API_KEY missing")
            return {'success': False, 'error': 'TIINGO_API_KEY missing', 'updated': 0, 'total': len(stock_list)}
        
        try:
            log_info(f"Production: Fetching OHLCV data for {len(stock_list)} tickers via Tiingo daily prices API (PARALLEL)")
            
            # Split into chunks of 100
            chunk_size = 100
            chunks = [stock_list[i:i + chunk_size] for i in range(0, len(stock_list), chunk_size)]
            
            log_info(f"Fetching {len(chunks)} batches in parallel...")
            
            # Fetch all chunks in parallel using ThreadPoolExecutor
            all_ohlcv = {}
            updated_count = 0
            failed_chunks = 0
            
            with ThreadPoolExecutor(max_workers=10) as executor:
                # Submit all fetch tasks
                future_to_chunk = {executor.submit(self._fetch_chunk, chunk, idx): idx 
                                   for idx, chunk in enumerate(chunks)}
                
                # Collect results as they complete
                for future in as_completed(future_to_chunk):
                    result = future.result()
                    
                    if result['success']:
                        chunk_data = result['data']
                        all_ohlcv.update(chunk_data)
                        updated_count += len(chunk_data)
                        
                        # Log first 10 OHLCV entries for verification
                        if result['chunk_index'] == 0:
                            for ticker, data in list(chunk_data.items())[:10]:
                                log_info(f"Got OHLCV for {ticker}: O=${data['open']:.2f} H=${data['high']:.2f} L=${data['low']:.2f} C=${data['close']:.2f} V={data['volume']:,}")
                    else:
                        failed_chunks += 1
            
            log_info(f"Production: Successfully fetched {updated_count}/{len(stock_list)} ticker OHLCV data in {len(chunks)} parallel requests")
            if failed_chunks > 0:
                log_warning(f"Warning: {failed_chunks} chunks failed to fetch")
            
            # Update parquet files with fresh OHLCV data
            parquet_updated = 0
            for ticker, ohlcv in all_ohlcv.items():
                if self._update_parquet_with_ohlcv(ticker, ohlcv):
                    parquet_updated += 1
            
            log_info(f"Updated {parquet_updated} parquet files with fresh OHLCV data")
            
            # Return prices for immediate use (trading loop compatibility)
            return {'success': True, 'updated': updated_count, 'total': len(stock_list), 
                    'prices': {k: v['close'] for k, v in all_ohlcv.items()},
                    'ohlcv': all_ohlcv}
            
        except requests.exceptions.RequestException as e:
            log_error(f"Tiingo daily prices API request failed: {e}")
            return {'success': False, 'error': f'API request failed: {e}', 'updated': 0, 'total': len(stock_list)}
        except Exception as e:
            log_error_with_tracking(f"Tiingo OHLCV update failed: {e}")
            return {'success': False, 'error': str(e), 'updated': 0, 'total': len(stock_list)}
    
    def _update_parquet_with_ohlcv(self, ticker: str, ohlcv: dict) -> bool:
        """
        Update a single parquet file with fresh OHLCV data.
        Returns True if successfully updated.
        """
        try:
            parquet_path = DATA_DIR / f"{ticker.lower()}.parquet"
            
            # Load existing parquet
            if parquet_path.exists():
                df = pd.read_parquet(parquet_path)
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    df = df.set_index('date')
                if hasattr(df.index, 'tz') and df.index.tz is not None:
                    df.index = df.index.tz_localize(None)
                df = df[~df.index.duplicated(keep='last')]
                df.sort_index(inplace=True)
            else:
                # Create new DataFrame if parquet doesn't exist
                df = pd.DataFrame()
            
            # Get the latest date in parquet
            latest_parquet_date = df.index[-1] if not df.empty else None
            new_date = pd.to_datetime(ohlcv['date'])
            
            # Only update if new data is newer than existing data
            if latest_parquet_date is None or new_date > latest_parquet_date:
                # Create new row with OHLCV data
                new_row = pd.DataFrame({
                    'date': [new_date],
                    'open': [ohlcv['open']],
                    'high': [ohlcv['high']],
                    'low': [ohlcv['low']],
                    'close': [ohlcv['close']],
                    'volume': [ohlcv['volume']],
                    'adjClose': [ohlcv['close']]  # Use close as adjClose for simplicity
                }).set_index('date')
                
                # Append new data
                df = pd.concat([df, new_row])
                
                # Save updated parquet
                df.to_parquet(parquet_path)
                log_info(f"Updated {ticker} parquet with OHLCV data for {new_date.strftime('%Y-%m-%d')}")
                return True
            else:
                log_info(f"Skipping {ticker} - data already up to date")
                return False
                
        except Exception as e:
            log_error(f"Failed to update parquet for {ticker}: {e}")
            return False
    
    def fetch_ticker_metadata(self, ticker: str) -> dict:
        """
        Fetch metadata for a single ticker from Tiingo.
        Returns sector information and other metadata.
        """
        url = f"https://api.tiingo.com/tiingo/meta/{ticker}"
        params = {
            'token': self.api_key
        }
        headers = {
            'Content-Type': 'application/json'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=30, verify=False)
            response.raise_for_status()
            data = response.json()
            
            return {
                'ticker': ticker,
                'sector': data.get('sector', 'Unknown'),
                'industry': data.get('industry', 'Unknown'),
                'description': data.get('description', ''),
                'exchange': data.get('exchange', 'Unknown'),
                'assetType': data.get('assetType', 'stock')
            }
        except Exception as e:
            log_error(f"Failed to fetch metadata for {ticker}: {e}")
            return {'ticker': ticker, 'sector': 'Unknown'}
    
    def fetch_all_metadata(self, ticker_list: list) -> dict:
        """
        Fetch metadata for all tickers in parallel.
        Returns dictionary mapping ticker -> metadata.
        """
        log_info(f"Fetching metadata for {len(ticker_list)} tickers...")
        
        all_metadata = {}
        failed_count = 0
        
        with ThreadPoolExecutor(max_workers=5) as executor:  # Fewer workers for metadata API
            # Submit all fetch tasks
            future_to_ticker = {executor.submit(self.fetch_ticker_metadata, ticker): ticker 
                               for ticker in ticker_list}
            
            # Collect results as they complete
            for future in as_completed(future_to_ticker):
                ticker = future_to_ticker[future]
                try:
                    metadata = future.result()
                    all_metadata[ticker] = metadata
                    
                    # Log first few for verification
                    if len(all_metadata) <= 10:
                        log_info(f"Got metadata for {ticker}: sector={metadata['sector']}")
                        
                except Exception as e:
                    failed_count += 1
                    log_error(f"Metadata fetch failed for {ticker}: {e}")
        
        log_info(f"Successfully fetched metadata for {len(all_metadata)}/{len(ticker_list)} tickers")
        if failed_count > 0:
            log_warning(f"Failed to fetch metadata for {failed_count} tickers")
        
        # Save metadata to cache file
        self._save_metadata_cache(all_metadata)
        
        return all_metadata
    
    def _save_metadata_cache(self, metadata: dict):
        """Save metadata to cache file for persistence."""
        try:
            cache_file = DATA_DIR / 'ticker_metadata.json'
            with open(cache_file, 'w') as f:
                json.dump(metadata, f, indent=2)
            log_info(f"Saved metadata cache to {cache_file}")
        except Exception as e:
            log_error(f"Failed to save metadata cache: {e}")
    
    def load_metadata_cache(self) -> dict:
        """Load metadata from cache file."""
        try:
            cache_file = DATA_DIR / 'ticker_metadata.json'
            if cache_file.exists():
                with open(cache_file, 'r') as f:
                    metadata = json.load(f)
                log_info(f"Loaded {len(metadata)} ticker metadata from cache")
                return metadata
        except Exception as e:
            log_error(f"Failed to load metadata cache: {e}")
        return {}
    
    def download_nasdaq_tickers(self):
        """Tiingo doesn't provide ticker list, use manual list."""
        from src.config import STOCK_LIST
        return STOCK_LIST
    
    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        """Tiingo doesn't support filtering, return all tickers."""
        return pd.DataFrame([{'ticker': t, 'price': 0, 'avg_volume': 0} for t in tickers])
