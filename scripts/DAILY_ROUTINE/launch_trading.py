#!/usr/bin/env python3
"""
VolatilityHunter Trading Launcher
Called by PowerShell script to launch the trading system
"""

import sys
import os
import asyncio
from pathlib import Path

# Add current directory and src to Python path
current_dir = Path.cwd()
sys.path.insert(0, str(current_dir))
sys.path.insert(0, str(current_dir / 'src'))

# Debug: Print current path and sys.path
print(f"Current directory: {current_dir}")
print(f"Python path: {sys.path[:3]}")

try:
    # Use main_unified.py which handles imports correctly
    import main_unified
    
    print("🚀 Launching VolatilityHunter using main_unified.py...")
    # Set up command line arguments for live mode
    sys.argv = ['main_unified.py', '--mode', 'live']
    
    # This will run the main system
    main_unified.main()
    
except ImportError as e:
    print(f"❌ Import Error: {e}")
    print(f"Current directory: {current_dir}")
    print(f"Python path: {sys.path}")
    print("Make sure you're in the correct directory and the virtual environment is activated")
    sys.exit(1)
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)
