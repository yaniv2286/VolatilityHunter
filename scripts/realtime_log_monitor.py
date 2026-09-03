#!/usr/bin/env python3
"""
Real-time Log Monitor
===================
Monitors trading logs in real-time for critical issues.
Can be run alongside the daily trading loop.
"""

import os
import sys
import time
import re
import logging
from datetime import datetime
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.email_notifier import EmailNotifier

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class LogFileHandler(FileSystemEventHandler):
    """Handles log file changes."""
    
    def __init__(self, log_monitor):
        self.log_monitor = log_monitor
        self.last_position = {}
        
    def on_modified(self, event):
        """Called when a file is modified."""
        if event.is_directory:
            return
            
        if event.src_path.endswith('.log'):
            self.check_log_file(event.src_path)
            
    def check_log_file(self, file_path):
        """Check for new lines in log file."""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                # Get current file size
                f.seek(0, 2)
                size = f.tell()
                
                # Get last position for this file
                last_pos = self.last_position.get(file_path, 0)
                
                # If file was truncated (new day), reset position
                if size < last_pos:
                    last_pos = 0
                    
                # Read new lines
                f.seek(last_pos)
                new_lines = f.readlines()
                
                # Update position
                self.last_position[file_path] = f.tell()
                
                # Process new lines
                for line in new_lines:
                    self.log_monitor.process_log_line(line.strip())
                    
        except Exception as e:
            logger.error(f"Error checking log file {file_path}: {e}")

class RealtimeLogMonitor:
    def __init__(self):
        self.email_notifier = EmailNotifier()
        self.issues = []
        self.last_alert_time = {}
        self.alert_cooldown = 300  # 5 minutes between same alert type
        
    def process_log_line(self, line):
        """Process a single log line."""
        # Check for critical issues
        if "ERROR ORDER CANCEL" in line:
            match = re.search(r"ORDER CANCEL: (\w+) unfilled", line)
            if match:
                ticker = match.group(1)
                self.handle_order_cancel(ticker)
                
        elif "Failed download" in line:
            match = re.search(r"\['(\w+)'\]", line)
            if match:
                ticker = match.group(1)
                self.handle_data_failure(ticker)
                
        elif "ERROR" in line and "ORDER CANCEL" not in line and "Failed download" not in line:
            self.handle_general_error(line)
            
    def handle_order_cancel(self, ticker):
        """Handle order cancellation."""
        alert_key = "order_cancel"
        now = time.time()
        
        # Check cooldown
        if now - self.last_alert_time.get(alert_key, 0) < self.alert_cooldown:
            return
            
        subject = f"ALERT: Order Cancellation Alert - {ticker}"
        message = f"""
Order failed to fill and was cancelled:

Ticker: {ticker}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Action: Check if market is open or if there are liquidity issues

This is an automated alert from VolatilityHunter.
"""
        
        if self.email_notifier.send_email(subject, message):
            logger.info(f"Order cancellation alert sent for {ticker}")
            self.last_alert_time[alert_key] = now
        else:
            logger.error(f"Failed to send order cancellation alert for {ticker}")
            
    def handle_data_failure(self, ticker):
        """Handle data download failure."""
        alert_key = "data_failure"
        now = time.time()
        
        # Check cooldown
        if now - self.last_alert_time.get(alert_key, 0) < self.alert_cooldown:
            return
            
        subject = f"⚠️ Data Failure Alert - {ticker}"
        message = f"""
Failed to download price data:

Ticker: {ticker}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Action: Ticker may be delisted or yfinance API issues

This is an automated alert from VolatilityHunter.
"""
        
        if self.email_notifier.send_email(subject, message):
            logger.info(f"Data failure alert sent for {ticker}")
            self.last_alert_time[alert_key] = now
        else:
            logger.error(f"Failed to send data failure alert for {ticker}")
            
    def handle_general_error(self, error_line):
        """Handle general errors."""
        alert_key = "general_error"
        now = time.time()
        
        # Check cooldown
        if now - self.last_alert_time.get(alert_key, 0) < self.alert_cooldown:
            return
            
        subject = "[FAIL] General Error Alert"
        message = f"""
General error detected in trading system:

Error: {error_line}
Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
Action: Check the trading logs immediately

This is an automated alert from VolatilityHunter.
"""
        
        if self.email_notifier.send_email(subject, message):
            logger.info("General error alert sent")
            self.last_alert_time[alert_key] = now
        else:
            logger.error("Failed to send general error alert")
            
    def start_monitoring(self, log_dir="logs"):
        """Start monitoring the log directory."""
        log_path = Path(log_dir)
        if not log_path.exists():
            logger.error(f"Log directory does not exist: {log_path}")
            return
            
        logger.info(f"Starting real-time log monitoring for {log_path}")
        
        # Set up file system observer
        event_handler = LogFileHandler(self)
        observer = Observer()
        observer.schedule(event_handler, log_path, recursive=False)
        
        # Start monitoring
        observer.start()
        
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            logger.info("Real-time log monitoring stopped")
            
        observer.join()

def main():
    """Main entry point."""
    monitor = RealtimeLogMonitor()
    
    # Check if log directory exists
    if not Path("logs").exists():
        logger.info("Creating logs directory...")
        Path("logs").mkdir(exist_ok=True)
        
    monitor.start_monitoring()

if __name__ == "__main__":
    main()
