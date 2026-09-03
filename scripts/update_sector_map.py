#!/usr/bin/env python3
"""
Update data/sector_map.json from Tiingo fundamentals/meta.
Run after major universe changes or when sector_map.json is stale/Unknown.
"""

import os
import sys
from pathlib import Path

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

from dotenv import load_dotenv
load_dotenv(ROOT / '.env')

from src.smart_data_loader_factory import get_data_loader

TICKERS_FILE = ROOT / 'tickers.txt'


def load_tickers():
    return [t.strip().upper() for t in TICKERS_FILE.read_text().splitlines() if t.strip()]


def main() -> int:
    tickers = load_tickers()
    if not tickers:
        print('No tickers loaded')
        return 1
    universe = list(dict.fromkeys(tickers + ['SPY']))
    loader = get_data_loader()
    count = loader.update_sector_map(universe)
    print(f'Sector map updated: {count} real sectors for {len(universe)} tickers')
    return 0


if __name__ == '__main__':
    sys.exit(main())
