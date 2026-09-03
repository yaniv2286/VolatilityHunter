#!/usr/bin/env python3
"""
Fallback sector-map builder using the public adanos free-ticker-database CSV.
Downloads the CSV once, filters for US stocks in the local universe, and updates
sector_map.json. This is a metadata-only source; no price data is used.
"""

import os
import sys
import json
import requests
import pandas as pd
from pathlib import Path
from io import StringIO

ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

CSV_URL = 'https://raw.githubusercontent.com/adanos-software/free-ticker-database/main/data/tickers.csv'
TICKERS_FILE = ROOT / 'tickers.txt'
SECTOR_MAP_FILE = ROOT / 'data' / 'sector_map.json'


def load_tickers():
    return [t.strip().upper() for t in TICKERS_FILE.read_text().splitlines() if t.strip()]


def main() -> int:
    print('=' * 70)
    print('Updating sector_map.json from public ticker reference CSV')
    print('=' * 70)

    tickers = set(load_tickers())
    if not tickers:
        print('No tickers loaded')
        return 1

    existing = {}
    if SECTOR_MAP_FILE.exists():
        try:
            existing = json.loads(SECTOR_MAP_FILE.read_text(encoding='utf-8'))
        except Exception as e:
            print(f'Warning: could not load existing sector_map.json: {e}')

    print(f'Downloading {CSV_URL} ...')
    try:
        resp = requests.get(CSV_URL, timeout=120)
        resp.raise_for_status()
    except Exception as e:
        print(f'Failed to download CSV: {e}')
        return 1

    df = pd.read_csv(StringIO(resp.text), low_memory=False)
    print(f'CSV loaded: {len(df)} rows')

    # Keep only US stocks in our universe.
    df['ticker'] = df['ticker'].astype(str).str.upper()
    mask = (
        df['ticker'].isin(tickers) &
        (df.get('country_code') == 'US') &
        (df.get('asset_type') == 'Stock')
    )
    df = df[mask]
    print(f'Matched {len(df)} US stocks in universe')

    updated = 0
    for _, row in df.iterrows():
        t = row['ticker']
        sector = str(row.get('stock_sector', '')).strip()
        if not sector or sector.lower() in ('nan', 'none', ''):
            continue
        existing[t] = {
            'name': str(row.get('name', t)),
            'sector': sector,
            'industry': str(row.get('stock_sector', '')),  # no industry column; reuse sector
            'exchange': str(row.get('exchange', existing.get(t, {}).get('exchange', 'Unknown'))),
        }
        if t in existing and existing[t].get('sector') and existing[t]['sector'] != 'Unknown':
            updated += 1

    with open(SECTOR_MAP_FILE, 'w', encoding='utf-8') as f:
        json.dump(existing, f, indent=2)

    real = sum(1 for v in existing.values()
               if v.get('sector') and v['sector'] != 'Unknown' and 'not available' not in str(v['sector']).lower())
    print(f'Sector map saved: {real}/{len(existing)} real sectors ({updated} updated from CSV)')
    print('=' * 70)
    return 0


if __name__ == '__main__':
    sys.exit(main())
