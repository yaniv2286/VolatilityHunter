import time
import os
from datetime import datetime

print("=== COMPREHENSIVE DAILY TRADING TRACKER ===")
print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print()

# Track both logs
trading_log = f"logs/trading_{datetime.now().strftime('%Y-%m-%d')}.log"
gateway_log = "logs/ibc_gateway.log"

print(f"Monitoring:")
print(f"  Trading Log: {trading_log}")
print(f"  Gateway Log: {gateway_log}")
print()

# Key events to track
critical_events = [
    "Step 1: Reconciling with IBKR",
    "Step 2: Fetching latest prices",
    "Step 3: Checking exits",
    "Step 4: Scanning universe", 
    "Step 5: Executing entries",
    "Step 6: OrderMonitor",
    "Step 7: Sending summary",
    "Daily loop complete"
]

portfolio_events = [
    "Portfolio synced with IBKR",
    "Positions:",
    "Cash:",
    "Total equity",
    "entries:",
    "exits:",
    "placed",
    "filled",
    "cancelled"
]

print("Critical Events to Track:")
for event in critical_events:
    print(f"  - {event}")
print()

print("Portfolio & Trade Events:")
for event in portfolio_events:
    print(f"  - {event}")
print()

# Initialize positions
trading_pos = 0
gateway_pos = 0

print("=" * 60)
print("MONITORING STARTED")
print("=" * 60)

while True:
    try:
        timestamp = datetime.now().strftime('%H:%M:%S')
        
        # Check trading log
        if os.path.exists(trading_log):
            current_size = os.path.getsize(trading_log)
            if 'trading_pos' not in locals():
                trading_pos = current_size
            elif current_size > trading_pos:
                with open(trading_log, 'r', encoding='utf-8') as f:
                    f.seek(trading_pos)
                    new_lines = f.readlines()
                
                for line in new_lines:
                    # Check for critical events
                    for event in critical_events:
                        if event in line:
                            print(f"[{timestamp}] 🎯 CRITICAL: {event}")
                            break
                    else:
                        # Check for portfolio/trade events
                        for event in portfolio_events:
                            if event in line.lower():
                                print(f"[{timestamp}] 📊 {line.strip()}")
                                break
                        else:
                            # Check for errors
                            if any(keyword in line.lower() for keyword in ["error", "failed", "abort"]):
                                print(f"[{timestamp}] ❌ ERROR: {line.strip()}")
                            elif "connected to ibkr" in line.lower():
                                print(f"[{timestamp}] ✅ IBKR: {line.strip()}")
                
                trading_pos = current_size
        
        # Check gateway log
        if os.path.exists(gateway_log):
            current_size = os.path.getsize(gateway_log)
            if 'gateway_pos' not in locals():
                gateway_pos = current_size
            elif current_size > gateway_pos:
                with open(gateway_log, 'r', encoding='utf-8') as f:
                    f.seek(gateway_pos)
                    new_lines = f.readlines()
                
                for line in new_lines:
                    if "2026-03-19" in line and any(keyword in line.lower() for keyword in ["login", "api", "ready", "error"]):
                        print(f"[{timestamp}] 🌐 GATEWAY: {line.strip()}")
                
                gateway_pos = current_size
        
        time.sleep(1)  # Check every second
        
    except KeyboardInterrupt:
        print("\n" + "=" * 60)
        print("MONITORING STOPPED BY USER")
        print("=" * 60)
        break
    except Exception as e:
        print(f"[{timestamp}] 🚨 TRACKER ERROR: {e}")
        time.sleep(1)
