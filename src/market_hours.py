"""
Market Hours Checker for VolatilityHunter
Prevents order placement outside US market hours
"""

import pytz
from datetime import datetime, time, timedelta
from src.notifications import log_info, log_warning, log_error

class MarketHours:
    """US Market Hours Checker"""
    
    def __init__(self):
        self.timezone = pytz.timezone('US/Eastern')
        self.market_open = time(9, 30)  # 9:30 AM
        self.market_close = time(16, 0)  # 4:00 PM
        self.early_close_time = time(13, 0)  # 1:00 PM for early close days
    
    def get_current_time(self):
        """Get current US/Eastern time"""
        return datetime.now(self.timezone)
    
    def is_market_open(self, current_time=None):
        """
        Check if US market is currently open
        
        Args:
            current_time: datetime to check (defaults to now)
            
        Returns:
            bool: True if market is open
        """
        if current_time is None:
            current_time = self.get_current_time()
        
        # Check if it's a weekday
        if current_time.weekday() >= 5:  # Saturday = 5, Sunday = 6
            return False
        
        # Check if it's within market hours
        current_time_only = current_time.time()
        
        # Regular trading hours: 9:30 AM - 4:00 PM
        if self.market_open <= current_time_only <= self.market_close:
            return True
        
        return False
    
    def get_time_until_open(self, current_time=None):
        """Get time until market opens"""
        if current_time is None:
            current_time = self.get_current_time()
        
        # If it's weekend, calculate until Monday open
        if current_time.weekday() >= 5:
            days_until_monday = 7 - current_time.weekday()
            next_open = current_time + timedelta(days=days_until_monday)
            next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)
        else:
            # If before market open, calculate until today's open
            if current_time.time() < self.market_open:
                next_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
            else:
                # If after market close, calculate until tomorrow's open
                next_open = current_time + timedelta(days=1)
                next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)
        
        return next_open - current_time
    
    def get_time_until_close(self, current_time=None):
        """Get time until market closes"""
        if current_time is None:
            current_time = self.get_current_time()
        
        # If it's weekend, market is already closed
        if current_time.weekday() >= 5:
            return timedelta(0)
        
        # If before market open, time until close includes open time
        if current_time.time() < self.market_open:
            close_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        elif current_time.time() > self.market_close:
            # Market is already closed
            return timedelta(0)
        else:
            # Market is open, calculate until close
            close_time = current_time.replace(hour=16, minute=0, second=0, microsecond=0)
        
        return close_time - current_time
    
    def validate_trading_time(self):
        """
        Validate if current time is suitable for trading
        
        Returns:
            dict: Validation result with details
        """
        current_time = self.get_current_time()
        is_open = self.is_market_open(current_time)
        
        result = {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'is_market_open': is_open,
            'market_hours': f"{self.market_open.strftime('%H:%M')} - {self.market_close.strftime('%H:%M')} US/Eastern",
            'weekday': current_time.strftime('%A')
        }
        
        if not is_open:
            if current_time.weekday() >= 5:
                result['reason'] = 'Weekend - Market closed'
                result['next_open'] = (current_time + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')
            elif current_time.time() < self.market_open:
                result['reason'] = 'Pre-market - Market not yet open'
                result['next_open'] = current_time.replace(hour=9, minute=30, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')
            else:
                result['reason'] = 'After-hours - Market closed'
                result['next_open'] = (current_time + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')
        
        return result
    
    def log_market_status(self):
        """Log current market status"""
        status = self.validate_trading_time()
        
        log_info(f"Market Status: {status['current_time']}")
        log_info(f"Market Hours: {status['market_hours']}")
        log_info(f"Weekday: {status['weekday']}")
        
        if status['is_market_open']:
            log_info("✅ Market is OPEN - Trading allowed")
            time_until_close = self.get_time_until_close()
            log_info(f"⏰ Time until close: {time_until_close}")
        else:
            log_warning(f"❌ Market is CLOSED - {status['reason']}")
            log_info(f"📅 Next open: {status.get('next_open', 'Unknown')}")
        
        return status

# Global instance
market_hours = MarketHours()

def is_trading_time():
    """Quick check if it's trading time"""
    return market_hours.is_market_open()

def validate_before_trading():
    """Validate market hours before trading"""
    status = market_hours.log_market_status()
    
    if not status['is_market_open']:
        log_error("🚨 TRADING HALTED - Market is closed")
        log_error(f"Reason: {status['reason']}")
        log_error(f"Next open: {status.get('next_open', 'Unknown')}")
        return False
    
    return True
