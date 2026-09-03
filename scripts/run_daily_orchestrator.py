#!/usr/bin/env python3
"""
VolatilityHunter Daily Orchestrator
Canonical production entry point for one deterministic trading day.
"""

import json
import os
import socket
import subprocess
import sys
import time
import traceback
from datetime import datetime
from pathlib import Path

try:
    import pyautogui
except ImportError:
    pyautogui = None

ROOT = Path(os.path.abspath(os.path.dirname(os.path.dirname(__file__))))
DATA_DIR = ROOT / "data"
LOG_DIR = ROOT / "logs"
MANIFEST_PATH = DATA_DIR / f"run_manifest_{datetime.now().strftime('%Y-%m-%d')}.json"


def _now() -> str:
    return datetime.now().isoformat()


def _is_port_open(port: int = 7497) -> bool:
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    try:
        return sock.connect_ex(("127.0.0.1", port)) == 0
    finally:
        sock.close()


def _write_manifest(manifest: dict) -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    manifest["updated_at"] = _now()
    MANIFEST_PATH.write_text(json.dumps(manifest, indent=2), encoding="utf-8")


def _run_step(name: str, command: list[str], manifest: dict, timeout: int | None = None) -> int:
    print(f"[ORCH] START {name}: {' '.join(command)}", flush=True)
    started = time.time()
    result = subprocess.run(command, cwd=str(ROOT), timeout=timeout)
    elapsed = round(time.time() - started, 1)
    manifest.setdefault("steps", {})[name] = {
        "command": command,
        "exit_code": result.returncode,
        "elapsed_seconds": elapsed,
        "completed_at": _now(),
    }
    _write_manifest(manifest)
    print(f"[ORCH] END {name}: exit={result.returncode} elapsed={elapsed}s", flush=True)
    return result.returncode


def _start_gateway_with_retries(manifest: dict, attempts: int = 1) -> bool:
    if _is_port_open(7497):
        manifest["gateway"] = {"status": "already_online", "attempts": 0, "port": 7497}
        _write_manifest(manifest)
        return True

    for attempt in range(1, attempts + 1):
        print(f"[ORCH] Gateway attempt {attempt}/{attempts}", flush=True)
        code = _run_step(
            f"gateway_start_attempt_{attempt}",
            [sys.executable, "scripts/auto_tws_manager.py", "--one-shot"],
            manifest,
            timeout=600,
        )
        if code == 0 and _is_port_open(7497):
            manifest["gateway"] = {"status": "online", "attempts": attempt, "port": 7497}
            _write_manifest(manifest)
            return True

        _run_step(
            f"gateway_cleanup_attempt_{attempt}",
            [sys.executable, "scripts/stop_gateway.py"],
            manifest,
            timeout=90,
        )
        time.sleep(20)

    manifest["gateway"] = {"status": "failed", "attempts": attempts, "port": 7497}
    _write_manifest(manifest)
    return False


