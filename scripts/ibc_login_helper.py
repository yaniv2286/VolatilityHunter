import os
import sys
import time
import pyautogui
import pygetwindow as gw
from dotenv import load_dotenv

# Disable fail-safe: automated system should not crash if mouse reaches corner
pyautogui.FAILSAFE = False


def clamp(val, lo, hi):
    """Clamp a value to [lo, hi] range."""
    return max(lo, min(val, hi))


def safe_click(x, y):
    """Click at (x,y) clamped within screen bounds."""
    screen_w, screen_h = pyautogui.size()
    cx = clamp(x, 5, screen_w - 5)
    cy = clamp(y, 5, screen_h - 5)
    if cx != x or cy != y:
        print(f"  CLAMPED click: ({x},{y}) -> ({cx},{cy})  screen={screen_w}x{screen_h}")
    pyautogui.click(cx, cy)


def find_gateway_window(timeout=60):
    """Locate IBKR Gateway window within timeout seconds."""
    for i in range(timeout):
        for title_pattern in ["IBKR Gateway", "ibgateway", "IB Gateway"]:
            windows = gw.getWindowsWithTitle(title_pattern)
            if windows:
                print(f"Found Gateway window: {windows[0].title} after {i} seconds.")
                return windows[0]
        time.sleep(1)
    return None


def ensure_window_ready(win):
    """Activate the window and bring it to the foreground.
    
    IMPORTANT: Do NOT maximize. The Gateway login form is a fixed-size dialog
    (~790x610). When maximized, the window stretches to 1920x1080 but the form
    stays centered — making all percentage-based coordinate calculations wrong.
    Coordinates like 75% width only work at the natural dialog size.
    """
    for attempt in range(3):
        try:
            win.activate()
            time.sleep(0.5)
        except Exception as e:
            if "Error code from Windows: 0" in str(e):
                print(f"  activate() attempt {attempt+1}: Ignored Error Code 0")
            else:
                print(f"  activate() attempt {attempt+1}: {e}")
        
        # Re-fetch window geometry
        try:
            win = gw.getWindowsWithTitle(win.title)[0]
        except Exception:
            pass
        
        if win.width > 0 and win.height > 0:
            print(f"  Window ready: {win.width}x{win.height} at ({win.left},{win.top})")
            return win
    
    print(f"  Using window as-is: {win.width}x{win.height} at ({win.left},{win.top})")
    return win


def inject_credentials(win, username, password):
    """Click IB API tab, enter username/password, and submit."""
    # NUCLEAR CLEAR PROTOCOL: Click window center for focus
    print("NUCLEAR CLEAR: Clicking window center for absolute focus...")
    center_x = win.left + win.width // 2
    center_y = win.top + win.height // 2
    safe_click(center_x, center_y)
    time.sleep(0.5)
    
    # Click "IB API" tab (right tab: ~75% from left, ~180px from top)
    print("Clicking 'IB API' tab on the right side...")
    ib_api_tab_x = win.left + int(win.width * 0.75)
    ib_api_tab_y = win.top + 180
    print(f"Clicking at coordinates: x={ib_api_tab_x}, y={ib_api_tab_y}")
    safe_click(ib_api_tab_x, ib_api_tab_y)
    time.sleep(1.0)
    
    # Double-click to ensure tab selected
    print("Clicking 'IB API' tab again to ensure it's selected...")
    safe_click(ib_api_tab_x, ib_api_tab_y)
    time.sleep(0.5)
    
    # Click username field area
    print("Clicking username field area in IB API tab...")
    username_field_x = win.left + int(win.width * 0.55)
    username_field_y = win.top + 300
    safe_click(username_field_x, username_field_y)
    time.sleep(0.5)
    
    # Nuclear Clear + Type Username
    print("FOCUSED INJECTION: Nuclear Clear Username field...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('backspace')
    time.sleep(0.2)
    
    print(f"Typing username {username}...")
    pyautogui.PAUSE = 0.1
    pyautogui.write(username)
    time.sleep(0.2)
    
    # Tab to Password field
    print("Moving to Password field...")
    pyautogui.press('tab')
    time.sleep(0.2)
    
    # Nuclear Clear + Type Password
    print("FOCUSED INJECTION: Nuclear Clear Password field...")
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('backspace')
    time.sleep(0.2)
    
    print("Typing password...")
    pyautogui.write(password)
    time.sleep(0.2)
    
    # Submit
    print("Submitting login...")
    pyautogui.press('enter')
    
    print("Ghost-Typist: Credentials injected successfully. Mission complete.")


def main():
    print("Ghost-Typist: Enhanced Auto-Login Recovery System")
    
    load_dotenv()
    
    username = os.getenv('IBKR_USER_NAME')
    password = os.getenv('IBKR_PASSWORD')
    
    if not username or not password:
        print("ERROR: Could not find IBKR_USER_NAME or IBKR_PASSWORD in .env file!")
        sys.exit(1)
        
    print(f"Loaded credentials. Username: {username}")
    print(f"Screen size: {pyautogui.size()}")
    
    pyautogui.PAUSE = 0.1
    
    print("Waiting for IB Gateway window (up to 60s)...")
    
    gateway_window = find_gateway_window(timeout=60)
    if not gateway_window:
        print("ERROR: Gateway window not found after 60 seconds!")
        for window in gw.getAllWindows():
            if "gateway" in window.title.lower() or "ibkr" in window.title.lower():
                print(f"  - {window.title}")
        sys.exit(1)
    
    print("Waiting 4s for UI components to be fully interactable...")
    time.sleep(4)
    
    # Ensure window is maximized and properly positioned
    gateway_window = ensure_window_ready(gateway_window)
    
    # Inject credentials with retry
    for attempt in range(2):
        try:
            inject_credentials(gateway_window, username, password)
            break
        except Exception as e:
            print(f"Ghost-Typist attempt {attempt+1} FAILED: {e}")
            if attempt == 0:
                print("Retrying in 5 seconds...")
                time.sleep(5)
                # Re-find and re-maximize window
                gateway_window = find_gateway_window(timeout=15)
                if gateway_window:
                    gateway_window = ensure_window_ready(gateway_window)
                else:
                    print("ERROR: Gateway window lost during retry!")
                    sys.exit(1)
            else:
                print("Ghost-Typist: All attempts exhausted.")
                sys.exit(1)


if __name__ == "__main__":
    main()