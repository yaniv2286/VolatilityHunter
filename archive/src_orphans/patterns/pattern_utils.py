"""
Pattern Utilities for Sweet Spot Blueprint
Common pattern detection utilities and signal combination logic
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from src.notifications import log_info, log_warning, log_error

def calculate_pattern_strength(pattern_signals: Dict[str, pd.Series], 
                            current_index: int = -1) -> Tuple[float, Dict[str, float]]:
    """
    Calculate overall pattern strength and individual pattern contributions
    
    Args:
        pattern_signals: Dictionary of pattern signals
        current_index: Index to analyze (default -1 for most recent)
        
    Returns:
        Tuple of (overall_strength, individual_strengths)
    """
    try:
        individual_strengths = {}
        overall_strength = 0.0
        
        # Pattern weights (can be adjusted based on historical performance)
        pattern_weights = {
            'engulfing': 0.3,           # Strong reversal signal
            'hammer': 0.2,               # Potential reversal
            'doji': -0.5,                # Avoid trading (negative weight)
            'w_formation': 0.25,         # Bullish continuation
            'm_formation': -0.3,         # Bearish reversal
            'head_shoulders': -0.4,      # Strong bearish reversal
            'fifty_percent_rule': -0.2   # Resistance level
        }
        
        for pattern_name, signals in pattern_signals.items():
            if pattern_name in pattern_weights:
                signal_value = signals.iloc[current_index] if current_index < len(signals) else 0
                weight = pattern_weights[pattern_name]
                
                # Calculate individual pattern contribution
                pattern_strength = signal_value * weight
                individual_strengths[pattern_name] = pattern_strength
                
                # Add to overall strength
                overall_strength += pattern_strength
        
        # Normalize overall strength to -1 to 1 range
        max_possible_strength = sum(abs(w) for w in pattern_weights.values())
        if max_possible_strength > 0:
            overall_strength = overall_strength / max_possible_strength
        
        log_info(f"[PATTERN] Overall pattern strength: {overall_strength:.3f}")
        
        return overall_strength, individual_strengths
        
    except Exception as e:
        log_error(f"[PATTERN] Error calculating pattern strength: {e}")
        return 0.0, {}

def combine_pattern_signals(candlestick_signals: Dict[str, pd.Series],
                          chart_signals: Dict[str, pd.Series]) -> Dict[str, pd.Series]:
    """
    Combine candlestick and chart pattern signals
    
    Args:
        candlestick_signals: Candlestick pattern signals
        chart_signals: Chart pattern signals
        
    Returns:
        Combined pattern signals dictionary
    """
    try:
        combined_signals = {}
        
        # Combine all signals
        all_signals = {**candlestick_signals, **chart_signals}
        
        # Ensure all signals have the same index
        if not all_signals:
            return combined_signals
        
        # Get the common index (use the first signal's index as reference)
        reference_index = list(all_signals.values())[0].index
        
        # Align all signals to the same index
        for pattern_name, signals in all_signals.items():
            if signals.index.equals(reference_index):
                combined_signals[pattern_name] = signals
            else:
                # Reindex to match reference
                combined_signals[pattern_name] = signals.reindex(reference_index, fill_value=0)
        
        log_info(f"[PATTERN] Combined {len(combined_signals)} pattern signals")
        
        return combined_signals
        
    except Exception as e:
        log_error(f"[PATTERN] Error combining pattern signals: {e}")
        return {}

def get_pattern_recommendation(pattern_strength: float, 
                             individual_strengths: Dict[str, float]) -> Tuple[str, str]:
    """
    Get trading recommendation based on pattern analysis
    
    Args:
        pattern_strength: Overall pattern strength (-1 to 1)
        individual_strengths: Individual pattern contributions
        
    Returns:
        Tuple of (recommendation, reasoning)
    """
    try:
        # Strong bullish patterns
        if pattern_strength > 0.6:
            recommendation = "STRONG_BUY"
            reasoning = "Strong bullish pattern combination detected"
            
        # Moderate bullish patterns
        elif pattern_strength > 0.3:
            recommendation = "BUY"
            reasoning = "Moderate bullish patterns present"
            
        # Weak bullish patterns
        elif pattern_strength > 0.1:
            recommendation = "WEAK_BUY"
            reasoning = "Weak bullish patterns, proceed with caution"
            
        # Neutral/no clear pattern
        elif pattern_strength >= -0.1:
            recommendation = "HOLD"
            reasoning = "No clear pattern direction"
            
        # Weak bearish patterns
        elif pattern_strength >= -0.3:
            recommendation = "WEAK_SELL"
            reasoning = "Weak bearish patterns, consider reducing exposure"
            
        # Moderate bearish patterns
        elif pattern_strength >= -0.6:
            recommendation = "SELL"
            reasoning = "Moderate bearish patterns detected"
            
        # Strong bearish patterns
        else:
            recommendation = "STRONG_SELL"
            reasoning = "Strong bearish pattern combination detected"
        
        # Add specific pattern details to reasoning
        if individual_strengths:
            strong_patterns = [name for name, strength in individual_strengths.items() 
                            if abs(strength) > 0.2]
            if strong_patterns:
                reasoning += f" (Key patterns: {', '.join(strong_patterns)})"
        
        return recommendation, reasoning
        
    except Exception as e:
        log_error(f"[PATTERN] Error getting pattern recommendation: {e}")
        return "HOLD", "Error in pattern analysis"

def validate_pattern_data(df: pd.DataFrame) -> bool:
    """
    Validate that DataFrame has required data for pattern analysis
    
    Args:
        df: DataFrame to validate
        
    Returns:
        True if valid, False otherwise
    """
    try:
        required_columns = ['open', 'high', 'low', 'close']
        
        # Check for required columns (case-insensitive)
        df_columns_lower = [col.lower() for col in df.columns]
        
        for required_col in required_columns:
            if required_col not in df_columns_lower:
                log_error(f"[PATTERN] Missing required column: {required_col}")
                return False
        
        # Check minimum data length
        if len(df) < 20:
            log_error(f"[PATTERN] Insufficient data: {len(df)} periods (minimum 20 required)")
            return False
        
        # Check for NaN values
        if df[required_columns].isna().any().any():
            log_warning(f"[PATTERN] NaN values found in data, patterns may be unreliable")
        
        log_info(f"[PATTERN] Data validation passed: {len(df)} periods, columns: {list(df.columns)}")
        return True
        
    except Exception as e:
        log_error(f"[PATTERN] Error validating pattern data: {e}")
        return False

def get_pattern_summary(pattern_signals: Dict[str, pd.Series], 
                       current_index: int = -1) -> Dict[str, any]:
    """
    Get comprehensive pattern analysis summary
    
    Args:
        pattern_signals: Dictionary of pattern signals
        current_index: Index to analyze (default -1 for most recent)
        
    Returns:
        Dictionary with pattern analysis summary
    """
    try:
        summary = {
            'total_patterns': len(pattern_signals),
            'active_patterns': 0,
            'bullish_patterns': [],
            'bearish_patterns': [],
            'neutral_patterns': [],
            'pattern_strength': 0.0,
            'recommendation': 'HOLD',
            'reasoning': 'No pattern data available'
        }
        
        if not pattern_signals:
            return summary
        
        # Analyze each pattern
        individual_strengths = {}
        for pattern_name, signals in pattern_signals.items():
            if current_index < len(signals):
                signal_value = signals.iloc[current_index]
                
                if signal_value != 0:
                    summary['active_patterns'] += 1
                    
                    if signal_value > 0:
                        summary['bullish_patterns'].append(pattern_name)
                    elif signal_value < 0:
                        summary['bearish_patterns'].append(pattern_name)
                else:
                    summary['neutral_patterns'].append(pattern_name)
        
        # Calculate overall strength
        pattern_strength, individual_strengths = calculate_pattern_strength(
            pattern_signals, current_index
        )
        summary['pattern_strength'] = pattern_strength
        
        # Get recommendation
        recommendation, reasoning = get_pattern_recommendation(
            pattern_strength, individual_strengths
        )
        summary['recommendation'] = recommendation
        summary['reasoning'] = reasoning
        
        log_info(f"[PATTERN] Pattern summary: {summary['active_patterns']} active patterns, "
                f"strength: {pattern_strength:.3f}, recommendation: {recommendation}")
        
        return summary
        
    except Exception as e:
        log_error(f"[PATTERN] Error getting pattern summary: {e}")
        return {
            'total_patterns': 0,
            'active_patterns': 0,
            'bullish_patterns': [],
            'bearish_patterns': [],
            'neutral_patterns': [],
            'pattern_strength': 0.0,
            'recommendation': 'HOLD',
            'reasoning': 'Error in pattern analysis'
        }
