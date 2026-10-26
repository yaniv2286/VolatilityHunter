"""Audit the local ticker universe against Tiingo's supported-tickers catalog.

Downloads https://apimedia.tiingo.com/docs/tiingo/daily/supported_tickers.zip,
inventories local data/*.parquet coverage, probes the meta endpoint for
conflicts, and writes a timestamped evidence bundle under data/research/:

  coverage_<UTC ts>/supported_tickers.zip   - raw catalog download
  coverage_<UTC ts>/local_inventory.json    - per-file local coverage + sha256
  coverage_<UTC ts>/coverage_report.json    - findings, catalog summary, gates
  coverage_<UTC ts>/manifest.json           - run fingerprint + input hashes

Statuses per local ticker:
  ok                                  - coverage consistent with catalog
  provider_also_ends_early_reason_unknown
                                      - provider catalog also ends early
                                        (probable delisting, not a gap)
  provider_local_date_conflict        - local end date != catalog end date
  provider_coverage_unknown           - not present in catalog
  provider_symbol_redirect_requires_review
                                      - meta endpoint returns a different
                                        ticker (symbol was recycled/renamed)

Exit 0 on completion (including 'complete' status), 1 on failure.
"""

import argparse
import hashlib
import io
import json
import logging
import os
import sys
import time
import zipfile
from datetime import datetime, timezone
from pathlib import Path

import pandas as pd
import pyarrow.parquet as pq
import requests
from dotenv import load_dotenv

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
CATALOG_URL = ("https://apimedia.tiingo.com/docs/tiingo/daily/"
               "supported_tickers.zip")
META_URL = "https://api.tiingo.com/tiingo/daily/{ticker}"
US_EXCHANGES = {'NYSE', 'NASDAQ', 'AMEX', 'NYSE ARCA', 'BATS',
                'NYSE MKT', 'NYSE American'}
logger = logging.getLogger(__name__)


def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest()


def local_inventory(root: Path) -> dict:
    inv = {}
    for path in sorted((root / 'data').glob('*.parquet')):
        ticker = path.stem.upper()
        try:
            pf = pq.ParquetFile(path)
            names = pf.schema_arrow.names
            date_col = 'date' if 'date' in names else None
            cols = [c for c in ([date_col] if date_col else names[:1])]
            df = pf.read(columns=cols).to_pandas()
            if date_col:
                dates = pd.DatetimeIndex(pd.to_datetime(df[date_col]))
            else:
                dates = pd.DatetimeIndex(pd.to_datetime(df.index))
            if dates.tz is not None:
                dates = dates.tz_localize(None)
            inv[ticker] = {
                'ticker': ticker,
                'start': str(dates.min().date()),
                'end': str(dates.max().date()),
                'rows': int(len(dates)),
                'sha256': sha256_file(path),
                'bytes': path.stat().st_size,
                'mtime_ns': path.stat().st_mtime_ns,
            }
        except Exception:
            logger.exception("cannot inventory %s", path)
    return inv


def fetch_catalog(session, timeout=120):
    r = session.get(CATALOG_URL, timeout=timeout)
    r.raise_for_status()
    return r.content


