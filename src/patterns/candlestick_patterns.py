"""
Candlestick Pattern Recognition for Sweet Spot Blueprint
Implements Engulfing, Hammer, and Doji pattern detection
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from src.notifications import log_info, log_warning, log_error

def detect_engulfing(df: pd.DataFrame, lookback: int = 2) -> pd.Series:
    """
    Detect Bullish and Bearish Engulfing patterns
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to look back (default 2 for engulfing)
        
    Returns:
        Series with pattern signals: 1 (bullish engulfing), -1 (bearish engulfing), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                # Try capitalized versions
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for engulfing detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        for i in range(lookback, len(df)):
            # Current candle
            current_open = df.iloc[i]['open']
            current_close = df.iloc[i]['close']
            current_high = df.iloc[i]['high']
            current_low = df.iloc[i]['low']
            
            # Previous candle
            prev_open = df.iloc[i-1]['open']
            prev_close = df.iloc[i-1]['close']
            prev_high = df.iloc[i-1]['high']
            prev_low = df.iloc[i-1]['low']
            
            # Bullish Engulfing:
            # 1. Previous candle is bearish (close < open)
            # 2. Current candle is bullish (close > open)
            # 3. Current open < previous close
            # 4. Current close > previous open
            if (prev_close < prev_open and  # Previous bearish
                current_close > current_open and  # Current bullish
                current_open < prev_close and  # Engulfs previous close
                current_close > prev_open):  # Engulfs previous open
                
                patterns.iloc[i] = 1
                log_info(f"[PATTERN] Bullish Engulfing detected at index {i}")
            
            # Bearish Engulfing:
            # 1. Previous candle is bullish (close > open)
            # 2. Current candle is bearish (close < open)
            # 3. Current open > previous close
            # 4. Current close < previous open
            elif (prev_close > prev_open and  # Previous bullish
                  current_close < current_open and  # Current bearish
                  current_open > prev_close and  # Engulfs previous close
                  current_close < prev_open):  # Engulfs previous open
                
                patterns.iloc[i] = -1
                log_info(f"[PATTERN] Bearish Engulfing detected at index {i}")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in engulfing detection: {e}")
        return pd.Series(0, index=df.index)

def detect_hammer(df: pd.DataFrame, lookback: int = 1) -> pd.Series:
    """
    Detect Hammer and Inverted Hammer patterns
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to look back (default 1)
        
    Returns:
        Series with pattern signals: 1 (hammer), -1 (inverted hammer), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for hammer detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        for i in range(lookback, len(df)):
            open_price = df.iloc[i]['open']
            close_price = df.iloc[i]['close']
            high_price = df.iloc[i]['high']
            low_price = df.iloc[i]['low']
            
            # Calculate body and wick sizes
            body_size = abs(close_price - open_price)
            upper_wick = high_price - max(open_price, close_price)
            lower_wick = min(open_price, close_price) - low_price
            total_range = high_price - low_price
            
            if total_range == 0:
                continue
            
            # Hammer criteria:
            # 1. Lower wick at least 2x body size
            # 2. Upper wick very small (< 10% of total range)
            # 3. Body in upper portion of candle
            if (lower_wick >= 2 * body_size and
                upper_wick < 0.1 * total_range and
                min(open_price, close_price) > (low_price + 0.6 * total_range)):
                
                patterns.iloc[i] = 1
                log_info(f"[PATTERN] Hammer detected at index {i}")
            
            # Inverted Hammer criteria:
            # 1. Upper wick at least 2x body size
            # 2. Lower wick very small (< 10% of total range)
            # 3. Body in lower portion of candle
            elif (upper_wick >= 2 * body_size and
                  lower_wick < 0.1 * total_range and
                  max(open_price, close_price) < (high_price - 0.6 * total_range)):
                
                patterns.iloc[i] = -1
                log_info(f"[PATTERN] Inverted Hammer detected at index {i}")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in hammer detection: {e}")
        return pd.Series(0, index=df.index)

def detect_doji(df: pd.DataFrame, lookback: int = 1) -> pd.Series:
    """
    Detect Doji patterns (indecision candles)
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to look back (default 1)
        
    Returns:
        Series with pattern signals: 1 (doji detected), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['open', 'high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for doji detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        for i in range(lookback, len(df)):
            open_price = df.iloc[i]['open']
            close_price = df.iloc[i]['close']
            high_price = df.iloc[i]['high']
            low_price = df.iloc[i]['low']
            
            # Calculate body size and total range
            body_size = abs(close_price - open_price)
            total_range = high_price - low_price
            
            if total_range == 0:
                continue
            
            # Doji criteria:
            # Body size less than 5% of total range (very small body)
            if body_size < 0.05 * total_range:
                patterns.iloc[i] = 1
                log_info(f"[PATTERN] Doji (indecision) detected at index {i} - AVOID TRADING")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in doji detection: {e}")
        return pd.Series(0, index=df.index)

def get_candlestick_signals(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Get all candlestick pattern signals
    
    Args:
        df: DataFrame with OHLC data
        
    Returns:
        Dictionary with pattern signals
    """
    signals = {}
    
    try:
        signals['engulfing'] = detect_engulfing(df)
        signals['hammer'] = detect_hammer(df)
        signals['doji'] = detect_doji(df)
        
        log_info(f"[PATTERN] Candlestick analysis completed for {len(df)} candles")
        
    except Exception as e:
        log_error(f"[PATTERN] Error in candlestick signal generation: {e}")
        # Return empty signals on error
        signals = {
            'engulfing': pd.Series(0, index=df.index),
            'hammer': pd.Series(0, index=df.index),
            'doji': pd.Series(0, index=df.index)
        }
    
    return signals
