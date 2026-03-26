import os
from datetime import datetime, timedelta

# Current time
dt = datetime.now()
print(f"Current: {dt.strftime('%Y-%m-%d %H:%M')}")

# Check if March 18 trading log exists
log_file = "logs/trading_2026-03-18.log"
if os.path.exists(log_file):
    print(f"✅ Found: {log_file}")
    with open(log_file, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"Lines: {len(lines)}")
    
    # Find completion
    for line in reversed(lines):
        if "Daily loop complete" in line:
            print(f"Completion: {line.strip()}")
            break
        elif "ERROR" in line:
            print(f"Error: {line.strip()}")
            break
else:
    print(f"❌ Not found: {log_file}")
    
    # Check other logs from March 18
    for file in os.listdir("logs"):
        if "2026-03-18" in file:
            print(f"Found: {file}")
            size = os.path.getsize(f"logs/{file}")
            print(f"  Size: {size:,} bytes")

# Check task scheduler
print("\n=== Task Scheduler Status ===")
print("Task ran at 17:06 IST on March 18")
print("Last Result: 1 (FAILED)")
print("Next Run: Today at 17:06 IST")
