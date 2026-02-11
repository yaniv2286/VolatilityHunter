#!/usr/bin/env python3
import pandas as pd

df = pd.read_parquet('data/mnkd.parquet')
print('MNKD Data Summary:')
print(f'Total rows: {len(df)}')
print(f'Date range: {df["date"].min()} to {df["date"].max()}')
print(f'Latest 3 rows:')
print(df.tail(3)[['date', 'close']].to_string())
