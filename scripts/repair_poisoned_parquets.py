#!/usr/bin/env python3
"""
One-shot repair: overwrite poisoned parquet rows (2026-04-29 -> today) with
completed Tiingo EOD bars.  The IEX intraday snapshots are removed/replaced.
"""

import os
import sys
import logging
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from src.smart_data_loader_factory import get_data_loader

logging.basicConfig(level=logging.INFO, format='%(asctime)s %(levelname)s %(message)s')
logger = logging.getLogger('repair_parquets')

TICKERS_FILE = ROOT / 'tickers.txt'
REPAIR_START = '2026-04-29'


def load_tickers():
    return [t.strip().upper() for t in TICKERS_FILE.read_text().splitlines() if t.strip()]


def main() -> int:
    logger.info('=' * 70)
    logger.info('PARQUET POISON REPAIR')
    logger.info(f'Replacing IEX-snapshot rows from {REPAIR_START} with EOD bars')
    logger.info('=' * 70)

    tickers = load_tickers()
    if not tickers:
        logger.error('No tickers found')
        return 1

    universe = list(dict.fromkeys(tickers + ['SPY']))
    logger.info(f'Loaded {len(universe)} tickers')

    loader = get_data_loader()
    result = loader.repair_parquet_range(universe, start_date=REPAIR_START)

    logger.info('=' * 70)
    logger.info(f'Repair complete: {result["updated"]}/{result["total"]} tickers repaired')
    if result.get('failed'):
        logger.warning(f'Failed tickers: {len(result["failed"])}')
        logger.warning(str(result['failed'][:20]))
    logger.info('=' * 70)
    return 0 if result.get('success') else 1


if __name__ == '__main__':
    sys.exit(main())