def probe_meta(session, ticker, api_key):
    try:
        r = session.get(META_URL.format(ticker=ticker),
                        params={'token': api_key}, timeout=30)
        return {'http_status': r.status_code,
                'data': r.json() if r.status_code == 200 else None}
    except Exception:
        logger.exception("meta probe failed %s", ticker)
        return {'http_status': None, 'data': None}


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--as-of', default=None,
                    help='cutoff date (default: latest common local end)')
    ap.add_argument('--out', default=None,
                    help='output dir (default data/research/coverage_<ts>)')
    args = ap.parse_args()

    logging.basicConfig(level=logging.INFO,
                        format='%(asctime)s %(levelname)s %(message)s')
    load_dotenv(ROOT / '.env')
    api_key = os.getenv('TIINGO_API_KEY') or os.getenv('TIINGO_KEY')
    session = requests.Session()

    ts = datetime.now(timezone.utc).strftime('%Y%m%dT%H%M%S%fZ')
    out = Path(args.out) if args.out else \
        ROOT / 'data' / 'research' / f'coverage_{ts}'
    out.mkdir(parents=True, exist_ok=True)

    manifest = {
        'started_utc': datetime.now(timezone.utc).isoformat(),
        'as_of': args.as_of,
        'status': 'failed',
        'inputs': {
            'tickers.txt': sha256_file(ROOT / 'tickers.txt'),
            'scripts/audit_backtest_data.py':
                sha256_file(ROOT / 'scripts' / 'audit_backtest_data.py'),
            'scripts/audit_tiingo_universe.py':
                sha256_file(ROOT / 'scripts' / 'audit_tiingo_universe.py'),
        },
    }

    logger.info('downloading supported-tickers catalog')
    cat_bytes = fetch_catalog(session)
    (out / 'supported_tickers.zip').write_bytes(cat_bytes)
    cat = pd.read_csv(io.BytesIO(cat_bytes))
    cat['endDate'] = pd.to_datetime(cat['endDate'])

    logger.info('building local inventory')
    inv = local_inventory(ROOT)
    (out / 'local_inventory.json').write_text(json.dumps(inv, indent=2))

    common_end = pd.Series([v['end'] for v in inv.values()]).mode()[0]
    as_of = args.as_of or common_end
    manifest['as_of'] = as_of
    logger.info('as_of=%s (common local end %s)', as_of, common_end)

    cat_by_ticker = {}
    for row in cat.itertuples():
        cat_by_ticker.setdefault(row.ticker.upper() if
                                 isinstance(row.ticker, str)
                                 else row.ticker, []).append({
            'ticker': row.ticker, 'exchange': row.exchange,
            'assetType': row.assetType, 'priceCurrency': row.priceCurrency,
            'startDate': str(row.startDate)[:10] if pd.notna(row.startDate)
            else None,
            'endDate': str(row.endDate)[:10] if pd.notna(row.endDate)
            else None,
        })

    findings = []
    for ticker, loc in inv.items():
        matches = cat_by_ticker.get(ticker, [])
        status = 'ok'
        meta = None
        cat_ends = {m['endDate'] for m in matches if m['endDate']}
        if not matches:
            status = 'provider_coverage_unknown'
        elif loc['end'] not in cat_ends:
            max_cat = max(cat_ends)
            if max_cat < as_of and loc['end'] < as_of:
                status = 'provider_also_ends_early_reason_unknown'
            else:
                status = 'provider_local_date_conflict'
        if status != 'ok' and api_key:
            meta = probe_meta(session, ticker, api_key)
            data = (meta or {}).get('data') or {}
            returned = data.get('ticker')
            if returned and returned != ticker:
                status = 'provider_symbol_redirect_requires_review'
            time.sleep(0.3)
        if status != 'ok':
            findings.append({
                'ticker': ticker, 'local': loc,
                'catalog_matches': matches,
                'metadata': meta or {},
                'status': status,
                'provider_symbol_matches_request':
                    (meta or {}).get('data', {}).get('ticker') == ticker,
                'delisting_confirmed': False,
            })
        if len(findings) and len(findings) % 20 == 0:
            logger.info('%d findings so far', len(findings))

    us = cat[(cat.priceCurrency == 'USD') & (cat.assetType == 'Stock')]
    us_ex = us[us.exchange.isin(US_EXCHANGES)]
    ended = us_ex[us_ex.endDate < pd.Timestamp(as_of)]
    counts = (ended.endDate.dt.year.value_counts().sort_index()
              .to_dict())
    local_set = set(inv)
    summary = {
        'rows': int(len(cat)),
        'usd_stock_rows': int(len(us)),
        'usd_stock_rows_ending_before_cutoff': int(len(ended)),
        'early_ending_usd_symbols_outside_current_universe':
            int((~ended.ticker.str.upper().isin(local_set)).sum()),
        'outside_universe_examples':
            sorted(ended[~ended.ticker.str.upper().isin(local_set)]
                   .ticker.tolist())[:25],
        'usd_stock_end_year_counts': {int(k): int(v)
                                      for k, v in counts.items()},
        'current_universe_symbols_with_pre2000_provider_history': int(
            (us_ex[us_ex.ticker.str.upper().isin(local_set)]
             .startDate < '2000-01-01').sum()),
        'duplicate_symbol_keys': int(len(cat) -
                                     cat.ticker.nunique()),
    }

    report = {
        'as_of': as_of,
        'findings': findings,
        'finding_counts': pd.Series([f['status'] for f in findings])
            .value_counts().to_dict(),
        'catalog_summary': summary,
        'historical_universe_validated': False,
        'investment_conclusions_allowed': False,
        'limitations': [
            'Catalog start/end dates do not prove listing/delisting dates.',
            'Current metadata does not resolve historical ticker recycling.',
            'USD Stock includes instruments not necessarily eligible '
            'common shares.',
            'The current ticker list is not a historical universe.',
            'Probe observations were retrieved now, not at historical '
            'decision times.',
            'This is an inventory snapshot, not a frozen price dataset.',
        ],
    }
    (out / 'coverage_report.json').write_text(json.dumps(
        report, indent=2, default=str))

    manifest['status'] = 'complete'
    manifest['completed_utc'] = datetime.now(timezone.utc).isoformat()
    manifest['artifacts'] = {
        'local_inventory.json': sha256_file(out / 'local_inventory.json'),
        'supported_tickers.zip': sha256_file(out / 'supported_tickers.zip'),
        'coverage_report.json': sha256_file(out / 'coverage_report.json'),
    }
    manifest['historical_universe_validated'] = False
    (out / 'manifest.json').write_text(json.dumps(manifest, indent=2))
    logger.info('complete: %d findings -> %s', len(findings), out)
    return 0


if __name__ == '__main__':
    sys.exit(main())
