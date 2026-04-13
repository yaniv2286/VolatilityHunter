#!/usr/bin/env python3
"""
AUTOMATED TWS MANAGER (IBC Edition)
=====================================
Fully headless, unattended IB Gateway auto-login using IBC.
- Reads IBKR credentials from .env (IBKR_USER_NAME / IBKR_PASSWORD)
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
IBKR_USER     = os.getenv("IBKR_USER_NAME", "")
IBKR_PASS     = os.getenv("IBKR_PASSWORD",  "")
TWS_PORT      = 7497
API_WAIT_SECS = 300    # max seconds to wait for API after Gateway starts
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

    def is_api_ready(self):
        """Check if port 7497 accepts connections."""
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            result = s.connect_ex(('127.0.0.1', TWS_PORT))
            s.close()
            return result == 0
        except Exception:
            return False

    # ── IBC config management ────────────────────────────────────────────

    def ensure_ibc_config(self):
        """Write/refresh IBC config.ini with current .env credentials."""
        if not IBKR_USER or not IBKR_PASS:
            logger.error("IBKR_USER_NAME or IBKR_PASSWORD missing from .env")
            return False

        IBC_DIR.mkdir(parents=True, exist_ok=True)
        # NOTE: TradingMode is NOT a config.ini key in IBC 3.18+
        # It is passed as the 3rd CLI argument to IbcGateway
        config = (
            "# IBC config - auto-managed by auto_tws_manager.py\n"
            "[IBC]\n"
            f"IbDir={self.gateway_dir.replace(chr(92), '/')}\n"
            "StoreSettingsOnServer=no\n"
            "MinimizeMainWindow=yes\n"
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
            "LoginDialogDisplayTimeout=180\n"
            "TradingMode=paper\n"
        )
        # Add LOGON section with credentials
        config += (
            "\n[LOGON]\n"
            f"Username={IBKR_USER}\n"
            f"Password={IBKR_PASS}\n"
        )
        # Add IBGateway section with API configuration
        config += (
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
                                final.append(f'Username={IBKR_USER}')
                                user_set = True
                        in_logon = stripped.lower() == '[logon]'
                        final.append(line)
                        continue
                    key = line.split('=')[0].strip().lower()
                    if in_logon and key == 'tradingmode':
                        final.append('tradingMode=p')
                        mode_set = True
                    elif in_logon and key == 'username':
                        final.append(f'Username={IBKR_USER}')
                        user_set = True
                    else:
                        final.append(line)
                # Handle keys missing at end of file
                if in_logon:
                    if not mode_set:
                        final.append('tradingMode=p')
                    if not user_set:
                        final.append(f'Username={IBKR_USER}')
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
        Launch IB Gateway via IBC for fully headless auto-login.
        IBC handles the login dialog automatically using credentials from config.ini.
        """
        if not IBC_JAR.exists():
            logger.error(f"IBC not installed. Run: python scripts/setup_ibc.py")
            logger.error(f"IBC.jar expected at: {IBC_JAR}")
            return False

        if not self.ensure_ibc_config():
            return False

        self._ensure_clean_jts_ini()

        # IBC works by intercepting ibgateway.exe's Swing login dialog.
        # We must launch ibgateway.exe (the native install4j launcher) with
        # IBC injected via -javaagent so IBC can hook the login window.
        # Calling javaw directly bypasses the display context setup that
        # install4j performs, causing exit 1112 (login dialog never appeared).

        java_exe = self._find_java17()
        if not java_exe:
            logger.error("Java 17+ not found - trying bat fallback")
            return self._fallback_bat_launch()

        # Use classpath launch with the i4j-cached JRE (has JavaFX).
        # Do NOT use ibgateway.exe directly - it ignores our vmoptions
        # javaagent and picks its own JRE, causing IBC to miss the dialog.
        # Ensure the javaagent line is removed from vmoptions (cleanup).
        vmoptions_path = Path(self.gateway_dir) / "ibgateway.vmoptions"
        self._remove_javaagent(vmoptions_path)
        return self._launch_via_classpath(java_exe)

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
            # Spawn Ghost-Typist to handle login via GUI automation
            # IBC will launch Gateway but NOT handle login
            helper = Path(__file__).parent / "ibc_login_helper.py"
            if helper.exists():
                ghost_log = LOG_DIR / "ghost_typist.log"
                with open(ghost_log, 'a', encoding='utf-8') as gf:
                    subprocess.Popen([sys.executable, str(helper)],
                                     stdout=gf, stderr=gf)
                logger.info("Ghost-Typist spawned (will handle login via GUI automation)")
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
        """Wait up to API_WAIT_SECS for port 7497 to open."""
        logger.info(f"Waiting up to {API_WAIT_SECS}s for IB Gateway API on port {TWS_PORT}...")
        start_time = time.time()
        for i in range(API_WAIT_SECS):
            # Check if we've been waiting too long and process is stuck
            if time.time() - start_time > API_WAIT_SECS - 60:  # Give 60s buffer
                logger.error(f"Gateway process stuck - forcing restart")
                if self.ibc_process:
                    try:
                        self.ibc_process.terminate()
                        logger.info("Terminated stuck Gateway process")
                    except Exception:
                        pass
                return False
                
            if self.is_api_ready():
                logger.info(f"IB Gateway API ready after {i}s")
                return True
            if i % 15 == 0 and i > 0:
                logger.info(f"  Still waiting... ({i}s)")
            time.sleep(1)
        logger.error(f"IB Gateway API did not open after {API_WAIT_SECS}s")
        return False

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
        logger.info(f"IBKR User : {IBKR_USER}")
        logger.info(f"Gateway   : {self.gateway_dir}")
        logger.info(f"IBC       : {IBC_DIR}")
        logger.info("=" * 60)

        if not IBKR_USER or not IBKR_PASS:
            logger.error("IBKR_USER_NAME / IBKR_PASSWORD not in .env - cannot auto-login")
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
            logger.info("Launching Gateway via IBC...")
            if not manager.start_gateway_via_ibc():
                logger.error("Failed to launch Gateway")
                return 1
        
        # Wait for API
        logger.info("Waiting for API to be ready...")
        if not manager.wait_for_api():
            logger.error("API did not become ready in time")
            return 1
        
        logger.info("Gateway API ready - ONE-SHOT mode complete")
        return 0
    else:
        # Watchdog mode: Run indefinitely
        logger.info("Running in WATCHDOG mode (continuous monitoring)")
        manager.run()
        return 0


if __name__ == "__main__":
    exit(main())
