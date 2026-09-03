"""
Market Hours Checker for VolatilityHunter
Prevents order placement outside US market hours, on holidays, and after early closes.
"""

import pytz
from datetime import datetime, time, timedelta, date
from src.notifications import log_info, log_warning, log_error


class MarketHours:
    """US Market Hours Checker (NYSE) with 2026 holiday/early-close calendar."""

    # 2026 NYSE holidays (full market closures)
    HOLIDAYS_2026 = {
        date(2026, 1, 1),   # New Year's Day
        date(2026, 1, 19),  # Martin Luther King Jr. Day
        date(2026, 2, 16),  # Presidents' Day
        date(2026, 4, 3),   # Good Friday
        date(2026, 5, 25),  # Memorial Day
        date(2026, 6, 19),  # Juneteenth National Independence Day
        date(2026, 7, 3),   # Independence Day observed (July 4 is Saturday)
        date(2026, 9, 7),   # Labor Day
        date(2026, 11, 26), # Thanksgiving Day
        date(2026, 12, 25), # Christmas Day
    }

    # 2026 early closes (1:00 PM ET)
    EARLY_CLOSES_2026 = {
        date(2026, 7, 3):   time(13, 0),  # Independence Day observed
        date(2026, 11, 27): time(13, 0),  # Day after Thanksgiving
        date(2026, 12, 24): time(13, 0),  # Christmas Eve
    }

    def __init__(self):
        self.timezone = pytz.timezone('US/Eastern')
        self.market_open = time(9, 30)
        self.market_close = time(16, 0)
        self.early_close_time = time(13, 0)

    def get_current_time(self):
        """Get current US/Eastern time."""
        return datetime.now(self.timezone)

    def is_trading_day(self, current_time=None):
        """Return True if the current date is a US trading day."""
        if current_time is None:
            current_time = self.get_current_time()
        d = current_time.date()
        # Weekend check
        if d.weekday() >= 5:
            return False
        # Holiday check
        if d in self.HOLIDAYS_2026:
            return False
        return True

    def is_market_open(self, current_time=None):
        """
        Check if US market is currently open, accounting for holidays and early closes.
        """
        if current_time is None:
            current_time = self.get_current_time()

        if not self.is_trading_day(current_time):
            return False

        if current_time.weekday() >= 5:
            return False

        current_time_only = current_time.time()
        d = current_time.date()
        close_time = self.EARLY_CLOSES_2026.get(d, self.market_close)

        if self.market_open <= current_time_only <= close_time:
            return True

        return False

    def get_time_until_open(self, current_time=None):
        """Get time until market opens."""
        if current_time is None:
            current_time = self.get_current_time()

        if current_time.weekday() >= 5:
            days_until_monday = 7 - current_time.weekday()
            next_open = current_time + timedelta(days=days_until_monday)
            next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)
        else:
            if current_time.time() < self.market_open:
                next_open = current_time.replace(hour=9, minute=30, second=0, microsecond=0)
            else:
                next_open = current_time + timedelta(days=1)
                next_open = next_open.replace(hour=9, minute=30, second=0, microsecond=0)

        return next_open - current_time

    def get_time_until_close(self, current_time=None):
        """Get time until market closes (or early close)."""
        if current_time is None:
            current_time = self.get_current_time()

        if current_time.weekday() >= 5:
            return timedelta(0)

        d = current_time.date()
        close_time = self.EARLY_CLOSES_2026.get(d, self.market_close)

        if current_time.time() < self.market_open:
            close_time = current_time.replace(hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0)
        elif current_time.time() > close_time:
            return timedelta(0)
        else:
            close_time = current_time.replace(hour=close_time.hour, minute=close_time.minute, second=0, microsecond=0)

        return close_time - current_time

    def validate_trading_time(self):
        """Validate if current time is suitable for trading."""
        current_time = self.get_current_time()
        is_open = self.is_market_open(current_time)
        is_trading_day = self.is_trading_day(current_time)

        result = {
            'current_time': current_time.strftime('%Y-%m-%d %H:%M:%S %Z'),
            'is_market_open': is_open,
            'is_trading_day': is_trading_day,
            'market_hours': f"{self.market_open.strftime('%H:%M')} - {self.market_close.strftime('%H:%M')} US/Eastern",
            'weekday': current_time.strftime('%A')
        }

        if not is_open:
            if not is_trading_day:
                result['reason'] = 'Holiday or weekend - Market closed'
            elif current_time.weekday() >= 5:
                result['reason'] = 'Weekend - Market closed'
            elif current_time.time() < self.market_open:
                result['reason'] = 'Pre-market - Market not yet open'
            else:
                result['reason'] = 'After-hours / Early close - Market closed'
            result['next_open'] = (current_time + timedelta(days=1)).replace(hour=9, minute=30, second=0, microsecond=0).strftime('%Y-%m-%d %H:%M:%S %Z')

        return result

    def log_market_status(self):
        """Log current market status."""
        status = self.validate_trading_time()

        log_info(f"Market Status: {status['current_time']}")
        log_info(f"Market Hours: {status['market_hours']}")
        log_info(f"Weekday: {status['weekday']}")

        if status['is_market_open']:
            log_info("Market is OPEN - Trading allowed")
            time_until_close = self.get_time_until_close()
            log_info(f"Time until close: {time_until_close}")
        else:
            log_warning(f"Market is CLOSED - {status['reason']}")
            log_info(f"Next open: {status.get('next_open', 'Unknown')}")

        return status


# Global instance
market_hours = MarketHours()


def is_trading_time():
    """Quick check if it's trading time."""
    return market_hours.is_market_open()


def validate_before_trading():
    """Validate market hours before trading."""
    return market_hours.log_market_status()
