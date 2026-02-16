#!/usr/bin/env python3
"""
Simulated Data Loader for Time-Shifted Forward Testing
Prevents lookahead bias by strictly truncating data to target_date.
Never calls Tiingo API - only uses local parquet data.
"""

import os
import sys
import pandas as pd
from typing import Optional
from datetime import datetime

# Add src to path for imports (need to go up one level from simulation/)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.storage import DataStorage
from src.notifications import log_info, log_warning, log_error


class SimulatedParquetLoader:
    """
    Data loader for time-shifted forward testing.
    Prevents lookahead bias by strictly truncating data to target_date.
    Never calls Tiingo API - only uses local parquet data.
    """
    
    def __init__(self, target_date: str):
        """
        Initialize with target date for data truncation.
        
        Args:
            target_date: Target date in 'YYYY-MM-DD' format
        """
        self.target_date = pd.to_datetime(target_date).normalize()
        self.storage = DataStorage()
        
    def load_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load parquet data truncated to target_date.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            DataFrame with data only up to target_date, or None if not found
        """
        try:
            df = self.storage.load_data(ticker)
            if df is None or df.empty:
                return None
                
            # Convert date column to datetime if it's not already
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date']).dt.normalize()
                
                # Ensure target_date is timezone-naive for comparison
                target_date_naive = self.target_date.tz_localize(None) if self.target_date.tz is not None else self.target_date
                
                # Strict truncation: remove all rows where date > target_date
                truncated_df = df[df['date'].dt.tz_localize(None) <= target_date_naive].copy()
                
                if truncated_df.empty:
                    return None
                    
                return truncated_df
            else:
                log_warning(f"No date column found for {ticker}")
                return None
                
        except Exception as e:
            log_error(f"Error loading simulated data for {ticker}: {e}")
            return None
    
    def get_latest_price(self, ticker: str) -> Optional[float]:
        """
        Get latest price up to target_date.
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            Latest price or None if not found
        """
        df = self.load_data(ticker)
        if df is None or df.empty:
            return None
            
        try:
            # Try different column name variations
            latest_price = None
            if 'adjClose' in df.columns:
                latest_price = df.iloc[-1]['adjClose']
            elif 'Close' in df.columns:
                latest_price = df.iloc[-1]['Close']
            elif 'close' in df.columns:
                latest_price = df.iloc[-1]['close']
            elif 'price' in df.columns:
                latest_price = df.iloc[-1]['price']
            elif 'Price' in df.columns:
                latest_price = df.iloc[-1]['Price']
            else:
                # Last resort - try to find any numeric column
                numeric_cols = df.select_dtypes(include=['number']).columns
                if len(numeric_cols) > 0:
                    latest_price = df.iloc[-1][numeric_cols[0]]
                    log_warning(f"{ticker}: Using fallback column {numeric_cols[0]}")
                else:
                    return None
                    
            return float(latest_price) if latest_price is not None else None
            
        except Exception as e:
            log_error(f"Error getting latest price for {ticker}: {e}")
            return None
