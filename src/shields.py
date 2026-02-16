#!/usr/bin/env python3
"""
Universal Shield System for VolatilityHunter
Provides safety checks that work across all execution modes (live, sim, backtest)
"""

import os
import sys
import pandas as pd
from datetime import datetime, timedelta
from typing import Optional, Dict, Any

# Add src to path for imports
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import get_stock_data
from src.notifications import log_info, log_warning, log_error


def is_earnings_safe(ticker: str, reference_date: str) -> bool:
    """
    Universal earnings safety shield that works across all execution modes.
    
    Args:
        ticker: Stock ticker symbol
        reference_date: Reference date for earnings check (YYYY-MM-DD format)
                       - Today for live mode
                       - Simulation date for sim mode
    
    Returns:
        True if earnings safe, False if earnings announcement within 3 days
    """
    try:
        # Load stock data (works with both Tiingo and Parquet loaders)
        df = get_stock_data(ticker)
        if df is None or df.empty:
            log_warning(f"No data available for earnings check: {ticker}")
            return True  # Default to safe if no data
        
        # Convert reference date to datetime
        ref_date = pd.to_datetime(reference_date).normalize()
        
        # Look for earnings announcements in the data
        earnings_safe = True
        
        # Check for earnings announcements within ±3 days of reference date
        for i in range(-3, 4):  # -3 to +3 days
            check_date = ref_date + timedelta(days=i)
            check_date_str = check_date.strftime('%Y-%m-%d')
            
            # Find the row for this date
            date_rows = df[df['date'].astype(str).str.startswith(check_date_str)]
            
            if not date_rows.empty:
                row = date_rows.iloc[0]
                
                # Check various earnings-related columns
                earnings_columns = [
                    'earnings_announcement', 'earnings_date', 'earnings',
                    'earnings_surprise', 'earnings_estimate', 'eps_surprise'
                ]
                
                for col in earnings_columns:
                    if col in df.columns and pd.notna(row[col]):
                        earnings_value = row[col]
                        if earnings_value not in [0, '', None, 'N/A']:
                            log_warning(f"Earnings announcement found for {ticker} on {check_date_str}: {earnings_value}")
                            earnings_safe = False
                            break
                
                # Also check for high volume spikes (potential earnings indicator)
                if 'volume' in df.columns and 'volume_sma_30' in df.columns:
                    volume_ratio = row['volume'] / row['volume_sma_30'] if row['volume_sma_30'] > 0 else 1
                    if volume_ratio > 3.0:  # Volume > 3x normal = potential earnings
                        log_warning(f"High volume spike detected for {ticker} on {check_date_str}: {volume_ratio:.1f}x normal")
                        earnings_safe = False
                
                if not earnings_safe:
                    break
        
        if earnings_safe:
            log_info(f"Earnings safe: {ticker} for {reference_date}")
        else:
            log_warning(f"Earnings unsafe: {ticker} for {reference_date} (announcement within 3 days)")
        
        return earnings_safe
        
    except Exception as e:
        log_error(f"Error checking earnings safety for {ticker}: {e}")
        return True  # Default to safe on error


def apply_universal_shields(ticker: str, reference_date: str) -> Dict[str, bool]:
    """
    Apply all universal shields to a ticker.
    
    Args:
        ticker: Stock ticker symbol
        reference_date: Reference date for shield checks
    
    Returns:
        Dictionary with shield results
    """
    shields = {
        'earnings_safe': True,
        'volume_safe': True,
        'price_safe': True
    }
    
    try:
        # Earnings Safety Shield
        shields['earnings_safe'] = is_earnings_safe(ticker, reference_date)
        
        # Volume Safety Shield (basic check)
        df = get_stock_data(ticker)
        if df is not None and not df.empty and 'volume' in df.columns:
            latest_volume = df['volume'].iloc[-1]
            if latest_volume < 100000:  # Minimum volume threshold
                shields['volume_safe'] = False
                log_warning(f"Low volume shield triggered: {ticker} ({latest_volume:,})")
        
        # Price Safety Shield (basic check)
        if df is not None and not df.empty:
            # Try different price column names
            price_col = None
            for col in ['adjClose', 'Close', 'close', 'price', 'Price']:
                if col in df.columns:
                    price_col = col
                    break
            
            if price_col:
                latest_price = df[price_col].iloc[-1]
                if latest_price < 5.0:  # Minimum price threshold
                    shields['price_safe'] = False
                    log_warning(f"Low price shield triggered: {ticker} (${latest_price:.2f})")
        
        # Overall safety
        all_safe = all(shields.values())
        
        if all_safe:
            log_info(f"All shields passed: {ticker}")
        else:
            failed_shields = [name for name, safe in shields.items() if not safe]
            log_warning(f"Shields failed: {ticker} - {', '.join(failed_shields)}")
        
        return shields
        
    except Exception as e:
        log_error(f"Error applying shields to {ticker}: {e}")
        return shields
