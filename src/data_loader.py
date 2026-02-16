import pandas as pd
import numpy as np
import requests
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, Any
from src.config import TIINGO_KEY, TIINGO_BASE_URL, BATCH_SIZE, STOCK_LIST
from src.storage import DataStorage
from src.notifications import log_info, log_error, log_warning

def fetch_tiingo_data(tickers, start_date=None, end_date=None):
    if not TIINGO_KEY:
        log_error("TIINGO_KEY not set in environment variables")
        return {}
    
    if start_date is None:
        start_date = '2000-01-01'  # Full historical data instead of 2-year limit
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_KEY}'
    }
    
    results = {}
    
    # Process one ticker at a time to avoid URL length limits
    for i, ticker in enumerate(tickers):
        try:
            log_info(f"Fetching {ticker} ({i+1}/{len(tickers)})")
            
            url = f"{TIINGO_BASE_URL}/prices"
            params = {
                'tickers': ticker,
                'startDate': start_date,
                'endDate': end_date,
                'resampleFreq': 'daily'
            }
            
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            if data and len(data) > 0:
                item = data[0]
                ticker_name = item.get('ticker')
                if ticker_name and 'priceData' in item:
                    df = pd.DataFrame(item['priceData'])
                    if not df.empty:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.rename(columns={
                            'open': 'Open',
                            'high': 'High',
                            'low': 'Low',
                            'close': 'Close',
                            'volume': 'Volume'
                        })
                        df = df[['date', 'Open', 'High', 'Low', 'Close', 'Volume']]
                        df = df.sort_values('date').reset_index(drop=True)
                        results[ticker_name] = df
                        log_info(f"Fetched {len(df)} rows for {ticker_name}")
                    else:
                        log_warning(f"No price data available for {ticker}")
                else:
                    log_warning(f"Invalid data format for {ticker}")
            else:
                log_warning(f"No data returned for {ticker}")
            
            # Rate limiting: small delay between requests
            time.sleep(0.1)
            
        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 404:
                log_warning(f"Ticker {ticker} not found on Tiingo (possibly delisted)")
            else:
                log_error(f"HTTP error fetching {ticker}: {e}")
        except requests.exceptions.RequestException as e:
            log_error(f"Network error fetching {ticker}: {e}")
        except Exception as e:
            log_error(f"Error processing {ticker}: {e}")
    
    return results

def update_all_stocks(full_refresh=False, stock_list=None):
    storage = DataStorage()
    
    # Use provided stock list or default to config
    stocks = stock_list if stock_list is not None else STOCK_LIST
    
    if full_refresh:
        start_date = '2000-01-01'  # Full historical data instead of 2 years
        log_info(f"Starting full data refresh for {len(stocks)} stocks (full history)")
    else:
        start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')
        log_info(f"Starting incremental update for {len(stocks)} stocks (7 days)")
    
    end_date = datetime.now().strftime('%Y-%m-%d')
    
    log_info(f"Fetching batch: {stocks}")
    data = fetch_tiingo_data(stocks, start_date, end_date)
    
    updated_count = 0
    for ticker, new_df in data.items():
        existing_df = storage.load_data(ticker)
        if existing_df is not None and not full_refresh:
            combined_df = pd.concat([existing_df, new_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date').reset_index(drop=True)
            storage.save_data(combined_df, ticker)
            log_info(f"Updated {ticker}: {len(combined_df)} total rows")
        else:
            storage.save_data(new_df, ticker)
        
        updated_count += 1
    
    log_info(f"Update complete: {updated_count}/{len(stocks)} stocks updated")
    return {
        'success': True,
        'updated': updated_count,
        'total': len(stocks),
        'timestamp': datetime.now().isoformat()
    }

def get_stock_data(ticker):
    """Load stock data from local storage only (no API fallback)."""
    storage = DataStorage()
    df = storage.load_data(ticker)
    # Silent fail - no logging for missing local data to reduce noise
    return df
