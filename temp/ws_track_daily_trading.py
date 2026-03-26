import time
import os
from datetime import datetime

print("=== DAILY TRADING LOOP TRACKER ===")
print(f"Starting at: {datetime.now().strftime('%H:%M:%S')}")
print()

# Track the trading log
log_file = f"logs/trading_{datetime.now().strftime('%Y-%m-%d')}.log"
print(f"Monitoring: {log_file}")

# Key events to track
trading_events = [
    "Step 1: Reconciling with IBKR",
    "Step 2: Fetching latest prices",
    "Step 3: Checking exits",
    "Step 4: Scanning universe",
    "Step 5: Executing entries",
    "Step 6: OrderMonitor",
    "Step 7: Sending summary",
    "Daily loop complete"
]

print("\nExpected Trading Events:")
for event in trading_events:
    print(f"  - {event}")
print()

# Start monitoring
print("Monitoring trading loop...")
print("-" * 50)

last_position = 0
if os.path.exists(log_file):
    last_position = os.path.getsize(log_file)

while True:
    try:
        if os.path.exists(log_file):
            current_size = os.path.getsize(log_file)
            
            if current_size > last_position:
                with open(log_file, 'r', encoding='utf-8') as f:
                    f.seek(last_position)
                    new_lines = f.readlines()
                
                for line in new_lines:
                    timestamp = datetime.now().strftime('%H:%M:%S')
                    
                    # Check for trading events
                    for event in trading_events:
                        if event in line:
                            print(f"[{timestamp}] 🎯 {event.upper()}")
                            break
                    else:
                        # Show important events
                        if any(keyword in line.lower() for keyword in ["error", "entry:", "exit:", "placed", "filled", "cancelled", "summary"]):
                            print(f"[{timestamp}] 📊 {line.strip()}")
                        elif "connected to ibkr" in line.lower():
                            print(f"[{timestamp}] ✅ {line.strip()}")
                        elif "positions:" in line.lower() and "cash:" in line.lower():
                            print(f"[{timestamp}] 💰 {line.strip()}")
                
                last_position = current_size
        
        time.sleep(1)  # Check every second
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
