"""
Production Data Loader Factory - Tiingo Professional API Only
100% Tiingo integration - No Yahoo Finance, No Fallback Logic.

Two responsibilities:
  1. EOD daily bars: write COMPLETED end-of-day OHLCV to data/*.parquet.
  2. Intraday snapshots: fetch IEX last-trade prices for execution only;
     these are NEVER persisted to parquet.
"""

import gc
import os
import time
import threading
import requests
import pandas as pd
import urllib3
import json
from datetime import datetime, timedelta, time as dtime
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from src.config import TIINGO_KEY
from src.notifications import log_info, log_warning, log_error
from src.log_sanitizer import log_error_with_tracking

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
DATA_DIR = ROOT / 'data'

# Target ~4 Tiingo EOD requests/sec; safe for standard paid plans.
EOD_MIN_INTERVAL = 0.25
EOD_MAX_WORKERS = 4
IEX_CHUNK_SIZE = 100


class _RateLimiter:
    """Thread-safe token-bucket-ish limiter: enforces a minimum interval between any two requests."""

    def __init__(self, interval: float):
        self.interval = interval
        self._lock = threading.Lock()
        self._last = 0.0

    def acquire(self):
        with self._lock:
            now = time.time()
            wait = self.interval - (now - self._last)
            if wait > 0:
                time.sleep(wait)
                self._last = time.time()
            else:
                self._last = now


