#!/usr/bin/env python3
"""
verify_control_api.py
=====================
Standalone validation script for the Family Agent Platform monitoring adapter.

Actions:
  1. Start the read-only FastAPI adapter on a test port.
  2. Verify HMAC authentication (valid, invalid, expired).
  3. Verify every required monitoring endpoint returns the generic envelope.
  4. Verify no mutation methods (POST/PUT/DELETE) are accepted.
  5. Stop the server and report Exit Code 0 only on full success.

Per .windsurfrules Rule 4.1, this script must return Exit Code 0 before the
architectural change can be considered complete.
"""

import hashlib
import hmac
import os
import sys
import time
import traceback
from pathlib import Path

import requests
from dotenv import load_dotenv

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
LOG_DIR = ROOT / 'logs'
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

AGENT_ID = os.getenv('AGENT_ID', 'volatilityhunter')
AGENT_SHARED_SECRET = os.getenv('AGENT_SHARED_SECRET', '')
PORT = int(os.getenv('VERIFY_CONTROL_API_PORT') or '18080')
BASE_URL = f'http://127.0.0.1:{PORT}'


def _print_header():
    print("=" * 70)
    print("VOLATILITYHUNTER MONITORING ADAPTER VERIFICATION")
    print("=" * 70)


def _sign_request(method: str, path: str, timestamp: int = None, body: bytes = b'') -> dict:
    """Build HMAC-SHA256 authentication headers matching adapter expectations."""
    if timestamp is None:
        timestamp = int(time.time())
    body_hash = hashlib.sha256(body).hexdigest() if body else ''
    payload = f'{timestamp}|{method.upper()}|{path}|{body_hash}'
    signature = hmac.new(
        AGENT_SHARED_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()
    return {
        'X-Agent-ID': AGENT_ID,
        'X-Timestamp': str(timestamp),
        'X-Signature': signature,
    }


def _start_server():
    """Launch uvicorn in a subprocess and wait for readiness."""
    import subprocess

    env = os.environ.copy()
    env['MONITORING_PORT'] = str(PORT)
    env['MONITORING_HOST'] = '127.0.0.1'

    cmd = [
        sys.executable, '-m', 'uvicorn',
        'src.monitoring_adapter:app',
        '--host', '127.0.0.1',
        '--port', str(PORT),
    ]

    print(f'[START] Launching monitoring adapter: {" ".join(cmd)}')
    # Redirect uvicorn console output to the adapter's own log file so the
    # subprocess stdout/stderr pipes do not fill up and deadlock the server.
    log_path = LOG_DIR / 'verify_control_api_server.log'
    log_path.parent.mkdir(parents=True, exist_ok=True)
    log_file = open(log_path, 'a', encoding='utf-8')
    proc = subprocess.Popen(
        cmd,
        cwd=str(ROOT),
        env=env,
        stdout=log_file,
        stderr=subprocess.STDOUT,
    )

    # Wait for /docs to become reachable (unauthenticated health probe).
    # The adapter pre-loads strategy_engine on startup, which can take 20-30s.
    ready = False
    for attempt in range(120):
        try:
            requests.get(f'{BASE_URL}/docs', timeout=1)
            ready = True
            break
        except requests.exceptions.ConnectionError:
            time.sleep(0.5)

    if not ready:
        proc.terminate()
        try:
            proc.wait(timeout=5)
        except Exception:
            proc.kill()
        try:
            log_file.close()
        except Exception:
            pass
        raise RuntimeError('Server did not become ready within 60 seconds')

    print('[START] Server ready')
    return proc, log_file


def _stop_server(proc, log_file=None):
    """Gracefully terminate the uvicorn subprocess."""
    print('[STOP] Terminating monitoring adapter...')
    proc.terminate()
    try:
        proc.wait(timeout=5)
    except Exception:
        proc.kill()
        proc.wait(timeout=5)
    if log_file is not None:
        try:
            log_file.close()
        except Exception:
            pass
    print('[STOP] Server stopped')


def _assert_response(path: str, expected_status: int, response) -> dict:
    """Assert status and return parsed JSON."""
    if response.status_code != expected_status:
        raise AssertionError(
            f'{path}: expected HTTP {expected_status}, got {response.status_code}: {response.text[:200]}'
        )
    try:
        return response.json()
    except Exception as exc:
        raise AssertionError(f'{path}: response is not valid JSON: {exc}') from exc


def main() -> int:
    _print_header()

    if not AGENT_SHARED_SECRET:
        print('[FAIL] AGENT_SHARED_SECRET is not set in .env')
        return 1

    proc = None
    log_file = None
    passed = 0
    failed = 0

    try:
        proc, log_file = _start_server()

        # 1. Capabilities endpoint + envelope validation.
        path = '/api/v1/capabilities'
        resp = requests.get(
            f'{BASE_URL}{path}',
            headers=_sign_request('GET', path),
            timeout=10,
        )
        data = _assert_response(path, 200, resp)
        if data.get('agent_id') != AGENT_ID:
            raise AssertionError(f'{path}: unexpected agent_id {data.get("agent_id")}')
        if 'data' not in data:
            raise AssertionError(f'{path}: envelope missing "data" key')
        if data['data'].get('read_only') is not True:
            raise AssertionError(f'{path}: read_only flag missing or False')
        print(f'[PASS] {path}')
        passed += 1

        # 2. All remaining read-only monitoring endpoints.
        endpoints = [
            '/api/v1/health',
            '/api/v1/status',
            '/api/v1/portfolio/totals',
            '/api/v1/positions',
            '/api/v1/orders',
            '/api/v1/performance',
            '/api/v1/signals',
            '/api/v1/risk',
            '/api/v1/alerts',
            '/api/v1/logs',
        ]
        for ep in endpoints:
            resp = requests.get(
                f'{BASE_URL}{ep}',
                headers=_sign_request('GET', ep),
                timeout=10,
            )
            data = _assert_response(ep, 200, resp)
            if data.get('error') is not None:
                raise AssertionError(f'{ep}: envelope error: {data.get("error")}')
            if 'data' not in data:
                raise AssertionError(f'{ep}: envelope missing "data" key')
            print(f'[PASS] {ep}')
            passed += 1

        # 3. Invalid signature must be rejected.
        path = '/api/v1/health'
        headers = _sign_request('GET', path)
        headers['X-Signature'] = 'invalidsignature'
        resp = requests.get(
            f'{BASE_URL}{path}',
            headers=headers,
            timeout=10,
        )
        if resp.status_code != 401:
            raise AssertionError(
                f'{path}: invalid signature expected 401, got {resp.status_code}'
            )
        print('[PASS] Invalid signature rejected (401)')
        passed += 1

        # 4. Expired timestamp must be rejected.
        old_ts = int(time.time()) - 10000
        resp = requests.get(
            f'{BASE_URL}{path}',
            headers=_sign_request('GET', path, timestamp=old_ts),
            timeout=10,
        )
        if resp.status_code != 401:
            raise AssertionError(
                f'{path}: expired timestamp expected 401, got {resp.status_code}'
            )
        print('[PASS] Expired timestamp rejected (401)')
        passed += 1

        # 5. Missing headers must be rejected.
        resp = requests.get(f'{BASE_URL}{path}', timeout=10)
        if resp.status_code != 401:
            raise AssertionError(
                f'{path}: missing headers expected 401, got {resp.status_code}'
            )
        print('[PASS] Missing auth headers rejected (401)')
        passed += 1

        # 6. Mutation methods must not be exposed.
        for method in ['POST', 'PUT', 'DELETE', 'PATCH']:
            ep = '/api/v1/positions'
            resp = requests.request(
                method,
                f'{BASE_URL}{ep}',
                headers=_sign_request(method, ep),
                timeout=10,
            )
            if resp.status_code not in (401, 405, 404):
                raise AssertionError(
                    f'{method} {ep}: expected blocked (401/405/404), got {resp.status_code}'
                )
            print(f'[PASS] {method} {ep} blocked ({resp.status_code})')
            passed += 1

        print("=" * 70)
        print(f'[SUCCESS] All {passed} checks passed.')
        print("=" * 70)
        return 0

    except Exception as exc:
        print(f'[FAIL] Verification failed: {exc}')
        traceback.print_exc()
        failed += 1
        return 1
    finally:
        if proc is not None:
            _stop_server(proc, log_file)


if __name__ == '__main__':
    sys.exit(main())
