"""
Sweet Spot Strategy - Enhanced Trading Strategy with Pattern Recognition
Integrates Sweet Spot Blueprint features with existing VolatilityHunter v7.2 strategy
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from datetime import datetime

# Import existing v7.2 strategy components
from src.strategy_v7_2 import (
    analyze_stock_v7_2, 
    check_exit_conditions_v7_2, 
    calculate_position_size_v7_2, 
    add_indicators_v7_2,
    generate_vectorized_signals
)

# Import Sweet Spot components
from src.patterns.candlestick_patterns import get_candlestick_signals
from src.patterns.chart_patterns import get_chart_pattern_signals
from src.patterns.pattern_utils import (
    combine_pattern_signals, 
    calculate_pattern_strength, 
    get_pattern_summary,
    validate_pattern_data
)
from src.market_microstructure.time_filters import (
    check_10_06_rule, 
    check_friday_rule, 
    calculate_time_score,
    is_in_sweet_spot_window
)
from src.market_microstructure.spread_monitor import SpreadMonitor, check_spread_limits

# Import additional Sweet Spot components for full compliance
from src.shields import is_earnings_safe, apply_universal_shields

# Import existing components
from src.notifications import log_info, log_warning, log_error, alert_signal

class SweetSpotStrategy:
    """
    Enhanced trading strategy integrating Sweet Spot Blueprint features
    with existing VolatilityHunter v7.2 strategy
    """
    
    def __init__(self, config: Dict[str, Any] = None, brokerage_interface=None):
        """
        Initialize Sweet Spot Strategy
        
        Args:
            config: Strategy configuration
            brokerage_interface: IBKR interface for spread monitoring
        """
        self.config = config or {}
        self.brokerage = brokerage_interface
        self.spread_monitor = SpreadMonitor(brokerage_interface)
        
        # Strategy settings
        self.enable_patterns = self.config.get('enable_patterns', True)
        self.enable_spread_monitoring = self.config.get('enable_spread_monitoring', True)
        self.enable_time_filters = self.config.get('enable_time_filters', True)
        self.enable_earnings_filter = self.config.get('enable_earnings_filter', True)
        self.enable_volume_confirmation = self.config.get('enable_volume_confirmation', True)
        self.enable_candlestick_confirmation = self.config.get('enable_candlestick_confirmation', True)
        self.pattern_weight = self.config.get('pattern_weight', 0.3)  # Weight of patterns in final decision
        
        log_info(f"[SWEET_SPOT] Strategy initialized - Patterns: {self.enable_patterns}, "
                f"Spread: {self.enable_spread_monitoring}, Time: {self.enable_time_filters}")
    
    def analyze_stock_sweet_spot(self, ticker: str, df: pd.DataFrame, 
                                portfolio_data: Dict = None) -> Dict[str, Any]:
        """
        Enhanced stock analysis with Sweet Spot Blueprint features
        
        Args:
            ticker: Stock symbol
            df: DataFrame with OHLCV data
            portfolio_data: Current portfolio state
            
        Returns:
            Enhanced analysis results
        """
        try:
            # Start with v7.2 analysis
            log_info(f"[SWEET_SPOT] Analyzing {ticker} with enhanced strategy")
            
            # Validate pattern data
            if self.enable_patterns and not validate_pattern_data(df):
                log_warning(f"[SWEET_SPOT] Pattern data validation failed for {ticker}")
            
            # Get base v7.2 analysis
            base_analysis = analyze_stock_v7_2(df, ticker)
            
            # Add Sweet Spot enhancements
            enhanced_analysis = self._add_sweet_spot_analysis(
                ticker, df, base_analysis, portfolio_data
            )
            
            return enhanced_analysis
            
        except Exception as e:
            log_error(f"[SWEET_SPOT] Error in enhanced analysis for {ticker}: {e}")
            # Fallback to base analysis
            return analyze_stock_v7_2(df, ticker)
    
    def _add_sweet_spot_analysis(self, ticker: str, df: pd.DataFrame, 
                                base_analysis: Dict, portfolio_data: Dict) -> Dict[str, Any]:
        """
        Add Sweet Spot Blueprint enhancements to base analysis
        
        Args:
            ticker: Stock symbol
            df: DataFrame with OHLCV data
            base_analysis: Base v7.2 analysis results
            portfolio_data: Current portfolio state
            
        Returns:
            Enhanced analysis results
        """
        enhanced_analysis = base_analysis.copy()
        enhanced_analysis['sweet_spot_analysis'] = {}
        
        current_price = base_analysis.get('price', 0)
        if current_price == 0:
            current_price = df.iloc[-1]['close'] if 'close' in df.columns else df.iloc[-1]['Close']
        
        # 1. Pattern Recognition
        pattern_score = 0.0
        pattern_summary = {}
        if self.enable_patterns:
            try:
                # Get pattern signals
                candlestick_signals = get_candlestick_signals(df)
                chart_signals = get_chart_pattern_signals(df)
                all_signals = combine_pattern_signals(candlestick_signals, chart_signals)
                
                # Calculate pattern strength and summary
                pattern_score, _ = calculate_pattern_strength(all_signals)
                pattern_summary = get_pattern_summary(all_signals)
                
                enhanced_analysis['sweet_spot_analysis']['patterns'] = pattern_summary
                log_info(f"[SWEET_SPOT] {ticker} pattern score: {pattern_score:.3f}")
                
            except Exception as e:
                log_error(f"[SWEET_SPOT] Error in pattern analysis for {ticker}: {e}")
        
        # 2. Time-based Filters
        time_score = 1.0
        time_analysis = {}
        if self.enable_time_filters:
            try:
                # Check time-based rules
                is_10_06_optimal, msg_10_06 = check_10_06_rule()
                is_friday_optimal, msg_friday = check_friday_rule()
                time_score = calculate_time_score()
                
                time_analysis = {
                    'time_score': time_score,
                    'is_10_06_optimal': is_10_06_optimal,
                    'is_friday_optimal': is_friday_optimal,
                    'in_sweet_spot_window': is_in_sweet_spot_window(),
                    'messages': [msg_10_06, msg_friday]
                }
                
                enhanced_analysis['sweet_spot_analysis']['time_filters'] = time_analysis
                log_info(f"[SWEET_SPOT] {ticker} time score: {time_score:.3f}")
                
            except Exception as e:
                log_error(f"[SWEET_SPOT] Error in time analysis for {ticker}: {e}")
        
        # 3. Spread Monitoring
        spread_score = 1.0
        spread_analysis = {}
        if self.enable_spread_monitoring and self.brokerage:
            try:
                # Check spread limits
                is_spread_ok, spread_msg, spread_pct = check_spread_limits(
                    ticker, current_price, self.brokerage
                )
                
                # Convert spread to score (1.0 = good, 0.0 = bad)
                spread_score = 1.0 if is_spread_ok else 0.0
                
                spread_analysis = {
                    'spread_acceptable': is_spread_ok,
                    'spread_percentage': spread_pct,
                    'spread_message': spread_msg,
                    'spread_score': spread_score
                }
                
                enhanced_analysis['sweet_spot_analysis']['spread_monitoring'] = spread_analysis
                log_info(f"[SWEET_SPOT] {ticker} spread score: {spread_score:.3f}")
                
            except Exception as e:
                log_error(f"[SWEET_SPOT] Error in spread analysis for {ticker}: {e}")
        
        # 4. Earnings Filter (Critical Safety Check)
        earnings_score = 1.0
        earnings_analysis = {}
        if self.enable_earnings_filter:
            try:
                # Check earnings safety for today
                from datetime import datetime
                today = datetime.now().strftime('%Y-%m-%d')
                is_earnings_safe_today = is_earnings_safe(ticker, today)
                
                earnings_score = 1.0 if is_earnings_safe_today else 0.0
                
                earnings_analysis = {
                    'earnings_safe': is_earnings_safe_today,
                    'check_date': today,
                    'earnings_score': earnings_score,
                    'message': 'Earnings safe' if is_earnings_safe_today else 'Earnings announcement within 3 days - AVOID'
                }
                
                enhanced_analysis['sweet_spot_analysis']['earnings_filter'] = earnings_analysis
                
                if not is_earnings_safe_today:
                    log_warning(f"[SWEET_SPOT] {ticker} - Earnings announcement detected - AVOID TRADE")
                    # Early exit for earnings safety
                    enhanced_analysis['should_enter'] = False
                    enhanced_analysis['signal'] = 'HOLD'
                    enhanced_analysis['reason'] = f"Earnings announcement within 3 days - {earnings_analysis['message']}"
                    return enhanced_analysis
                
                log_info(f"[SWEET_SPOT] {ticker} earnings score: {earnings_score:.3f}")
                
            except Exception as e:
                log_error(f"[SWEET_SPOT] Error in earnings analysis for {ticker}: {e}")
        
        # 5. Volume Confirmation (Fuel Check)
        volume_score = 1.0
        volume_analysis = {}
        if self.enable_volume_confirmation:
            try:
                # Check volume consistency and 30% rule
                latest_volume = df.iloc[-1]['volume'] if 'volume' in df.columns else df.iloc[-1]['Volume']
                volume_sma = df.iloc[-1]['volume_sma_30'] if 'volume_sma_30' in df.columns else df.iloc[-1].get('volume_sma', latest_volume)
                
                # Volume consistency (last 3 days)
                if len(df) >= 3:
                    recent_volumes = [df.iloc[-i]['volume'] if 'volume' in df.columns else df.iloc[-i]['Volume'] for i in range(1, 4)]
                    volume_consistent = all(recent_volumes[i] >= recent_volumes[i-1] * 0.8 for i in range(1, len(recent_volumes)))
                else:
                    volume_consistent = True
                
                # 30% rule simulation (check if today's volume is strong)
                volume_ratio = latest_volume / volume_sma if volume_sma > 0 else 1.0
                volume_strong = volume_ratio >= 0.75  # Not "fumes"
                
                # Calculate volume score
                volume_score = 0.0
                if volume_consistent and volume_strong:
                    volume_score = 1.0
                elif volume_strong:
                    volume_score = 0.7
                elif volume_consistent:
                    volume_score = 0.5
                else:
                    volume_score = 0.0
                
                volume_analysis = {
                    'latest_volume': latest_volume,
                    'volume_sma': volume_sma,
                    'volume_ratio': volume_ratio,
                    'volume_consistent': volume_consistent,
                    'volume_strong': volume_strong,
                    'volume_score': volume_score,
                    'message': f"Volume ratio: {volume_ratio:.1%}, Consistent: {volume_consistent}"
                }
                
                enhanced_analysis['sweet_spot_analysis']['volume_confirmation'] = volume_analysis
                log_info(f"[SWEET_SPOT] {ticker} volume score: {volume_score:.3f}")
                
            except Exception as e:
                log_error(f"[SWEET_SPOT] Error in volume analysis for {ticker}: {e}")
        
        # 6. Calculate Enhanced Score
        enhanced_score = self._calculate_enhanced_score(
            base_analysis, pattern_score, time_score, spread_score, earnings_score, volume_score
        )
        
        enhanced_analysis['sweet_spot_analysis']['enhanced_score'] = enhanced_score
        enhanced_analysis['sweet_spot_analysis']['components'] = {
            'base_score': base_analysis.get('score', 0),
            'pattern_score': pattern_score,
            'time_score': time_score,
            'spread_score': spread_score,
            'earnings_score': earnings_score,
            'volume_score': volume_score
        }
        
        # 5. Enhanced Entry Decision
        enhanced_analysis['should_enter'] = self._make_enhanced_entry_decision(
            enhanced_analysis, base_analysis.get('should_enter', False)
        )
        
        log_info(f"[SWEET_SPOT] {ticker} enhanced score: {enhanced_score:.3f}, "
                f"enter: {enhanced_analysis['should_enter']}")
        
        return enhanced_analysis
    
    def _calculate_enhanced_score(self, base_analysis: Dict, pattern_score: float, 
                                time_score: float, spread_score: float, 
                                earnings_score: float, volume_score: float) -> float:
        """
        Calculate enhanced score combining all Sweet Spot components
        
        Args:
            base_analysis: Base v7.2 analysis
            pattern_score: Pattern analysis score
            time_score: Time-based score
            spread_score: Spread quality score
            earnings_score: Earnings safety score
            volume_score: Volume confirmation score
            
        Returns:
            Enhanced score (0.0 to 1.0)
        """
        try:
            # Get base score from v7.2 analysis
            base_score = base_analysis.get('score', 0)
            
            # Weight the components (earnings and volume are critical)
            weights = {
                'base': 0.3,  # 30% base strategy
                'pattern': 0.15,  # 15% patterns
                'time': 0.1,  # 10% time filters
                'spread': 0.1,  # 10% spread quality
                'earnings': 0.2,  # 20% earnings safety (critical)
                'volume': 0.15  # 15% volume confirmation
            }
            
            # Calculate weighted score
            enhanced_score = (
                base_score * weights['base'] +
                pattern_score * weights['pattern'] +
                time_score * weights['time'] +
                spread_score * weights['spread'] +
                earnings_score * weights['earnings'] +
                volume_score * weights['volume']
            )
            
            # Apply critical safety overrides
            if earnings_score == 0.0:  # Earnings announcement - CRITICAL
                enhanced_score = 0.0
            elif volume_score < 0.3:  # Trading on fumes - CRITICAL
                enhanced_score = enhanced_score * 0.3  # Heavily penalize
            
            return min(1.0, max(0.0, enhanced_score))
            
        except Exception as e:
            log_error(f"[SWEET_SPOT] Error calculating enhanced score: {e}")
            return base_analysis.get('score', 0)
    
    def _make_enhanced_entry_decision(self, enhanced_analysis: Dict, 
                                    base_should_enter: bool) -> bool:
        """
        Make enhanced entry decision combining base and Sweet Spot analysis
        
        Args:
            enhanced_analysis: Complete enhanced analysis
            base_should_enter: Base v7.2 entry decision
            
        Returns:
            Enhanced entry decision
        """
        try:
            # Get components
            sweet_spot = enhanced_analysis.get('sweet_spot_analysis', {})
            enhanced_score = sweet_spot.get('enhanced_score', 0)
            
            # Check for hard rejections
            spread_monitoring = sweet_spot.get('spread_monitoring', {})
            if spread_monitoring.get('spread_acceptable') is False:
                log_info(f"[SWEET_SPOT] Entry rejected due to spread limits")
                return False
            
            # Check for Doji patterns (hard rejection)
            patterns = sweet_spot.get('patterns', {})
            if 'doji' in patterns.get('neutral_patterns', []):
                log_info(f"[SWEET_SPOT] Entry rejected due to Doji pattern (indecision)")
                return False
            
            # Enhanced scoring threshold
            min_enhanced_score = self.config.get('min_enhanced_score', 0.6)
            
            # Decision logic
            if enhanced_score >= min_enhanced_score and base_should_enter:
                log_info(f"[SWEET_SPOT] Entry approved - Enhanced score: {enhanced_score:.3f}")
                return True
            elif enhanced_score >= min_enhanced_score and not base_should_enter:
                log_info(f"[SWEET_SPOT] Entry approved by Sweet Spot enhancement - "
                        f"Enhanced score: {enhanced_score:.3f} (base rejected)")
                return True
            else:
                log_info(f"[SWEET_SPOT] Entry rejected - Enhanced score: {enhanced_score:.3f} "
                        f"(min: {min_enhanced_score})")
                return False
                
        except Exception as e:
            log_error(f"[SWEET_SPOT] Error in enhanced entry decision: {e}")
            return base_should_enter
    
    def check_exit_conditions_sweet_spot(self, ticker: str, df: pd.DataFrame, 
                                       position: Dict) -> Dict[str, Any]:
        """
        Enhanced exit conditions with Sweet Spot features
        
        Args:
            ticker: Stock symbol
            df: DataFrame with OHLCV data
            position: Current position data
            
        Returns:
            Enhanced exit analysis
        """
        try:
            # Start with v7.2 exit analysis
            base_exit = check_exit_conditions_v7_2(df, position)
            
            # Add Sweet Spot enhancements
            enhanced_exit = base_exit.copy()
            enhanced_exit['sweet_spot_exit_analysis'] = {}
            
            # Pattern-based exit signals
            if self.enable_patterns:
                try:
                    # Get pattern signals
                    candlestick_signals = get_candlestick_signals(df)
                    chart_signals = get_chart_pattern_signals(df)
                    all_signals = combine_pattern_signals(candlestick_signals, chart_signals)
                    
                    # Check for bearish patterns that might suggest early exit
                    pattern_summary = get_pattern_summary(all_signals)
                    
                    # Enhanced exit logic based on patterns
                    pattern_exit_signal = self._check_pattern_exit_signals(
                        pattern_summary, position
                    )
                    
                    enhanced_exit['sweet_spot_exit_analysis']['patterns'] = pattern_summary
                    enhanced_exit['sweet_spot_exit_analysis']['pattern_exit_signal'] = pattern_exit_signal
                    
                    # Update exit decision if pattern suggests exit
                    if pattern_exit_signal['should_exit']:
                        enhanced_exit['should_exit'] = True
                        enhanced_exit['exit_reason'] = f"Pattern-based exit: {pattern_exit_signal['reason']}"
                        log_info(f"[SWEET_SPOT] {ticker} pattern-based exit signal: {pattern_exit_signal['reason']}")
                
                except Exception as e:
                    log_error(f"[SWEET_SPOT] Error in pattern exit analysis for {ticker}: {e}")
            
            return enhanced_exit
            
        except Exception as e:
            log_error(f"[SWEET_SPOT] Error in enhanced exit analysis for {ticker}: {e}")
            return check_exit_conditions_v7_2(ticker, df, position)
    
    def _check_pattern_exit_signals(self, pattern_summary: Dict, 
                                  position: Dict) -> Dict[str, Any]:
        """
        Check if patterns suggest early exit
        
        Args:
            pattern_summary: Pattern analysis summary
            position: Current position data
            
        Returns:
            Exit signal analysis
        """
        try:
            exit_signal = {
                'should_exit': False,
                'reason': '',
                'confidence': 0.0
            }
            
            # Check for strong bearish patterns
            bearish_patterns = pattern_summary.get('bearish_patterns', [])
            pattern_strength = pattern_summary.get('pattern_strength', 0)
            
            # Strong bearish patterns suggest exit
            if pattern_strength < -0.6:
                exit_signal['should_exit'] = True
                exit_signal['reason'] = f"Strong bearish patterns: {', '.join(bearish_patterns)}"
                exit_signal['confidence'] = abs(pattern_strength)
            
            # Specific patterns that suggest exit
            high_priority_bearish = ['head_shoulders', 'm_formation', 'fifty_percent_rule']
            found_high_priority = [p for p in high_priority_bearish if p in bearish_patterns]
            
            if found_high_priority:
                exit_signal['should_exit'] = True
                exit_signal['reason'] = f"High priority bearish pattern: {', '.join(found_high_priority)}"
                exit_signal['confidence'] = 0.8
            
            # Doji pattern suggests indecision - consider exit
            if 'doji' in pattern_summary.get('neutral_patterns', []):
                exit_signal['should_exit'] = True
                exit_signal['reason'] = "Doji pattern indicates indecision"
                exit_signal['confidence'] = 0.6
            
            return exit_signal
            
        except Exception as e:
            log_error(f"[SWEET_SPOT] Error checking pattern exit signals: {e}")
            return {'should_exit': False, 'reason': 'Error in pattern exit analysis', 'confidence': 0.0}

# Convenience functions for backward compatibility
def analyze_stock_sweet_spot(ticker: str, df: pd.DataFrame, 
                           portfolio_data: Dict = None, config: Dict = None,
                           brokerage_interface=None) -> Dict[str, Any]:
    """
    Convenience function for Sweet Spot analysis
    
    Args:
        ticker: Stock symbol
        df: DataFrame with OHLCV data
        portfolio_data: Current portfolio state
        config: Strategy configuration
        brokerage_interface: IBKR interface
        
    Returns:
        Enhanced analysis results
    """
    strategy = SweetSpotStrategy(config, brokerage_interface)
    return strategy.analyze_stock_sweet_spot(ticker, df, portfolio_data)

def check_exit_conditions_sweet_spot(ticker: str, df: pd.DataFrame, 
                                   position: Dict, config: Dict = None,
                                   brokerage_interface=None) -> Dict[str, Any]:
    """
    Convenience function for Sweet Spot exit analysis
    
    Args:
        ticker: Stock symbol
        df: DataFrame with OHLCV data
        position: Current position data
        config: Strategy configuration
        brokerage_interface: IBKR interface
        
    Returns:
        Enhanced exit analysis
    """
    strategy = SweetSpotStrategy(config, brokerage_interface)
    return strategy.check_exit_conditions_sweet_spot(ticker, df, position)
