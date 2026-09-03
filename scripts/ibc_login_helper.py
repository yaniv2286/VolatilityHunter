import os
import sys
import time
import pyautogui
import pygetwindow as gw
from dotenv import load_dotenv
from pathlib import Path
from datetime import datetime
import ctypes

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
        print(f"  CLAMPED click: ({x},{y}) -> ({cx},{cy})  screen={screen_w}x{screen_h}", flush=True)
    pyautogui.click(cx, cy)


def find_gateway_window(timeout=30):
    """Locate IBKR Gateway window within timeout seconds.
    
    STRICT TIMEOUT: 30 seconds max. If window not found, abort with Exit Code 1.
    This prevents silent failures from headless/locked sessions.
    """
    print(f"[GUI SANITY CHECK] Searching for Gateway window (timeout: {timeout}s)...", flush=True)
    for i in range(timeout):
        for title_pattern in ["IBKR Gateway", "ibgateway", "IB Gateway"]:
            windows = gw.getWindowsWithTitle(title_pattern)
            if windows and windows[0].width > 400:
                print(f"[OK] [GUI SANITY CHECK] Found Gateway window: '{windows[0].title}' after {i}s", flush=True)
                return windows[0]
        time.sleep(1)
    
    # STRICT FAILURE: Window not found within timeout
    print("\n" + "="*80, flush=True)
    print("[FAIL] CRITICAL ERROR: IBKR Gateway window NOT FOUND within 30 seconds", flush=True)
    print("="*80, flush=True)
    print("Possible causes:", flush=True)
    print("  1. User not logged into Windows (Session 0 isolation)", flush=True)
    print("  2. Screen locked (GUI automation cannot access desktop)", flush=True)
    print("  3. Gateway failed to launch (check auto_tws_manager.log)", flush=True)
    print("  4. Running in headless environment (no display available)", flush=True)
    print("\nAvailable windows:", flush=True)
    for window in gw.getAllWindows():
        print(f"  - {window.title}", flush=True)
    print("="*80, flush=True)
    return None


def ensure_window_ready(win):
    """Restore the Gateway window if minimized. Does NOT require foreground focus.
    SendMessage-based injection works without focus so we skip foreground fights.
    """
    user32 = ctypes.windll.user32
    try:
        wins = gw.getWindowsWithTitle(win.title)
        if wins:
            win = wins[0]
        hwnd = win._hWnd
        if user32.IsIconic(hwnd):
            user32.ShowWindow(hwnd, 9)  # SW_RESTORE
            time.sleep(0.5)
        print(f"  Window ready: {win.width}x{win.height} at ({win.left},{win.top})", flush=True)
    except Exception as e:
        print(f"  [WARN] ensure_window_ready: {e}", flush=True)
    return win

def verify_jts_ini_config():
    """Verify jts.ini has correct Logon.API=IB and LastUser settings.
    
    This prevents Ghost-Typist from typing into a misconfigured Gateway.
    """
    print("[GUI SANITY CHECK] Verifying jts.ini configuration...", flush=True)
    
    jts_paths = [
        Path(r"C:\Jts\jts.ini"),
        Path(r"D:\TWS\ibgateway\jts.ini"),
    ]
    
    verified = False
    for jts_path in jts_paths:
        if not jts_path.exists():
            continue
        
        try:
            content = jts_path.read_text(encoding='utf-8')
            has_api_ib = 'API=IB' in content
            has_lastuser = 'LastUser=' in content and 'yanivl228' in content
            
            if has_api_ib and has_lastuser:
                print(f"[OK] [GUI SANITY CHECK] {jts_path} verified: API=IB, LastUser=yanivl228", flush=True)
                verified = True
            else:
                print(f"[WARN] [GUI SANITY CHECK] {jts_path} incomplete: API=IB={has_api_ib}, LastUser={has_lastuser}", flush=True)
        except Exception as e:
            print(f"[WARN] [GUI SANITY CHECK] Could not read {jts_path}: {e}", flush=True)
    
    if not verified:
        print("\n" + "="*80, flush=True)
        print("[FAIL] CRITICAL ERROR: jts.ini verification FAILED", flush=True)
        print("="*80, flush=True)
        print("Expected: Logon.API=IB and LastUser=yanivl228", flush=True)
        print("Action: Check auto_tws_manager.py clean_jts_ini() execution", flush=True)
        print("="*80, flush=True)
        return False
    
    return True