def _check_gui_environment() -> bool:
    """Verify GUI environment is available before Gateway launch.
    
    Detects headless/Session 0 by checking pyautogui.size().
    Returns False if environment is unsuitable for Ghost-Typist.
    """
    print("[ORCH] " + "="*76, flush=True)
    print("[ORCH] GUI ENVIRONMENT CHECK: Verifying interactive session...", flush=True)
    print("[ORCH] " + "="*76, flush=True)
    
    if pyautogui is None:
        print("[ORCH] ERROR: pyautogui not installed - cannot verify GUI environment", flush=True)
        return False
    
    try:
        screen_size = pyautogui.size()
        if screen_size[0] == 0 or screen_size[1] == 0:
            print("[ORCH] " + "="*76, flush=True)
            print("[ORCH] CRITICAL ERROR: HEADLESS ENVIRONMENT DETECTED", flush=True)
            print("[ORCH] " + "="*76, flush=True)
            print(f"[ORCH] Screen size: {screen_size[0]}x{screen_size[1]} (INVALID)", flush=True)
            print("[ORCH] ", flush=True)
            print("[ORCH] Possible causes:", flush=True)
            print("[ORCH]   1. Task Scheduler running in Session 0 (background mode)", flush=True)
            print("[ORCH]   2. User not logged into Windows desktop", flush=True)
            print("[ORCH]   3. Screen locked or display unavailable", flush=True)
            print("[ORCH]   4. Task Scheduler NOT configured for 'Run only when user is logged on'", flush=True)
            print("[ORCH] ", flush=True)
            print("[ORCH] REQUIRED ACTION:", flush=True)
            print("[ORCH]   - Open Task Scheduler", flush=True)
            print("[ORCH]   - Edit task 'VolatilityHunter_Daily_Live'", flush=True)
            print("[ORCH]   - Select 'Run only when user is logged on'", flush=True)
            print("[ORCH]   - Ensure user is logged in at scheduled time (17:06 IST)", flush=True)
            print("[ORCH] " + "="*76, flush=True)
            return False
        
        print(f"[ORCH] SUCCESS: GUI environment verified - {screen_size[0]}x{screen_size[1]}", flush=True)
        print("[ORCH] Interactive session confirmed - Ghost-Typist will work", flush=True)
        print("[ORCH] " + "="*76, flush=True)
        return True
        
    except Exception as e:
        print("[ORCH] " + "="*76, flush=True)
        print("[ORCH] CRITICAL ERROR: pyautogui.size() failed", flush=True)
        print("[ORCH] " + "="*76, flush=True)
        print(f"[ORCH] Error: {e}", flush=True)
        print("[ORCH] This indicates a headless or inaccessible GUI environment.", flush=True)
        print("[ORCH] Ghost-Typist authentication will FAIL in this environment.", flush=True)
        print("[ORCH] " + "="*76, flush=True)
        return False


def main() -> int:
    manifest = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "started_at": _now(),
        "status": "RUNNING",
        "steps": {},
    }
    _write_manifest(manifest)

    try:
        # CRITICAL: Check GUI environment BEFORE Gateway launch
        if not _check_gui_environment():
            manifest["status"] = "FAILED_GUI_ENVIRONMENT"
            manifest["error"] = "Headless/Session 0 detected - Ghost-Typist requires interactive session"
            _write_manifest(manifest)
            print("\n[ORCH] ABORTING: GUI environment check FAILED", flush=True)
            print("[ORCH] Exit Code: 1", flush=True)
            return 1
        
        if not _start_gateway_with_retries(manifest):
            manifest["status"] = "FAILED_GATEWAY"
            _write_manifest(manifest)
            return 1

        steps = [
            # data_update now refreshes EOD for the full universe + sector map; allow 15 min.
            ("data_update", [sys.executable, "scripts/update_data.py"], 1200),
            ("health_check", [sys.executable, "scripts/functional_health_check.py"], 180),
            ("trading_loop", [sys.executable, "scripts/daily_trading_loop.py"], 1800),
            ("live_reconciliation", [sys.executable, "scripts/live_reconciliation.py"], 120),
        ]
        for name, command, timeout in steps:
            code = _run_step(name, command, manifest, timeout=timeout)
            if code != 0:
                manifest["status"] = f"FAILED_{name.upper()}"
                _write_manifest(manifest)
                return code

        manifest["status"] = "SUCCESS"
        manifest["completed_at"] = _now()
        _write_manifest(manifest)
        return 0

    except Exception as exc:
        manifest["status"] = "FAILED_EXCEPTION"
        manifest["exception"] = str(exc)
        manifest["traceback"] = traceback.format_exc()
        _write_manifest(manifest)
        print(manifest["traceback"], flush=True)
        return 1
    finally:
        _run_step("gateway_final_cleanup", [sys.executable, "scripts/stop_gateway.py"], manifest, timeout=90)


if __name__ == "__main__":
    sys.exit(main())
