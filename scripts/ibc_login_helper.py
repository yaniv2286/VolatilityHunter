"""
IBC Login Helper - fills IBKR Gateway login dialog when IBC fails to.
Called by auto_tws_manager.py after Gateway window appears.
Waits for the IBKR Gateway window, clears fields, types credentials, clicks login.
"""
import os
import sys
import time
import logging
import traceback

# ── Setup ──────────────────────────────────────────────────────────────────
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger("ibc_login_helper")

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)

from dotenv import load_dotenv
load_dotenv(os.path.join(ROOT, '.env'))

IBKR_USER = os.getenv("IBKR_USER_NAME", "")
IBKR_PASS = os.getenv("IBKR_PASSWORD", "")
TRADING_MODE = os.getenv("IBKR_TRADING_MODE", "paper")  # paper or live

BUTTON_TEXT = "Paper Log In" if TRADING_MODE == "paper" else "Log In"
WAIT_SECS   = 60   # how long to wait for the window to appear


def find_gateway_window():
    """Return the IBKR Gateway window or None."""
    try:
        import pygetwindow as gw
        wins = gw.getWindowsWithTitle("IBKR Gateway")
        if not wins:
            wins = gw.getWindowsWithTitle("IB Gateway")
        return wins[0] if wins else None
    except Exception as e:
        logger.error(f"Window search failed: {e}")
        return None


def fill_and_login():
    import pyautogui
    import pygetwindow as gw

    pyautogui.FAILSAFE = False
    pyautogui.PAUSE = 0.15

    logger.info(f"Waiting up to {WAIT_SECS}s for IBKR Gateway window...")
    win = None
    for _ in range(WAIT_SECS):
        win = find_gateway_window()
        if win:
            break
        time.sleep(1)

    if not win:
        logger.error("IBKR Gateway window not found - exiting")
        sys.exit(1)

    logger.info(f"Found window: {win.title} at ({win.left},{win.top})")

    # Bring window to front
    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.5)

    # Click username field (center-left of the window, ~40% from top)
    cx = win.left + win.width // 2
    user_y = win.top + int(win.height * 0.42)
    pass_y  = win.top + int(win.height * 0.54)

    # Wait for IBC to finish its own attempts before we take over
    time.sleep(4)

    # Re-find window after wait
    win = find_gateway_window()
    if not win:
        logger.error("Window disappeared before we could fill credentials")
        sys.exit(1)

    try:
        win.activate()
    except Exception:
        pass
    time.sleep(0.5)

    cx     = win.left + win.width // 2
    user_y = win.top + int(win.height * 0.43)

    # Click username field directly, triple-click to select all, retype
    logger.info("Filling username field...")
    pyautogui.click(cx, user_y)
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('delete')
    time.sleep(0.2)
    logger.info(f"Typing username: {IBKR_USER}")
    pyautogui.typewrite(IBKR_USER, interval=0.07)
    time.sleep(0.4)

    # Tab to password field
    logger.info("Tabbing to password field...")
    pyautogui.press('tab')
    time.sleep(0.4)
    pyautogui.hotkey('ctrl', 'a')
    time.sleep(0.2)
    pyautogui.press('delete')
    time.sleep(0.2)
    logger.info("Typing password...")
    pyautogui.typewrite(IBKR_PASS, interval=0.07)
    time.sleep(0.4)

    # Press Enter to submit (or Tab to button then Enter)
    logger.info(f"Submitting login...")
    pyautogui.press('enter')
    time.sleep(0.5)

    logger.info("Login submitted.")
    return True


if __name__ == "__main__":
    if not IBKR_USER or not IBKR_PASS:
        logger.error("IBKR_USER_NAME / IBKR_PASSWORD not in .env")
        sys.exit(1)
    try:
        fill_and_login()
    except Exception as e:
        logger.error(f"Login helper failed: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)
