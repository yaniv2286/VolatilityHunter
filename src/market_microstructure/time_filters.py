"""
Time-based Filters for Sweet Spot Blueprint
Implements 10:06 AM rule and Friday rule as preference filters
"""

import pandas as pd
import numpy as np
from datetime import datetime, timezone, timedelta
from typing import Tuple, Optional
from src.notifications import log_info, log_warning

def check_10_06_rule(current_time: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Check 10:06 AM Rule - Preference filter for pre-10:06 AM EST trading
    
    Args:
        current_time: Current datetime (defaults to now)
        
    Returns:
        Tuple of (is_optimal, message) for logging and scoring
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Convert to EST (UTC-5 or UTC-4 during DST)
    est_time = current_time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-5)))
    
    # Check if before 10:06 AM EST
    if est_time.hour < 10 or (est_time.hour == 10 and est_time.minute < 6):
        message = f"[TIME] Pre-10:06 AM EST ({est_time.strftime('%H:%M')} EST) - Preference penalty applied"
        log_warning(message)
        return False, message
    else:
        message = f"[TIME] Post-10:06 AM EST ({est_time.strftime('%H:%M')} EST) - Optimal trading time"
        log_info(message)
        return True, message

def check_friday_rule(current_time: Optional[datetime] = None) -> Tuple[bool, str]:
    """
    Check Friday Rule - Preference filter for Friday trading
    
    Args:
        current_time: Current datetime (defaults to now)
        
    Returns:
        Tuple of (is_optimal, message) for logging and scoring
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Convert to EST
    est_time = current_time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=-5)))
    
    # Check if it's Friday
    if est_time.weekday() == 4:  # Friday is 4 in Monday=0 system
        message = f"[TIME] Friday trading - Profit-taking risk, preference penalty applied"
        log_warning(message)
        return False, message
    else:
        message = f"[TIME] {est_time.strftime('%A')} trading - Optimal day"
        log_info(message)
        return True, message

def calculate_time_score(current_time: Optional[datetime] = None) -> float:
    """
    Calculate overall time-based preference score (0.0 to 1.0)
    
    Args:
        current_time: Current datetime (defaults to now)
        
    Returns:
        Time score between 0.0 (poor) and 1.0 (optimal)
    """
    score = 1.0
    
    # Check 10:06 AM rule
    is_optimal_10_06, _ = check_10_06_rule(current_time)
    if not is_optimal_10_06:
        score -= 0.3  # 30% penalty for pre-10:06 AM
    
    # Check Friday rule
    is_optimal_friday, _ = check_friday_rule(current_time)
    if not is_optimal_friday:
        score -= 0.2  # 20% penalty for Friday
    
    # Ensure score doesn't go below 0
    return max(0.0, score)

def is_in_sweet_spot_window(current_time: Optional[datetime] = None) -> bool:
    """
    Check if current time is within VolatilityHunter SweetSpot window (17:30-23:00 IST)
    
    Args:
        current_time: Current datetime (defaults to now)
        
    Returns:
        True if within SweetSpot window
    """
    if current_time is None:
        current_time = datetime.now(timezone.utc)
    
    # Convert to IST (UTC+5:30)
    ist_time = current_time.replace(tzinfo=timezone.utc).astimezone(timezone(timedelta(hours=5, minutes=30)))
    
    # Check if within 17:30-23:00 IST window
    ist_hour = ist_time.hour
    ist_minute = ist_time.minute
    
    # Convert to minutes since midnight for comparison
    current_minutes = ist_hour * 60 + ist_minute
    window_start = 17 * 60 + 30  # 17:30
    window_end = 23 * 60           # 23:00
    
    return window_start <= current_minutes <= window_end
