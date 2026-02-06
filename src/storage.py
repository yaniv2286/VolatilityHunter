import pandas as pd
import os
import glob
from io import StringIO
from google.cloud import storage
from datetime import datetime, timedelta
from src.notifications import log_info, log_warning, log_error

class DataStorage:
    def __init__(self):
        self.is_cloud = os.environ.get("IS_CLOUD_RUN", "False").lower() == "true"
        self.bucket_name = os.environ.get("GCS_BUCKET_NAME", "")
        self.local_dir = "data"
        
        if self.is_cloud:
            self.client = storage.Client()
            self.bucket = self.client.bucket(self.bucket_name)
        else:
            # Ensure local directory exists
            os.makedirs(self.local_dir, exist_ok=True)
            print(f"INFO: LocalStorage initialized at {self.local_dir}")
            print(f"INFO: Using local parquet data from {self.local_dir}")

    def _get_local_file_path(self, ticker):
        """Finds the file for a ticker, checking local parquet files first, then local CSV."""
        # First check local parquet files (copied from NeuralTrader)
        parquet_path = os.path.join(self.local_dir, f"{ticker.lower()}.parquet")
        if os.path.exists(parquet_path):
            return parquet_path
        
        # Fallback to local CSV files
        standard_path = os.path.join(self.local_dir, f"{ticker}_1d_full.csv")
        if os.path.exists(standard_path):
            return standard_path
        # Fallback: search for dated suffix pattern: TICKER_1d_full_*.csv
        search_pattern = os.path.join(self.local_dir, f"{ticker}_1d_full_*.csv")
        files = glob.glob(search_pattern)
        if files:
            return files[0]
        return None

    def load_data(self, ticker):
        """Loads DataFrame for a specific ticker."""
        if self.is_cloud:
            # Cloud: Search for files with date suffix pattern
            prefix = f"{ticker}_1d_full"
            blobs = list(self.bucket.list_blobs(prefix=prefix))
            
            # Filter for CSV files matching the pattern
            matching_blobs = [b for b in blobs if b.name.endswith('.csv') and b.name.startswith(prefix)]
            
            if matching_blobs:
                # Use the first matching blob
                blob = matching_blobs[0]
                content = blob.download_as_text()
                df = pd.read_csv(StringIO(content))
                df = self._ensure_date_column(df)
                return self._normalize_columns(df)
            return None
        else:
            # Local: Use the robust finder
            file_path = self._get_local_file_path(ticker)
            if file_path and os.path.exists(file_path):
                # Check if it's a parquet file (local) or CSV (local)
                if file_path.endswith('.parquet'):
                    df = pd.read_parquet(file_path)
                    print(f"INFO: Loaded {ticker} from local parquet data")
                else:
                    df = pd.read_csv(file_path)
                    print(f"INFO: Loaded {ticker} from local CSV data")
                
                df = self._ensure_date_column(df)
                return self._normalize_columns(df)
            return None
    
    def _ensure_date_column(self, df):
        """Ensure 'date' column exists, handling both 'Date' and 'date' formats."""
        if 'Date' in df.columns and 'date' not in df.columns:
            df = df.rename(columns={'Date': 'date'})
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'], errors='coerce')
        return df

    def _normalize_columns(self, df):
        """Normalize column names to match expected format."""
        # Handle YFinance multi-index columns (common issue)
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        # Map various column name formats to standard format
        column_mapping = {
            'open': 'Open',
            'high': 'High', 
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume',
            'adj close': 'Close',  # YFinance adjusted close
            'adjclose': 'Close',
            'adjclose': 'Close',  # Parquet adjusted close
            'adjhigh': 'High',
            'adjlow': 'Low',
            'adjopen': 'Open',
            'adjvolume': 'Volume',
            'divcash': 'Volume',  # Parquet dividend cash
            'splitfactor': 'Volume'  # Parquet split factor
        }
        
        # Apply column mapping
        df = df.rename(columns=column_mapping)
        
        # Keep only the columns we need
        required_cols = ['date', 'Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        
        # Drop rows with NaN in critical price columns
        if 'Close' in df.columns and 'High' in df.columns and 'Low' in df.columns and 'Open' in df.columns:
            df = df.dropna(subset=['Close', 'High', 'Low', 'Open'])
        
        return df

    def load_data_with_incremental_update(self, ticker):
        """
        Load data from NeuralTrader parquet, then fetch only missing recent days via API.
        This gives you the best of both worlds: fast local data + fresh daily updates.
        """
        # Step 1: Load existing data from NeuralTrader
        existing_df = self.load_data(ticker)
        
        if existing_df is None or len(existing_df) == 0:
            log_info(f"No existing data found for {ticker}, fetching full history via API")
            return self._fetch_full_data_via_api(ticker)
        
        # Step 2: Check if we need incremental update
        latest_date = existing_df['date'].max()
        today = datetime.now().date()
        days_behind = (today - latest_date.date()).days
        
        if days_behind <= 1:
            log_info(f"{ticker} data is up-to-date (latest: {latest_date.date()})")
            return existing_df
        
        log_info(f"{ticker} is {days_behind} days behind, fetching incremental data since {latest_date.date()}")
        
        # Step 3: Fetch only missing data via API
        incremental_df = self._fetch_incremental_data_via_api(ticker, latest_date)
        
        if incremental_df is not None and len(incremental_df) > 0:
            # Step 4: Merge and return
            combined_df = pd.concat([existing_df, incremental_df], ignore_index=True)
            combined_df = combined_df.drop_duplicates(subset=['date'], keep='last')
            combined_df = combined_df.sort_values('date').reset_index(drop=True)
            
            log_info(f"Added {len(incremental_df)} new days to {ticker} (range: {incremental_df['date'].min()} to {incremental_df['date'].max()})")
            
            # Step 5: Save updated data locally
            self._save_updated_data(combined_df, ticker)
            
            return combined_df
        else:
            log_warning(f"Failed to fetch incremental data for {ticker}, using existing data")
            return existing_df
    
    def _fetch_full_data_via_api(self, ticker):
        """Fetch complete historical data via API when no local data exists."""
        try:
            from src.smart_data_loader_factory import get_smart_data_loader
            loader = get_smart_data_loader()
            
            # Use the correct loader (primary or fallback)
            if loader.using_fallback:
                # YFinanceLoader has nested structure
                df = loader.fallback_loader.loader.download_historical_data(ticker, period='2y')
            else:
                # TiingoLoader doesn't have download_historical_data, use YFinance fallback
                if hasattr(loader.primary_loader, 'loader'):
                    df = loader.primary_loader.loader.download_historical_data(ticker, period='2y')
                else:
                    # Fall back to YFinance if Tiingo doesn't support this
                    df = loader.fallback_loader.loader.download_historical_data(ticker, period='2y')
                
            if df is not None and len(df) > 0:
                log_info(f"Fetched {len(df)} days of full history for {ticker} via API")
                df = self._ensure_date_column(df)
                df = self._normalize_columns(df)
                self._save_updated_data(df, ticker)
                return df
            else:
                log_error(f"Failed to fetch full data for {ticker} via API")
                return None
        except Exception as e:
            log_error(f"Error fetching full data for {ticker}: {e}")
            return None
    
    def _fetch_incremental_data_via_api(self, ticker, since_date):
        """Fetch only data since the given date via API."""
        try:
            from src.smart_data_loader_factory import get_smart_data_loader
            loader = get_smart_data_loader()
            
            # Calculate days to fetch (max 30 days to avoid API limits)
            days_to_fetch = min(30, (datetime.now().date() - since_date.date()).days)
            
            # Use the correct loader (primary or fallback)
            if loader.using_fallback:
                # YFinanceLoader has nested structure
                df = loader.fallback_loader.loader.download_historical_data(ticker, period=f'{days_to_fetch}d')
            else:
                # TiingoLoader doesn't have download_historical_data, use YFinance fallback
                if hasattr(loader.primary_loader, 'loader'):
                    df = loader.primary_loader.loader.download_historical_data(ticker, period=f'{days_to_fetch}d')
                else:
                    # Fall back to YFinance if Tiingo doesn't support this
                    df = loader.fallback_loader.loader.download_historical_data(ticker, period=f'{days_to_fetch}d')
                
            if df is not None and len(df) > 0:
                # Filter to only get data newer than our existing data
                df = df[df['date'] > since_date]
                log_info(f"Fetched {len(df)} days of incremental data for {ticker} via API")
                df = self._ensure_date_column(df)
                df = self._normalize_columns(df)
                return df
            else:
                log_warning(f"No incremental data available for {ticker}")
                return None
        except Exception as e:
            log_error(f"Error fetching incremental data for {ticker}: {e}")
            return None
    
    def _save_updated_data(self, df, ticker):
        """Save updated data to both local CSV and maintain parquet reference."""
        try:
            # Save to local CSV for VolatilityHunter usage
            csv_path = os.path.join(self.local_dir, f"{ticker}_1d_full.csv")
            df.to_csv(csv_path, index=False)
            log_info(f"Saved updated {ticker} data to {csv_path}")
            
            # Also update the NeuralTrader parquet if you want (optional)
            # parquet_path = os.path.join(self.neuraltrader_dir, f"{ticker.lower()}.parquet")
            # df.to_parquet(parquet_path, index=False)
            
        except Exception as e:
            log_error(f"Error saving updated data for {ticker}: {e}")

    def save_data(self, df, ticker):
        """Saves DataFrame."""
        # We save with a simple name to make future loads easier, 
        # or you can keep the date. Let's standarize to 'TICKER_1d_full.csv' 
        # to fix this issue permanently for the future.
        filename = f"{ticker}_1d_full.csv"
        
        if self.is_cloud:
            blob = self.bucket.blob(filename)
            blob.upload_from_string(df.to_csv(), content_type='text/csv')
        else:
            # Local: Overwrite the old file or create new standard one
            # Let's just create a standard one to clean up the mess
            path = os.path.join(self.local_dir, filename)
            df.to_csv(path, index=False)
            print(f"Saved {ticker} to {path}")

    def list_available_tickers(self):
        """Scans the storage to see what stocks we have."""
        tickers = set()
        if self.is_cloud:
            blobs = self.client.list_blobs(self.bucket_name)
            for b in blobs:
                # NVDA_1d_full... -> NVDA
                t = b.name.split('_')[0]
                tickers.add(t)
        else:
            # Local: glob all CSVs (both standard and dated formats)
            csv_files = glob.glob(os.path.join(self.local_dir, "*.csv"))
            for f in csv_files:
                t = os.path.basename(f).split('_')[0]
                tickers.add(t)
            
            # Also check local parquet files (copied from NeuralTrader)
            parquet_files = glob.glob(os.path.join(self.local_dir, "*.parquet"))
            for f in parquet_files:
                t = os.path.basename(f).replace('.parquet', '').upper()
                tickers.add(t)
        
        return list(tickers)
