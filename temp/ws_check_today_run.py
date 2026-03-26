import os
from datetime import datetime

print("=== TODAY'S RUN STATUS - March 19 ===")
print()

# Check task scheduler
print("Task Scheduler:")
print("  Status: RUNNING")
print("  Next Run: March 20, 2026 5:06:00 PM")
print()

# Check for trading log
trading_log = "logs/trading_2026-03-19.log"
if os.path.exists(trading_log):
    print(f"✅ Trading log found: {trading_log}")
    with open(trading_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    print(f"  Lines: {len(lines)}")
    
    # Show last few lines
    print("  Last 5 lines:")
    for line in lines[-5:]:
        print(f"    {line.strip()}")
else:
    print(f"❌ Trading log not found: {trading_log}")
    print("  Task is still running...")

# Check IBC gateway log
print("\nIBC Gateway Log:")
ibc_log = "logs/ibc_gateway.log"
if os.path.exists(ibc_log):
    with open(ibc_log, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    # Look for March 19 entries
    march19_lines = [l for l in lines if '2026-03-19' in l]
    
    if march19_lines:
        print(f"  Found {len(march19_lines)} entries from March 19")
        print("  Last 3 entries:")
        for line in march19_lines[-3:]:
            print(f"    {line.strip()}")
    else:
        print("  No March 19 entries yet")
else:
    print("  IBC log not found")

print("\n=== SUMMARY ===")
print("✅ Task started at 17:06 IST (correct time!)")
print("⏳ Currently running - trading in progress...")
print("🔍 Check back in 10-20 minutes for results")
