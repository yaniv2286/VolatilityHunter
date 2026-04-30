#!/usr/bin/env python3
"""
Update market data using Tiingo API
"""

import os
import sys
import pandas as pd
import requests
from datetime import datetime, timedelta
from tqdm import tqdm
import time

# Add src to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.config import TIINGO_KEY
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables directly
import os
from dotenv import load_dotenv
load_dotenv()

# Use environment variable if config doesn't work
API_KEY = TIINGO_KEY or os.getenv('TIINGO_API_KEY') or os.getenv('TIINGO_API_KEY')

class DataUpdater:
    """Update market data using Tiingo API"""
    
    def __init__(self):
        self.api_key = API_KEY
        self.base_url = "https://api.tiingo.com/tiingo"
        self.data_dir = "data"
        
    def update_ticker_data(self, ticker, start_date=None, end_date=None):
        """Update data for a single ticker"""
        try:
            if not self.api_key:
                logger.error("No Tiingo API key found")
                return False
                
            # Set default dates
            if end_date is None:
                end_date = datetime.now().strftime('%Y-%m-%d')
            if start_date is None:
                start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
            
            # Make API request
            url = f"{self.base_url}/daily/{ticker}/prices"
            params = {
                'token': self.api_key,
                'startDate': start_date,
                'endDate': end_date,
                'format': 'json'
            }
            
            response = requests.get(url, params=params)
            response.raise_for_status()
            
            data = response.json()
            
            if not data:
                logger.warning(f"No data returned for {ticker}")
                return False
            
            # Debug: Log response structure
            logger.info(f"Response for {ticker}: {type(data)} - {len(data)} items")
            if isinstance(data, list) and len(data) > 0:
                logger.info(f"Sample item keys: {list(data[0].keys())}")
                
            # Convert to DataFrame
            df = pd.DataFrame(data)
            
            if df.empty:
                logger.warning(f"Empty data for {ticker}")
                return False
            
            # Convert date column - check if 'date' column exists
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
            else:
                # Try to find date-like column
                date_cols = [col for col in df.columns if 'date' in col.lower()]
                if date_cols:
                    df['date'] = pd.to_datetime(df[date_cols[0]])
                else:
                    # Use index if it's date-like
                    if hasattr(df.index, 'to_datetime'):
                        df['date'] = pd.to_datetime(df.index)
                    else:
                        raise ValueError("No date column found in response")
            
            # Load existing data
            file_path = os.path.join(self.data_dir, f"{ticker.lower()}.parquet")
            existing_data = None
            
            if os.path.exists(file_path):
                existing_data = pd.read_parquet(file_path)
                if 'date' in existing_data.columns:
                    existing_data['date'] = pd.to_datetime(existing_data['date'])
                else:
                    # Try to set date from index if it's date-like
                    if hasattr(existing_data.index, 'to_datetime'):
                        existing_data['date'] = pd.to_datetime(existing_data.index)
                    else:
                        logger.warning(f"Existing data for {ticker} has no date column, skipping merge")
                        existing_data = None
                
                if existing_data is not None:
                    # Remove overlapping dates
                    df = df[~df['date'].isin(existing_data['date'])]
                    
                    # Combine data
                    combined_data = pd.concat([existing_data, df], ignore_index=True)
                    combined_data = combined_data.sort_values('date').reset_index(drop=True)
                else:
                    combined_data = df.sort_values('date').reset_index(drop=True)
            else:
                combined_data = df.sort_values('date').reset_index(drop=True)
            
            # Save updated data
            combined_data.to_parquet(file_path, index=False)
            
            logger.info(f"Updated {ticker}: {len(df)} new records, total: {len(combined_data)} records")
            return True
            
        except Exception as e:
            logger.error(f"Error updating {ticker}: {e}")
            return False
    
    def update_all_tickers(self, tickers=None):
        """Update data for all tickers"""
        if tickers is None:
            # Load tickers from file
            tickers_file = "tickers.txt"
            if os.path.exists(tickers_file):
                with open(tickers_file, 'r') as f:
                    tickers = [line.strip() for line in f if line.strip()]
            else:
                tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA']  # Default tickers
        
        logger.info(f"Updating data for {len(tickers)} tickers")
        
        success_count = 0
        for ticker in tqdm(tickers, desc="Updating tickers"):
            if self.update_ticker_data(ticker):
                success_count += 1
            time.sleep(0.1)  # Rate limiting
        
        logger.info(f"Successfully updated {success_count}/{len(tickers)} tickers")
        return success_count == len(tickers)

if __name__ == "__main__":
    updater = DataUpdater()
    
    # Update key tickers
    key_tickers = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'TSLA', 'AMZN', 'META', 'JPM']
    
    print("🚀 Updating Market Data")
    print("=" * 50)
    
    success = updater.update_all_tickers(key_tickers)
    
    if success:
        print("✅ Data update completed successfully!")
    else:
        print("⚠️  Data update completed with some errors")
    
    print("=" * 50)
    print("📊 Checking updated data...")
    
    # Check updated data
    os.system("python check_data_dates.py")
