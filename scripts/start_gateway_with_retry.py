#!/usr/bin/env python3
"""
IB GATEWAY STARTUP WITH RETRY
==============================
Launch IB Gateway via IBC with 120s timeout and 3 retries.
One-shot execution (not infinite loop like auto_tws_manager.py).
Returns exit code 0 on success, 1 on failure.

Usage: python scripts/start_gateway_with_retry.py
"""

import os
import sys
import time
import socket
import logging
import subprocess
import traceback
import psutil
from datetime import datetime
from pathlib import Path

# ── Path setup ─────────────────────────────────────────────────────────────
ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / ".env")

# ── Logging (ASCII only) ───────────────────────────────────────────────────
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(str(LOG_DIR / "gateway_startup.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("start_gateway_with_retry")

# ── Config ─────────────────────────────────────────────────────────────────
IBKR_USER     = os.getenv("IBKR_USER_NAME", "")
IBKR_PASS     = os.getenv("IBKR_PASSWORD",  "")
TRADING_MODE  = os.getenv("TRADING_MODE", "paper")  # paper or live
TWS_PORT      = 7497
API_WAIT_SECS = 120    # max seconds to wait for API after Gateway starts
MAX_RETRIES   = 3      # number of startup attempts
RETRY_DELAY   = 10     # seconds between retries

IBC_DIR         = Path("C:\\IBC")
IBC_JAR         = IBC_DIR / "IBC.jar"
IBC_CONFIG = Path(r"C:\IBC\config_startgateway.ini")

GATEWAY_PATHS = [
    r"D:\TWS\ibgateway",
    r"C:\Jts",
    r"C:\IBJts",
]


class GatewayStarter:
    def __init__(self):
        self.gateway_dir = self._find_gateway()
        self.ibc_process = None

    def _find_gateway(self):
        for p in GATEWAY_PATHS:
            if Path(p).exists():
                logger.info(f"IB Gateway found at: {p}")
                return p
        logger.warning("IB Gateway not found in common paths - using default")
        return GATEWAY_PATHS[0]

    def is_gateway_running(self):
        """Check if IB Gateway java process is alive."""
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info.get('cmdline') or []).lower()
                if 'ibgateway' in name or 'ibgateway' in cmdline:
                    return True
                if name == 'javaw.exe' and ('ibgateway' in cmdline or 'ibcgateway' in cmdline):
                    return True
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue
        return False

    def is_api_ready(self):
        """Check if port 7497 accepts connections."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex(('127.0.0.1', TWS_PORT))
            s.close()
            return result == 0
        except Exception:
            return False

    def ensure_ibc_config(self):
        """Write/refresh IBC config.ini with current .env credentials."""
        if not IBKR_USER or not IBKR_PASS:
            logger.error("IBKR_USER_NAME or IBKR_PASSWORD missing from .env")
            return False
        
        # DEBUG: Log exact credentials being used (mask password)
        logger.info(f"DEBUG: Username from .env: '{IBKR_USER}'")
        logger.info(f"DEBUG: Password length: {len(IBKR_PASS)} chars")

        IBC_DIR.mkdir(parents=True, exist_ok=True)
        config = (
            "# IBC config - auto-managed by start_gateway_with_retry.py\n"
            "[IBC]\n"
            f"IbDir={self.gateway_dir.replace(chr(92), '/')}\n"
            "StoreSettingsOnServer=no\n"
            "ExistingSessionDetectedAction=primary\n"
            "AcceptIncomingConnectionAction=accept\n"
            "ShowAllTrades=no\n"
            "FIX=no\n"
            "IbAutoClosedown=no\n"
            "ClosedownAt=\n"
            "AllowBlindTrading=yes\n"
            "DismissPasswordExpiryWarning=yes\n"
            "DismissNSEComplianceNotice=yes\n"
            "AcceptBidAskLastSizeDisplayUpdateNotification=accept\n"
            "LogComponents=never\n"
            "LoginDialogDisplayTimeout=90\n"
            "MinimizeMainWindow=no\n"
            "TradingMode=paper\n"
            "\n[LOGON]\n"
            f"Username={IBKR_USER}\n"
            f"Password={IBKR_PASS}\n"
            "\n[IBGateway]\n"
            "ApiOnly=yes\n"
            "ReadOnlyApi=no\n"
            "OtherTrades=none\n"
            "MasterClientId=1\n"
            "ClientId=100\n"
            "AcceptIncomingConnectionAction=accept\n"
            "LocalServerPort=7497\n"
        )
        try:
            with open(IBC_CONFIG, 'w', encoding='utf-8', newline='\n') as f:
                f.write(config)
            logger.info(f"IBC config written: {IBC_CONFIG}")
            logger.info(f"DEBUG: Config contains Username={IBKR_USER}")
            logger.info(f"DEBUG: Config contains Password={'*' * len(IBKR_PASS)}")
            return True
        except Exception as e:
            logger.error(f"Failed to write IBC config: {e}")
            logger.error(traceback.format_exc())
            return False

    def _ensure_clean_jts_ini(self):
        """Strip saved SSO session tokens from jts.ini before IBC launch."""
        # Aggressive cleanup of lock files and temp directories
        lock_file = Path(self.gateway_dir) / "jts.ini.lock"
        if lock_file.exists():
            try:
                lock_file.unlink()
                logger.info(f"Deleted lock file: {lock_file}")
            except Exception as e:
                logger.warning(f"Failed to delete {lock_file}: {e}")
        
        # Clean tmp directory
        tmp_dir = Path(self.gateway_dir) / "tmp"
        if tmp_dir.exists():
            try:
                import shutil
                shutil.rmtree(tmp_dir)
                tmp_dir.mkdir(exist_ok=True)
                logger.info(f"Cleaned tmp directory: {tmp_dir}")
            except Exception as e:
                logger.warning(f"Failed to clean {tmp_dir}: {e}")
        
        jts_candidates = [
            Path(self.gateway_dir) / "jts.ini",
            Path(self.gateway_dir) / "TWSibgateway" / "jts.ini",
        ]
        for jts in jts_candidates:
            if not jts.exists():
                continue
            try:
                lines = jts.read_text(encoding='utf-8', errors='ignore').splitlines()
                cleaned = []
                for line in lines:
                    key = line.split('=')[0].strip().lower()
                    if key not in ('usernametodirectory', 's3store', 'useremotesettings'):
                        cleaned.append(line)
                
                # Force paper mode + username in [Logon] section
                final = []
                in_logon = False
                mode_set = False
                user_set = False
                bind_set = False
                s3store_set = False
                for line in cleaned:
                    stripped = line.strip()
                    if stripped.startswith('['):
                        if in_logon:
                            if not mode_set:
                                final.append(f'tradingMode={TRADING_MODE}')
                            if not user_set:
                                final.append(f'Username={IBKR_USER}')
                            if not bind_set:
                                final.append('BindToConsole=yes')
                            if not s3store_set:
                                final.append('S3Store=no')
                        in_logon = stripped.lower() == '[logon]'
                        mode_set = False
                        user_set = False
                        bind_set = False
                        s3store_set = False
                        final.append(line)
                    elif in_logon:
                        if stripped.lower().startswith('tradingmode='):
                            final.append(f'tradingMode={TRADING_MODE}')
                            mode_set = True
                        elif stripped.lower().startswith('username='):
                            final.append(f'Username={IBKR_USER}')
                            user_set = True
                        elif stripped.lower().startswith('bindtoconsole='):
                            final.append('BindToConsole=yes')
                            bind_set = True
                        elif stripped.lower().startswith('s3store='):
                            final.append('S3Store=no')
                            s3store_set = True
                        else:
                            final.append(line)
                    else:
                        final.append(line)
                
                # Add missing items at end of [Logon] section
                if in_logon:
                    if not mode_set:
                        final.append(f'# Force trading mode and clean session')
                        final.append(f'tradingMode={TRADING_MODE}')
                    if not user_set:
                        final.append(f'Username={IBKR_USER}')
                    if not bind_set:
                        final.append('BindToConsole=yes')
                    if not s3store_set:
                        final.append('S3Store=no')
                
                jts.write_text('\n'.join(final) + '\n', encoding='utf-8')
                logger.info(f"jts.ini cleaned: {jts}")
            except Exception as e:
                logger.warning(f"Failed to clean {jts}: {e}")

    def _find_java17(self):
        """Find Java 17+ executable."""
        import re
        import subprocess as _sp
        
        candidates = [
            Path(r"C:\Users\Yaniv\AppData\Local\Programs\Common\i4j_jres") / "**" / "java.exe",
            Path(r"C:\Program Files\Java") / "**" / "java.exe",
            Path(r"C:\Program Files\thinkorswim\jre\bin\java.exe"),
        ]
        
        for pattern in candidates:
            if isinstance(pattern, Path) and pattern.is_file():
                paths = [pattern]
            else:
                paths = list(Path(str(pattern).split('**')[0]).rglob('java.exe'))
            
            for p in paths:
                if not p.is_file():
                    continue
                try:
                    out = _sp.check_output([str(p), '-version'],
                                           stderr=_sp.STDOUT, timeout=5).decode(errors='ignore')
                    m = re.search(r'version "(\d+)(?:\.(\d+))?', out)
                    if m:
                        major = int(m.group(1))
                        if major == 1:
                            major = int(m.group(2) or 0)
                        if major >= 17:
                            logger.info(f"Found Java {major} at: {p}")
                            return str(p)
                except Exception:
                    continue
        
        logger.error("No Java 17+ found")
        return ''

    def launch_gateway_via_ibc(self):
        """Launch IB Gateway via native Java command."""
        if not self.ensure_ibc_config(): return False
        self._ensure_clean_jts_ini()
        java_exe = self._find_java17()
        
        gateway_jars = list((Path(self.gateway_dir) / "jars").glob("*.jar"))
        classpath = str(IBC_JAR) + ";" + ";".join(str(j) for j in gateway_jars)

        add_opens = [
            "--add-opens=java.desktop/javax.swing=ALL-UNNAMED",
            "--add-opens=java.desktop/javax.swing.plaf.basic=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.awt=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.swing=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
        ]
        
        # Use config file + trading mode as command-line argument
        cmd = [
            java_exe, *add_opens, "-cp", classpath,
            "ibcalpha.ibc.IbcGateway",
            str(IBC_CONFIG),
            str(self.gateway_dir),
            "paper"
        ]
        
        logger.info(f"Launching IB Gateway natively...")
        logger.info(f"DEBUG: Command: {' '.join(cmd)}")
        logger.info(f"DEBUG: Username from config: {IBKR_USER}")
        logger.info(f"DEBUG: Password length: {len(IBKR_PASS)} chars")
        try:
            # Let Java output stream directly to terminal for real-time visibility
            self.ibc_process = subprocess.Popen(
                cmd, cwd=str(self.gateway_dir)
            )
            logger.info(f"IBC process started (PID {self.ibc_process.pid})")
            logger.info(f"Watch the IB Gateway window - IBC should type credentials automatically...")
            return True
        except Exception as e:
            logger.error(f"Failed to launch IBC: {e}")
            return False

    def _try_manual_login(self):
        """Try manual credential injection using pyautogui directly."""
        try:
            import pyautogui
            import time
            from dotenv import load_dotenv
            
            logger.info("Attempting manual credential injection...")
            
            # Load credentials from .env
            load_dotenv()
            username = os.getenv('IBKR_USER_NAME')
            password = os.getenv('IBKR_PASSWORD')
            
            if not username or not password:
                logger.error("Missing credentials in .env")
                return
            
            logger.info(f"Credentials loaded - Username length: {len(username)}")
            
            # Wait for window to be ready
            time.sleep(3)
            
            # Clear and type username
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.press('backspace')
            time.sleep(0.2)
            pyautogui.write(username)
            time.sleep(0.5)
            
            # Move to password field
            pyautogui.press('tab')
            time.sleep(0.5)
            
            # Clear and type password
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.2)
            pyautogui.press('backspace')
            time.sleep(0.2)
            pyautogui.write(password)
            time.sleep(0.5)
            
            # Press Enter to login
            pyautogui.press('enter')
            logger.info("Manual credential injection completed")
                
        except ImportError:
            logger.warning("pyautogui not available - cannot do manual login")
        except Exception as e:
            logger.error(f"Manual login failed: {e}")

    def wait_for_api(self):
        """Wait up to API_WAIT_SECS for port 7497 to open."""
        logger.info(f"Waiting up to {API_WAIT_SECS}s for IB Gateway API on port {TWS_PORT}...")
        start_time = time.time()
        
        # Give UI more time to settle - wait 15 seconds before first check
        logger.info("  Giving UI 15 seconds to settle...")
        time.sleep(15)
        
        # Try manual credential injection if IBC hasn't done it
        self._try_manual_login()
        
        # Check API every 2 seconds for first 30 seconds (login phase)
        for i in range(15):  # 15 * 2 = 30 seconds
            if self.is_api_ready():
                elapsed = int(time.time() - start_time)
                logger.info(f"IB Gateway API ready after {elapsed}s")
                return True
            
            if i % 2 == 0:  # Every 4 seconds
                logger.info(f"  Checking API... ({i*2}s)")
            
            time.sleep(2)
        
        # After 30 seconds, check if Gateway process is still alive
        if self.ibc_process and self.ibc_process.poll() is not None:
            logger.error("Gateway process has terminated - checking exit code")
            logger.error(f"Process return code: {self.ibc_process.returncode}")
            return False
        
        # Continue checking for remaining time
        for i in range(30, API_WAIT_SECS):
            if self.is_api_ready():
                elapsed = int(time.time() - start_time)
                logger.info(f"IB Gateway API ready after {elapsed}s")
                return True
            
            if i > 0 and i % 15 == 0:
                logger.info(f"  Still waiting... ({i}s)")
            
            time.sleep(1)
        
        logger.error(f"IB Gateway API did not open after {API_WAIT_SECS}s")
        return False

    def kill_gateway_process(self):
        """Kill any running Gateway process."""
        logger.info("Killing Gateway process...")
        if self.ibc_process:
            try:
                self.ibc_process.terminate()
                self.ibc_process.wait(timeout=5)
                logger.info(f"Terminated IBC process (PID {self.ibc_process.pid})")
            except Exception as e:
                logger.warning(f"Failed to terminate IBC process: {e}")
                try:
                    self.ibc_process.kill()
                except Exception:
                    pass
            self.ibc_process = None
        
        # Kill any remaining Gateway processes
        for proc in psutil.process_iter(['name', 'cmdline']):
            try:
                name = proc.info['name'].lower()
                cmdline = ' '.join(proc.info.get('cmdline') or []).lower()
                if 'ibgateway' in cmdline or 'ibc' in cmdline:
                    proc.terminate()
                    logger.info(f"Terminated Gateway process (PID {proc.pid})")
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                continue

    def start_with_retry(self):
        """Main entry point: try to start Gateway with retries."""
        logger.info("=" * 60)
        logger.info("IB GATEWAY STARTUP WITH RETRY")
        logger.info(f"IBKR User : {IBKR_USER}")
        logger.info(f"Gateway   : {self.gateway_dir}")
        logger.info(f"Mode      : {TRADING_MODE}")
        logger.info(f"Max Retries: {MAX_RETRIES}")
        logger.info(f"Timeout   : {API_WAIT_SECS}s per attempt")
        logger.info("=" * 60)

        if not IBKR_USER or not IBKR_PASS:
            logger.error("IBKR_USER_NAME / IBKR_PASSWORD not in .env - cannot auto-login")
            return 1

        for attempt in range(1, MAX_RETRIES + 1):
            logger.info(f"")
            logger.info(f"--- Attempt {attempt}/{MAX_RETRIES} ---")
            
            # Check if Gateway already running
            if self.is_gateway_running():
                logger.info("Gateway process already running - checking API...")
                if self.is_api_ready():
                    logger.info("Gateway API already ready - success!")
                    return 0
                else:
                    logger.warning("Gateway running but API not ready - killing and restarting")
                    self.kill_gateway_process()
                    time.sleep(5)
            
            # Launch Gateway
            if not self.launch_gateway_via_ibc():
                logger.error(f"Attempt {attempt} failed - could not launch Gateway")
                if attempt < MAX_RETRIES:
                    logger.info(f"Waiting {RETRY_DELAY}s before retry...")
                    time.sleep(RETRY_DELAY)
                continue
            
            # Wait for API
            if self.wait_for_api():
                logger.info("")
                logger.info("=" * 60)
                logger.info("SUCCESS: IB Gateway started and API ready")
                logger.info("=" * 60)
                return 0
            else:
                logger.error(f"Attempt {attempt} failed - API not ready after {API_WAIT_SECS}s")
                self.kill_gateway_process()
                if attempt < MAX_RETRIES:
                    logger.info(f"Waiting {RETRY_DELAY}s before retry...")
                    time.sleep(RETRY_DELAY)
        
        logger.error("")
        logger.error("=" * 60)
        logger.error(f"FAILURE: All {MAX_RETRIES} attempts failed")
        logger.error("=" * 60)
        return 1


def main():
    starter = GatewayStarter()
    exit_code = starter.start_with_retry()
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
