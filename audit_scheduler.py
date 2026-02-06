#!/usr/bin/env python3
"""
VolatilityHunter Audit Scheduler
Automated audit scheduling and reporting
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
from src.notifications import log_info, log_error

def run_audit():
    """Run the comprehensive audit"""
    try:
        log_info("Starting VolatilityHunter Full Deep Dive Audit...")
        
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        audit_script = os.path.join(script_dir, "volatilityhunter_audit.py")
        
        # Run the audit
        result = subprocess.run(
            [sys.executable, audit_script],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=1800  # 30 minutes timeout
        )
        
        if result.returncode == 0:
            log_info("VolatilityHunter audit completed successfully")
            print("[OK] VolatilityHunter audit completed successfully")
            if result.stdout:
                print("Audit Summary:")
                print(result.stdout[-1000:])  # Last 1000 characters
        else:
            log_error(f"VolatilityHunter audit failed with exit code {result.returncode}")
            print("[ERROR] VolatilityHunter audit failed")
            if result.stderr:
                print("Error:", result.stderr[-500:])
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        log_error("VolatilityHunter audit timed out after 30 minutes")
        print("[ERROR] VolatilityHunter audit timed out")
        return False
    except Exception as e:
        log_error(f"Audit execution failed: {e}")
        print(f"[ERROR] Audit execution failed: {e}")
        return False

def weekly_audit():
    """Run weekly comprehensive audit"""
    print("=" * 60)
    print("WEEKLY VOLATILITYHUNTER AUDIT")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = run_audit()
    
    if success:
        print("✅ Weekly audit completed successfully")
    else:
        print("❌ Weekly audit failed")
    
    print("=" * 60)

def monthly_audit():
    """Run monthly comprehensive audit with enhanced reporting"""
    print("=" * 60)
    print("MONTHLY VOLATILITYHUNTER DEEP DIVE AUDIT")
    print("=" * 60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    
    success = run_audit()
    
    if success:
        print("✅ Monthly audit completed successfully")
        # Additional monthly reporting could be added here
    else:
        print("❌ Monthly audit failed")
    
    print("=" * 60)

def run_scheduler():
    """Run the audit scheduler"""
    print("VolatilityHunter Audit Scheduler Started")
    print("=" * 60)
    
    # Schedule audits
    # Weekly audit every Sunday at 3:00 AM
    schedule.every().sunday.at("03:00").do(weekly_audit)
    
    # Monthly audit on the 1st of each month at 2:00 AM
    schedule.every().month.do(monthly_audit)
    
    print("Scheduled Audits:")
    print("• Weekly: Every Sunday at 3:00 AM")
    print("• Monthly: 1st of each month at 2:00 AM")
    print("\nPress Ctrl+C to stop the scheduler")
    print("=" * 60)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")
        print("Final audit run...")
        run_audit()
        print("Scheduler shutdown complete")

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='VolatilityHunter Audit Scheduler')
    parser.add_argument('--weekly', action='store_true', help='Run weekly audit now')
    parser.add_argument('--monthly', action='store_true', help='Run monthly audit now')
    parser.add_argument('--scheduler', action='store_true', help='Run audit scheduler')
    parser.add_argument('--test', action='store_true', help='Test audit execution')
    
    args = parser.parse_args()
    
    if args.weekly:
        weekly_audit()
    elif args.monthly:
        monthly_audit()
    elif args.scheduler:
        run_scheduler()
    elif args.test:
        print("Testing audit execution...")
        success = run_audit()
        print(f"Test {'PASSED' if success else 'FAILED'}")
    else:
        print("Usage:")
        print("  python audit_scheduler.py --weekly     # Run weekly audit")
        print("  python audit_scheduler.py --monthly    # Run monthly audit")
        print("  python audit_scheduler.py --scheduler  # Run scheduler daemon")
        print("  python audit_scheduler.py --test      # Test audit execution")
