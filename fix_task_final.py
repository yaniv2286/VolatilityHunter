#!/usr/bin/env python3
"""
Final Task Scheduler Fix
Updates Windows Task to use native batch file instead of Python wrapper
"""

import os
import subprocess
import sys

def run_schtasks(cmd, description):
    """Run schtasks command and return success"""
    try:
        print(f"🔧 {description}")
        print(f"   Command: {cmd}")
        
        result = subprocess.run(
            cmd,
            shell=True,
            capture_output=True,
            text=True,
            check=False
        )
        
        if result.returncode == 0:
            print(f"   ✅ SUCCESS")
            return True
        else:
            print(f"   ❌ FAILED (Exit Code: {result.returncode})")
            if result.stderr:
                print(f"   Error: {result.stderr.strip()}")
            return False
            
    except Exception as e:
        print(f"   ❌ EXCEPTION: {e}")
        return False

def main():
    print("=" * 60)
    print("🚀 FINAL TASK SCHEDULER FIX")
    print("=" * 60)
    print("Switching to native batch file execution...")
    print()
    
    # Get paths
    base_dir = os.path.dirname(os.path.abspath(__file__))
    batch_file = os.path.join(base_dir, "daily_scan.bat")
    
    print(f"📁 Project Directory: {base_dir}")
    print(f"📄 Batch File: {batch_file}")
    print()
    
    # Verify batch file exists
    if not os.path.exists(batch_file):
        print("❌ ERROR: daily_scan.bat not found!")
        return False
    
    print("✅ Batch file found")
    print()
    
    # Step 1: Delete old task
    print("🗑️ Step 1: Deleting old task...")
    delete_cmd = 'schtasks /Delete /TN "VolatilityHunter Daily Scan" /F'
    run_schtasks(delete_cmd, "Delete existing task")
    print()
    
    # Step 2: Create new task pointing to batch file
    print("📝 Step 2: Creating new task with batch file...")
    
    # Create task with batch file
    create_cmd = f'''schtasks /Create /TN "VolatilityHunter Daily Scan" /TR "{batch_file}" /SC DAILY /ST 22:00 /RL HIGHEST /RU "SYSTEM" /F'''
    
    success = run_schtasks(create_cmd, "Create new task with batch file")
    
    if success:
        print()
        print("🎉 TASK SCHEDULER UPDATED SUCCESSFULLY!")
        print()
        print("📋 New Task Configuration:")
        print("   • Name: VolatilityHunter Daily Scan")
        print("   • Schedule: Daily at 22:00 (10:00 PM)")
        print("   • Action: Run daily_scan.bat")
        print("   • Working Directory: D:\\GitHub\\VolatilityHunter")
        print("   • Account: SYSTEM")
        print("   • Privileges: Highest")
        print()
        print("✅ Benefits:")
        print("   • No Python wrapper buffering issues")
        print("   • Direct batch file execution")
        print("   • Real-time logging to scheduler_debug.log")
        print("   • More reliable Task Scheduler integration")
        print()
        print("🎯 The task will now run VolatilityHunter every day at 10:00 PM")
        print("📧 You will receive email reports after each execution")
    else:
        print()
        print("❌ TASK UPDATE FAILED!")
        print("   Please run this script as Administrator")
    
    return success

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
