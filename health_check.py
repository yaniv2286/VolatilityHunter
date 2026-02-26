#!/usr/bin/env python3
"""
VolatilityHunter Health Check
Validates system health before trading
"""

import sys
import os
import asyncio
from datetime import datetime

def check_environment():
    """Check environment variables"""
    try:
        from dotenv import load_dotenv
        load_dotenv()
        
        required_vars = ['EMAIL_SENDER', 'EMAIL_PASSWORD']
        missing_vars = []
        
        for var in required_vars:
            if not os.getenv(var):
                missing_vars.append(var)
        
        if missing_vars:
            print(f"❌ Missing environment variables: {missing_vars}")
            return False
        
        print("✅ Environment variables OK")
        return True
    except Exception as e:
        print(f"❌ Environment check failed: {e}")
        return False

def check_data_files():
    """Check essential data files"""
    try:
        # Check tickers.txt
        if not os.path.exists('tickers.txt'):
            print("❌ tickers.txt not found")
            return False
        
        # Check data directory
        if not os.path.exists('data'):
            print("❌ data directory not found")
            return False
        
        # Check config directory
        if not os.path.exists('config'):
            print("❌ config directory not found")
            return False
        
        print("✅ Data files OK")
        return True
    except Exception as e:
        print(f"❌ Data files check failed: {e}")
        return False

def check_python_modules():
    """Check essential Python modules"""
    try:
        import pandas as pd
        import numpy as np
        print("✅ Python modules OK")
        return True
    except ImportError as e:
        print(f"❌ Missing Python module: {e}")
        return False

async def main():
    """Run health check"""
    try:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] Starting VolatilityHunter Health Check...")
        print("=" * 50)
        
        checks = [
            ("Environment", check_environment),
            ("Data Files", check_data_files),
            ("Python Modules", check_python_modules),
        ]
        
        all_passed = True
        for name, check_func in checks:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Checking {name}...")
            if not check_func():
                all_passed = False
        
        print("=" * 50)
        if all_passed:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ✅ Health Check PASSED")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] System is ready for trading")
            return 0
        else:
            print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Health Check FAILED")
            print(f"[{datetime.now().strftime('%H:%M:%S')}] System not ready for trading")
            return 1
            
    except Exception as e:
        print(f"[{datetime.now().strftime('%H:%M:%S')}] ❌ Health Check ERROR: {e}")
        return 1

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