def check_gui_environment():
    """Verify GUI environment is available (not headless).
    
    Detects headless/locked sessions by checking pyautogui.size().
    """
    print("[GUI SANITY CHECK] Checking GUI environment...", flush=True)
    
    try:
        screen_size = pyautogui.size()
        if screen_size[0] == 0 or screen_size[1] == 0:
            print("\n" + "="*80, flush=True)
            print("[FAIL] CRITICAL ERROR: Headless environment detected", flush=True)
            print("="*80, flush=True)
            print(f"Screen size: {screen_size[0]}x{screen_size[1]} (invalid)", flush=True)
            print("Possible causes:", flush=True)
            print("  1. Running in Session 0 (Task Scheduler background)", flush=True)
            print("  2. User not logged into Windows", flush=True)
            print("  3. Screen locked or display unavailable", flush=True)
            print("="*80, flush=True)
            return False
        
        print(f"[OK] [GUI SANITY CHECK] GUI environment OK: {screen_size[0]}x{screen_size[1]}", flush=True)
        return True
        
    except Exception as e:
        print("\n" + "="*80, flush=True)
        print("[FAIL] CRITICAL ERROR: pyautogui.size() failed", flush=True)
        print("="*80, flush=True)
        print(f"Error: {e}", flush=True)
        print("This indicates a headless or inaccessible GUI environment.", flush=True)
        print("="*80, flush=True)
        return False


def _enum_child_hwnds(parent_hwnd):
    """Return list of all child HWNDs under parent_hwnd."""
    user32 = ctypes.windll.user32
    children = []
    EnumChildProc = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_void_p)
    def _cb(hwnd, _):
        children.append(hwnd)
        return True
    user32.EnumChildWindows(parent_hwnd, EnumChildProc(_cb), 0)
    return children


def _get_child_class(hwnd):
    """Return the window class name of hwnd."""
    buf = ctypes.create_unicode_buffer(256)
    ctypes.windll.user32.GetClassNameW(hwnd, buf, 256)
    return buf.value


def _get_child_text(hwnd):
    """Return the window text of hwnd via WM_GETTEXT."""
    WM_GETTEXTLENGTH = 0x000E
    WM_GETTEXT = 0x000D
    user32 = ctypes.windll.user32
    length = user32.SendMessageW(hwnd, WM_GETTEXTLENGTH, 0, 0)
    if length == 0:
        return ""
    buf = ctypes.create_unicode_buffer(length + 1)
    user32.SendMessageW(hwnd, WM_GETTEXT, length + 1, buf)
    return buf.value


def _sendmsg_set_text(hwnd, text):
    """Set text in a child HWND via WM_SETTEXT - no focus required."""
    WM_SETTEXT = 0x000C
    ctypes.windll.user32.SendMessageW(hwnd, WM_SETTEXT, 0, text)


def _postmsg_click(hwnd):
    """Simulate a mouse click on hwnd via WM_LBUTTONDOWN/UP - no focus required."""
    WM_LBUTTONDOWN = 0x0201
    WM_LBUTTONUP   = 0x0202
    MK_LBUTTON = 0x0001
    ctypes.windll.user32.PostMessageW(hwnd, WM_LBUTTONDOWN, MK_LBUTTON, 0x00050005)
    time.sleep(0.05)
    ctypes.windll.user32.PostMessageW(hwnd, WM_LBUTTONUP, 0, 0x00050005)


