#!/usr/bin/env python3
"""
Trading Log Monitor
==================
Monitors trading logs for critical errors and sends alerts.
This script should be run after the daily trading to check for issues.
"""

import os
import sys
import re
import logging
from datetime import datetime
from pathlib import Path

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email_notifier import EmailNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogMonitor:
    def __init__(self):
        self.email_notifier = EmailNotifier()
        self.issues = []
        
    def check_latest_log(self):
        """Check the latest trading log for issues."""
        log_dir = Path("logs")
        today = datetime.now().strftime("%Y-%m-%d")
        log_file = log_dir / f"trading_{today}.log"
        
        if not log_file.exists():
            logger.warning(f"No log file found for today: {log_file}")
            return False
            
        logger.info(f"Checking log file: {log_file}")
        
        with open(log_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            
        # Track issues
        errors = []
        warnings = []
        order_issues = []
        data_issues = []
        
        for line in lines:
            # Check for errors
            if "ERROR" in line:
                if "ORDER CANCEL" in line:
                    # Extract cancelled order
                    match = re.search(r"ORDER CANCEL: (\w+) unfilled", line)
                    if match:
                        order_issues.append(match.group(1))
                elif "Failed download" in line:
                    # Extract failed ticker
                    match = re.search(r"\['(\w+)'\]", line)
                    if match:
                        data_issues.append(match.group(1))
                else:
                    errors.append(line.strip())
                    
            # Check for warnings
            elif "WARNING" in line:
                warnings.append(line.strip())
                
        # Generate report
        report = self.generate_report(errors, warnings, order_issues, data_issues)
        
        # Send alert if critical issues found
        if order_issues or len(errors) > 5 or len(data_issues) > 3:
            self.send_critical_alert(report)
            return True
            
        return False
    
    def generate_report(self, errors, warnings, order_issues, data_issues):
        """Generate a comprehensive report of issues."""
        report = []
        report.append("VolatilityHunter Trading Log Monitor Report")
        report.append("=" * 50)
        report.append(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        report.append("")
        
        # Order issues (most critical)
        if order_issues:
            report.append("ALERT: CRITICAL: Order Execution Issues")
            report.append(f"  - {len(order_issues)} orders failed to fill:")
            for ticker in order_issues:
                report.append(f"    • {ticker}")
            report.append("")
            
        # Data issues
        if data_issues:
            report.append("⚠️  Data Fetch Issues")
            report.append(f"  - {len(data_issues)} tickers failed to download:")
            for ticker in data_issues:
                report.append(f"    • {ticker}")
            report.append("")
            
        # General errors
        if errors:
            report.append("[FAIL] General Errors")
            report.append(f"  - {len(errors)} error(s) found:")
            for i, error in enumerate(errors[:10]):  # Limit to first 10
                report.append(f"    {i+1}. {error}")
            if len(errors) > 10:
                report.append(f"    ... and {len(errors) - 10} more")
            report.append("")
            
        # Warnings
        if warnings:
            report.append("⚠️  Warnings")
            report.append(f"  - {len(warnings)} warning(s):")
            for i, warning in enumerate(warnings[:5]):  # Limit to first 5
                report.append(f"    {i+1}. {warning}")
            if len(warnings) > 5:
                report.append(f"    ... and {len(warnings) - 5} more")
            report.append("")
            
        # Summary
        report.append("📊 Summary")
        report.append(f"  - Order Issues: {len(order_issues)}")
        report.append(f"  - Data Issues: {len(data_issues)}")
        report.append(f"  - General Errors: {len(errors)}")
        report.append(f"  - Warnings: {len(warnings)}")
        
        return "\n".join(report)
        
    def send_critical_alert(self, report):
        """Send critical alert email."""
        subject = f"ALERT: VolatilityHunter CRITICAL Issues Detected - {datetime.now().strftime('%Y-%m-%d')}"
        
        if self.email_notifier.send_email(subject, report):
            logger.info("Critical alert email sent successfully")
        else:
            logger.error("Failed to send critical alert email")
            
    def run(self):
        """Run the log monitor."""
        logger.info("Starting trading log monitor...")
        
        if self.check_latest_log():
            logger.info("Critical issues found - alert sent")
        else:
            logger.info("No critical issues found")

def main():
    monitor = LogMonitor()
    monitor.run()

if __name__ == "__main__":
    main()
