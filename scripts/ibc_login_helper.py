import os
import sys
import time
import pyautogui
import pygetwindow as gw
from dotenv import load_dotenv

def main():
    print("Ghost-Typist: Enhanced Auto-Login Recovery System")
    
    # Force load from .env, completely ignoring any garbage command-line arguments
    load_dotenv()
    
    username = os.getenv('IBKR_USER_NAME')
    password = os.getenv('IBKR_PASSWORD')
    
    if not username or not password:
        print("ERROR: Could not find IBKR_USER_NAME or IBKR_PASSWORD in .env file!")
        sys.exit(1)
        
    print(f"Loaded credentials. Username: {username}")
    
    # Configure PyAutoGUI for human-like behavior
    pyautogui.PAUSE = 0.1  # 0.1s interval between keystrokes
    pyautogui.FAILSAFE = True
    
    print("Waiting for IB Gateway window (up to 60s)...")
    
    try:
        # 1. FIND & FOCUS: Locate IBKR Gateway window (handles both "IBKR Gateway" and "ibgateway" titles)
        gateway_window = None
        for i in range(60):
            # Try multiple possible window titles
            for title_pattern in ["IBKR Gateway", "ibgateway", "IB Gateway"]:
                windows = gw.getWindowsWithTitle(title_pattern)
                if windows:
                    gateway_window = windows[0]
                    print(f"Found Gateway window: {gateway_window.title} after {i} seconds.")
                    break
            if gateway_window:
                break
            time.sleep(1)
            
        if not gateway_window:
            print("ERROR: Gateway window not found after 60 seconds!")
            print("Available windows:")
            for window in gw.getAllWindows():
                if "gateway" in window.title.lower() or "ibkr" in window.title.lower():
                    print(f"  - {window.title}")
            sys.exit(1)
        
        print("Waiting 4s for UI components to be fully interactable...")
        time.sleep(4)
        
        # Activate and maximize the window
        try:
            if not gateway_window.isActive:
                gateway_window.activate()
            if not gateway_window.isMaximized:
                gateway_window.maximize()
            time.sleep(1)  # Wait for window to stabilize
        except Exception as e:
            if "Error code from Windows: 0" in str(e):
                print("Ignored Windows Error Code 0 (window likely already active)")
            else:
                print(f"WARNING: Failed to fully activate/maximize window, but continuing: {e}")
        
        # NUCLEAR CLEAR PROTOCOL: Click window center to ensure proper focus
        # This eliminates pre-filled paths like 'D:\TWS' that cause field offsets
        print("NUCLEAR CLEAR: Clicking window center for absolute focus...")
        window_center_x = gateway_window.left + gateway_window.width // 2
        window_center_y = gateway_window.top + gateway_window.height // 2
        pyautogui.click(window_center_x, window_center_y)
        time.sleep(0.5)
        
        # 2. FOCUSED INJECTION: Nuclear Clear + Type Username
        print("FOCUSED INJECTION: Nuclear Clear Username field...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.press('backspace')
        time.sleep(0.2)
        
        # 3. Type username from environment
        print(f"Typing username {username}...")
        pyautogui.PAUSE = 0.1  # Set 0.1s interval for slow typing
        pyautogui.write(username)
        time.sleep(0.2)
        
        # 4. Move to Password field
        print("Moving to Password field...")
        pyautogui.press('tab')
        time.sleep(0.2)
        
        # 5. FOCUSED INJECTION: Nuclear Clear + Type Password
        print("FOCUSED INJECTION: Nuclear Clear Password field...")
        pyautogui.hotkey('ctrl', 'a')
        time.sleep(0.2)
        pyautogui.press('backspace')
        time.sleep(0.2)
        
        # 6. Type password
        print("Typing password...")
        pyautogui.write(password)
        time.sleep(0.2)
        
        # 7. Submit login
        print("Submitting login...")
        pyautogui.press('enter')
        
        print("Ghost-Typist: Credentials injected successfully. Mission complete.")
        
    except Exception as e:
        print(f"Ghost-Typist ERROR: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()