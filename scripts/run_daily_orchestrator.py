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


def _start_gateway_with_retries(manifest: dict, attempts: int = 3) -> bool:
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
            timeout=300,
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


def main() -> int:
    manifest = {
        "date": datetime.now().strftime("%Y-%m-%d"),
        "started_at": _now(),
        "status": "RUNNING",
        "steps": {},
    }
    _write_manifest(manifest)

    try:
        if not _start_gateway_with_retries(manifest):
            manifest["status"] = "FAILED_GATEWAY"
            _write_manifest(manifest)
            return 1

        steps = [
            ("data_update", [sys.executable, "scripts/update_data.py"], 600),
            ("health_check", [sys.executable, "scripts/functional_health_check.py"], 180),
            ("trading_loop", [sys.executable, "scripts/daily_trading_loop.py"], 1800),
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
