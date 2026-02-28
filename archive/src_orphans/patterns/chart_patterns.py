"""
Chart Pattern Recognition for Sweet Spot Blueprint
Implements W/M formations, Head & Shoulders, and 50% Rule patterns
"""

import pandas as pd
import numpy as np
from typing import Tuple, Dict, List, Optional
from src.notifications import log_info, log_warning, log_error

def detect_w_formation(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Detect W formation (double bottom with higher lows)
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to analyze for pattern
        
    Returns:
        Series with pattern signals: 1 (W formation detected), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['low', 'close']
        for col in required_cols:
            if col not in df.columns:
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for W formation detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        # Need at least lookback periods to detect pattern
        if len(df) < lookback:
            return patterns
        
        for i in range(lookback, len(df)):
            # Look for W formation in the last 'lookback' periods
            window = df.iloc[i-lookback:i+1]
            
            if len(window) < lookback:
                continue
            
            # Find local minima (potential bottoms)
            lows = window['low'].values
            
            # Simple approach: look for two distinct lows with the second low higher
            # Find first low (around 1/3 of window)
            first_third = lookback // 3
            first_low_idx = np.argmin(lows[:first_third])
            first_low = lows[first_low_idx]
            
            # Find second low (around 2/3 of window)
            second_third = 2 * (lookback // 3)
            second_low_start = first_third + 5  # Some separation
            if second_low_start >= lookback:
                continue
                
            second_low_idx = np.argmin(lows[second_low_start:second_third]) + second_low_start
            second_low = lows[second_low_idx]
            
            # Check if second low is higher than first low (higher low = bullish)
            if second_low > first_low * 1.02:  # At least 2% higher
                # Check if we're currently breaking above the middle peak
                middle_start = first_low_idx + 2
                middle_end = second_low_idx - 1
                if middle_start >= middle_end:
                    continue
                
                middle_peak = np.max(window['close'].iloc[middle_start:middle_end])
                current_price = df.iloc[i]['close']
                
                # If current price is breaking above middle peak, confirm W formation
                if current_price > middle_peak * 1.01:  # 1% break confirmation
                    patterns.iloc[i] = 1
                    log_info(f"[PATTERN] W formation detected at index {i} - Higher lows confirmed")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in W formation detection: {e}")
        return pd.Series(0, index=df.index)

def detect_m_formation(df: pd.DataFrame, lookback: int = 20) -> pd.Series:
    """
    Detect M formation (double top with lower highs)
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to analyze for pattern
        
    Returns:
        Series with pattern signals: -1 (M formation detected), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['high', 'close']
        for col in required_cols:
            if col not in df.columns:
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for M formation detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        # Need at least lookback periods to detect pattern
        if len(df) < lookback:
            return patterns
        
        for i in range(lookback, len(df)):
            # Look for M formation in the last 'lookback' periods
            window = df.iloc[i-lookback:i+1]
            
            if len(window) < lookback:
                continue
            
            # Find local maxima (potential tops)
            highs = window['high'].values
            
            # Find first top (around 1/3 of window)
            first_third = lookback // 3
            first_high_idx = np.argmax(highs[:first_third])
            first_high = highs[first_high_idx]
            
            # Find second top (around 2/3 of window)
            second_third = 2 * (lookback // 3)
            second_high_start = first_third + 5  # Some separation
            if second_high_start >= lookback:
                continue
                
            second_high_idx = np.argmax(highs[second_high_start:second_third]) + second_high_start
            second_high = highs[second_high_idx]
            
            # Check if second high is lower than first high (lower high = bearish)
            if second_high < first_high * 0.98:  # At least 2% lower
                # Check if we're currently breaking below the middle valley
                middle_start = first_high_idx + 2
                middle_end = second_high_idx - 1
                if middle_start >= middle_end:
                    continue
                
                middle_valley = np.min(window['close'].iloc[middle_start:middle_end])
                current_price = df.iloc[i]['close']
                
                # If current price is breaking below middle valley, confirm M formation
                if current_price < middle_valley * 0.99:  # 1% break confirmation
                    patterns.iloc[i] = -1
                    log_info(f"[PATTERN] M formation detected at index {i} - Lower highs confirmed")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in M formation detection: {e}")
        return pd.Series(0, index=df.index)

def detect_head_shoulders(df: pd.DataFrame, lookback: int = 30) -> pd.Series:
    """
    Detect Head & Shoulders pattern (distinct top formation)
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to analyze for pattern
        
    Returns:
        Series with pattern signals: -1 (Head & Shoulders detected), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for Head & Shoulders detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        # Need at least lookback periods to detect pattern
        if len(df) < lookback:
            return patterns
        
        for i in range(lookback, len(df)):
            # Look for Head & Shoulders in the last 'lookback' periods
            window = df.iloc[i-lookback:i+1]
            
            if len(window) < lookback:
                continue
            
            highs = window['high'].values
            
            # Divide window into 3 sections for left shoulder, head, right shoulder
            section_size = lookback // 3
            
            # Left shoulder peak
            ls_start = 0
            ls_end = section_size
            ls_idx = np.argmax(highs[ls_start:ls_end]) + ls_start
            ls_high = highs[ls_idx]
            
            # Head peak (should be highest)
            head_start = section_size
            head_end = 2 * section_size
            head_idx = np.argmax(highs[head_start:head_end]) + head_start
            head_high = highs[head_idx]
            
            # Right shoulder peak
            rs_start = 2 * section_size
            rs_end = lookback
            if rs_start >= rs_end:
                continue
            rs_idx = np.argmax(highs[rs_start:rs_end]) + rs_start
            rs_high = highs[rs_idx]
            
            # Head & Shoulders criteria:
            # 1. Head is significantly higher than shoulders
            # 2. Shoulders are roughly equal height
            # 3. Current price is breaking below neckline
            
            if (head_high > ls_high * 1.05 and  # Head 5% higher than left shoulder
                head_high > rs_high * 1.05 and  # Head 5% higher than right shoulder
                abs(ls_high - rs_high) < max(ls_high, rs_high) * 0.1):  # Shoulders within 10%
                
                # Calculate neckline (line connecting the valleys between shoulders)
                # Find valley between left shoulder and head
                valley1_start = ls_idx + 1
                valley1_end = head_idx - 1
                if valley1_start >= valley1_end:
                    continue
                    
                valley1 = np.min(window['low'].iloc[valley1_start:valley1_end])
                
                # Find valley between head and right shoulder
                valley2_start = head_idx + 1
                valley2_end = rs_idx - 1
                if valley2_start >= valley2_end:
                    continue
                    
                valley2 = np.min(window['low'].iloc[valley2_start:valley2_end])
                
                # Neckline is the higher of the two valleys
                neckline = max(valley1, valley2)
                current_price = df.iloc[i]['close']
                
                # If current price breaks below neckline, confirm pattern
                if current_price < neckline * 0.99:  # 1% break confirmation
                    patterns.iloc[i] = -1
                    log_info(f"[PATTERN] Head & Shoulders detected at index {i} - Neckline break confirmed")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in Head & Shoulders detection: {e}")
        return pd.Series(0, index=df.index)

def detect_50_percent_rule(df: pd.DataFrame, lookback: int = 60) -> pd.Series:
    """
    Detect 50% Rule - rallies back to 50% of previous drop often hit ceiling
    
    Args:
        df: DataFrame with OHLC data
        lookback: Number of periods to analyze for pattern
        
    Returns:
        Series with pattern signals: -1 (50% ceiling detected), 0 (no pattern)
    """
    try:
        # Ensure we have required columns
        required_cols = ['high', 'low', 'close']
        for col in required_cols:
            if col not in df.columns:
                cap_col = col.capitalize()
                if cap_col in df.columns:
                    df[col] = df[cap_col]
                else:
                    log_error(f"[PATTERN] Required column {col} not found for 50% rule detection")
                    return pd.Series(0, index=df.index)
        
        patterns = pd.Series(0, index=df.index)
        
        # Need at least lookback periods to detect pattern
        if len(df) < lookback:
            return patterns
        
        for i in range(lookback, len(df)):
            # Look for significant drop followed by rally in the last 'lookback' periods
            window = df.iloc[i-lookback:i+1]
            
            if len(window) < lookback:
                continue
            
            # Find the highest high in the window
            highest_high = window['high'].max()
            highest_idx = window['high'].idxmax()
            
            # Find the lowest low after the highest high
            after_peak = window.loc[window.index > highest_idx]
            if len(after_peak) < 5:  # Need some data after peak
                continue
                
            lowest_low = after_peak['low'].min()
            lowest_idx = after_peak['low'].idxmin()
            
            # Calculate the drop percentage
            drop_percentage = (highest_high - lowest_low) / highest_high
            
            # Only consider significant drops (>20%)
            if drop_percentage < 0.20:
                continue
            
            # Calculate the 50% level
            fifty_percent_level = lowest_low + (highest_high - lowest_low) * 0.5
            
            # Current price
            current_price = df.iloc[i]['close']
            
            # Check if current price is approaching the 50% level
            tolerance = 0.02  # 2% tolerance
            if (abs(current_price - fifty_percent_level) / fifty_percent_level) < tolerance:
                patterns.iloc[i] = -1
                log_info(f"[PATTERN] 50% Rule detected at index {i} - Price at {current_price:.2f}, 50% level at {fifty_percent_level:.2f}")
        
        return patterns
        
    except Exception as e:
        log_error(f"[PATTERN] Error in 50% rule detection: {e}")
        return pd.Series(0, index=df.index)

def get_chart_pattern_signals(df: pd.DataFrame) -> Dict[str, pd.Series]:
    """
    Get all chart pattern signals
    
    Args:
        df: DataFrame with OHLC data
        
    Returns:
        Dictionary with pattern signals
    """
    signals = {}
    
    try:
        signals['w_formation'] = detect_w_formation(df)
        signals['m_formation'] = detect_m_formation(df)
        signals['head_shoulders'] = detect_head_shoulders(df)
        signals['fifty_percent_rule'] = detect_50_percent_rule(df)
        
        log_info(f"[PATTERN] Chart pattern analysis completed for {len(df)} periods")
        
    except Exception as e:
        log_error(f"[PATTERN] Error in chart pattern signal generation: {e}")
        # Return empty signals on error
        signals = {
            'w_formation': pd.Series(0, index=df.index),
            'm_formation': pd.Series(0, index=df.index),
            'head_shoulders': pd.Series(0, index=df.index),
            'fifty_percent_rule': pd.Series(0, index=df.index)
        }
    
    return signals
