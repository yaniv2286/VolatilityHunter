"""
Technical Analysis Utilities for A+ Wealth Builder
"""

import pandas as pd
import numpy as np
from src.notifications import log_info, log_error

def calculate_atr(df, period=14):
    """
    Calculate Average True Range (ATR) using adjClose for accuracy.
    
    Args:
        df: DataFrame with OHLC data
        period: ATR calculation period (default: 14)
    
    Returns:
        pandas Series: ATR values
    """
    try:
        if len(df) < period:
            # Use smaller period for limited data
            period = max(2, len(df) // 2)
            log_info(f"ATR period adjusted to {period} due to limited data")
        
        # Use adjClose if available, otherwise use Close
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close'
        
        # Handle both uppercase and lowercase column names
        high_col = 'High' if 'High' in df.columns else 'high'
        low_col = 'Low' if 'Low' in df.columns else 'low'
        
        # Calculate True Range
        high_low = df[high_col] - df[low_col]
        high_close = np.abs(df[high_col] - df[close_col].shift(1))
        low_close = np.abs(df[low_col] - df[close_col].shift(1))
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        
        # Calculate ATR as rolling average of True Range
        atr = true_range.rolling(window=period, min_periods=1).mean()
        
        return atr
        
    except Exception as e:
        log_error(f"Error calculating ATR: {e}")
        # Return series of zeros as fallback
        return pd.Series([0.0] * len(df), index=df.index)

def calculate_sma_200(df):
    """
    Calculate SMA 200 using adjClose for accuracy.
    
    Args:
        df: DataFrame with price data
    
    Returns:
        float: Latest SMA 200 value
    """
    try:
        if len(df) < 200:
            # Use smaller period for limited data
            period = max(50, len(df) // 2)
            log_info(f"SMA period adjusted to {period} due to limited data")
        else:
            period = 200
        
        # Use adjClose if available, otherwise use Close
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close'
        
        sma = df[close_col].rolling(window=period, min_periods=1).mean()
        return sma.iloc[-1]
        
    except Exception as e:
        log_error(f"Error calculating SMA 200: {e}")
        return None

def get_position_risk_data(ticker, data_loader):
    """
    Get current ATR and SMA data for a position.
    
    Args:
        ticker: Stock ticker symbol
        data_loader: Data loader instance
    
    Returns:
        dict: {'atr': current_atr, 'sma_200': current_sma, 'price': current_price}
    """
    try:
        df = data_loader.storage.load_data(ticker)
        if df is None or df.empty:
            log_error(f"No data available for {ticker}")
            return None
        
        # Use adjClose if available, otherwise use Close
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close'
        
        # Calculate indicators
        atr_series = calculate_atr(df)
        current_atr = atr_series.iloc[-1] if not atr_series.empty else 0.0
        current_sma = calculate_sma_200(df)
        
        # Calculate SMA 25 for Power Stock Shield
        sma_25_period = min(25, len(df) // 2)
        if sma_25_period < 5:
            sma_25_period = 5
        current_sma_25 = df[close_col].rolling(window=sma_25_period, min_periods=1).mean().iloc[-1]
        
        current_price = df[close_col].iloc[-1]
        
        return {
            'atr': current_atr,
            'sma_200': current_sma,
            'sma_25': current_sma_25,
            'price': current_price
        }
        
    except Exception as e:
        log_error(f"Error getting risk data for {ticker}: {e}")
        return None
