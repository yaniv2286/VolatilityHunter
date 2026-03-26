import time
import subprocess
import os
from datetime import datetime

print("=== GATEWAY UI TRACKER ===")
print(f"Starting at: {datetime.now().strftime('%H:%M:%S')}")
print()

# Track the IBC log
log_file = "logs/ibc_gateway.log"
initial_size = 0
if os.path.exists(log_file):
    initial_size = os.path.getsize(log_file)

print(f"Initial log size: {initial_size:,} bytes")
print("Watching for UI events...")
print()

# Key events to track
ui_events = [
    "detected frame",
    "WINDOW_OPENED", 
    "Login dialog",
    "Setting user name",
    "Setting password",
    "Login attempt",
    "Click button",
    "Login successful",
    "API connection ready"
]

print("Expected UI Events:")
for event in ui_events:
    print(f"  - {event}")
print()

# Start monitoring
print("Monitoring log for UI events...")
print("-" * 50)

last_position = initial_size
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
                    
                    # Check for UI events
                    for event in ui_events:
                        if event.lower() in line.lower():
                            print(f"[{timestamp}] 🎯 {event.upper()}: {line.strip()}")
                            break
                    else:
                        # Show other important events
                        if any(keyword in line.lower() for keyword in ["error", "failed", "success", "ready"]):
                            print(f"[{timestamp}] ⚠️  {line.strip()}")
                
                last_position = current_size
        
        time.sleep(0.5)  # Check every 500ms
        
    except KeyboardInterrupt:
        print("\nMonitoring stopped by user")
        break
    except Exception as e:
        print(f"Error: {e}")
        time.sleep(1)
