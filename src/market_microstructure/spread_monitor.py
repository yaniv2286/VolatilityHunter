"""
Spread Monitor for Sweet Spot Blueprint
Implements real-time bid/ask spread monitoring via IBKR API
"""

import pandas as pd
import numpy as np
from typing import Dict, Tuple, Optional, Any
from src.notifications import log_info, log_warning, log_error
from src.brokerage_interface import BrokerageInterface

class SpreadMonitor:
    """
    Real-time bid/ask spread monitoring using IBKR data
    """
    
    def __init__(self, brokerage_interface: Optional[BrokerageInterface] = None):
        """
        Initialize spread monitor
        
        Args:
            brokerage_interface: IBKR connection for real-time data
        """
        self.brokerage = brokerage_interface
        self.spread_cache = {}  # Cache recent spread data
        self.cache_timeout = 60  # Cache for 60 seconds
        
    def get_current_spread(self, ticker: str) -> Tuple[float, float, float]:
        """
        Get current bid/ask spread for a ticker
        
        Args:
            ticker: Stock symbol
            
        Returns:
            Tuple of (bid, ask, spread) or (0, 0, 0) if unavailable
        """
        try:
            if self.brokerage is None:
                log_warning(f"[SPREAD] No brokerage interface available for {ticker}")
                return 0.0, 0.0, 0.0
            
            # Get real-time quote from IBKR
            quote_data = self.brokerage.get_real_time_quote(ticker)
            
            if quote_data is None or 'bid' not in quote_data or 'ask' not in quote_data:
                log_warning(f"[SPREAD] No quote data available for {ticker}")
                return 0.0, 0.0, 0.0
            
            bid = float(quote_data['bid'])
            ask = float(quote_data['ask'])
            spread = ask - bid
            
            log_info(f"[SPREAD] {ticker}: Bid=${bid:.2f}, Ask=${ask:.2f}, Spread=${spread:.2f}")
            
            return bid, ask, spread
            
        except Exception as e:
            log_error(f"[SPREAD] Error getting spread for {ticker}: {e}")
            return 0.0, 0.0, 0.0
    
    def check_spread_limits(self, ticker: str, current_price: float) -> Tuple[bool, str, float]:
        """
        Check if spread meets Sweet Spot Blueprint limits
        
        Args:
            ticker: Stock symbol
            current_price: Current stock price
            
        Returns:
            Tuple of (is_acceptable, message, spread_percentage)
        """
        bid, ask, spread = self.get_current_spread(ticker)
        
        if spread == 0.0:
            message = f"[SPREAD] {ticker}: No spread data available - proceeding with caution"
            log_warning(message)
            return True, message, 0.0
        
        # Calculate spread percentage
        spread_percentage = (spread / current_price) * 100
        
        # Sweet Spot Blueprint spread limits
        if current_price < 100:
            max_spread = 0.02  # 2 cents for under $100
            max_spread_desc = "2 cents"
        elif current_price >= 250 and current_price < 300:
            max_spread = 0.05  # 5 cents for $250+
            max_spread_desc = "5 cents"
        elif current_price >= 300:
            max_spread = 0.20  # 20 cents absolute max for $300+
            max_spread_desc = "20 cents (absolute max)"
        else:
            max_spread = 0.03  # 3 cents default for $100-$249
            max_spread_desc = "3 cents"
        
        is_acceptable = spread <= max_spread
        
        if is_acceptable:
            message = f"[SPREAD] {ticker}: ${spread:.2f} spread acceptable (max: {max_spread_desc})"
            log_info(message)
        else:
            message = f"[SPREAD] {ticker}: ${spread:.2f} spread EXCEEDS limit (max: {max_spread_desc}) - REJECTING"
            log_error(message)
        
        return is_acceptable, message, spread_percentage
    
    def get_spread_quality_score(self, ticker: str, current_price: float) -> float:
        """
        Calculate spread quality score (0.0 to 1.0)
        
        Args:
            ticker: Stock symbol
            current_price: Current stock price
            
        Returns:
            Quality score between 0.0 (poor) and 1.0 (excellent)
        """
        bid, ask, spread = self.get_current_spread(ticker)
        
        if spread == 0.0:
            return 0.5  # Neutral score if no data available
        
        # Calculate ideal spread based on price
        if current_price < 100:
            ideal_spread = 0.01  # 1 cent ideal
        elif current_price < 250:
            ideal_spread = 0.02  # 2 cents ideal
        elif current_price < 300:
            ideal_spread = 0.03  # 3 cents ideal
        else:
            ideal_spread = 0.05  # 5 cents ideal
        
        # Calculate score based on how close to ideal
        if spread <= ideal_spread:
            return 1.0
        else:
            # Linear decay from ideal to max acceptable
            if current_price < 100:
                max_spread = 0.02
            elif current_price < 250:
                max_spread = 0.03
            elif current_price < 300:
                max_spread = 0.05
            else:
                max_spread = 0.20
            
            if spread >= max_spread:
                return 0.0
            else:
                # Linear interpolation between ideal and max
                score = 1.0 - ((spread - ideal_spread) / (max_spread - ideal_spread))
                return max(0.0, score)

# Convenience function for direct usage
def check_spread_limits(ticker: str, current_price: float, brokerage_interface: Optional[BrokerageInterface] = None) -> Tuple[bool, str, float]:
    """
    Convenience function to check spread limits
    
    Args:
        ticker: Stock symbol
        current_price: Current stock price
        brokerage_interface: IBKR connection
        
    Returns:
        Tuple of (is_acceptable, message, spread_percentage)
    """
    monitor = SpreadMonitor(brokerage_interface)
    return monitor.check_spread_limits(ticker, current_price)
