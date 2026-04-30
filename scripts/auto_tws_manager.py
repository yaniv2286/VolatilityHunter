#!/usr/bin/env python3
"""
AUTOMATED TWS MANAGER (IBC Edition)
=====================================
Fully headless, unattended IB Gateway auto-login using IBC.
- Reads IBKR credentials from .env (IBKR_LOGIN_ID / IBKR_PASSWORD)
- Launches IB Gateway via IBC (no human login needed)
- Monitors process health every 5 minutes
- Auto-restarts if Gateway crashes
- Starts keep-alive heartbeat after connection confirmed
- ASCII output only (Task Scheduler compatible)

Modes:
  - Watchdog mode (default): Runs indefinitely, monitoring Gateway health
  - One-shot mode (--one-shot): Launches Gateway, waits for API ready, then exits

First-time setup: python scripts/setup_ibc.py
"""

import os
import sys
import time
import socket
import logging
import subprocess
import traceback
import psutil
import argparse
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
        logging.FileHandler(str(LOG_DIR / "auto_tws_manager.log"), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger("auto_tws_manager")

# ── Config ─────────────────────────────────────────────────────────────────
IBKR_LOGIN_ID  = os.getenv("IBKR_LOGIN_ID", "")
IBKR_PASSWORD  = os.getenv("IBKR_PASSWORD",  "")
IBKR_TRADING_MODE = os.getenv("IBKR_TRADING_MODE", "paper")
TWS_PORT      = 7497
API_WAIT_SECS = 600    # max seconds to wait for API after Gateway starts (5 minutes)
CHECK_INTERVAL = 300   # health check every 5 minutes

IBC_DIR         = Path("C:\\IBC")
IBC_JAR         = IBC_DIR / "IBC.jar"
IBC_CONFIG      = IBC_DIR / "config.ini"
IBC_START_BAT   = IBC_DIR / "StartGateway.bat"

GATEWAY_PATHS = [
    r"D:\TWS\ibgateway",
    r"C:\Jts",
    r"C:\IBJts",
]

GATEWAY_PROCESS_NAMES = ['ibgateway.exe', 'tws.exe', 'javaw.exe']


class AutoTWSManager:
    def __init__(self):
        self.gateway_dir  = self._find_gateway()
        self.ibc_process = None
        self.keep_alive_process = None
        self._api_last_seen_up = None
        self._api_closed_since = None
        self.USER_GRACE_PERIOD = 300

    # ── Discovery ────────────────────────────────────────────────────────

    def _find_gateway(self):
        for p in GATEWAY_PATHS:
            if Path(p).exists():
                logger.info(f"IB Gateway found at: {p}")
                return p
        logger.warning("IB Gateway not found in common paths")
        return GATEWAY_PATHS[0]

    # ── JTS Configuration Guard ─────────────────────────────────────────

    def clean_jts_ini(self):
        """
        JTS Configuration Guard: Force-create/overwrite jts.ini with correct settings.
        
        Forces:
        - Logon.API=IB (not FIX)
        - LastUser=IBKR_LOGIN_ID (pre-fill username for IBC)
        - TradingMode=p (paper trading)
        
        This runs BEFORE Gateway launch to eliminate startup failures.
        """
        login_id = os.environ.get('IBKR_LOGIN_ID', 'yanivl228')
        jts_paths = [
            Path(r"C:\Jts\jts.ini"),
            Path(self.gateway_dir) / "jts.ini",
        ]
        
        for jts_path in jts_paths:
            try:
                logger.info(f"JTS Configuration Guard: Processing {jts_path}")
                
                # Force-create/overwrite the file with correct content
                config_content = f"""[Logon]
API=IB
LastUser={login_id}
TradingMode=p

[IBGateway]
ApiOnly=yes
ReadOnlyApi=no

[Global]
LogToConsole=no
"""
                
                # Ensure parent directory exists
                jts_path.parent.mkdir(parents=True, exist_ok=True)
                
                # Write the enforced configuration
                jts_path.write_text(config_content, encoding='utf-8')
                logger.info(f"JTS Configuration Guard: Enforced clean config in {jts_path}")
                
            except Exception as e:
                logger.warning(f"JTS Configuration Guard failed for {jts_path}: {e}")
                logger.error(traceback.format_exc())

    # ── Process checks ───────────────────────────────────────────────────

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

    def is_api_ready(self, timeout=5):
        """Check if TWS API is accepting connections on port 7497 ONLY."""
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            result = sock.connect_ex(('127.0.0.1', 7497))  # Hardcoded port enforcement
            sock.close()
            return result == 0
        except Exception:
            return False

    def ping_gateway_until_ready(self, max_wait_seconds=180):
        """
        Robust polling mechanism for Gateway API readiness.
        Attempts TCP socket connection to 127.0.0.1:7497 every 5 seconds for up to 3 minutes.
        Returns True on success, False on timeout.
        """
        logger.info(f"Pinging Gateway API on port {TWS_PORT} (max wait: {max_wait_seconds}s)")
        
        start_time = time.time()
        attempt = 0
        
        while time.time() - start_time < max_wait_seconds:
            attempt += 1
            
            if self.is_api_ready(timeout=2):
                elapsed = time.time() - start_time
                logger.info(f"Gateway Online - API ready after {elapsed:.1f}s (attempt {attempt})")
                return True
            
            # Log progress every 30 seconds
            if attempt % 6 == 0:  # Every 30 seconds (6 * 5s)
                elapsed = time.time() - start_time
                logger.info(f"Still waiting for Gateway... {elapsed:.1f}s elapsed (attempt {attempt})")
            
            time.sleep(5)  # Poll every 5 seconds
        
        # Timeout reached
        elapsed = time.time() - start_time
        logger.error(f"Gateway API timeout after {elapsed:.1f}s (max {max_wait_seconds}s)")
        logger.error(f"Final attempt: {attempt} tries made")
        return False

    def kill_gateway_process_tree(self):
        """
        Kill the entire Java process tree if Gateway times out.
        No silent failures - forceful termination.
        """
        logger.warning("Killing Gateway process tree due to timeout...")
        
        try:
            if self.ibc_process and self.ibc_process.poll() is None:
                # Kill the main IBC process
                self.ibc_process.terminate()
                try:
                    self.ibc_process.wait(timeout=10)
                    logger.info("IBC process terminated gracefully")
                except subprocess.TimeoutExpired:
                    self.ibc_process.kill()
                    logger.warning("IBC process killed forcefully")
            
            # Kill any remaining Java/Gateway processes
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if any(name.lower() in proc.info['name'].lower() for name in GATEWAY_PROCESS_NAMES):
                        logger.info(f"Killing residual process: {proc.info['name']} (PID {proc.info['pid']})")
                        proc.terminate()
                        try:
                            proc.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            proc.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue
            
            logger.info("Gateway process tree cleanup completed")
            
        except Exception as e:
            logger.error(f"Error during process cleanup: {e}")
            logger.error(traceback.format_exc())

    # ── IBC config management ────────────────────────────────────────────

    def ensure_ibc_config(self):
        """Generate IBC config.ini with credentials from .env."""
        if not IBKR_LOGIN_ID or not IBKR_PASSWORD:
            logger.error("IBKR_LOGIN_ID or IBKR_PASSWORD missing from .env")
            return False

        IBC_DIR.mkdir(parents=True, exist_ok=True)
        
        # Generate config.ini with credentials injected
        config_lines = [
            "# IBC config - auto-managed by auto_tws_manager.py",
            "[IBC]",
            f"IbLoginId={IBKR_LOGIN_ID}",
            f"IbPassword={IBKR_PASSWORD}",
            f"TradingMode={IBKR_TRADING_MODE}",
            f"IbDir={self.gateway_dir.replace(chr(92), '/')}",
            "StoreSettingsOnServer=no",
            "MinimizeMainWindow=yes",
            "ExistingSessionDetectedAction=primary",
            "AcceptIncomingConnectionAction=accept",
            "ShowAccountTradesWindow=no",
            "ShowAllTrades=no",
            "FIX=no",
            "IbAutoClosedown=no",
            "ClosedownAt=",
            "AllowBlindTrading=yes",
            "DismissPasswordExpiryWarning=yes",
            "DismissNSEComplianceNotice=yes",
            "AcceptBidAskLastSizeDisplayUpdateNotification=accept",
            "LogComponents=never",
            "LoginDialogDisplayTimeout=180",
            "MaxLoginAttempts=3",
            "ReloginIfConnectionLost=yes",
            "AutoReconnect=yes",
            "",
            "[LOGON]",
            f"IbLoginId={IBKR_LOGIN_ID}",
            f"IbPassword={IBKR_PASSWORD}",
            "ReadOnlyApi=yes",  # Disable automatic login
            "",
            "[IBGateway]",
            "ApiOnly=yes",
            "ReadOnlyApi=no",
            "OtherTrades=none",
            "MasterClientId=1",
            "ClientId=100",
            "AcceptIncomingConnectionAction=accept",
            "LocalServerPort=7497"
        ]
        
        try:
            with open(IBC_CONFIG, 'w', encoding='utf-8', newline='\n') as f:
                for line in config_lines:
                    f.write(line + '\n')
            logger.info(f"IBC config generated: {IBC_CONFIG}")
            return True
        except Exception as e:
            logger.error(f"Failed to write IBC config: {e}")
            logger.error(traceback.format_exc())
            return False

    def _ensure_clean_jts_ini(self):
        """
        Strip saved SSO session tokens from jts.ini before IBC launch.
        IB Gateway 10.37 with s3store=true + UserNameToDirectory skips the
        login dialog entirely via SSO auto-login. IBC then waits 60s for a
        dialog that never appears -> exit 1112.
        Fix: remove UserNameToDirectory and s3store so Gateway shows the
        real login dialog which IBC can intercept and fill.
        """
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
                removed = []
                for line in lines:
                    key = line.split('=')[0].strip().lower()
                    if key in ('usernametodirectory', 's3store', 'useremotesettings'):
                        removed.append(line)
                    else:
                        cleaned.append(line)
                # Force paper mode + username in jts.ini so IB Gateway
                # pre-fills the username field correctly. IBC then only
                # needs to fill the password (avoids field-clear bug in 10.37).
                # Rewrite jts.ini: ensure tradingMode=p and Username are
                # inside [Logon] section so IB Gateway pre-fills them.
                final = []
                in_logon = False
                mode_set = False
                user_set = False
                for line in cleaned:
                    stripped = line.strip()
                    if stripped.startswith('['):
                        # Leaving a section - inject missing keys before closing
                        if in_logon:
                            if not mode_set:
                                final.append('tradingMode=p')
                                mode_set = True
                            if not user_set:
                                final.append(f"Username={os.environ.get('IBKR_LOGIN_ID', 'yanivl228')}")
                                user_set = True
                        in_logon = stripped.lower() == '[logon]'
                        final.append(line)
                        continue
                    key = line.split('=')[0].strip().lower()
                    if in_logon and key == 'tradingmode':
                        final.append('tradingMode=p')
                        mode_set = True
                    elif in_logon and key == 'username':
                        final.append(f"Username={os.environ.get('IBKR_LOGIN_ID', 'yanivl228')}")
                        user_set = True
                    else:
                        final.append(line)
                # Handle keys missing at end of file
                if in_logon:
                    if not mode_set:
                        final.append('tradingMode=p')
                    if not user_set:
                        final.append(f"Username={os.environ.get('IBKR_LOGIN_ID', 'yanivl228')}")
                jts.write_text('\n'.join(final) + '\n', encoding='utf-8')
                logger.info(f"jts.ini updated: paper mode + username in [Logon] section in {jts}")
            except Exception as e:
                logger.warning(f"Could not clean jts.ini at {jts}: {e}")

    # ── Java discovery ───────────────────────────────────────────────────

    def _find_java17(self) -> str:
        """
        Return path to javaw.exe that is Java 17+.
        Checks Zulu JRE (downloaded by setup_ibc.py) first, then
        other known locations, then a broad glob fallback.
        Returns empty string if nothing >= Java 17 found.
        """
        import glob as _glob
        import re as _re
        import subprocess as _sp
        import os as _os

        userprofile = _os.environ.get('USERPROFILE', r'C:\Users\Public')
        zulu_home = Path(userprofile) / 'zulu-jre17'

        # i4j shared JRE cache - IB Gateway installer places its bundled
        # Zulu+JavaFX JRE here. This is the correct JRE for IB Gateway 10.37.
        i4j_base = Path(userprofile) / 'AppData' / 'Local' / 'Programs' / 'Common' / 'i4j_jres'
        i4j_hits = sorted(i4j_base.glob('**/javaw.exe'), reverse=True) if i4j_base.exists() else []

        candidates = (
            [str(p) for p in i4j_hits]                     # i4j bundled JRE (has JavaFX)
            + [str(zulu_home / 'bin' / 'javaw.exe')]        # Zulu 17 from setup_ibc.py
            + [str(Path(self.gateway_dir) / 'jre' / 'bin' / 'javaw.exe')]
            + [
                r'C:\Program Files\Zulu\zulu-17\bin\javaw.exe',
                r'C:\Program Files\Zulu\zulu-21\bin\javaw.exe',
                r'C:\Program Files\Eclipse Adoptium\jre-17\bin\javaw.exe',
                r'C:\Program Files\Microsoft\jdk-17\bin\javaw.exe',
            ]
        )
        hits = _glob.glob(r'C:\Program Files\**\javaw.exe', recursive=True)
        hits += _glob.glob(r'C:\Program Files (x86)\**\javaw.exe', recursive=True)
        candidates += hits

        for c in candidates:
            p = Path(c)
            if not p.is_file():
                continue
            try:
                out = _sp.check_output([str(p), '-version'],
                                       stderr=_sp.STDOUT, timeout=5).decode(errors='ignore')
                m = _re.search(r'version "(\d+)(?:\.(\d+))?', out)
                if m:
                    major = int(m.group(1))
                    if major == 1:
                        major = int(m.group(2) or 0)
                    if major >= 17:
                        logger.info(f"Found Java {major} at: {p}")
                        return str(p)
            except Exception:
                continue

        logger.error("No Java 17+ found. Run: python scripts/setup_ibc.py to download Zulu JRE 17.")
        return ''

    # ── Gateway launch ───────────────────────────────────────────────────

    def start_gateway_via_ibc(self):
        """
        Headless IBC Gateway launcher.
        No GUI automation, no pyautogui, no mouse movements.
        Launches as hidden/background subprocess with credential injection.
        """
        if not IBC_JAR.exists():
            logger.error(f"IBC not installed. Run: python scripts/setup_ibc.py")
            logger.error(f"IBC.jar expected at: {IBC_JAR}")
            return False

        if not self.ensure_ibc_config():
            logger.error("Failed to generate IBC config.ini")
            return False

        # ZOMBIE PROCESS EXECUTION: Kill existing Java processes first
        self._kill_zombie_java_processes()

        # JTS Configuration Guard: Run BEFORE Gateway launch
        self.clean_jts_ini()
        self._ensure_clean_jts_ini()

        # Find Java 17+
        java_exe = self._find_java17()
        if not java_exe:
            logger.error("Java 17+ not found - cannot launch IBC")
            return False

        # Launch IBC as hidden subprocess
        return self._launch_headless_ibc(java_exe)

    def _kill_zombie_java_processes(self):
        """
        Forcefully kill existing Java processes that might be blocking Port 7497.
        Suppress errors if none exist.
        """
        logger.info("Killing zombie Java processes...")
        
        try:
            # Kill javaw.exe processes
            subprocess.run(['taskkill', '/F', '/IM', 'javaw.exe', '/T'], 
                          capture_output=True, check=False)
            # Kill java.exe processes  
            subprocess.run(['taskkill', '/F', '/IM', 'java.exe', '/T'], 
                          capture_output=True, check=False)
            logger.info("Zombie Java process cleanup completed")
        except Exception as e:
            logger.warning(f"Java process cleanup warning: {e}")
            # Don't fail - continue with launch attempt

    def _launch_headless_ibc(self, java_exe: str) -> bool:
        """
        Launch IBC Gateway as hidden background subprocess.
        No window focusing, no GUI automation - completely headless.
        """
        gateway_jars = list((Path(self.gateway_dir) / "jars").glob("*.jar"))
        classpath = str(IBC_JAR) + ";" + ";".join(str(j) for j in gateway_jars)

        add_opens = [
            "--add-opens=java.desktop/javax.swing=ALL-UNNAMED",
            "--add-opens=java.desktop/javax.swing.plaf.basic=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.awt=ALL-UNNAMED",
            "--add-opens=java.desktop/sun.swing=ALL-UNNAMED",
            "--add-opens=java.base/java.lang=ALL-UNNAMED",
            "--add-opens=java.base/java.util=ALL-UNNAMED",
            "--add-opens=javafx.graphics/com.sun.javafx.application=ALL-UNNAMED",
            "--add-opens=javafx.controls/com.sun.javafx.scene.control.skin=ALL-UNNAMED",
            "--add-opens=javafx.fxml/com.sun.javafx.fxml=ALL-UNNAMED",
            "--add-opens=javafx.graphics/com.sun.glass.ui=ALL-UNNAMED",
        ]
        
        cmd = [
            java_exe, *add_opens,
            "-cp", classpath,
            "ibcalpha.ibc.IbcGateway",
            str(IBC_CONFIG),
            str(self.gateway_dir),
            IBKR_TRADING_MODE,
        ]
        
        log_file = LOG_DIR / "ibc_gateway.log"
        logger.info("Launching headless IBC Gateway...")
        
        try:
            # NORMAL WINDOW MODE: Fix GUI detachment issue
            startupinfo = None
            if sys.platform == "win32":
                startupinfo = subprocess.STARTUPINFO()
                startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                startupinfo.wShowWindow = 1  # SW_NORMAL - Show normally
            
            with open(log_file, 'a', encoding='utf-8') as lf:
                self.ibc_process = subprocess.Popen(
                    cmd, 
                    stdout=lf, 
                    stderr=lf, 
                    cwd=str(self.gateway_dir),
                    startupinfo=startupinfo,  # Hidden window
                    creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == "win32" else 0
                )
            
            logger.info(f"Headless IBC process started (PID {self.ibc_process.pid})")
            
            # Wait for Gateway window to appear before launching Ghost-Typist
            logger.info("Waiting for Gateway window to appear...")
            time.sleep(15)  # Give Gateway time to fully load
            
            # Launch Surgical Ghost-Typist for credential injection
            ghost_script = Path(__file__).parent / "surgical_ghost_typist.py"
            if ghost_script.exists():
                logger.info("Launching Surgical Ghost-Typist for login...")
                ghost_log = LOG_DIR / "surgical_ghost_typist.log"
                with open(ghost_log, 'a', encoding='utf-8') as gf:
                    ghost_process = subprocess.Popen(
                        [sys.executable, str(ghost_script)],
                        stdout=gf,
                        stderr=gf,
                        cwd=str(ROOT)
                    )
                
                # Wait for Ghost-Typist to complete (max 90 seconds)
                try:
                    ghost_process.wait(timeout=90)
                    if ghost_process.returncode == 0:
                        logger.info("✅ Surgical Ghost-Typist completed successfully")
                    else:
                        logger.error("❌ Surgical Ghost-Typist failed")
                        return False
                except subprocess.TimeoutExpired:
                    logger.error("❌ Surgical Ghost-Typist timed out")
                    ghost_process.kill()
                    return False
            else:
                logger.warning("Surgical Ghost-Typist script not found")
                return False
            
            return True
            
        except Exception as e:
            logger.error(f"Failed to launch IBC: {e}")
            logger.error(traceback.format_exc())
            return False

    def _remove_javaagent(self, vmoptions_path: Path):
        """Remove any IBC javaagent line from ibgateway.vmoptions (cleanup)."""
        if not vmoptions_path.exists():
            return
        try:
            lines = vmoptions_path.read_text(encoding='utf-8').splitlines()
            cleaned = [l for l in lines if not ('-javaagent:' in l and 'IBC' in l)]
            if len(cleaned) != len(lines):
                vmoptions_path.write_text('\n'.join(cleaned) + '\n', encoding='utf-8')
                logger.info(f"Removed IBC javaagent from {vmoptions_path.name}")
        except Exception as e:
            logger.warning(f"Could not clean {vmoptions_path.name}: {e}")

    def _launch_via_classpath(self, java_exe: str) -> bool:
        """
        Fallback: launch IBC directly via javaw classpath.
        Requires Java 17+ and --add-opens flags.
        """
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
        cmd = [
            java_exe, *add_opens,
            "-cp", classpath,
            "ibcalpha.ibc.IbcGateway",
            str(IBC_CONFIG),
            str(self.gateway_dir),
            "paper",
        ]
        log_file = LOG_DIR / "ibc_gateway.log"
        logger.info(f"Fallback classpath launch with Java 17...")
        try:
            with open(log_file, 'a', encoding='utf-8') as lf:
                self.ibc_process = subprocess.Popen(
                    cmd, stdout=lf, stderr=lf, cwd=str(self.gateway_dir)
                )
            logger.info(f"IBC classpath process started (PID {self.ibc_process.pid})")
            
            # Always spawn Ghost-Typist to handle login via GUI automation
            # Ghost-Typist exits gracefully if no Gateway window is found within 60s
            # Note: SESSIONNAME env var is NOT reliable for detecting Task Scheduler
            # context - it may be empty even when running in user's interactive session
            helper = Path(__file__).parent / "ibc_login_helper.py"
            if helper.exists():
                ghost_log = LOG_DIR / "ghost_typist.log"
                with open(ghost_log, 'a', encoding='utf-8') as gf:
                    subprocess.Popen([sys.executable, str(helper)],
                                     stdout=gf, stderr=gf)
                logger.info("Ghost-Typist spawned for Gateway login (IB API tab + credential injection)")
            
            return True
        except Exception as e:
            logger.error(f"Classpath launch failed: {e}")
            logger.error(traceback.format_exc())
            return self._fallback_bat_launch()

    def _fallback_bat_launch(self):
        """Fallback: launch via StartGateway.bat if Java classpath fails."""
        if not IBC_START_BAT.exists():
            logger.error(f"StartGateway.bat not found at {IBC_START_BAT}")
            return False
        logger.info(f"Fallback: launching via {IBC_START_BAT}")
        try:
            log_file = LOG_DIR / "ibc_gateway.log"
            with open(log_file, 'a', encoding='utf-8') as lf:
                self.ibc_process = subprocess.Popen(
                    ["cmd.exe", "/c", str(IBC_START_BAT)],
                    stdout=lf, stderr=lf
                )
            logger.info(f"IBC bat process started (PID {self.ibc_process.pid})")
            return True
        except Exception as e:
            logger.error(f"Fallback bat launch failed: {e}")
            logger.error(traceback.format_exc())
            return False

    def wait_for_api(self):
        """Wait up to API_WAIT_SECS for port 7497 to open using robust ping loop."""
        if not self.ping_gateway_until_ready(max_wait_seconds=API_WAIT_SECS):
            # Timeout - kill process tree and exit with code 1
            self.kill_gateway_process_tree()
            logger.error("Gateway startup FAILED - exiting with code 1")
            sys.exit(1)
        
        logger.info("Gateway API ready - continuing")
        return True

    # ── Keep-alive ───────────────────────────────────────────────────────

    def start_keep_alive(self):
        """Start tws_keep_alive.py as a background process."""
        script = ROOT / "scripts" / "tws_keep_alive.py"
        if not script.exists():
            logger.warning(f"tws_keep_alive.py not found at {script}")
            return False

        if self.keep_alive_process and self.keep_alive_process.poll() is None:
            logger.info("Keep-alive already running")
            return True

        try:
            log_file = LOG_DIR / "tws_keep_alive.log"
            with open(log_file, 'a', encoding='utf-8') as lf:
                self.keep_alive_process = subprocess.Popen(
                    [sys.executable, str(script)],
                    stdout=lf, stderr=lf
                )
            logger.info(f"Keep-alive started (PID {self.keep_alive_process.pid})")
            return True
        except Exception as e:
            logger.error(f"Failed to start keep-alive: {e}")
            logger.error(traceback.format_exc())
            return False

    def is_keep_alive_running(self):
        return self.keep_alive_process is not None and self.keep_alive_process.poll() is None

    # ── Main loop ────────────────────────────────────────────────────────

    def cleanup_processes(self):
        """Clean up all managed processes."""
        logger.info("Cleaning up managed processes...")
        if self.ibc_process:
            try:
                self.ibc_process.terminate()
                logger.info(f"Terminated Gateway process (PID {self.ibc_process.pid})")
                self.ibc_process = None
            except Exception:
                pass
        if self.keep_alive_process:
            try:
                self.keep_alive_process.terminate()
                logger.info(f"Terminated keep-alive process (PID {self.keep_alive_process.pid})")
                self.keep_alive_process = None
            except Exception:
                pass

    def run(self):
        logger.info("=" * 60)
        logger.info("AUTOMATED TWS MANAGER (IBC Edition)")
        logger.info("Fully headless IB Gateway management")
        logger.info(f"IBKR User : {os.environ.get('IBKR_LOGIN_ID', 'yanivl228')}")
        logger.info(f"Gateway   : {self.gateway_dir}")
        logger.info(f"IBC       : {IBC_DIR}")
        logger.info("=" * 60)

        login_id = os.environ.get('IBKR_LOGIN_ID', 'yanivl228')
        password = os.environ.get('IBKR_PASSWORD', '')
        if not login_id or not password:
            logger.error("IBKR_LOGIN_ID / IBKR_PASSWORD not in .env - cannot auto-login")
            sys.exit(1)

        while True:
            try:
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                logger.info(f"--- Health check at {now} ---")

                # ── 1. Gateway process check ───────────────────────────
                if not self.is_gateway_running():
                    logger.warning("IB Gateway not running - launching via IBC...")
                    if not self.start_gateway_via_ibc():
                        logger.error("Launch failed - retry in 5 minutes")
                        time.sleep(300)
                        continue

                    # Wait for API to come up after fresh launch
                    if not self.wait_for_api():
                        logger.error("API did not open - killing and retrying in 5 minutes")
                        if self.ibc_process:
                            try:
                                self.ibc_process.terminate()
                            except Exception:
                                pass
                        time.sleep(300)
                        continue

                # ── 2. API port check ──────────────────────────────────
                is_weekend = datetime.now().weekday() >= 5  # Sat=5, Sun=6
                
                # Watchdog: Check if we've been in this loop too long
                loop_start = time.time()
                max_loop_time = 3600  # 1 hour max per health check cycle
                
                def check_watchdog():
                    if time.time() - loop_start > max_loop_time:
                        logger.error("Watchdog: Health check loop stuck - forcing restart")
                        if self.ibc_process:
                            try:
                                self.ibc_process.terminate()
                                logger.info("Watchdog: Terminated stuck Gateway process")
                            except Exception:
                                pass
                        return True
                    return False
                
                if self.is_api_ready():
                    self._api_last_seen_up = time.time()
                    self._api_closed_since = None
                elif is_weekend:
                    logger.info("Weekend - API port not required (markets closed). Gateway process alive - OK")
                else:
                    now_ts = time.time()
                    if self._api_closed_since is None:
                        self._api_closed_since = now_ts
                        logger.warning("API port closed - may be user browsing IBKR portal. Grace period: 5 min")
                    elapsed = now_ts - self._api_closed_since
                    if elapsed < 300:
                        remaining = int(300 - elapsed)
                        logger.info(f"API closed for {int(elapsed)}s - waiting (grace period, {remaining}s left)")
                        time.sleep(CHECK_INTERVAL)
                        continue
                    else:
                        logger.error("API closed for >5 min - restarting Gateway")
                        self._api_closed_since = None
                        if self.ibc_process:
                            try:
                                self.ibc_process.terminate()
                            except Exception:
                                pass
                        time.sleep(10)
                        continue

                # ── 3. Keep-alive check ───────────────────────────────
                if not self.is_keep_alive_running():
                    logger.info("Starting keep-alive heartbeat...")
                    self.start_keep_alive()

                # ── 4. Watchdog check ───────────────────────────────
                if check_watchdog():
                    logger.info("Watchdog triggered - restarting loop...")
                    time.sleep(10)
                    continue

                # ── 5. All good ───────────────────────────────────────
                logger.info(f"All systems OK - next check in {CHECK_INTERVAL}s")
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Stopped by user")
                self.cleanup_processes()
                break
            except Exception as e:
                logger.error(f"Manager loop error: {e}")
                logger.error(traceback.format_exc())
                self.cleanup_processes()
                time.sleep(60)


def main():
    parser = argparse.ArgumentParser(description='Automated TWS Manager')
    parser.add_argument('--one-shot', action='store_true',
                        help='Launch Gateway, wait for API ready, then exit (for batch scripts)')
    args = parser.parse_args()
    
    manager = AutoTWSManager()
    
    if args.one_shot:
        # One-shot mode: Launch Gateway and exit after API is ready
        logger.info("Running in ONE-SHOT mode (launch and exit)")
        
        # Check if already running
        if manager.is_gateway_running() and manager.is_api_ready():
            logger.info("Gateway already running and API ready - exiting")
            return 0
        
        # Launch Gateway
        if not manager.is_gateway_running():
            logger.info("Launching headless Gateway via IBC...")
            if not manager.start_gateway_via_ibc():
                logger.error("Failed to launch Gateway")
                return 1
        
        # Wait for API using robust ping loop
        logger.info("Waiting for Gateway API readiness...")
        if not manager.ping_gateway_until_ready(max_wait_seconds=180):
            # Timeout - kill process tree and exit with code 1
            manager.kill_gateway_process_tree()
            logger.error("Gateway startup FAILED - exiting with code 1")
            return 1
        
        logger.info("Gateway API ready - ONE-SHOT mode complete")
        logger.info("Headless Gateway successfully launched and ready")
        return 0
    else:
        # Watchdog mode: Run indefinitely
        logger.info("Running in WATCHDOG mode (continuous monitoring)")
        manager.run()
        return 0


if __name__ == "__main__":
    exit(main())
