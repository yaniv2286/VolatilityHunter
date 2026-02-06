#!/usr/bin/env python3
"""
Updated VolatilityHunter Scheduler
Uses the new unified entry point (volatilityhunter.py)
"""

import schedule
import time
import subprocess
import sys
import os
from datetime import datetime
from src.notifications import log_info, log_error

def run_volatilityhunter(mode="trading"):
    """Run VolatilityHunter using the unified entry point"""
    try:
        log_info(f"Starting VolatilityHunter in {mode} mode...")
        
        # Get the directory where this script is located
        script_dir = os.path.dirname(os.path.abspath(__file__))
        volatilityhunter_path = os.path.join(script_dir, "volatilityhunter.py")
        
        # Run volatilityhunter.py with the specified mode
        result = subprocess.run(
            [sys.executable, volatilityhunter_path, "--mode", mode],
            cwd=script_dir,
            capture_output=True,
            text=True,
            timeout=3600  # 1 hour timeout
        )
        
        if result.returncode == 0:
            log_info(f"VolatilityHunter {mode} completed successfully")
            print(f"[OK] VolatilityHunter {mode} completed successfully")
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Last 500 chars
        else:
            log_error(f"VolatilityHunter {mode} failed with exit code {result.returncode}")
            print(f"[ERROR] VolatilityHunter {mode} failed")
            if result.stderr:
                print("Error:", result.stderr[-500:])  # Last 500 chars
            if result.stdout:
                print("Output:", result.stdout[-500:])  # Last 500 chars
        
        return result.returncode == 0
        
    except subprocess.TimeoutExpired:
        log_error(f"VolatilityHunter {mode} timed out after 1 hour")
        print(f"[ERROR] VolatilityHunter {mode} timed out")
        return False
    except Exception as e:
        log_error(f"Failed to run VolatilityHunter {mode}: {e}")
        print(f"[ERROR] Failed to run VolatilityHunter {mode}: {e}")
        return False

def daily_job():
    """Daily trading job - runs at 12:30 AM"""
    print(f"\n{'='*60}")
    print(f"VOLATILITYHUNTER DAILY JOB - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Set environment variable for production mode
    os.environ['VH_MODE'] = 'production'
    
    # Run in trading mode
    success = run_volatilityhunter("trading")
    
    if success:
        print(f"[SUCCESS] Daily job completed at {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"[FAILED] Daily job failed at {datetime.now().strftime('%H:%M:%S')}")

def weekly_job():
    """Weekly backtest job - runs on Sunday at 2:00 AM"""
    print(f"\n{'='*60}")
    print(f"VOLATILITYHUNTER WEEKLY BACKTEST - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    
    # Run backtest
    success = run_volatilityhunter("backtest")
    
    if success:
        print(f"[SUCCESS] Weekly backtest completed at {datetime.now().strftime('%H:%M:%S')}")
    else:
        print(f"[FAILED] Weekly backtest failed at {datetime.now().strftime('%H:%M:%S')}")

def health_check_job():
    """Hourly health check - runs every hour"""
    print(f"\n{'='*40}")
    print(f"HEALTH CHECK - {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print(f"{'='*40}")
    
    # Run quick dryrun
    success = run_volatilityhunter("dryrun")
    
    if success:
        print(f"[OK] System healthy at {datetime.now().strftime('%H:%M')}")
    else:
        print(f"[WARNING] System issues detected at {datetime.now().strftime('%H:%M')}")

def run_scheduler():
    """Run the updated scheduler."""
    print("="*60)
    print("VOLATILITYHUNTER UPDATED SCHEDULER")
    print("="*60)
    print("Using unified entry point: volatilityhunter.py")
    print("")
    print("Schedule:")
    print("  - Daily Trading: Every day at 12:30 AM (Production Mode)")
    print("  - Weekly Backtest: Every Sunday at 2:00 AM")
    print("  - Health Check: Every hour (Dryrun Mode)")
    print("="*60 + "\n")
    
    # Schedule daily trading job at 12:30 AM
    schedule.every().day.at("00:30").do(daily_job)
    
    # Schedule weekly backtest on Sunday at 2:00 AM
    schedule.every().sunday.at("02:00").do(weekly_job)
    
    # Schedule hourly health check
    schedule.every().hour.do(health_check_job)
    
    # Run initial health check
    print("Running initial health check...")
    health_check_job()
    
    print(f"\nScheduler started at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("Press Ctrl+C to stop.")
    print("="*60)
    
    try:
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    except KeyboardInterrupt:
        print("\nScheduler stopped by user")
        sys.exit(0)
    except Exception as e:
        log_error(f"Scheduler error: {e}")
        print(f"Scheduler error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    # Check for command line arguments
    if len(sys.argv) > 1:
        if sys.argv[1] == "--daily":
            daily_job()
        elif sys.argv[1] == "--weekly":
            weekly_job()
        elif sys.argv[1] == "--health":
            health_check_job()
        elif sys.argv[1] == "--test":
            print("Running test execution...")
            os.environ['VH_MODE'] = 'simulation'  # Test in simulation mode
            run_volatilityhunter("trading")
        else:
            print("Usage: python scheduler.py [--daily|--weekly|--health|--test]")
            sys.exit(1)
    else:
        run_scheduler()
