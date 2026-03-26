import os
from datetime import datetime

print("=== MARCH 18 TRADING ANALYSIS ===")
print()

# Check for trading log
trading_log = "logs/trading_2026-03-18.log"
if os.path.exists(trading_log):
    print("✅ Trading log found")
    with open(trading_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"Lines: {len(lines)}")
    
    # Find key events
    for line in lines[-10:]:
        if any(keyword in line for keyword in ["Daily loop complete", "ERROR", "CRITICAL"]):
            print(f"Event: {line.strip()}")
else:
    print("❌ Trading log NOT found - trading failed to start")

# Check IBC gateway log
print("\n=== IBC Gateway Log ===")
ibc_log = "logs/ibc_gateway.log"
if os.path.exists(ibc_log):
    with open(ibc_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Look for March 18 entries
    march18_lines = []
    for line in lines:
        if "2026-03-18" in line:
            march18_lines.append(line)
    
    if march18_lines:
        print(f"Found {len(march18_lines)} entries from March 18")
        print("Last 5 entries:")
        for line in march18_lines[-5:]:
            print(f"  {line.strip()}")
    else:
        print("No March 18 entries in IBC log")
else:
    print("❌ IBC gateway log not found")

# Check other logs
print("\n=== Other Logs ===")
for file in os.listdir("logs"):
    if "2026-03-18" in file:
        size = os.path.getsize(f"logs/{file}")
        print(f"Found: {file} ({size:,} bytes)")

print("\n=== SUMMARY ===")
print("Task Scheduler: Ran at 17:06 IST on March 18")
print("Exit Code: 1 (FAILED)")
print("Likely Cause: Gateway failed to start or trading loop crashed")
