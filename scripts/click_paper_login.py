import time
import pyautogui
import pygetwindow as gw

print("Paper Login Button Clicker - Looking for 'Paper Log In' or 'Paper Trading' button...")

# Find the Gateway window
gateway_window = None
for title_pattern in ["IBKR Gateway", "ibgateway", "IB Gateway"]:
    windows = gw.getWindowsWithTitle(title_pattern)
    if windows:
        gateway_window = windows[0]
        print(f"Found Gateway window: {gateway_window.title}")
        break

if not gateway_window:
    print("ERROR: Gateway window not found!")
    exit(1)

# Restore the window if minimized
try:
    if gateway_window.isMinimized:
        print("Window is minimized - restoring...")
        gateway_window.restore()
        time.sleep(2)
    gateway_window.activate()
    time.sleep(1)
except Exception as e:
    print(f"Warning activating window: {e}")

# Get window position and size after restoration
x, y, width, height = gateway_window.left, gateway_window.top, gateway_window.width, gateway_window.height
print(f"Window position: ({x}, {y}), size: {width}x{height}")

# Click in the center-bottom area where "Paper Log In" button typically appears
# Based on typical IBKR Gateway layout, the button is usually in the lower-center area
button_x = x + (width // 2)
button_y = y + int(height * 0.75)  # 75% down from top

print(f"Clicking at ({button_x}, {button_y}) to activate Paper Trading...")
pyautogui.click(button_x, button_y)
time.sleep(1)

# Also try pressing Enter in case it's a focused button
print("Pressing Enter to confirm...")
pyautogui.press('enter')
time.sleep(1)

print("Paper Login button click attempted. Check if API starts now.")
