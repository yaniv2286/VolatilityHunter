#!/usr/bin/env python3
import pandas as pd

df = pd.read_parquet('data/mnkd.parquet')
print('Column names:', df.columns.tolist())
print('DataFrame shape:', df.shape)
print('Last row:')
print(df.iloc[-1])
print('Last row close value:', df.iloc[-1]['close'])
