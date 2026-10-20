"""
earnings_calendar.py
====================
Free earnings-date feed for the VolatilityHunter earnings guard (v8.6).

Source: Nasdaq bulk earnings calendar (keyless JSON endpoint).
    GET https://api.nasdaq.com/api/calendar/earnings?date=YYYY-MM-DD
One request returns EVERY ticker reporting on that date, so ~30 requests cover
the full forward window for the entire 2,135-ticker universe - far cheaper than
a per-ticker API and no paid key required.

Cache: data/earnings_cache.json
    {"fetched_at": "YYYY-MM-DD", "window_days": N,
     "dates": {"AAPL": "YYYY-MM-DD", ...}}   # earliest upcoming report per ticker

Semantics:
  - Refreshed once per calendar day (fetched_at != today -> refresh).
  - Ticker absent from map == no earnings scheduled within the window.
    FAIL-OPEN by design: a missing/unknown date never blocks a trade, because
    coverage for small caps is spotty and false blocks would poison the scan.
  - All fetch failures log a full traceback and degrade to the stale cache
    (or {} if none) - the guard disables itself rather than crashing the loop.

Backtest caveat: this feed is forward-looking only (next ~30 days). There is no
free point-in-time 26-year earnings history, so EARNINGS_* params are live/sim
features - the historical backtest cannot measure them and any result claiming
otherwise would be lookahead-biased.
"""

import json
import logging
import os
import traceback
from datetime import date, datetime, timedelta
from typing import Dict, Optional

logger = logging.getLogger(__name__)

_CACHE_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), '..', 'data', 'earnings_cache.json'))

NASDAQ_URL = 'https://api.nasdaq.com/api/calendar/earnings?date={}'
WINDOW_DAYS = 30          # fetch ~1 month forward to cover BLOCK_DAYS=14 + slack
_REQUEST_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
    'Accept': 'application/json',
}


def _fetch_day(day: date) -> Dict[str, str]:
    """Return {symbol: 'YYYY-MM-DD'} for all tickers reporting on `day`."""
    import requests
    r = requests.get(NASDAQ_URL.format(day.isoformat()),
                     headers=_REQUEST_HEADERS, timeout=15)
    r.raise_for_status()
    rows = ((r.json().get('data') or {}).get('rows')) or []
    out = {}
    for row in rows:
        sym = (row.get('symbol') or '').strip()
        if sym:
            out[sym] = day.isoformat()
    return out


def refresh_cache(window_days: int = WINDOW_DAYS,
                  start: Optional[date] = None) -> Dict[str, str]:
    """
    Rebuild the earnings map by querying Nasdaq for each of the next
    `window_days` calendar days. Writes data/earnings_cache.json.
    Returns {ticker: earliest 'YYYY-MM-DD' within the window}.
    """
    start = start or date.today()
    dates: Dict[str, str] = {}
    for i in range(window_days):
        day = start + timedelta(days=i)
        try:
            for sym, d in _fetch_day(day).items():
                if sym not in dates:            # keep earliest date per ticker
                    dates[sym] = d
        except Exception as e:
            # Per-protocol: log full traceback; a dead day degrades coverage,
            # never aborts the refresh.
            logger.error(f"earnings_calendar: fetch {day} failed: {e}\n"
                         f"{traceback.format_exc()}")
    try:
        os.makedirs(os.path.dirname(_CACHE_PATH), exist_ok=True)
        with open(_CACHE_PATH, 'w') as f:
            json.dump({'fetched_at': start.isoformat(),
                       'window_days': window_days,
                       'dates': dates}, f, indent=1)
        logger.info(f"earnings_calendar: cached {len(dates)} tickers "
                    f"({start} + {window_days}d) -> {_CACHE_PATH}")
    except Exception as e:
        logger.error(f"earnings_calendar: cache write failed: {e}\n"
                     f"{traceback.format_exc()}")
    return dates


def load_cache() -> Optional[dict]:
    """Read the cache file; None if missing/corrupt."""
    try:
        with open(_CACHE_PATH) as f:
            return json.load(f)
    except Exception:
        return None


def get_earnings_map() -> Dict[str, str]:
    """
    Return {ticker: next earnings 'YYYY-MM-DD'} for the forward window.
    Always anchored at the real current date (never a sim date - a historical
    sim would otherwise overwrite the live cache with a bogus window).
    Refreshes once per calendar day; on any failure returns the stale cache's
    map or {} (fail-open).
    """
    today = date.today()
    cache = load_cache()
    if cache and cache.get('fetched_at') == today.isoformat():
        return cache.get('dates') or {}
    try:
        return refresh_cache(start=today)
    except Exception as e:
        logger.error(f"earnings_calendar: refresh failed: {e}\n"
                     f"{traceback.format_exc()}")
        return (cache or {}).get('dates') or {}


def days_to_earnings(ticker: str, today: date,
                     earnings_map: Optional[Dict[str, str]] = None
                     ) -> Optional[int]:
    """
    Calendar days from `today` until the ticker's next report.
    None = not scheduled within the fetched window (or unknown).
    Negative = already reported (past date still in a stale map).
    """
    if earnings_map is None:
        earnings_map = get_earnings_map()
    d = earnings_map.get(ticker)
    if not d:
        return None
    try:
        return (datetime.strptime(d, '%Y-%m-%d').date() - today).days
    except Exception as e:
        logger.error(f"earnings_calendar: bad date '{d}' for {ticker}: {e}\n"
                     f"{traceback.format_exc()}")
        return None
