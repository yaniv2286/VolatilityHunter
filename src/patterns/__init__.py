"""
Pattern Recognition Module for VolatilityHunter Sweet Spot Blueprint
Provides candlestick and chart pattern detection for enhanced trading signals
"""

from .candlestick_patterns import detect_engulfing, detect_hammer, detect_doji
from .chart_patterns import detect_w_formation, detect_m_formation, detect_head_shoulders, detect_50_percent_rule
from .pattern_utils import calculate_pattern_strength, combine_pattern_signals

__all__ = [
    'detect_engulfing',
    'detect_hammer', 
    'detect_doji',
    'detect_w_formation',
    'detect_m_formation',
    'detect_head_shoulders',
    'detect_50_percent_rule',
    'calculate_pattern_strength',
    'combine_pattern_signals'
]
