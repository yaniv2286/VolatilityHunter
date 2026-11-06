"""
monitoring_adapter.py
======================
Signed, read-only FastAPI monitoring adapter for the Family Agent Platform.

- No mutation, control, or order endpoints are exposed.
- All endpoints are HMAC-SHA256 authenticated via AGENT_SHARED_SECRET.
- Request signature covers timestamp + HTTP method + path + body hash.
- Requests outside the configured replay window are rejected.
- Response envelope: agent_id, version, timestamp, data, error.

Run locally:
    python src/monitoring_adapter.py

Run via uvicorn:
    uvicorn src.monitoring_adapter:app --host 0.0.0.0 --port 8080
"""

import hashlib
import hmac
import logging
import os
import sys
import time
import traceback
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, status
from fastapi.responses import JSONResponse

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

from src.log_sanitizer import setup_enhanced_logging
from src.monitoring_state import (
    DATA_DIR,
    LOG_DIR,
    get_latest_logs,
    get_portfolio,
    get_run_manifest,
    get_strategy_info,
    sanitize_logs,
)

# ── Configuration ────────────────────────────────────────────────────────────
AGENT_ID = os.getenv('AGENT_ID', 'volatilityhunter')
AGENT_SHARED_SECRET = os.getenv('AGENT_SHARED_SECRET', '')
try:
    REPLAY_WINDOW_SECONDS = int(os.getenv('AGENT_REPLAY_WINDOW') or '300')
except ValueError:
    REPLAY_WINDOW_SECONDS = 300
API_VERSION = 'v1'

logger = setup_enhanced_logging(
    'monitoring_adapter',
    str(LOG_DIR / 'monitoring_adapter.log')
)

# Pre-load strategy metadata so the first /signals request is not delayed by
# the heavy pandas/numpy imports inside strategy_engine.
logger.info('Pre-loading strategy metadata...')
_strategy_info_cache = get_strategy_info()
logger.info(f'Strategy metadata loaded: version={_strategy_info_cache.get("default_version")}')

# ── FastAPI App ──────────────────────────────────────────────────────────────
app = FastAPI(
    title='VolatilityHunter Family Agent Monitoring Adapter',
    description='Read-only monitoring API for the Family Agent Platform. '
                'No trading controls or order endpoints are exposed.',
    version='1.0.0',
)

# ── Helpers ──────────────────────────────────────────────────────────────────


def _make_envelope(request: Request, data: Any, error: Optional[str] = None) -> Dict[str, Any]:
    """Generic response envelope required by the Family Agent Platform."""
    return {
        'agent_id': AGENT_ID,
        'version': API_VERSION,
        'timestamp': datetime.now(timezone.utc).isoformat(),
        'data': data,
        'error': error,
    }


def _verify_signature(request: Request, body: bytes) -> None:
    """Validate HMAC-SHA256 signature and replay window."""
    if not AGENT_SHARED_SECRET:
        logger.error('AGENT_SHARED_SECRET is not configured')
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail='Server HMAC secret not configured'
        )

    agent_id = request.headers.get('x-agent-id', '')
    timestamp_str = request.headers.get('x-timestamp', '')
    signature = request.headers.get('x-signature', '')

    if not agent_id or not timestamp_str or not signature:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Missing HMAC authentication headers'
        )

    try:
        timestamp = int(timestamp_str)
    except ValueError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid timestamp header'
        )

    now = int(time.time())
    if abs(now - timestamp) > REPLAY_WINDOW_SECONDS:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Request outside replay window'
        )

    method = request.method.upper()
    path = request.url.path
    body_hash = hashlib.sha256(body).hexdigest() if body else ''
    payload = f'{timestamp}|{method}|{path}|{body_hash}'

    expected = hmac.new(
        AGENT_SHARED_SECRET.encode('utf-8'),
        payload.encode('utf-8'),
        hashlib.sha256,
    ).hexdigest()

    if not hmac.compare_digest(expected, signature):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail='Invalid HMAC signature'
        )


# ── Middleware ─────────────────────────────────────────────────────────────────

@app.middleware('http')
async def hmac_auth_middleware(request: Request, call_next):
    """Authenticate every request (except OpenAPI/docs)."""
    # Permit unauthenticated access to API documentation.
    if request.url.path in ('/', '/docs', '/openapi.json', '/redoc'):
        return await call_next(request)

    body = await request.body()

    # Rebuild request so downstream routes can still access the body if needed.
    async def _receive():
        return {'type': 'http.request', 'body': body}

    request = Request(request.scope, _receive)
    _verify_signature(request, body)
    return await call_next(request)


