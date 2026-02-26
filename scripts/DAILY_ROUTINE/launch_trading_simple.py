#!/usr/bin/env python3
"""
Simple VolatilityHunter Trading Launcher
Uses subprocess to avoid import issues
"""

import subprocess
import sys
import os
from pathlib import Path

def main():
    """Launch the trading system using subprocess"""
    print("🚀 Launching VolatilityHunter Trading System...")
    
    # Change to project root directory
    project_root = Path(__file__).parent.parent.parent  # Go up from DAILY_ROUTINE -> scripts -> project root
    os.chdir(project_root)
    
    print(f"📁 Changed to directory: {project_root}")
    
    # Run the main agent system using subprocess
    try:
        # Use python -m to run as a module
        cmd = [sys.executable, "-m", "src.main_agent_system"]
        print(f"🚀 Running command: {' '.join(cmd)}")
        
        # Start the process
        process = subprocess.Popen(cmd, 
                                  stdout=subprocess.PIPE, 
                                  stderr=subprocess.PIPE, 
                                  text=True,
                                  bufsize=1, 
                                  universal_newlines=True)
        
        # Print output in real-time
        while True:
            output = process.stdout.readline()
            if output == '' and process.poll() is not None:
                break
            if output:
                print(output.strip())
        
        # Get return code
        return_code = process.poll()
        
        if return_code == 0:
            print("✅ VolatilityHunter trading system launched successfully!")
        else:
            print(f"❌ Trading system failed with return code: {return_code}")
            
            # Print any error output
            error_output = process.stderr.read()
            if error_output:
                print(f"Error output: {error_output}")
                
        return return_code
        
    except Exception as e:
        print(f"❌ Error launching trading system: {e}")
        return 1

if __name__ == "__main__":
    exit(main())
