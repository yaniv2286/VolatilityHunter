from datetime import datetime, timezone, timedelta
import pytz

# Current times
now_utc = datetime.now(timezone.utc)
now_ist = now_utc.astimezone(pytz.timezone('Asia/Jerusalem'))
now_et = now_utc.astimezone(pytz.timezone('America/New_York'))

# Scheduled time
scheduled_ist = now_ist.replace(hour=17, minute=6, second=0, microsecond=0)
if scheduled_ist < now_ist:
    scheduled_ist += timedelta(days=1)

# Time to wait
time_to_wait = scheduled_ist - now_ist
hours_to_wait = time_to_wait.total_seconds() / 3600

print("=== SCHEDULE CHECK ===")
print(f"Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Current IST: {now_ist.strftime('%Y-%m-%d %H:%M:%S')}")
print(f"Current ET:  {now_et.strftime('%Y-%m-%d %H:%M:%S')}")
print()
print(f"Scheduled:   {scheduled_ist.strftime('%Y-%m-%d %H:%M:%S')} IST")
print(f"Time to wait: {hours_to_wait:.1f} hours")
print()

# Market hours at scheduled time
scheduled_et = scheduled_ist.astimezone(pytz.timezone('America/New_York'))
market_open = scheduled_et.replace(hour=9, minute=30, second=0, microsecond=0)
market_close = scheduled_et.replace(hour=16, minute=0, second=0, microsecond=0)

print("MARKET HOURS AT SCHEDULED TIME:")
print(f"Scheduled ET: {scheduled_et.strftime('%H:%M:%S')}")
print(f"Market open:  {market_open.strftime('%H:%M:%S')}")
print(f"Market close: {market_close.strftime('%H:%M:%S')}")
print()

if market_open <= scheduled_et <= market_close:
    print("✅ SCHEDULED TIME IS DURING MARKET HOURS")
else:
    print("❌ SCHEDULED TIME IS OUTSIDE MARKET HOURS")