@app.exception_handler(Exception)
async def generic_exception_handler(request: Request, exc: Exception):
    """Return all unexpected errors in the standard envelope.

    HTTPException raised by the HMAC middleware is preserved so that
    authentication failures return 401 instead of being masked as 500.
    """
    if isinstance(exc, HTTPException):
        return JSONResponse(
            status_code=exc.status_code,
            content=_make_envelope(request, {}, error=exc.detail)
        )
    logger.error(f'Unhandled exception in monitoring adapter: {exc}')
    logger.error(traceback.format_exc())
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=_make_envelope(request, {}, error=str(exc))
    )


# ── Endpoints ──────────────────────────────────────────────────────────────────

@app.get('/api/v1/health')
async def health(request: Request):
    """Adapter and underlying trading system health."""
    manifest = get_run_manifest()
    portfolio = get_portfolio()
    manifest_status = manifest.get('status')
    healthy_statuses = {'SUCCESS', 'RUNNING'}
    is_healthy = not manifest or manifest_status in healthy_statuses
    return _make_envelope(request, {
        'status': 'healthy' if is_healthy else 'degraded',
        'manifest_status': manifest_status,
        'portfolio_positions': len(portfolio.get('positions', {})),
        'agent_id': AGENT_ID,
        'read_only': True,
    })


@app.get('/api/v1/capabilities')
async def capabilities(request: Request):
    """List all available monitoring endpoints and capabilities."""
    return _make_envelope(request, {
        'agent_id': AGENT_ID,
        'api_version': API_VERSION,
        'auth': 'HMAC-SHA256',
        'read_only': True,
        'endpoints': [
            {'path': '/api/v1/health', 'method': 'GET', 'description': 'System health'},
            {'path': '/api/v1/capabilities', 'method': 'GET', 'description': 'API capabilities'},
            {'path': '/api/v1/status', 'method': 'GET', 'description': 'Pipeline status'},
            {'path': '/api/v1/portfolio/totals', 'method': 'GET', 'description': 'Portfolio totals'},
            {'path': '/api/v1/positions', 'method': 'GET', 'description': 'Open positions'},
            {'path': '/api/v1/orders', 'method': 'GET', 'description': 'Recent orders/trades'},
            {'path': '/api/v1/performance', 'method': 'GET', 'description': 'Performance/equity summary'},
            {'path': '/api/v1/signals', 'method': 'GET', 'description': 'Strategy version and parameters'},
            {'path': '/api/v1/risk', 'method': 'GET', 'description': 'Risk and circuit-breaker state'},
            {'path': '/api/v1/alerts', 'method': 'GET', 'description': 'Recent alerts'},
            {'path': '/api/v1/logs', 'method': 'GET', 'description': 'Sanitized operational logs'},
        ],
    })


@app.get('/api/v1/status')
async def system_status(request: Request):
    """Latest daily orchestrator status and portfolio sync state."""
    manifest = get_run_manifest()
    portfolio = get_portfolio()
    return _make_envelope(request, {
        'last_manifest': manifest,
        'positions_count': len(portfolio.get('positions', {})),
        'cash': portfolio.get('cash'),
        'last_updated': portfolio.get('last_updated'),
        'last_ibkr_sync': portfolio.get('last_ibkr_sync'),
        'ibkr_available': portfolio.get('ibkr_available'),
    })


@app.get('/api/v1/portfolio/totals')
async def portfolio_totals(request: Request):
    """Portfolio-level totals (cash, total value, position count)."""
    portfolio = get_portfolio()
    positions = portfolio.get('positions', {})
    cash = portfolio.get('cash', 0.0)
    total_value = portfolio.get('total_value')

    if total_value is None and isinstance(positions, dict):
        # Fallback computation using last known entry prices.
        total_value = cash + sum(
            pos.get('shares', 0) * pos.get('entry_price', 0.0)
            for pos in positions.values()
            if isinstance(pos, dict)
        )

    return _make_envelope(request, {
        'cash': cash,
        'total_value': total_value,
        'initial_capital': portfolio.get('initial_capital', 100_000.0),
        'unrealized_pnl': portfolio.get('unrealized_pnl'),
        'position_count': len(positions),
    })


@app.get('/api/v1/positions')
async def positions(request: Request):
    """All open positions from portfolio.json."""
    portfolio = get_portfolio()
    return _make_envelope(request, {
        'positions': portfolio.get('positions', {}),
        'count': len(portfolio.get('positions', {})),
    })


@app.get('/api/v1/orders')
async def orders(request: Request, limit: int = 50):
    """Recent trade/order history from portfolio.json."""
    portfolio = get_portfolio()
    history = portfolio.get('trade_history', [])
    if not isinstance(history, list):
        history = []
    return _make_envelope(request, {
        'trades': history[-limit:],
        'count': len(history),
    })


