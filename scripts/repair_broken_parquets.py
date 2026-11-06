#!/usr/bin/env python3
"""
repair_broken_parquets.py
=========================
One-shot repair: finds all parquet files with < 300 rows (insufficient for
indicator calculation) and re-fetches full history from Tiingo daily API.

Run once after the smart_data_loader_factory fix to restore broken tickers.
Logs every step; exit code 0 = all repaired or best-effort, 1 = fatal.
"""

import os
import sys
import time
import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / '.env')

# ── Logging ───────────────────────────────────────────────────────────────────
LOG_DIR = ROOT / 'logs'
LOG_DIR.mkdir(exist_ok=True)
log_path = LOG_DIR / f"repair_parquets_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[
        logging.FileHandler(str(log_path), encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger('repair_parquets')

# ── Config ────────────────────────────────────────────────────────────────────
DATA_DIR     = ROOT / 'data'
TIINGO_KEY   = os.getenv('TIINGO_API_KEY') or os.getenv('TIINGO_KEY')
MIN_ROWS     = 300
FULL_START   = '2000-01-01'
TODAY        = datetime.now().strftime('%Y-%m-%d')
RATE_LIMIT_S = 0.25   # 250ms between requests -> max 4/sec, Tiingo allows 50/min


def fetch_full_history(ticker: str) -> pd.DataFrame:
    """
    Fetch full OHLCV history from Tiingo daily endpoint for a single ticker.
    Returns DataFrame indexed by date, or empty DataFrame on failure.
    """
    url = f"https://api.tiingo.com/tiingo/daily/{ticker}/prices"
    params = {
        'startDate': FULL_START,
        'endDate':   TODAY,
        'columns':   'open,high,low,close,volume,adjOpen,adjHigh,adjLow,adjClose,adjVolume,divCash,splitFactor',
        'format':    'json',
        'resampleFreq': 'daily',
        'token':     TIINGO_KEY,
    }
    headers = {'Content-Type': 'application/json'}

    try:
        resp = requests.get(url, params=params, headers=headers, timeout=60)

        if resp.status_code == 404:
            logger.warning(f"  {ticker}: 404 Not Found (delisted or invalid)")
            return pd.DataFrame()
        if resp.status_code == 429:
            logger.warning(f"  {ticker}: 429 Rate Limited - waiting 30s")
            time.sleep(30)
            resp = requests.get(url, params=params, headers=headers, timeout=60)

        resp.raise_for_status()
        data = resp.json()

        if not data:
            logger.warning(f"  {ticker}: empty response")
            return pd.DataFrame()

        df = pd.DataFrame(data)
        df['date'] = pd.to_datetime(df['date'].str[:10])
        df = df.set_index('date')
        if hasattr(df.index, 'tz') and df.index.tz is not None:
            df.index = df.index.tz_localize(None)
        df = df[~df.index.duplicated(keep='last')]
        df.sort_index(inplace=True)
        return df

    except Exception as e:
        logger.error(f"  {ticker}: fetch failed: {e}\n{traceback.format_exc()}")
        return pd.DataFrame()


def find_broken_parquets() -> list:
    """Return list of (ticker, path, row_count) for parquets with < MIN_ROWS rows."""
    broken = []
    for path in sorted(DATA_DIR.glob('*.parquet')):
        ticker_name = path.stem  # e.g. 'aapl', 'SPY'
        try:
            df = pd.read_parquet(path)
            rows = len(df)
            if rows < MIN_ROWS:
                broken.append((ticker_name, path, rows))
        except Exception as e:
            logger.warning(f"Cannot read {path.name}: {e}")
            broken.append((ticker_name, path, 0))
    return broken


def repair_ticker(ticker_name: str, path: Path) -> bool:
    """
    Re-fetch full history for a ticker and overwrite its parquet.
    Returns True if repaired successfully.
    """
    # Tiingo expects uppercase tickers
    ticker_upper = ticker_name.upper()
    logger.info(f"  Repairing {ticker_upper} ...")

    df_new = fetch_full_history(ticker_upper)

    if df_new.empty or len(df_new) < MIN_ROWS:
        logger.warning(f"  {ticker_upper}: only got {len(df_new)} rows after repair - skipping write")
        return False

    # If existing parquet has more rows somehow, keep the longer one
    if path.exists():
        try:
            df_existing = pd.read_parquet(path)
            if 'date' in df_existing.columns:
                df_existing['date'] = pd.to_datetime(df_existing['date'])
                df_existing = df_existing.set_index('date')
            if hasattr(df_existing.index, 'tz') and df_existing.index.tz is not None:
                df_existing.index = df_existing.index.tz_localize(None)
            if len(df_existing) > len(df_new):
                logger.info(f"  {ticker_upper}: existing has more rows ({len(df_existing)}) than fetched ({len(df_new)}), merging")
                df_new = pd.concat([df_existing, df_new])
                df_new = df_new[~df_new.index.duplicated(keep='last')]
                df_new.sort_index(inplace=True)
        except Exception:
            pass  # just use fresh data

    df_new.to_parquet(path)
    logger.info(f"  {ticker_upper}: repaired -> {len(df_new)} rows saved to {path.name}")
    return True


def main():
    if not TIINGO_KEY:
        logger.error("TIINGO_API_KEY not found in .env - aborting")
        sys.exit(1)

    logger.info("=" * 70)
    logger.info("PARQUET REPAIR TOOL")
    logger.info(f"Data dir : {DATA_DIR}")
    logger.info(f"Min rows : {MIN_ROWS}")
    logger.info(f"Tiingo key: ...{TIINGO_KEY[-4:]}")
    logger.info("=" * 70)

    broken = find_broken_parquets()
    logger.info(f"Found {len(broken)} parquets with < {MIN_ROWS} rows")

    if not broken:
        logger.info("Nothing to repair. All parquets healthy.")
        sys.exit(0)

    for ticker_name, path, rows in broken:
        logger.info(f"[{ticker_name}] current rows={rows}")

    logger.info("")
    logger.info("Starting repair...")

    repaired   = []
    failed     = []
    skipped    = []

    for i, (ticker_name, path, rows) in enumerate(broken):
        ticker_upper = ticker_name.upper()
        logger.info(f"[{i+1}/{len(broken)}] {ticker_upper} ({rows} rows)")

        ok = repair_ticker(ticker_name, path)
        if ok:
            repaired.append(ticker_upper)
        else:
            failed.append(ticker_upper)

        # Rate limit
        time.sleep(RATE_LIMIT_S)

    logger.info("")
    logger.info("=" * 70)
    logger.info("REPAIR COMPLETE")
    logger.info(f"  Repaired : {len(repaired)}")
    logger.info(f"  Failed   : {len(failed)}")
    if repaired:
        logger.info(f"  Success  : {repaired}")
    if failed:
        logger.warning(f"  Failed   : {failed}")
    logger.info(f"Log written to: {log_path}")
    logger.info("=" * 70)

    # Exit 0 even if some failed - they may be delisted tickers
    sys.exit(0)


if __name__ == '__main__':
    main()
