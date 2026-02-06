import pandas as pd
import os
import glob
from io import StringIO
from google.cloud import storage

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

    def _get_local_file_path(self, ticker):
        """Finds the file for a ticker, checking standard name first, then dated suffix."""
        # First check for standard filename: TICKER_1d_full.csv
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
                df = pd.read_csv(file_path)
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
        # Map lowercase to capitalized column names
        column_mapping = {
            'open': 'Open',
            'high': 'High',
            'low': 'Low',
            'close': 'Close',
            'volume': 'Volume'
        }
        df = df.rename(columns=column_mapping)
        # Keep only the columns we need
        required_cols = ['date', 'Open', 'High', 'Low', 'Close', 'Volume']
        available_cols = [col for col in required_cols if col in df.columns]
        df = df[available_cols]
        # Drop rows with NaN in critical price columns
        df = df.dropna(subset=['Close', 'High', 'Low', 'Open'])
        return df

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
            for pattern in ["*_1d_full.csv", "*_1d_full_*.csv"]:
                files = glob.glob(os.path.join(self.local_dir, pattern))
                for f in files:
                    filename = os.path.basename(f)
                    t = filename.split('_')[0]
                    tickers.add(t)
        return list(tickers)