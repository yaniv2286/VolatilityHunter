from datetime import datetime, timezone, timedelta
import pytz

print("=== CORRECTED TIMEZONE ANALYSIS ===")
print()

# Current time
now_utc = datetime.now(timezone.utc)
now_ist = now_utc.astimezone(pytz.timezone('Asia/Jerusalem'))
print(f"Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M')}")
print(f"Current IST: {now_ist.strftime('%Y-%m-%d %H:%M')}")
print()

# Task Scheduler runs at 17:06 IST
print("Task Scheduler Settings:")
print("  Time: 17:06 IST (Israel Time)")
print("  This is CORRECT for your timezone")
print()

# When it ran on March 18
print("March 18 Execution:")
print("  Scheduled: 17:06 IST")
print("  IBC Log shows: 00:06:08 IST")
print("  This is 17 hours EARLY - not a timezone issue")
print()

# Convert 00:06 IST to UTC and ET
march18_ist = datetime(2026, 3, 18, 0, 6, 8)
march18_utc = march18_ist.astimezone(pytz.UTC)
march18_et = march18_ist.astimezone(pytz.timezone('America/New_York'))

print("Time Conversion for March 18 00:06 IST:")
print(f"  IST: {march18_ist.strftime('%H:%M')}")
print(f"  UTC: {march18_utc.strftime('%H:%M')}")
print(f"  ET:  {march18_et.strftime('%H:%M')}")
print()

# Market hours check
market_open_et = march18_et.replace(hour=9, minute=30)
market_close_et = march18_et.replace(hour=16, minute=0)

print("Market Hours on March 17 ET (when it actually ran):")
print(f"  Market Open:  {market_open_et.strftime('%H:%M')}")
print(f"  Market Close: {market_close_et.strftime('%H:%M')}")
print(f"  Gateway Start: {march18_et.strftime('%H:%M')} (March 17 ET)")
print()

if market_open_et <= march18_et <= market_close_et:
    print("✅ Gateway started DURING market hours")
else:
    print("❌ Gateway started OUTSIDE market hours")

print()
print("=== REAL ISSUE ===")
print("The Task Scheduler is correctly set to 17:06 IST")
print("But something made it run at 00:06 instead")
print("Possible causes:")
print("1. Daylight Saving Time transition")
print("2. Task Scheduler misconfiguration")
print("3. System clock issue")
print("4. Task triggered by another event")