@app.get('/api/v1/performance')
async def performance(request: Request):
    """High-level performance/equity summary."""
    portfolio = get_portfolio()
    positions = portfolio.get('positions', {})
    cash = portfolio.get('cash', 0.0)
    total_value = portfolio.get('total_value')

    if total_value is None and isinstance(positions, dict):
        total_value = cash + sum(
            pos.get('shares', 0) * pos.get('entry_price', 0.0)
            for pos in positions.values()
            if isinstance(pos, dict)
        )

    initial = portfolio.get('initial_capital', 100_000.0)
    pnl = (total_value - initial) if total_value is not None else None
    pnl_pct = (pnl / initial) if (pnl is not None and initial > 0) else None

    return _make_envelope(request, {
        'total_value': total_value,
        'cash': cash,
        'invested': (total_value - cash) if total_value is not None else None,
        'total_pnl': pnl,
        'total_pnl_pct': pnl_pct,
        'position_count': len(positions),
        'trade_count': len(portfolio.get('trade_history', [])),
    })


@app.get('/api/v1/signals')
async def signals(request: Request):
    """Current strategy version and parameters (read-only)."""
    info = _strategy_info_cache
    manifest = get_run_manifest()
    return _make_envelope(request, {
        'default_version': info.get('default_version'),
        'params': info.get('params'),
        'strategy_error': info.get('error'),
        'last_manifest_status': manifest.get('status'),
    })


@app.get('/api/v1/risk')
async def risk(request: Request):
    """Risk and circuit-breaker state derived from local state."""
    portfolio = get_portfolio()
    positions = portfolio.get('positions', {})
    cash = portfolio.get('cash', 0.0)
    total_value = portfolio.get('total_value')

    if total_value is None and isinstance(positions, dict):
        total_value = cash + sum(
            pos.get('shares', 0) * pos.get('entry_price', 0.0)
            for pos in positions.values()
            if isinstance(pos, dict)
        )

    manifest = get_run_manifest()
    manifest_status = manifest.get('status')
    circuit_breaker_tripped = bool(
        manifest_status and not str(manifest_status).startswith(('SUCCESS', 'RUNNING'))
    )

    warnings: List[str] = []
    if cash < 0:
        warnings.append('Negative cash detected')
    if cash > 150_000:
        warnings.append('Cash exceeds $150k ceiling')
    if len(positions) > 10:
        warnings.append('Positions exceed maximum of 10')

    concentration: Dict[str, float] = {}
    if total_value and total_value > 0 and isinstance(positions, dict):
        for ticker, pos in positions.items():
            if isinstance(pos, dict):
                position_value = pos.get('shares', 0) * pos.get('entry_price', 0.0)
                concentration[ticker] = position_value / total_value

    return _make_envelope(request, {
        'circuit_breaker_tripped': circuit_breaker_tripped,
        'manifest_status': manifest_status,
        'cash': cash,
        'cash_in_safe_range': 0 <= cash <= 150_000,
        'position_count': len(positions),
        'max_positions_limit': 10,
        'total_value': total_value,
        'position_concentration': concentration,
        'warnings': warnings,
    })


@app.get('/api/v1/alerts')
async def alerts(request: Request, lines: int = 200):
    """Recent ERROR/CRITICAL/FAILED/Traceback lines from operational logs."""
    logs = get_latest_logs(lines)
    alert_patterns = (
        'ERROR', 'CRITICAL', 'FAILED', 'Traceback',
        'CIRCUIT BREAKER', 'TRADING ABORTED', 'CRITICAL FAILURE'
    )
    found: List[Dict[str, str]] = []
    for name, log_lines in logs.items():
        for line in log_lines:
            if any(pattern in line for pattern in alert_patterns):
                found.append({'source': name, 'line': line})
    return _make_envelope(request, {
        'alerts': found[-lines:],
        'count': len(found),
    })


@app.get('/api/v1/logs')
async def logs(request: Request, lines: int = 200):
    """Sanitized recent operational logs."""
    raw_logs = get_latest_logs(lines)
    sanitized = sanitize_logs(raw_logs, lines)
    return _make_envelope(request, {
        'logs': sanitized,
    })


# ── Entrypoint ─────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import uvicorn
    port = int(os.getenv('MONITORING_PORT') or '8080')
    host = os.getenv('MONITORING_HOST') or '0.0.0.0'
    logger.info(f'Starting monitoring adapter on {host}:{port}')
    uvicorn.run('src.monitoring_adapter:app', host=host, port=port)
