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
    
    # Wait for the IB Gateway login window to open and settle
    print("Waiting for IB Gateway window...")
    time.sleep(8)  # Increased wait time for window stability
    
    try:
        # 1. FIND & FOCUS: Locate IBKR Gateway window
        print("Finding IBKR Gateway window...")
        gateway_windows = gw.getWindowsWithTitle("IBKR Gateway")
        
        if not gateway_windows:
            print("ERROR: IBKR Gateway window not found!")
            print("Available windows:")
            for window in gw.getAllWindows():
                if "gateway" in window.title.lower() or "ibkr" in window.title.lower():
                    print(f"  - {window.title}")
            sys.exit(1)
        
        gateway_window = gateway_windows[0]
        print(f"Found IBKR Gateway window: {gateway_window.title}")
        
        # Activate and maximize the window
        try:
            gateway_window.activate()
            gateway_window.maximize()
            time.sleep(1)  # Wait for window to stabilize
        except Exception as e:
            print(f"ERROR: Failed to activate/maximize window: {e}")
            sys.exit(1)
        
        # Window is already focused, no mouse click needed
        
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