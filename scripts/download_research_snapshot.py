"""Download a frozen, self-contained Tiingo price snapshot for research.

Fetches full-history EOD bars for a ticker universe into an isolated
directory under data/research/. NEVER reads or writes live data/*.parquet.

Resumable: per-ticker results are appended to progress.jsonl; re-running
skips tickers already recorded as 'ok' or 'no_data' for the same window.

Outputs:
  <out>/prices/<TICKER>.parquet   - date-indexed OHLCV + adjusted + div/split
  <out>/progress.jsonl           - one JSON record per completed ticker
  <out>/manifest.json            - run fingerprint, inputs, per-ticker summary

Usage:
  python scripts/download_research_snapshot.py \
      --out data/research/snapshot_1998_20261022 \
      --start 1998-01-01 --end 2026-10-22 [--limit 5] [--rate 4]
"""

import argparse
import hashlib
import json
import logging
import os
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
logger = logging.getLogger(__name__)

COLUMNS = ('open,high,low,close,volume,adjOpen,adjHigh,adjLow,adjClose,'
           'adjVolume,divCash,splitFactor')
PRICES_URL = 'https://api.tiingo.com/tiingo/daily/{ticker}/prices'
META_URL = 'https://api.tiingo.com/tiingo/daily/{ticker}'


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    h.update(path.read_bytes())
    return h.hexdigest()


def git_revision() -> str:
    try:
        return subprocess.run(
            ['git', 'rev-parse', 'HEAD'], cwd=ROOT,
            capture_output=True, text=True, timeout=10,
        ).stdout.strip()
    except Exception:
        logger.exception("git rev-parse failed")
        return 'unknown'


def load_tickers(path: Path) -> list:
    return list(dict.fromkeys(
        line.strip().upper()
        for line in path.read_text().splitlines()
        if line.strip() and not line.lstrip().startswith('#')
    ))


class SnapshotDownloader:
    def __init__(self, api_key: str, rate: float):
        self.session = requests.Session()
        self.session.headers.update({'Content-Type': 'application/json'})
        self.api_key = api_key
        self.min_interval = 1.0 / rate
        self._last_request = 0.0

    def _get(self, url: str, params: dict, timeout: int = 120):
        for attempt in range(5):
            wait = self.min_interval - (time.monotonic() - self._last_request)
            if wait > 0:
                time.sleep(wait)
            self._last_request = time.monotonic()
            try:
                resp = self.session.get(url, params=params, timeout=timeout)
            except Exception:
                logger.exception("request failed: %s", url)
                time.sleep(5 * (attempt + 1))
                continue
            if resp.status_code == 429:
                logger.warning("Tiingo 429 - backing off 60s")
                time.sleep(60)
                continue
            return resp
        return resp

    def fetch_prices(self, ticker: str, start: str, end: str):
        resp = self._get(PRICES_URL.format(ticker=ticker), {
            'startDate': start, 'endDate': end, 'columns': COLUMNS,
            'format': 'json', 'resampleFreq': 'daily', 'token': self.api_key,
        })
        if resp.status_code != 200:
            return resp.status_code, None
        try:
            rows = resp.json()
        except Exception:
            logger.exception("bad JSON for %s", ticker)
            return resp.status_code, None
        return resp.status_code, rows if rows else None

    def fetch_meta(self, ticker: str):
        resp = self._get(META_URL.format(ticker=ticker),
                         {'token': self.api_key}, timeout=30)
        if resp.status_code != 200:
            return None
        try:
            return resp.json()
        except Exception:
            logger.exception("bad meta JSON for %s", ticker)
            return None


