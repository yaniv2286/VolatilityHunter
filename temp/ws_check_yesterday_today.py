from datetime import datetime, timezone, timedelta
import pytz
import os

# Current time
now_utc = datetime.now(timezone.utc)
now_ist = now_utc.astimezone(pytz.timezone('Asia/Jerusalem'))

print("=== YESTERDAY'S RUN ANALYSIS ===")
print(f"Current UTC: {now_utc.strftime('%Y-%m-%d %H:%M')}")
print(f"Current IST: {now_ist.strftime('%Y-%m-%d %H:%M')}")
print()

# Check if yesterday's log exists
yesterday_log = "logs/trading_2026-03-17.log"
if os.path.exists(yesterday_log):
    with open(yesterday_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Find the completion line
    completion_line = None
    for line in reversed(lines):
        if "Daily loop complete" in line:
            completion_line = line
            break
    
    if completion_line:
        print("✅ YESTERDAY'S RUN STATUS:")
        print(f"  {completion_line.strip()}")
        
        # Extract timing
        if "complete in" in completion_line:
            runtime = completion_line.split("complete in ")[1].strip()
            print(f"  Runtime: {runtime}")
        
        # Find final portfolio
        for line in reversed(lines):
            if "Positions:" in line and "Cash:" in line:
                print(f"  Final: {line.strip()}")
                break
    else:
        print("❌ YESTERDAY'S RUN: No completion found")
else:
    print("❌ YESTERDAY'S LOG: Not found")

print()
print("=== TODAY'S SCHEDULE ===")
print(f"Scheduled: 17:06 IST")

# Check if scheduled run has passed today
if now_ist.hour >= 17 and now_ist.minute >= 6:
    print("✅ Scheduled run for today already completed")
    
    # Check for today's log
    today_log = f"logs/trading_{now_ist.strftime('%Y-%m-%d')}.log"
    if os.path.exists(today_log):
        print(f"✅ Today's log exists: {today_log}")
    else:
        print(f"❌ Today's log not found: {today_log}")
else:
    print("⏳ Scheduled run for today pending")
    time_to_wait = (now_ist.replace(hour=17, minute=6, second=0, microsecond=0) - now_ist)
    if time_to_wait.total_seconds() > 0:
        hours = time_to_wait.total_seconds() / 3600
        print(f"   Time to wait: {hours:.1f} hours")
    else:
        # If time passed but it's the next day
        tomorrow = now_ist + timedelta(days=1)
        time_to_wait = (tomorrow.replace(hour=17, minute=6, second=0, microsecond=0) - now_ist)
        hours = time_to_wait.total_seconds() / 3600
        print(f"   Time to wait: {hours:.1f} hours (tomorrow)")

print()
print("=== SYSTEM READINESS CHECK ===")
# Check key files
files_to_check = [
    "scripts/start_gateway_with_retry.py",
    "scripts/stop_gateway.py",
    "scripts/monitor_trading_logs.py",
    "scripts/DAILY_ROUTINE/run_trading.bat"
]

all_ready = True
for file_path in files_to_check:
    if os.path.exists(file_path):
        print(f"✅ {file_path}")
    else:
        print(f"❌ {file_path}")
        all_ready = False

if all_ready:
    print("✅ SYSTEM READY FOR TODAY'S RUN")
else:
    print("❌ SYSTEM NOT READY - Missing files")
