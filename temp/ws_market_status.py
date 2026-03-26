from datetime import datetime, timezone
import pytz

# Current times
utc = datetime.now(timezone.utc)
ist = utc.astimezone(pytz.timezone('Asia/Jerusalem'))
et = utc.astimezone(pytz.timezone('America/New_York'))

print("=== MARKET STATUS ===")
print(f"Current Times:")
print(f"  IST: {ist.strftime('%Y-%m-%d %H:%M:%S %A')}")
print(f"  UTC: {utc.strftime('%Y-%m-%d %H:%M:%S %A')}")
print(f"  ET:  {et.strftime('%Y-%m-%d %H:%M:%S %A')}")
print()

# Market hours
market_open = et.replace(hour=9, minute=30, second=0, microsecond=0)
market_close = et.replace(hour=16, minute=0, second=0, microsecond=0)

print(f"US Market Hours (ET):")
print(f"  Open:  {market_open.strftime('%H:%M')}")
print(f"  Close: {market_close.strftime('%H:%M')}")
print()

# Check if market is open
if market_open <= et <= market_close:
    print("✅ US Markets are OPEN")
    time_to_close = (market_close - et).total_seconds() / 3600
    print(f"   Time until close: {time_to_close:.1f} hours")
else:
    print("❌ US Markets are CLOSED")
    if et < market_open:
        time_to_open = (market_open - et).total_seconds() / 3600
        print(f"   Time until open: {time_to_open:.1f} hours")
    else:
        time_since_close = (et - market_close).total_seconds() / 3600
        print(f"   Time since close: {time_since_close:.1f} hours")

print()

# Check if today is a weekday
print(f"Day Check:")
print(f"  IST: {ist.strftime('%A')}")
print(f"  ET:  {et.strftime('%A')}")
if et.weekday() >= 5:  # Saturday=5, Sunday=6
    print("❌ Weekend - US Markets Closed")
else:
    print("✅ Weekday - US Markets Should Be Open")