def rows_to_frame(rows: list) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    df['date'] = pd.to_datetime(df['date']).dt.tz_localize(None).dt.normalize()
    df = df.set_index('date')
    for col in ('open', 'high', 'low', 'close', 'volume',
                'adjOpen', 'adjHigh', 'adjLow', 'adjClose', 'adjVolume',
                'divCash', 'splitFactor'):
        if col not in df.columns:
            df[col] = float('nan')
        else:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    for raw, adj in (('open', 'adjOpen'), ('high', 'adjHigh'),
                     ('low', 'adjLow'), ('close', 'adjClose'),
                     ('volume', 'adjVolume')):
        df[adj] = df[adj].fillna(df[raw])
    return df[~df.index.duplicated(keep='last')].sort_index()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--out', required=True, help='snapshot directory')
    parser.add_argument('--start', default='1998-01-01')
    parser.add_argument('--end', required=True, help='as-of date, e.g. 2026-10-22')
    parser.add_argument('--tickers', default=str(ROOT / 'tickers.txt'))
    parser.add_argument('--rate', type=float, default=4.0)
    parser.add_argument('--limit', type=int, default=0)
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    load_dotenv(ROOT / '.env')
    api_key = os.getenv('TIINGO_API_KEY') or os.getenv('TIINGO_KEY')
    if not api_key:
        logger.error('TIINGO_API_KEY not set')
        return 1

    out = Path(args.out)
    prices_dir = out / 'prices'
    prices_dir.mkdir(parents=True, exist_ok=True)
    progress_path = out / 'progress.jsonl'

    tickers = load_tickers(Path(args.tickers))
    if args.limit:
        tickers = tickers[:args.limit]

    done = {}
    if progress_path.exists():
        for line in progress_path.read_text().splitlines():
            if not line.strip():
                continue
            rec = json.loads(line)
            if rec.get('start') == args.start and rec.get('end') == args.end:
                done[rec['ticker']] = rec

    dl = SnapshotDownloader(api_key, args.rate)
    progress = progress_path.open('a', encoding='utf-8')
    records = dict(done)

    for i, ticker in enumerate(tickers, 1):
        if ticker in done:
            continue
        rec = {'ticker': ticker, 'start': args.start, 'end': args.end,
               'status': 'error', 'resolved_ticker': ticker}
        try:
            status, rows = dl.fetch_prices(ticker, args.start, args.end)
            resolved = ticker
            if rows is None:
                meta = dl.fetch_meta(ticker)
                if meta and meta.get('ticker') and meta['ticker'] != ticker:
                    resolved = meta['ticker']
                    status2, rows = dl.fetch_prices(
                        resolved, args.start, args.end)
                    if rows is not None:
                        status = status2
                        rec['symbol_redirect'] = resolved
                rec['meta'] = meta
            rec['resolved_ticker'] = resolved
            if rows is None:
                rec['status'] = 'no_data'
                rec['http_status'] = status
            else:
                df = rows_to_frame(rows)
                # Windows reserved device names need a suffix (con.parquet
                # is unwritable). Keep in sync with backtest_engine.
                _name = ticker.lower()
                if _name in {'con', 'prn', 'aux', 'nul'} | \
                        {f'com{i}' for i in range(1, 10)} | \
                        {f'lpt{i}' for i in range(1, 10)}:
                    _name += '_'
                path = prices_dir / f'{_name}.parquet'
                df.to_parquet(path)
                rec.update({
                    'status': 'ok', 'rows': len(df),
                    'first_date': str(df.index.min().date()),
                    'last_date': str(df.index.max().date()),
                    'sha256': sha256_file(path),
                })
        except Exception:
            logger.exception("ticker %s failed", ticker)
        records[ticker] = rec
        progress.write(json.dumps(rec) + '\n')
        progress.flush()
        if i % 100 == 0:
            logger.info('%s/%s tickers processed', i, len(tickers))
    progress.close()

    counts = {}
    for rec in records.values():
        counts[rec['status']] = counts.get(rec['status'], 0) + 1

    manifest = {
        'created_utc': datetime.now(timezone.utc).isoformat(),
        'window': {'start': args.start, 'end': args.end},
        'code_revision': git_revision(),
        'inputs': {
            'tickers_file': args.tickers,
            'tickers_sha256': sha256_file(Path(args.tickers)),
        },
        'universe_count': len(tickers),
        'status_counts': counts,
        'records': records,
        'limitations': [
            'Current ticker list is not a historical universe; delisted '
            'names not in tickers.txt are absent (survivorship bias).',
            'Symbol redirects resolved via live meta endpoint, not '
            'point-in-time identity.',
        ],
    }
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    logger.info('Done. status_counts=%s', counts)
    return 0


if __name__ == '__main__':
    sys.exit(main())
