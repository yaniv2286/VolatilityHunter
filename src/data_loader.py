import requests
import pandas as pd
from datetime import datetime, timedelta
from src.config import TIINGO_KEY, TIINGO_BASE_URL, BATCH_SIZE, STOCK_LIST
from src.storage import DataStorage
from src.notifications import log_info, log_error, log_warning

def fetch_tiingo_data(tickers, start_date=None, end_date=None):
    if not TIINGO_KEY:
        log_error("TIINGO_KEY not set in environment variables")
        return {}
    
    if start_date is None:
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
    if end_date is None:
        end_date = datetime.now().strftime('%Y-%m-%d')
    
    headers = {
        'Content-Type': 'application/json',
        'Authorization': f'Token {TIINGO_KEY}'
    }
    
    results = {}
    
    for i in range(0, len(tickers), BATCH_SIZE):
        batch = tickers[i:i + BATCH_SIZE]
        ticker_string = ','.join(batch)
        
        url = f"{TIINGO_BASE_URL}/prices"
        params = {
            'tickers': ticker_string,
            'startDate': start_date,
            'endDate': end_date,
            'resampleFreq': 'daily'
        }
        
        try:
            log_info(f"Fetching batch: {batch}")
            response = requests.get(url, headers=headers, params=params, timeout=30)
            response.raise_for_status()
            data = response.json()
            
            for item in data:
                ticker = item.get('ticker')
                if ticker and 'priceData' in item:
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
                        results[ticker] = df
                        log_info(f"Fetched {len(df)} rows for {ticker}")
            
        except requests.exceptions.RequestException as e:
            log_error(f"Failed to fetch batch {batch}: {e}")
        except Exception as e:
            log_error(f"Error processing batch {batch}: {e}")
    
    return results

def update_all_stocks(full_refresh=False, stock_list=None):
    storage = DataStorage()
    
    # Use provided stock list or default to config
    stocks = stock_list if stock_list is not None else STOCK_LIST
    
    if full_refresh:
        start_date = (datetime.now() - timedelta(days=730)).strftime('%Y-%m-%d')
        log_info(f"Starting full data refresh for {len(stocks)} stocks (2 years)")
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