def _postmsg_key(hwnd, vk):
    """Post a keydown+keyup to hwnd - no focus required."""
    WM_KEYDOWN = 0x0100
    WM_KEYUP   = 0x0101
    ctypes.windll.user32.PostMessageW(hwnd, WM_KEYDOWN, vk, 0)
    time.sleep(0.05)
    ctypes.windll.user32.PostMessageW(hwnd, WM_KEYUP,   vk, 0)


def inject_credentials(win, username, password):
    """Inject credentials via SendMessage/PostMessage directly to child HWNDs.

    This approach bypasses Windows foreground lock entirely - it works even
    when Task Scheduler has no desktop focus. No pyautogui clicks needed.
    Strategy:
      1. Enumerate all child HWNDs of the Gateway top-level window.
      2. Find JTextField children (class 'SunAwtTextField' or 'SunAwtWindow' children).
      3. WM_SETTEXT to clear+set username, WM_SETTEXT for password.
      4. PostMessage WM_KEYDOWN VK_RETURN to submit.
    Fallback: if child field enumeration fails, use SendInput (low-level key injection)
    after a best-effort SetForegroundWindow.
    """
    VK_RETURN = 0x0D
    VK_CONTROL = 0x11
    VK_A = 0x41
    VK_DELETE = 0x2E
    user32 = ctypes.windll.user32

    hwnd = win._hWnd
    print(f"Gateway HWND: {hwnd}", flush=True)

    # Enumerate all child windows
    children = _enum_child_hwnds(hwnd)
    print(f"Found {len(children)} child HWNDs", flush=True)

    # Log all children for diagnostics
    for ch in children:
        cls = _get_child_class(ch)
        txt = _get_child_text(ch)
        print(f"  child {ch}: class={cls!r} text={txt!r}", flush=True)

    # Find text fields: Java Swing renders as 'SunAwtTextField' or inside panels
    # We look for any child whose class contains 'TextField' or is a known Swing class
    # and has editable text (short text or empty = likely input field)
    text_fields = []
    for ch in children:
        cls = _get_child_class(ch)
        if 'TextField' in cls or 'SunAwt' in cls:
            txt = _get_child_text(ch)
            # Accept empty or short text (input fields), skip long labels/buttons
            if len(txt) < 100:
                text_fields.append((ch, cls, txt))

    print(f"Candidate text fields: {len(text_fields)}", flush=True)
    for ch, cls, txt in text_fields:
        print(f"  field {ch}: class={cls!r} current_text={txt!r}", flush=True)

    if len(text_fields) >= 2:
        # First text field = username, second = password
        user_hwnd = text_fields[0][0]
        pass_hwnd = text_fields[1][0]

        print(f"Username field HWND: {user_hwnd}", flush=True)
        print(f"Password field HWND: {pass_hwnd}", flush=True)

        # Clear and set username via WM_SETTEXT
        print(f"Setting username via WM_SETTEXT...", flush=True)
        _postmsg_click(user_hwnd)
        time.sleep(0.1)
        _sendmsg_set_text(user_hwnd, username)
        time.sleep(0.2)
        verify = _get_child_text(user_hwnd)
        print(f"Username field after set: {verify!r}", flush=True)

        # Clear and set password via WM_SETTEXT
        print(f"Setting password via WM_SETTEXT...", flush=True)
        _postmsg_click(pass_hwnd)
        time.sleep(0.1)
        _sendmsg_set_text(pass_hwnd, password)
        time.sleep(0.2)

        # Submit: PostMessage Enter to the password field
        print("Submitting via VK_RETURN to password field...", flush=True)
        _postmsg_key(pass_hwnd, VK_RETURN)
        time.sleep(0.3)
        # Also send to top-level window in case password field doesn't handle it
        _postmsg_key(hwnd, VK_RETURN)

        print("Ghost-Typist: Credentials injected via SendMessage. Mission complete.", flush=True)

    else:
        # FALLBACK: SendInput low-level injection after best-effort foreground
        print(f"[WARN] Child field enumeration found only {len(text_fields)} fields.", flush=True)
        print("[WARN] Falling back to SendInput coordinate-based injection...", flush=True)

        # Best-effort foreground (may fail on scheduler but worth trying)
        try:
            user32.AllowSetForegroundWindow(-1)
            user32.SystemParametersInfoW(0x2001, 0, 0, 0)
            user32.SetForegroundWindow(hwnd)
            user32.BringWindowToTop(hwnd)
            time.sleep(0.8)
        except Exception as e:
            print(f"  [WARN] SetForegroundWindow: {e}", flush=True)

        center_x = win.left + win.width // 2
        center_y = win.top + win.height // 2
        ib_api_tab_x = win.left + int(win.width * 0.75)
        ib_api_tab_y = win.top + 180
        username_field_x = win.left + int(win.width * 0.55)
        username_field_y = win.top + 300

        safe_click(center_x, center_y)
        time.sleep(0.3)
        safe_click(ib_api_tab_x, ib_api_tab_y)
        time.sleep(0.8)
        safe_click(ib_api_tab_x, ib_api_tab_y)
        time.sleep(0.3)
        safe_click(username_field_x, username_field_y)
        time.sleep(0.3)
        pyautogui.click(username_field_x, username_field_y, clicks=3)
        time.sleep(0.2)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        time.sleep(0.2)
        pyautogui.write(username, interval=0.05)
        time.sleep(0.2)
        pyautogui.press('tab')
        time.sleep(0.3)
        pyautogui.hotkey('ctrl', 'a')
        pyautogui.press('delete')
        time.sleep(0.2)
        pyautogui.write(password, interval=0.05)
        time.sleep(0.2)
        pyautogui.press('enter')
        print("Ghost-Typist: Credentials injected via fallback SendInput. Mission complete.", flush=True)

    # Screenshot proof
    try:
        from pathlib import Path as _P
        _log = _P(__file__).parent.parent / "logs"
        _log.mkdir(exist_ok=True)
        from datetime import datetime as _dt
        _shot = str(_log / f"ghost_inject_{_dt.now().strftime('%Y%m%d_%H%M%S')}.png")
        pyautogui.screenshot(_shot)
        print(f"[OK] Screenshot saved: {_shot}", flush=True)
    except Exception as _e:
        print(f"[WARN] Screenshot failed: {_e}", flush=True)


