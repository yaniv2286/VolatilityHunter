#!/usr/bin/env python3
"""
Gateway Failure Email Notifier
Send email notification when Gateway fails to start
"""

import os
import sys
import time
from pathlib import Path
from datetime import datetime

# Add project root to path
ROOT = Path(__file__).parent.parent.absolute()
sys.path.insert(0, str(ROOT))

from src.notifications import log_info, log_warning, log_error
from src.email_notifier import EmailNotifier

def read_last_log_lines(log_file, max_lines=200):
    """Read last N lines from log file"""
    try:
        if not log_file.exists():
            return ["Log file not found"]
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
        
        # Get last max_lines
        last_lines = lines[-max_lines:] if len(lines) > max_lines else lines
        return [line.strip() for line in last_lines]
        
    except Exception as e:
        return [f"Error reading log file: {e}"]

def send_failure_email():
    """Send gateway failure email notification"""
    log_info("Sending Gateway failure email notification...")
    
    try:
        # Initialize email notifier
        notifier = EmailNotifier()
        
        # Read startup log
        startup_log = ROOT / "logs" / "gateway_startup.log"
        log_lines = read_last_log_lines(startup_log, 200)
        
        # Read daily trading log (if exists)
        today_str = datetime.now().strftime("%Y-%m-%d")
        daily_log = ROOT / "logs" / f"trading_{today_str}.log"
        daily_log_lines = read_last_log_lines(daily_log, 100) if daily_log.exists() else ["No daily log found"]
        
        # Build email content
        subject = f"⚠️ IB Gateway Startup Failed - Trading Skipped [{today_str}]"
        
        body = f"""
VOLATILITYHUNTER - CRITICAL ALERT

IB Gateway failed to start after 3 retry attempts.

TIMESTAMP: {datetime.now().isoformat()}

IMPACT:
- Daily trading routine SKIPPED
- No positions entered/exited today
- System will retry again tomorrow

TROUBLESHOOTING:
1. Check IB Gateway installation: D:\\TWS\\ibgateway
2. Verify IBC configuration: {ROOT / 'config' / 'ibc.ini'}
3. Check Windows Event Viewer for Java errors
4. Manual test: Run scripts/start_gateway_with_retry.py

LAST GATEWAY STARTUP LOG (last 50 lines):
{'-' * 60}
{chr(10).join(log_lines[-50:])}
{'-' * 60}

LAST DAILY TRADING LOG (last 20 lines):
{'-' * 60}
{chr(10).join(daily_log_lines[-20:])}
{'-' * 60}

NEXT STEPS:
1. Investigate the error above
2. Fix the root cause
3. Test Gateway startup manually
4. System will automatically retry tomorrow

SYSTEM STATUS: FAILED - GATEWAY UNAVAILABLE
PORT 7497: NOT REACHABLE
TRADING MODE: SKIPPED

---
VolatilityHunter Automated System
"""
        
        # Prepare attachments
        attachments = []
        if startup_log.exists():
            attachments.append(str(startup_log))
        if daily_log.exists():
            attachments.append(str(daily_log))
        
        # Send email
        notifier.send_email(
            subject=subject,
            body=body,
            attachments=attachments
        )
        
        log_info("Gateway failure email sent successfully")
        return 0
        
    except Exception as e:
        log_error(f"Failed to send gateway failure email: {e}")
        return 1

def main():
    """Main entry point"""
    log_info("=" * 60)
    log_info("Gateway Failure Email Notifier")
    log_info(f"Started at: {datetime.now().isoformat()}")
    log_info("=" * 60)
    
    exit_code = send_failure_email()
    
    log_info(f"Email notification completed with exit code: {exit_code}")
    log_info("=" * 60)
    
    return exit_code

if __name__ == "__main__":
    sys.exit(main())
