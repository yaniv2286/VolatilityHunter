#!/usr/bin/env python3
"""
Log Monitoring Verification Script
Ensures we actively track logs during terminal operations
"""

import os
import time
import subprocess
from datetime import datetime

def monitor_log_file(log_path, keywords_to_watch):
    """
    Monitor log file for critical keywords
    """
    print(f"🔍 Monitoring: {log_path}")
    print(f"🚨 Watching for: {keywords_to_watch}")
    
    try:
        with open(log_path, 'r') as f:
            # Go to end of file
            f.seek(0, 2)
            
            while True:
                line = f.readline()
                if line:
                    for keyword in keywords_to_watch:
                        if keyword.lower() in line.lower():
                            print(f"🚨 DETECTED: {keyword.strip()}")
                            print(f"   Line: {line.strip()}")
                            return True
                else:
                    time.sleep(0.1)
                    
    except FileNotFoundError:
        print(f"❌ Log file not found: {log_path}")
        return False

def run_command_with_monitoring(command, log_file):
    """
    Run command while monitoring its log output
    """
    print(f"🚀 Executing: {command}")
    print(f"📋 Log file: {log_file}")
    
    # Start the command
    process = subprocess.Popen(command, shell=True, 
                              stdout=subprocess.PIPE, 
                              stderr=subprocess.STDOUT,
                              universal_newlines=True)
    
    # Critical keywords to watch for
    critical_keywords = [
        'ERROR',
        'CRITICAL',
        'FAILED',
        'Exception',
        'Traceback',
        'Permission denied',
        'Connection refused',
        'Timeout',
        '403',
        '404',
        '500'
    ]
    
    # Monitor the log file
    if monitor_log_file(log_file, critical_keywords):
        print("🛑 CRITICAL ISSUE DETECTED - Stopping execution")
        process.terminate()
        return False
    
    # Wait for completion
    stdout, stderr = process.communicate()
    
    if process.returncode == 0:
        print("✅ Command completed successfully")
        return True
    else:
        print(f"❌ Command failed with exit code: {process.returncode}")
        return False

if __name__ == "__main__":
    print("🔍 Log Monitoring Verification")
    print("=" * 50)
    
    # Test with trading log
    trading_log = "logs/trading_2026-03-24.log"
    
    # Simulate monitoring
    print("Testing log monitoring...")
    
    if os.path.exists(trading_log):
        print(f"✅ Found log file: {trading_log}")
        
        # Check for recent errors (with proper encoding)
        try:
            with open(trading_log, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()[-20:]  # Last 20 lines
        except Exception as e:
            print(f"❌ Error reading log file: {e}")
            exit(1)
            
        error_count = 0
        for line in lines:
            if any(keyword in line for keyword in ['ERROR', 'CRITICAL', 'FAILED']):
                error_count += 1
                print(f"🚨 Found: {line.strip()}")
        
        if error_count == 0:
            print("✅ No recent errors found")
        else:
            print(f"❌ Found {error_count} recent errors")
    else:
        print(f"❌ Log file not found: {trading_log}")
    
    print("\n🎯 LOG MONITORING PROTOCOL:")
    print("1. Always monitor terminal output during execution")
    print("2. Stop immediately on ERROR/CRITICAL/FAILED")
    print("3. Check exit codes before proceeding")
    print("4. Review logs before re-running commands")
    print("5. Document issues before attempting fixes")