def is_port_open(port=7497):
    """Check if port 7497 is already listening (IBC login succeeded)."""
    import socket
    try:
        with socket.create_connection(('127.0.0.1', port), timeout=2):
            return True
    except (ConnectionRefusedError, OSError):
        return False


def main():
    start_time = datetime.now()
    print("\n" + "="*80, flush=True)
    print("[GHOST-TYPIST] SURGICAL GUI AUTHENTICATION SYSTEM", flush=True)
    print("="*80, flush=True)
    print(f"Started: {start_time.strftime('%Y-%m-%d %H:%M:%S')}", flush=True)
    print("Mode: Primary Auto-Login (IBC [LOGON] disabled)", flush=True)
    print("="*80, flush=True)
    print("", flush=True)
    
    # SANITY CHECK 1: GUI Environment
    if not check_gui_environment():
        print("\n[FAIL] ABORT: GUI environment check FAILED", flush=True)
        print(f"Duration: {(datetime.now() - start_time).total_seconds():.1f}s", flush=True)
        print("Exit Code: 1", flush=True)
        print("="*80, flush=True)
        sys.exit(1)
    
    # SANITY CHECK 2: jts.ini Configuration
    if not verify_jts_ini_config():
        print("\n[FAIL] ABORT: jts.ini verification FAILED", flush=True)
        print(f"Duration: {(datetime.now() - start_time).total_seconds():.1f}s", flush=True)
        print("Exit Code: 1", flush=True)
        print("="*80, flush=True)
        sys.exit(1)
    
    load_dotenv()
    
    username = os.getenv('IBKR_USER_NAME')
    password = os.getenv('IBKR_PASSWORD')
    
    if not username or not password:
        print("\n" + "="*80, flush=True)
        print("[FAIL] CRITICAL ERROR: Credentials not found in .env", flush=True)
        print("="*80, flush=True)
        print("Missing: IBKR_USER_NAME or IBKR_PASSWORD", flush=True)
        print(f"Duration: {(datetime.now() - start_time).total_seconds():.1f}s", flush=True)
        print("Exit Code: 1", flush=True)
        print("="*80, flush=True)
        sys.exit(1)
        
    print(f"[OK] [GUI SANITY CHECK] Credentials loaded: {username}", flush=True)
    print("", flush=True)
    
    pyautogui.PAUSE = 0.1
    
    # Quick check: port might already be open from a previous session
    if is_port_open():
        print("Port 7497 already open - no login needed. Exiting.", flush=True)
        return
    
    # SANITY CHECK 3: Gateway Window Detection (30-second timeout)
    gateway_window = find_gateway_window(timeout=30)
    if not gateway_window:
        if is_port_open():
            print("\n[OK] SUCCESS: Port 7497 already open - login succeeded elsewhere", flush=True)
            duration = (datetime.now() - start_time).total_seconds()
            print(f"Duration: {duration:.1f}s", flush=True)
            print("Exit Code: 0", flush=True)
            print("="*80, flush=True)
            return
        
        print("\n[FAIL] ABORT: Gateway window not found within 30 seconds", flush=True)
        print(f"Duration: {(datetime.now() - start_time).total_seconds():.1f}s", flush=True)
        print("Exit Code: 1", flush=True)
        print("="*80, flush=True)
        sys.exit(1)
    
    # Check if port already open before touching window
    if is_port_open():
        print("Port 7497 already open - login succeeded. Done.", flush=True)
        return
    
    gateway_window = ensure_window_ready(gateway_window)
    
    # Inject credentials with retry
    for attempt in range(2):
        try:
            inject_credentials(gateway_window, username, password)
            break
        except Exception as e:
            print(f"Ghost-Typist attempt {attempt+1} FAILED: {e}", flush=True)
            if attempt == 0:
                print("Retrying in 5 seconds...", flush=True)
                time.sleep(5)
                gateway_window = find_gateway_window(timeout=15)
                if gateway_window:
                    gateway_window = ensure_window_ready(gateway_window)
                else:
                    if is_port_open():
                        print("Port 7497 open - login succeeded during retry. Done.", flush=True)
                        return
                    print("ERROR: Gateway window lost during retry!", flush=True)
                    sys.exit(1)
            else:
                print("\n" + "="*80, flush=True)
                print("[FAIL] CRITICAL ERROR: Ghost-Typist all attempts exhausted", flush=True)
                print("="*80, flush=True)
                duration = (datetime.now() - start_time).total_seconds()
                print(f"Duration: {duration:.1f}s", flush=True)
                print("Exit Code: 1", flush=True)
                print("="*80, flush=True)
                sys.exit(1)
    
    # SUCCESS: Credentials injected
    duration = (datetime.now() - start_time).total_seconds()
    print("\n" + "="*80, flush=True)
    print("[OK] SUCCESS: Ghost-Typist credentials injected", flush=True)
    print("="*80, flush=True)
    print(f"Duration: {duration:.1f}s", flush=True)
    print("Exit Code: 0", flush=True)
    print("="*80, flush=True)


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print("\n" + "="*80, flush=True)
        print("[FATAL] Unhandled exception in Ghost-Typist", flush=True)
        print("="*80, flush=True)
        print(f"Error: {e}", flush=True)
        import traceback
        traceback.print_exc()
        print("Exit Code: 1", flush=True)
        print("="*80, flush=True)
        sys.exit(1)