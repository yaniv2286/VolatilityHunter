"""
monitoring_state.py
===================
Read-only state accessors for the VolatilityHunter monitoring adapter.

This module ONLY reads local state files and strategy metadata.  It does not
connect to IBKR, place/cancel orders, or mutate any trading state.
"""

import json
import os
import re
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
DATA_DIR = ROOT / 'data'
LOG_DIR = ROOT / 'logs'


def _safe_load_json(path: Path, default: Any = None) -> Any:
    """Load JSON file safely, returning default on any error."""
    try:
        if not path.exists():
            return default
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return default


def _safe_tail(path: Path, lines: int = 200) -> List[str]:
    """Return the last N lines of a text file."""
    try:
        if not path.exists():
            return []
        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
            all_lines = f.readlines()
        return [line.rstrip('\n') for line in all_lines[-lines:]]
    except Exception:
        return []


def get_portfolio() -> Dict[str, Any]:
    """Read portfolio.json (live trading state)."""
    portfolio = _safe_load_json(DATA_DIR / 'portfolio.json', default={})
    if not isinstance(portfolio, dict):
        return {}
    return portfolio


def get_run_manifest() -> Dict[str, Any]:
    """Read today's run manifest, if present."""
    today = datetime.now(timezone.utc).strftime('%Y-%m-%d')
    path = DATA_DIR / f'run_manifest_{today}.json'
    manifest = _safe_load_json(path, default={})
    if not isinstance(manifest, dict):
        return {}
    return manifest


def get_strategy_info() -> Dict[str, Any]:
    """Return read-only strategy version and parameters."""
    try:
        from src.strategy_engine import DEFAULT_VERSION, get_params
        params = get_params(DEFAULT_VERSION)
        return {
            'default_version': DEFAULT_VERSION,
            'params': params,
        }
    except Exception as e:
        return {
            'default_version': 'unknown',
            'params': {},
            'error': str(e),
            'traceback': traceback.format_exc(),
        }


def get_recent_log_files(max_files: int = 5) -> List[Path]:
    """Return the most recently modified log files."""
    try:
        if not LOG_DIR.exists():
            return []
        files = [p for p in LOG_DIR.glob('*.log') if p.is_file()]
        files.sort(key=lambda p: p.stat().st_mtime, reverse=True)
        return files[:max_files]
    except Exception:
        return []


def get_latest_logs(lines_per_file: int = 200) -> Dict[str, List[str]]:
    """Read recent tail lines from the newest log files."""
    logs: Dict[str, List[str]] = {}
    for log_file in get_recent_log_files():
        logs[log_file.name] = _safe_tail(log_file, lines_per_file)
    return logs


# Patterns used to scrub secrets from log output.
_REDACTION_PATTERNS = [
    # Environment-style key=value
    (re.compile(
        r'(TIINGO_API_KEY|TIINGO_KEY|IBKR_PASSWORD|IBKR_LOGIN_ID|'
        r'EMAIL_PASSWORD|AGENT_SHARED_SECRET|IBEAM_ACCOUNT|IBEAM_PASSWORD)\s*=\s*\S+',
        re.IGNORECASE
    ), r'\1=***REDACTED***'),
    # JSON-style key: "value"
    (re.compile(
        r'((?:tiingo_api_key|tiingo_key|ibkr_password|ibkr_login_id|'
        r'email_password|agent_shared_secret|password|secret|token)\s*[=:]\s*)'
        r'["\'][^"\']+["\']',
        re.IGNORECASE
    ), r'\1"***REDACTED***"'),
    # Bearer/Authorization headers
    (re.compile(
        r'((?:Authorization|Bearer|X-Signature)\s*[:=]\s*)\S+',
        re.IGNORECASE
    ), r'\1***REDACTED***'),
]


def redact_secrets(text: str) -> str:
    """Sanitize a single log line by redacting known secret patterns."""
    if not isinstance(text, str):
        text = str(text)
    for pattern, repl in _REDACTION_PATTERNS:
        text = pattern.sub(repl, text)
    return text


def sanitize_logs(logs: Dict[str, List[str]], max_lines: int = 200) -> Dict[str, List[str]]:
    """Sanitize log dictionaries, keeping only the most recent lines."""
    sanitized: Dict[str, List[str]] = {}
    for name, lines in logs.items():
        sanitized[name] = [redact_secrets(line) for line in lines[-max_lines:]]
    return sanitized