class TiingoLoader:
    """Tiingo Professional API data loader.  EOD bars for history, IEX for live prices."""

    def __init__(self):
        self.api_key = TIINGO_KEY
        self._rate_limiter = _RateLimiter(EOD_MIN_INTERVAL)
        if not self.api_key:
            log_error('TIINGO_API_KEY not found in environment')

    # ── helpers ──────────────────────────────────────────────────────────────

    def _today_str(self) -> str:
        return datetime.now().strftime('%Y-%m-%d')

    def _request(self, url: str, params: dict, timeout: int = 60) -> requests.Response:
        """Make a rate-limited Tiingo request and handle 429 backoff."""
        self._rate_limiter.acquire()
        try:
            resp = requests.get(url, params=params,
                                headers={'Content-Type': 'application/json'},
                                timeout=timeout, verify=False)
            if resp.status_code == 429:
                log_warning('Tiingo 429 rate limited - backing off 60s')
                time.sleep(60)
                self._rate_limiter.acquire()
                resp = requests.get(url, params=params,
                                    headers={'Content-Type': 'application/json'},
                                    timeout=timeout, verify=False)
            resp.raise_for_status()
            return resp
        except Exception as e:
            log_error(f'Tiingo request failed {url}: {e}')
            raise

    def _load_parquet(self, ticker: str) -> Tuple[pd.DataFrame, Path]:
        path = DATA_DIR / f'{ticker.lower()}.parquet'
        if not path.exists():
            return pd.DataFrame(), path
        try:
            df = pd.read_parquet(path)
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df.index = df.index.tz_localize(None)
            df = df[~df.index.duplicated(keep='last')]
            df.sort_index(inplace=True)
            return df, path
        except Exception as e:
            log_error(f'Failed to read {path}: {e}')
            return pd.DataFrame(), path

    def _save_parquet(self, df: pd.DataFrame, path: Path):
        try:
            df = df[~df.index.duplicated(keep='last')]
            df.sort_index(inplace=True)
            df.to_parquet(path)
        except Exception as e:
            log_error(f'Failed to write {path}: {e}')
            raise

    def _last_completed_eod_date(self) -> datetime:
        """
        Return the most recent date for which a completed EOD bar exists.
        If the market has already closed today, today is completed;
        otherwise the previous trading day.
        """
        from src.market_hours import MarketHours
        mh = MarketHours()
        now = mh.get_current_time()
        d = now.date()
        if mh.is_trading_day(now):
            close_time = mh.EARLY_CLOSES_2026.get(d, mh.market_close)
            if now.time() >= close_time:
                return datetime.combine(d, close_time)
        # Step back to the previous trading day.
        d = d - timedelta(days=1)
        while d.weekday() >= 5 or d in mh.HOLIDAYS_2026:
            d = d - timedelta(days=1)
        return datetime.combine(d, dtime(16, 0))

    def _filter_incomplete_last_bar(self, df: pd.DataFrame) -> pd.DataFrame:
        """Drop any row newer than the last completed EOD (prevents partial IEX/INTRADAY bars)."""
        if df.empty:
            return df
        max_completed = self._last_completed_eod_date()
        return df[df.index <= pd.Timestamp(max_completed)]

    def _parse_eod_rows(self, rows: List[dict]) -> pd.DataFrame:
        if not rows:
            return pd.DataFrame()
        df = pd.DataFrame(rows)
        df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None).dt.normalize()
        df = df.set_index('date')

        required = ['open', 'high', 'low', 'close', 'volume',
                    'adjOpen', 'adjHigh', 'adjLow', 'adjClose', 'adjVolume',
                    'divCash', 'splitFactor']
        for col in required:
            if col not in df.columns:
                df[col] = float('nan')
            else:
                df[col] = pd.to_numeric(df[col], errors='coerce')

        # Fill missing adjusted columns with raw values.
        for raw, adj in [('open', 'adjOpen'), ('high', 'adjHigh'),
                         ('low', 'adjLow'), ('close', 'adjClose'),
                         ('volume', 'adjVolume')]:
            if df[adj].isna().any() and raw in df.columns:
                df[adj] = df[adj].fillna(df[raw])
        return df

    # ── EOD per-ticker update ───────────────────────────────────────────────

    def update_ticker_eod(self, ticker: str, start_date: Optional[str] = None,
                          end_date: Optional[str] = None,
                          overwrite_range: bool = False) -> bool:
        """
        Fetch EOHLCV from the Tiingo daily endpoint and update the ticker parquet.
        If overwrite_range=True, replace any existing rows in the fetched date range.
        """
        if not self.api_key:
            return False

        today = self._today_str()
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        url = f'https://api.tiingo.com/tiingo/daily/{ticker}/prices'
        params = {
            'startDate': start_date,
            'endDate': end_date,
            'columns': 'open,high,low,close,volume,adjOpen,adjHigh,adjLow,adjClose,adjVolume,divCash,splitFactor',
            'format': 'json',
            'resampleFreq': 'daily',
            'token': self.api_key,
        }

        try:
            resp = self._request(url, params, timeout=60)
            rows = resp.json()
            if not rows:
                return False

            new_df = self._parse_eod_rows(rows)
            new_df = self._filter_incomplete_last_bar(new_df)
            if new_df.empty:
                return False

            existing_df, path = self._load_parquet(ticker)
            if existing_df.empty:
                self._save_parquet(new_df, path)
                return True

            if overwrite_range:
                min_new = new_df.index.min()
                # Remove every existing bar from the repair start date forward;
                # new_df contains the repaired completed bars (up to max_completed).
                existing_df = existing_df[existing_df.index < min_new]
            else:
                # Normal daily update: only consider the latest existing bar and newer.
                latest_existing = existing_df.index[-1]
                new_df = new_df[new_df.index >= latest_existing]

            # Replace the last bar if we are refreshing it with a completed EOD bar.
            if not new_df.empty:
                latest_new = new_df.index[-1]
                if latest_new in existing_df.index:
                    existing_df = existing_df[existing_df.index != latest_new]

            combined = pd.concat([existing_df, new_df])
            combined = combined[~combined.index.duplicated(keep='last')].sort_index()
            self._save_parquet(combined, path)
            return True

        except Exception as e:
            log_error(f'update_ticker_eod {ticker}: {e}')
            return False

    # ── full-universe EOD update ─────────────────────────────────────────────

    def update_all_stocks_eod(self, stock_list: List[str],
                              start_date: Optional[str] = None,
                              end_date: Optional[str] = None,
                              overwrite_range: bool = False) -> dict:
        """Update EOD parquets for a list of tickers using the Tiingo daily endpoint."""
        if not self.api_key:
            return {'success': False, 'error': 'TIINGO_API_KEY missing', 'updated': 0, 'total': len(stock_list)}

        today = self._today_str()
        if end_date is None:
            end_date = today
        if start_date is None:
            start_date = (datetime.now() - timedelta(days=7)).strftime('%Y-%m-%d')

        updated = 0
        failed = []

        def _worker(ticker: str) -> Tuple[str, bool]:
            try:
                ok = self.update_ticker_eod(ticker, start_date, end_date, overwrite_range=overwrite_range)
                return ticker, ok
            except Exception as e:
                log_error(f'EOD worker {ticker}: {e}')
                return ticker, False

        with ThreadPoolExecutor(max_workers=EOD_MAX_WORKERS) as executor:
            future_to_ticker = {executor.submit(_worker, t): t for t in stock_list}
            for future in as_completed(future_to_ticker):
                ticker, ok = future.result()
                if ok:
                    updated += 1
                else:
                    failed.append(ticker)
                total = updated + len(failed)
                if total % 250 == 0:
                    log_info(f'EOD update progress: {updated} updated, {len(failed)} failed ({total}/{len(stock_list)})')

        log_info(f'EOD update complete: {updated}/{len(stock_list)} updated, {len(failed)} failed')
        return {
            'success': len(failed) < len(stock_list),
            'updated': updated,
            'total': len(stock_list),
            'failed': failed,
        }

    # ── IEX intraday prices (NOT persisted) ────────────────────────────────────

    def get_latest_ohlcv(self, stock_list: List[str], chunk_size: int = IEX_CHUNK_SIZE) -> Dict[str, dict]:
        """Fetch IEX intraday OHLCV snapshots via the bulk endpoint.  NOT persisted."""
        if not self.api_key:
            return {}

        ohlcv = {}
        failed_chunks = 0
        chunks = [stock_list[i:i + chunk_size] for i in range(0, len(stock_list), chunk_size)]

        for i, chunk in enumerate(chunks):
            url = 'https://api.tiingo.com/iex'
            params = {'tickers': ','.join(chunk), 'token': self.api_key}
            try:
                # IEX is a bulk endpoint; do not use the EOD rate limiter here.
                resp = requests.get(url, params=params,
                                    headers={'Content-Type': 'application/json'},
                                    timeout=60, verify=False)
                if resp.status_code == 429:
                    log_warning('IEX 429 - backing off 60s')
                    time.sleep(60)
                    resp = requests.get(url, params=params,
                                        headers={'Content-Type': 'application/json'},
                                        timeout=60, verify=False)
                resp.raise_for_status()
                data = resp.json()
                for item in data:
                    ticker = item.get('ticker')
                    if not ticker:
                        continue
                    last = item.get('tngoLast') or item.get('last')
                    if not last:
                        continue
                    ohlcv[ticker] = {
                        'open':   float(item.get('open') or last),
                        'high':   float(item.get('high') or last),
                        'low':    float(item.get('low') or last),
                        'close':  float(last),
                        'volume': int(item.get('volume') or 0),
                    }
            except Exception as e:
                log_error(f'IEX chunk {i} failed: {e}')
                failed_chunks += 1

        if failed_chunks:
            log_warning(f'IEX: {failed_chunks}/{len(chunks)} chunks failed')
        log_info(f'IEX snapshot OHLCV fetched: {len(ohlcv)}/{len(stock_list)}')
        return ohlcv

    def get_latest_prices(self, stock_list: List[str], chunk_size: int = IEX_CHUNK_SIZE) -> Dict[str, float]:
        """Fetch IEX last-trade prices (flat dict) for execution."""
        ohlcv = self.get_latest_ohlcv(stock_list, chunk_size=chunk_size)
        return {t: v['close'] for t, v in ohlcv.items()}

    # ── legacy-compatible combined update ─────────────────────────────────────

    def update_all_stocks(self, stock_list, full_refresh=False, batch_size=50,
                          eod_start_date: Optional[str] = None,
                          eod_end_date: Optional[str] = None) -> dict:
        """
        1. Refresh EOD parquets (default last 7 days; override with eod_start_date/eod_end_date).
        2. Return IEX intraday snapshot prices for the current session.
        """
        if not self.api_key:
            return {'success': False, 'error': 'TIINGO_API_KEY missing',
                    'updated': 0, 'total': len(stock_list), 'prices': {}}

        today = datetime.now()
        if eod_end_date is None:
            eod_end_date = today.strftime('%Y-%m-%d')
        if eod_start_date is None:
            eod_start_date = (today - timedelta(days=7)).strftime('%Y-%m-%d')

        # For a full repair, overwrite the fetched date range in each parquet.
        overwrite_range = bool(full_refresh)
        eod_result = self.update_all_stocks_eod(stock_list, start_date=eod_start_date,
                                                end_date=eod_end_date, overwrite_range=overwrite_range)
        ohlcv = self.get_latest_ohlcv(stock_list)
        prices = {t: v['close'] for t, v in ohlcv.items()}
        return {
            'success': eod_result['success'],
            'updated': eod_result['updated'],
            'total': len(stock_list),
            'prices': prices,
            'ohlcv': ohlcv,
            'failed': eod_result.get('failed', []),
        }

    # ── one-shot repair of a date range ───────────────────────────────────────

    def repair_parquet_range(self, stock_list: List[str],
                             start_date: str,
                             end_date: Optional[str] = None) -> dict:
        """Repair poisoned parquets by overwriting the specified date range with EOD data."""
        if end_date is None:
            end_date = self._today_str()
        return self.update_all_stocks_eod(stock_list, start_date=start_date,
                                          end_date=end_date, overwrite_range=True)

    # ── sector metadata (Tiingo fundamentals/meta) ─────────────────────────────

    def fetch_ticker_metadata(self, ticker: str) -> dict:
        """Fetch fundamentals metadata for a single ticker; returns sector/industry if available."""
        url = 'https://api.tiingo.com/tiingo/fundamentals/meta'
        params = {'tickers': ticker, 'token': self.api_key}
        try:
            resp = self._request(url, params, timeout=30)
            data = resp.json()
            if data and len(data) > 0:
                item = data[0]
                return {
                    'ticker': item.get('ticker', ticker).upper(),
                    'sector': item.get('sector') or 'Unknown',
                    'industry': item.get('industry') or 'Unknown',
                    'description': item.get('description', ''),
                    'exchange': item.get('exchangeCode') or 'Unknown',
                    'assetType': 'stock',
                }
        except Exception as e:
            log_error(f'Failed to fetch metadata for {ticker}: {e}')
        return {'ticker': ticker, 'sector': 'Unknown'}

    def update_sector_map(self, stock_list: List[str], batch_size: int = 100) -> int:
        """Update data/sector_map.json from Tiingo fundamentals/meta (batched)."""
        if not self.api_key:
            log_error('TIINGO_API_KEY missing - cannot update sector map')
            return 0

        sector_map_path = DATA_DIR / 'sector_map.json'
        existing = {}
        if sector_map_path.exists():
            try:
                with open(sector_map_path, 'r') as f:
                    existing = json.load(f)
            except Exception as e:
                log_warning(f'Could not load existing sector_map.json: {e}')

        updated = 0
        failed = 0
        chunks = [stock_list[i:i + batch_size] for i in range(0, len(stock_list), batch_size)]

        for i, chunk in enumerate(chunks):
            url = 'https://api.tiingo.com/tiingo/fundamentals/meta'
            params = {'tickers': ','.join(chunk), 'token': self.api_key}
            try:
                resp = self._request(url, params, timeout=60)
                items = resp.json()
                for item in items:
                    ticker = (item.get('ticker') or '').upper()
                    if not ticker:
                        continue
                    sector = item.get('sector')
                    industry = item.get('industry')
                    # Tiingo free/evaluation returns "Field not available..." for some tickers.
                    # Never overwrite an existing real sector with an Unknown placeholder.
                    sector_str = str(sector).strip()
                    if not sector or sector_str.lower() in ('unknown', 'nan', 'none') or 'not available' in sector_str.lower():
                        sector = existing.get(ticker, {}).get('sector', 'Unknown')
                    industry_str = str(industry).strip()
                    if not industry or industry_str.lower() in ('unknown', 'nan', 'none') or 'not available' in industry_str.lower():
                        industry = existing.get(ticker, {}).get('industry', 'Unknown')
                    existing[ticker] = {
                        'name': item.get('name') or ticker,
                        'sector': sector,
                        'industry': industry,
                        'exchange': item.get('exchangeCode') or existing.get(ticker, {}).get('exchange', 'Unknown'),
                    }
                    if sector and sector != 'Unknown':
                        updated += 1
            except Exception as e:
                log_error(f'Sector map chunk {i} failed: {e}')
                failed += 1

        try:
            with open(sector_map_path, 'w') as f:
                json.dump(existing, f, indent=2)
            log_info(f'Sector map updated: {updated} real sectors, {failed} failed chunks, total={len(existing)}')
        except Exception as e:
            log_error(f'Failed to write sector_map.json: {e}')

        return updated

    def fetch_all_metadata(self, ticker_list: List[str]) -> dict:
        """Backwards-compatible alias that updates and returns the sector map."""
        self.update_sector_map(ticker_list)
        sector_map_path = DATA_DIR / 'sector_map.json'
        if sector_map_path.exists():
            try:
                return json.loads(sector_map_path.read_text())
            except Exception:
                pass
        return {}

    # ── legacy helpers ─────────────────────────────────────────────────────────

    def download_nasdaq_tickers(self):
        from src.config import STOCK_LIST
        return STOCK_LIST

    def filter_tickers_by_criteria(self, tickers, min_price=5.0, min_volume=500000, batch_size=50):
        return pd.DataFrame([{'ticker': t, 'price': 0, 'avg_volume': 0} for t in tickers])


def get_data_loader():
    """Factory returning the Tiingo-only loader."""
    log_info('Production: Using Tiingo Professional API - No Fallback Logic')
    return TiingoLoader()
