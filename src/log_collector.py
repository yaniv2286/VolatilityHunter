"""
Log Collection System
Collects and formats logs for email notifications
"""

import os
import re
from datetime import datetime, timedelta
from typing import List, Dict
from src.notifications import log_info


class LogCollector:
    """Collects and formats logs for email notifications."""
    
    def __init__(self, log_file='volatility_hunter.log'):
        self.log_file = log_file
    
    def get_recent_logs(self, hours: int = 1) -> List[str]:
        """
        Get log entries from the last specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            List of log lines
        """
        if not os.path.exists(self.log_file):
            return ["No log file found"]
        
        cutoff_time = datetime.now() - timedelta(hours=hours)
        recent_logs = []
        
        try:
            with open(self.log_file, 'r', encoding='utf-8') as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    
                    # Extract timestamp from log line
                    timestamp_match = re.match(r'(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2},\d{3})', line)
                    if timestamp_match:
                        try:
                            timestamp_str = timestamp_match.group(1).replace(',', '')
                            log_time = datetime.strptime(timestamp_str, '%Y-%m-%d %H:%M:%S.%f')
                            
                            if log_time >= cutoff_time:
                                recent_logs.append(line)
                        except ValueError:
                            # If timestamp parsing fails, include the line anyway
                            recent_logs.append(line)
                    else:
                        # Include lines without timestamps (they might be continuations)
                        if recent_logs:  # Only add if we already have some recent logs
                            recent_logs.append(line)
        
        except Exception as e:
            log_info(f"Error reading log file: {e}")
            return [f"Error reading log file: {e}"]
        
        return recent_logs
    
    def format_logs_for_email(self, hours: int = 1, max_lines: int = 100) -> str:
        """
        Format recent logs for email notification.
        
        Args:
            hours: Number of hours to look back
            max_lines: Maximum number of lines to include
            
        Returns:
            Formatted log string for email
        """
        logs = self.get_recent_logs(hours)
        
        if not logs:
            return "No recent logs found"
        
        # Limit number of lines
        if len(logs) > max_lines:
            logs = logs[-max_lines:]  # Get most recent logs
            truncated = True
        else:
            truncated = False
        
        # Format logs
        formatted_logs = f"""
📋 SYSTEM LOGS (Last {hours} hours)
{'='*60}
"""
        
        for log in logs:
            # Color code based on log level
            if ' - ERROR - ' in log:
                formatted_logs += f"🔴 {log}\n"
            elif ' - WARNING - ' in log:
                formatted_logs += f"🟡 {log}\n"
            elif 'SIGNAL' in log:
                formatted_logs += f"📢 {log}\n"
            elif 'BOUGHT' in log or 'SOLD' in log:
                formatted_logs += f"💰 {log}\n"
            else:
                formatted_logs += f"   {log}\n"
        
        if truncated:
            formatted_logs += f"\n... ({len(logs)} of {len(logs) + max_lines} lines shown)\n"
        
        return formatted_logs
    
    def get_error_summary(self, hours: int = 1) -> Dict:
        """
        Get summary of errors in the last specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dict with error summary
        """
        logs = self.get_recent_logs(hours)
        
        errors = []
        warnings = []
        
        for log in logs:
            if ' - ERROR - ' in log:
                errors.append(log)
            elif ' - WARNING - ' in log:
                warnings.append(log)
        
        return {
            'error_count': len(errors),
            'warning_count': len(warnings),
            'errors': errors[-10:],  # Last 10 errors
            'warnings': warnings[-10:]  # Last 10 warnings
        }
    
    def get_signal_summary(self, hours: int = 1) -> Dict:
        """
        Get summary of trading signals in the last specified hours.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dict with signal summary
        """
        logs = self.get_recent_logs(hours)
        
        buy_signals = []
        sell_signals = []
        trades_executed = []
        
        for log in logs:
            if '[SIGNAL]' in log and 'BUY' in log:
                buy_signals.append(log)
            elif '[SIGNAL]' in log and 'SELL' in log:
                sell_signals.append(log)
            elif 'BOUGHT' in log:
                trades_executed.append(log)
            elif 'SOLD' in log:
                trades_executed.append(log)
        
        return {
            'buy_signals': len(buy_signals),
            'sell_signals': len(sell_signals),
            'trades_executed': len(trades_executed),
            'buy_signal_logs': buy_signals,
            'sell_signal_logs': sell_signals,
            'trade_logs': trades_executed
        }
    
    def get_performance_metrics(self, hours: int = 1) -> Dict:
        """
        Extract performance metrics from logs.
        
        Args:
            hours: Number of hours to look back
            
        Returns:
            Dict with performance metrics
        """
        logs = self.get_recent_logs(hours)
        
        metrics = {
            'stocks_scanned': 0,
            'data_updated': 0,
            'scan_duration': None,
            'errors': 0,
            'warnings': 0
        }
        
        for log in logs:
            # Extract stocks scanned
            if 'Stock Universe:' in log:
                match = re.search(r'\((\d+) stocks\)', log)
                if match:
                    metrics['stocks_scanned'] = int(match.group(1))
            
            # Extract data updates
            if 'Updated:' in log and 'stocks' in log:
                match = re.search(r'Updated: (\d+)/', log)
                if match:
                    metrics['data_updated'] = int(match.group(1))
            
            # Count errors and warnings
            if ' - ERROR - ' in log:
                metrics['errors'] += 1
            elif ' - WARNING - ' in log:
                metrics['warnings'] += 1
        
        return metrics
