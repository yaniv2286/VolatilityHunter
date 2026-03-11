"""Check if BASE currency exists for NetLiquidation"""
import os
import sys
from pathlib import Path

ROOT = Path(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, str(ROOT))

from ib_insync import IB

ib = IB()
ib.connect('127.0.0.1', 7497, clientId=998)

account_values = ib.accountValues()

print("NetLiquidation values:")
for value in account_values:
    if value.tag == 'NetLiquidation':
        print(f"  Currency: {value.currency}, Value: {value.value}")

print("\nAll BASE currency values:")
for value in account_values:
    if value.currency == 'BASE':
        print(f"  {value.tag}: {value.value}")

ib.disconnect()
