import argparse
import hashlib
import json
import logging
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.backtest_engine import price_filename

logger = logging.getLogger(__name__)


def digest_file(path):
    digest = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b''):
            digest.update(chunk)
    return digest.hexdigest()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--snapshot', required=True, type=Path)
    parser.add_argument('--report', required=True, type=Path)
    args = parser.parse_args()
    logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
    snapshot = args.snapshot.resolve()
    manifest_path = snapshot / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    records = {ticker: record for ticker, record in manifest['records'].items()
               if record.get('status') == 'ok'}
    mismatches, verified, aggregate = [], 0, hashlib.sha256()
    for ticker, record in sorted(records.items()):
        path = snapshot / 'prices' / price_filename(ticker)
        actual = digest_file(path) if path.is_file() else None
        if not actual or actual != record.get('sha256'):
            mismatches.append({'ticker': ticker, 'expected': record.get('sha256'),
                               'actual': actual})
        else:
            verified += 1
        aggregate.update(f'{ticker}:{actual}\n'.encode())
        if (verified + len(mismatches)) % 1000 == 0:
            logger.info('verified=%d mismatches=%d', verified, len(mismatches))
    report = {'snapshot': str(snapshot), 'manifest_sha256': digest_file(manifest_path),
              'declared_universe_count': manifest.get('universe_count'),
              'successful_records': len(records), 'verified': verified,
              'aggregate_price_sha256': aggregate.hexdigest(), 'mismatches': mismatches,
              'declared_count_matches': manifest.get('universe_count') == len(records)}
    target = args.report.resolve()
    if not target.parent.is_dir():
        parser.error('report parent directory must already exist')
    if target.exists():
        parser.error('report already exists; use a new filename')
    target.write_text(json.dumps(report, indent=2), encoding='utf-8')
    logger.info('verified=%d/%d mismatches=%d report=%s', verified, len(records),
                len(mismatches), target)
    return 1 if mismatches else 0


if __name__ == '__main__':
    sys.exit(main())
