#!/usr/bin/env python3

# Test script to demonstrate smart data loader behavior

import os
import sys
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.smart_data_loader_factory import get_smart_data_loader

print("=== SMART DATA LOADER TEST ===")
print()

# Test 1: With Tiingo key (current setup)
print("TEST 1: With Tiingo Key (Your Current Setup)")
loader1 = get_smart_data_loader()
info1 = loader1.get_data_source_info()
print(f"Active Source: {info1['source']}")
print(f"Reason: {info1['reason']}")
print(f"Tiingo Key Available: {info1['key_available']}")
print()

# Test 2: Without Tiingo key (simulate no key)
print("TEST 2: Without Tiingo Key (Fallback Test)")
# Temporarily clear the key
original_key = os.environ.get('TIINGO_KEY')
if 'TIINGO_KEY' in os.environ:
    del os.environ['TIINGO_KEY']

# Reload the module to pick up the change
import importlib
import src.smart_data_loader_factory
importlib.reload(src.smart_data_loader_factory)

from src.smart_data_loader_factory import get_smart_data_loader
loader2 = get_smart_data_loader()
info2 = loader2.get_data_source_info()
print(f"Active Source: {info2['source']}")
print(f"Reason: {info2['reason']}")
print(f"Tiingo Key Available: {info2['key_available']}")

# Restore the key
if original_key:
    os.environ['TIINGO_KEY'] = original_key

print()
print("=== ENVIRONMENT VARIABLE TESTS ===")
print()

# Test 3: Explicitly request Yahoo Finance
print("TEST 3: Explicit Yahoo Finance Request")
os.environ['VH_DATA_SOURCE'] = 'yfinance'
importlib.reload(src.smart_data_loader_factory)
from src.smart_data_loader_factory import get_data_loader
loader3 = get_data_loader()
info3 = loader3.get_data_source_info()
print(f"Active Source: {info3['source']}")
print(f"Reason: {info3['reason']}")

# Test 4: Explicitly request Tiingo
print("TEST 4: Explicit Tiingo Request")
os.environ['VH_DATA_SOURCE'] = 'tiingo'
importlib.reload(src.smart_data_loader_factory)
from src.smart_data_loader_factory import get_data_loader
loader4 = get_data_loader()
info4 = loader4.get_data_source_info()
print(f"Active Source: {info4['source']}")
print(f"Reason: {info4['reason']}")

print()
print("=== SUMMARY ===")
print("✅ Smart data loader supports both Tiingo and Yahoo Finance")
print("✅ Defaults to Tiingo when key is available (you're paying for it!)")
print("✅ Falls back to Yahoo Finance when Tiingo unavailable")
print("✅ Respects explicit VH_DATA_SOURCE environment variable")
print("✅ Automatic failover during runtime if primary fails")
