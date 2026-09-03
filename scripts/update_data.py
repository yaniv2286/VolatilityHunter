#!/usr/bin/env python3
"""
Update market data using the Tiingo Professional API.
Runs before the daily trading loop and is the ONLY place that writes EOD bars to parquets.
"""

import os
import sys
import time
import logging
from pathlib import Path
from datetime import datetime

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from src.smart_data_loader_factory import get_data_loader

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger('update_data')

TICKERS_FILE = ROOT / 'tickers.txt'


def load_tickers() -> list:
    try:
        lines = TICKERS_FILE.read_text(encoding='utf-8').splitlines()
        return [t.strip().upper() for t in lines if t.strip()]
    except Exception as e:
        logger.error(f'Failed to load {TICKERS_FILE}: {e}')
        return []


def main() -> int:
    logger.info('=' * 60)
    logger.info('VolatilityHunter EOD Data Update')
    logger.info('=' * 60)

    tickers = load_tickers()
    if not tickers:
        logger.error('No tickers loaded - aborting')
        return 1

    # Ensure SPY is present for the regime filter.
    universe = list(dict.fromkeys(tickers + ['SPY']))
    logger.info(f'Updating EOD data for {len(universe)} tickers')

    loader = get_data_loader()

    # 1. Last-7-days EOD update for the full universe (fast incremental refresh).
    result = loader.update_all_stocks_eod(universe)
    if not result.get('success'):
        logger.error(f'EOD update failed or incomplete: {result}')
        return 1
    logger.info(f'EOD update: {result["updated"]}/{result["total"]} tickers updated')

    # 2. Refresh the sector map once a day.
    logger.info('Refreshing sector map from Tiingo fundamentals...')
    sector_count = loader.update_sector_map(universe)
    logger.info(f'Sector map: {sector_count} real sectors mapped')

    logger.info('=' * 60)
    logger.info('EOD data update complete')
    logger.info('=' * 60)
    return 0


if __name__ == '__main__':
    sys.exit(main())
