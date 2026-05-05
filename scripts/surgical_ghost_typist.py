#!/usr/bin/env python3
"""
SURGICAL GHOST-TYPIST
=====================
Enterprise-grade UI automation for IBKR Gateway login.
Deterministic, strict timeouts, no brittle coordinates.
"""

import os
import sys
import time
import socket
import logging
from pathlib import Path
from typing import Optional

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Imports ─────────────────────────────────────────────────────────────────
try:
    import pyautogui
    import pygetwindow as gw
except ImportError as e:
    print(f"ERROR: Missing required packages: {e}")
    print("Install with: pip install pyautogui pygetwindow")
    sys.exit(1)

# ── Configuration ───────────────────────────────────────────────────────
IBKR_LOGIN_ID = os.getenv("IBKR_LOGIN_ID", "")
IBKR_PASSWORD = os.getenv("IBKR_PASSWORD", "")

if not IBKR_LOGIN_ID or not IBKR_PASSWORD:
    print("ERROR: IBKR_LOGIN_ID or IBKR_PASSWORD missing from .env")
    sys.exit(1)

# Configure pyautogui
pyautogui.FAILSAFE = False
pyautogui.PAUSE = 0.1

# ── Logging ───────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("surgical_ghost_typist")

class SurgicalGhostTypist:
    """Deterministic IBKR Gateway login automation."""
    
    def __init__(self):
        self.window_titles = ["I B API", "IB Gateway", "IBKR Gateway", "Gateway", "IBKR", "TWS Gateway"]
        self.timeout_seconds = 60
        self.keystroke_delay = 0.1
        self.api_port = 7497
        self.api_wait_timeout = 120
        
    def find_gateway_window(self) -> Optional[gw.Win32Window]:
        """Find and activate the IB Gateway window."""
        logger.info(f"Searching for windows: {self.window_titles}")
        
        # Debug: List all available windows
        try:
            all_windows = gw.getAllWindows()
            logger.info(f"DEBUG: Found {len(all_windows)} total windows")
            for w in all_windows:  # Show ALL windows to find the right one
                if w.visible and w.title.strip():
                    logger.info(f"DEBUG: Window '{w.title}' (size: {w.size})")
        except Exception as e:
            logger.warning(f"DEBUG: Could not list windows: {e}")
        
        start_time = time.time()
        while time.time() - start_time < self.timeout_seconds:
            try:
                for title in self.window_titles:
                    windows = gw.getWindowsWithTitle(title)
                    if windows:
                        window = windows[0]
                        # Validate this is the right window (not a FIX/CTCI window)
                        if any(bad_word in window.title.lower() for bad_word in ['fix', 'ctci', 'fix ctc i']):
                            logger.warning(f"Skipping FIX/CTCI window: {window.title}")
                            continue
                        logger.info(f"Found correct window: {window.title} (size: {window.size})")
                        return window
            except Exception as e:
                logger.warning(f"Window search error: {e}")
            
            time.sleep(1)
        
        raise RuntimeError(f"Gateway window not found within {self.timeout_seconds}s. Tried: {self.window_titles}")
    
    def activate_window(self, window: gw.Win32Window) -> None:
        """Activate and bring window to front."""
        logger.info("Activating window...")
        
        try:
            if window.isMinimized:
                window.restore()
            
            window.activate()
            time.sleep(2)
            
            # Verify window is active
            if not window.isActive:
                logger.warning("Window not active after activation attempt")
                window.activate()
                time.sleep(1)
                
        except Exception as e:
            raise RuntimeError(f"Failed to activate window: {e}")
    
    def focus_click_username_field(self, window: gw.Win32Window) -> None:
        """Click in username field (55% down) to safely gain focus."""
        logger.info("Performing username field focus click...")
        
        try:
            # Target username field at 55% down from top
            click_x = window.left + (window.width // 2)
            click_y = window.top + int(window.height * 0.55)
            
            logger.info(f"Clicking username field at ({click_x}, {click_y})")
            pyautogui.click(click_x, click_y)
            time.sleep(0.5)
            
        except Exception as e:
            raise RuntimeError(f"Username field focus click failed: {e}")
    
    def nuclear_clear_field(self) -> None:
        """Obliterate current field content with Ctrl+A + Backspace."""
        logger.info("Executing nuclear clear...")
        
        try:
            # Select all
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(self.keystroke_delay)
            
            # Delete
            pyautogui.press('backspace')
            time.sleep(self.keystroke_delay)
            
            logger.info("Field cleared")
            
        except Exception as e:
            raise RuntimeError(f"Nuclear clear failed: {e}")
    
    def wait_for_api_ready(self) -> bool:
        """Wait for Gateway API to become available on port 7497."""
        logger.info(f"Waiting for Gateway API on port {self.api_port} (timeout: {self.api_wait_timeout}s)...")
        start_time = time.time()
        
        while time.time() - start_time < self.api_wait_timeout:
            try:
                with socket.create_connection(('127.0.0.1', self.api_port), timeout=2):
                    elapsed = time.time() - start_time
                    logger.info(f"✅ Gateway API ready on port {self.api_port} after {elapsed:.1f}s")
                    return True
            except (socket.timeout, ConnectionRefusedError, OSError):
                pass
            
            time.sleep(2)
        
        elapsed = time.time() - start_time
        logger.error(f"❌ Gateway API not ready after {elapsed:.1f}s")
        return False
    
        
    def execute_login(self) -> bool:
        """Execute the complete surgical login sequence."""
        logger.info("=" * 60)
        logger.info("SURGICAL GHOST-TYPIST - LOGIN SEQUENCE")
        logger.info("=" * 60)
        
        try:
            # Step 1: Find window
            window = self.find_gateway_window()
            
            # Step 2: Activate window
            self.activate_window(window)
            
            # Step 3: Username field focus click
            self.focus_click_username_field(window)
            
            # Step 4: Clear username field and inject username
            logger.info("Clearing username field...")
            pyautogui.hotkey('ctrl', 'a')  # Select all
            time.sleep(self.keystroke_delay)
            pyautogui.press('backspace')  # Clear
            time.sleep(self.keystroke_delay)
            
            logger.info(f"Typing username: {IBKR_LOGIN_ID[:3]}***")
            pyautogui.typewrite(IBKR_LOGIN_ID, interval=self.keystroke_delay)
            time.sleep(self.keystroke_delay)
            
            # Step 5: Clear password field and inject password
            logger.info("Moving to password field...")
            pyautogui.press('tab')
            time.sleep(self.keystroke_delay)
            
            logger.info("Clearing password field...")
            pyautogui.hotkey('ctrl', 'a')  # Select all
            time.sleep(self.keystroke_delay)
            pyautogui.press('backspace')  # Clear
            time.sleep(self.keystroke_delay)
            
            logger.info("Typing password...")
            pyautogui.typewrite(IBKR_PASSWORD, interval=self.keystroke_delay)
            time.sleep(self.keystroke_delay)
            
            # Step 6: Press Enter to login
            logger.info("Pressing Enter to login...")
            pyautogui.press('enter')
            
            # Wait for potential paper trading warning popup
            logger.info("Waiting for potential paper trading warning...")
            time.sleep(3)
            
            # Handle paper trading warning popup
            try:
                # Look for warning window with common titles
                warning_titles = ["Paper Trading", "Paper Trading Account", "Simulated Trading", "Warning"]
                warning_found = False
                
                for _ in range(10):  # Check for 10 seconds
                    for title in warning_titles:
                        windows = gw.getWindowsWithTitle(title)
                        if windows:
                            logger.info(f"Found paper trading warning: {title}")
                            warning_found = True
                            # Click "I Understand" or "Accept" button
                            pyautogui.press('enter')  # Usually the default button
                            time.sleep(1)
                            break
                    time.sleep(1)
                
                if warning_found:
                    logger.info("Paper trading warning handled")
                else:
                    logger.info("No paper trading warning detected")
                    
            except Exception as e:
                logger.warning(f"Warning popup handling failed: {e}")
            
            # CRITICAL: Wait for Gateway API to actually become available
            logger.info("Credentials submitted. Waiting for Gateway API to start...")
            
            if not self.wait_for_api_ready():
                logger.error("Gateway API never became available after login")
                logger.error("Possible causes: wrong credentials, 2FA required, IBKR server error, account locked")
                logger.error("=" * 60)
                return False
            
            # Verify Gateway window is still visible
            try:
                if window.isVisible:
                    logger.info("✅ Gateway window is still open")
                else:
                    logger.warning("⚠ Gateway window closed but API is running")
            except Exception as e:
                logger.warning(f"Could not verify Gateway window state: {e}")
            
            logger.info("=" * 60)
            logger.info("✅ SURGICAL LOGIN COMPLETED - API VERIFIED")
            logger.info("=" * 60)
            return True
            
        except Exception as e:
            logger.error(f"❌ SURGICAL LOGIN FAILED: {e}")
            logger.error("=" * 60)
            return False

def main():
    """Main execution function."""
    try:
        typist = SurgicalGhostTypist()
        success = typist.execute_login()
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        logger.info("Login interrupted by user")
        sys.exit(1)
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
