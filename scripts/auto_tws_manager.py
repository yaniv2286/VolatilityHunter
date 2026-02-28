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
API_WAIT_SECS = 120    # max seconds to wait for API after Gateway starts
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
        self.ibc_process  = None    # subprocess.Popen handle for IBC
        self.keep_alive_process = None

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
            f"IbLoginId={IBKR_USER}\n"
            f"IbPassword={IBKR_PASS}\n"
            f"IbDir={self.gateway_dir.replace(chr(92), chr(92)+chr(92))}\n"
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
            "LoginDialogDisplayTimeout=90\n"
        )
        try:
            with open(IBC_CONFIG, 'w', encoding='utf-8') as f:
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
                if removed:
                    jts.write_text('\n'.join(cleaned) + '\n', encoding='utf-8')
                    logger.info(f"Cleared SSO tokens from {jts}: {removed}")
                else:
                    logger.info(f"jts.ini already clean (no SSO tokens): {jts}")
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
            "live",
        ]
        log_file = LOG_DIR / "ibc_gateway.log"
        logger.info(f"Fallback classpath launch with Java 17...")
        try:
            with open(log_file, 'a', encoding='utf-8') as lf:
                self.ibc_process = subprocess.Popen(
                    cmd, stdout=lf, stderr=lf, cwd=str(self.gateway_dir)
                )
            logger.info(f"IBC classpath process started (PID {self.ibc_process.pid})")
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
        for i in range(API_WAIT_SECS):
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
                if not self.is_api_ready():
                    logger.warning("API port closed but process running - waiting 30s")
                    time.sleep(30)
                    if not self.is_api_ready():
                        logger.error("API still closed - restarting Gateway")
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

                # ── 4. All good ───────────────────────────────────────
                logger.info(f"All systems OK - next check in {CHECK_INTERVAL}s")
                time.sleep(CHECK_INTERVAL)

            except KeyboardInterrupt:
                logger.info("Stopped by user")
                break
            except Exception as e:
                logger.error(f"Manager loop error: {e}")
                logger.error(traceback.format_exc())
                time.sleep(60)


def main():
    manager = AutoTWSManager()
    manager.run()
    return 0


if __name__ == "__main__":
    exit(main())
