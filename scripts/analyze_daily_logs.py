#!/usr/bin/env python3
"""
Comprehensive Daily Trading Log Analyzer
Analyzes all trading logs to extract statistics on performance, accuracy, failures, and P&L.
"""

import os
import re
import json
from datetime import datetime
from collections import defaultdict
from pathlib import Path
import sys

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

class LogAnalyzer:
    def __init__(self, logs_dir="logs"):
        self.logs_dir = Path(logs_dir)
        self.all_stats = []
        self.error_patterns = {
            'connection_errors': [],
            'data_errors': [],
            'order_errors': [],
            'system_errors': [],
            'other_errors': []
        }
        
    def parse_log_file(self, log_path):
        """Parse a single trading log file and extract statistics."""
        stats = {
            'date': None,
            'success': False,
            'error': None,
            'capital': 100000,
            'starting_positions': 0,
            'starting_cash': 0,
            'ending_positions': 0,
            'ending_cash': 0,
            'ending_total': 0,
            'entries': 0,
            'exits': 0,
            'exit_signals': 0,
            'candidates': 0,
            'tickers_scanned': 0,
            'execution_time': 0,
            'market_status': 'UNKNOWN',
            'regime': 'UNKNOWN',
            'orders_placed': 0,
            'orders_filled': 0,
            'orders_cancelled': 0,
            'order_errors': 0,
            'pnl_total': 0,
            'pnl_realized': 0,
            'warnings': 0,
            'api_errors': 0,
            'tickers_fetched': 0,
            'tickers_failed': 0
        }
        
        try:
            with open(log_path, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
                
            # Extract date from filename
            date_match = re.search(r'trading_(\d{4}-\d{2}-\d{2})', log_path.name)
            if date_match:
                stats['date'] = date_match.group(1)
            
            # Parse log content line by line
            lines = content.split('\n')
            for line in lines:
                # Extract capital
                capital_match = re.search(r'Capital: \$(\d+,?\d*)', line)
                if capital_match:
                    stats['capital'] = int(capital_match.group(1).replace(',', ''))
                
                # Extract starting portfolio
                start_portfolio_match = re.search(r'Portfolio loaded: (\d+) positions, \$([-\d,\.]+) cash', line)
                if start_portfolio_match:
                    stats['starting_positions'] = int(start_portfolio_match.group(1))
                    stats['starting_cash'] = float(start_portfolio_match.group(2).replace(',', ''))
                
                # Extract ending portfolio
                end_portfolio_match = re.search(r'Positions: (\d+) \| Cash: \$([-\d,\.]+) \| Total: \$([-\d,\.]+)', line)
                if end_portfolio_match:
                    stats['ending_positions'] = int(end_portfolio_match.group(1))
                    stats['ending_cash'] = float(end_portfolio_match.group(2).replace(',', ''))
                    stats['ending_total'] = float(end_portfolio_match.group(3).replace(',', ''))
                
                # Extract entries and exits
                entries_exits_match = re.search(r'Exits: (\d+) \| Entries: (\d+)', line)
                if entries_exits_match:
                    stats['exits'] = int(entries_exits_match.group(1))
                    stats['entries'] = int(entries_exits_match.group(2))
                
                # Extract exit signals
                exit_signals_match = re.search(r'Exit signals: (\d+)', line)
                if exit_signals_match:
                    stats['exit_signals'] = int(exit_signals_match.group(1))
                
                # Extract candidates
                candidates_match = re.search(r'Scan complete.*?: (\d+) candidates from (\d+) tickers', line)
                if candidates_match:
                    stats['candidates'] = int(candidates_match.group(1))
                    stats['tickers_scanned'] = int(candidates_match.group(2))
                
                # Extract execution time
                time_match = re.search(r'Daily loop complete in ([\d\.]+)s', line)
                if time_match:
                    stats['execution_time'] = float(time_match.group(1))
                
                # Extract market status
                market_match = re.search(r'Market is OPEN - Trading allowed', line)
                if market_match:
                    stats['market_status'] = 'OPEN'
                market_closed_match = re.search(r'Market is CLOSED', line)
                if market_closed_match:
                    stats['market_status'] = 'CLOSED'
                
                # Extract regime
                regime_match = re.search(r'SPY regime: (\w+)', line)
                if regime_match:
                    stats['regime'] = regime_match.group(1)
                
                # Extract tickers fetched
                fetched_match = re.search(r'Successfully fetched (\d+)/(\d+) ticker', line)
                if fetched_match:
                    stats['tickers_fetched'] = int(fetched_match.group(1))
                    stats['tickers_failed'] = int(fetched_match.group(2)) - int(fetched_match.group(1))
                
                # Count order placements
                if 'Placed' in line and ('BUY' in line or 'SELL' in line):
                    stats['orders_placed'] += 1
                
                # Count order fills
                if 'status=\'Filled\'' in line or 'Filled' in line:
                    stats['orders_filled'] += 1
                
                # Count order cancellations
                if 'status=\'Cancelled\'' in line or 'Canceled order' in line:
                    stats['orders_cancelled'] += 1
                
                # Count order errors
                if 'Error' in line and 'order' in line.lower():
                    stats['order_errors'] += 1
                
                # Count warnings
                if 'WARNING' in line:
                    stats['warnings'] += 1
                
                # Count API errors
                if 'ERROR' in line and ('API' in line or 'fetch' in line.lower() or 'download' in line.lower()):
                    stats['api_errors'] += 1
                
                # Check for success
                if 'Email sent successfully' in line:
                    stats['success'] = True
                
                # Check for specific errors
                if 'ERROR' in line or 'Traceback' in line or 'Exception' in line:
                    if not stats['error']:
                        stats['error'] = line.strip()
                    
                    # Categorize errors
                    if 'connection' in line.lower() or 'timeout' in line.lower() or 'gateway' in line.lower():
                        self.error_patterns['connection_errors'].append((stats['date'], line.strip()))
                    elif 'data' in line.lower() or 'fetch' in line.lower() or 'download' in line.lower():
                        self.error_patterns['data_errors'].append((stats['date'], line.strip()))
                    elif 'order' in line.lower() or 'fill' in line.lower():
                        self.error_patterns['order_errors'].append((stats['date'], line.strip()))
                    elif 'system' in line.lower() or 'memory' in line.lower() or 'disk' in line.lower():
                        self.error_patterns['system_errors'].append((stats['date'], line.strip()))
                    else:
                        self.error_patterns['other_errors'].append((stats['date'], line.strip()))
        
        except Exception as e:
            stats['error'] = f"Failed to parse log file: {str(e)}"
            stats['success'] = False
        
        return stats
    
    def analyze_all_logs(self):
        """Analyze all trading log files."""
        log_files = sorted(self.logs_dir.glob('trading_*.log'))
        
        print(f"Found {len(log_files)} trading log files")
        
        for log_file in log_files:
            print(f"Processing {log_file.name}...")
            stats = self.parse_log_file(log_file)
            self.all_stats.append(stats)
        
        return self.all_stats
    
    def calculate_summary_statistics(self):
        """Calculate summary statistics from all parsed logs."""
        if not self.all_stats:
            return None
        
        total_days = len(self.all_stats)
        successful_days = sum(1 for s in self.all_stats if s['success'])
        failed_days = total_days - successful_days
        
        # Calculate average portfolio values
        avg_starting_cash = sum(s['starting_cash'] for s in self.all_stats if s['starting_cash']) / max(1, sum(1 for s in self.all_stats if s['starting_cash']))
        avg_ending_cash = sum(s['ending_cash'] for s in self.all_stats if s['ending_cash']) / max(1, sum(1 for s in self.all_stats if s['ending_cash']))
        avg_ending_total = sum(s['ending_total'] for s in self.all_stats if s['ending_total']) / max(1, sum(1 for s in self.all_stats if s['ending_total']))
        
        # Calculate trading activity
        total_entries = sum(s['entries'] for s in self.all_stats)
        total_exits = sum(s['exits'] for s in self.all_stats)
        total_exit_signals = sum(s['exit_signals'] for s in self.all_stats)
        total_candidates = sum(s['candidates'] for s in self.all_stats)
        
        # Calculate order statistics
        total_orders_placed = sum(s['orders_placed'] for s in self.all_stats)
        total_orders_filled = sum(s['orders_filled'] for s in self.all_stats)
        total_orders_cancelled = sum(s['orders_cancelled'] for s in self.all_stats)
        total_order_errors = sum(s['order_errors'] for s in self.all_stats)
        
        # Calculate error statistics
        total_warnings = sum(s['warnings'] for s in self.all_stats)
        total_api_errors = sum(s['api_errors'] for s in self.all_stats)
        total_tickers_failed = sum(s['tickers_failed'] for s in self.all_stats)
        
        # Calculate average execution time
        avg_execution_time = sum(s['execution_time'] for s in self.all_stats if s['execution_time']) / max(1, sum(1 for s in self.all_stats if s['execution_time']))
        
        # Calculate regime distribution
        regime_counts = defaultdict(int)
        for s in self.all_stats:
            if s['regime']:
                regime_counts[s['regime']] += 1
        
        # Calculate market status distribution
        market_status_counts = defaultdict(int)
        for s in self.all_stats:
            if s['market_status']:
                market_status_counts[s['market_status']] += 1
        
        summary = {
            'total_days': total_days,
            'successful_days': successful_days,
            'failed_days': failed_days,
            'success_rate': (successful_days / total_days * 100) if total_days > 0 else 0,
            'avg_starting_cash': avg_starting_cash,
            'avg_ending_cash': avg_ending_cash,
            'avg_ending_total': avg_ending_total,
            'total_entries': total_entries,
            'total_exits': total_exits,
            'total_exit_signals': total_exit_signals,
            'total_candidates': total_candidates,
            'avg_entries_per_day': total_entries / total_days if total_days > 0 else 0,
            'avg_exits_per_day': total_exits / total_days if total_days > 0 else 0,
            'total_orders_placed': total_orders_placed,
            'total_orders_filled': total_orders_filled,
            'total_orders_cancelled': total_orders_cancelled,
            'total_order_errors': total_order_errors,
            'order_fill_rate': (total_orders_filled / total_orders_placed * 100) if total_orders_placed > 0 else 0,
            'total_warnings': total_warnings,
            'total_api_errors': total_api_errors,
            'total_tickers_failed': total_tickers_failed,
            'avg_execution_time': avg_execution_time,
            'regime_distribution': dict(regime_counts),
            'market_status_distribution': dict(market_status_counts),
            'error_patterns': self.error_patterns
        }
        
        return summary
    
    def safe_print(self, text):
        """Safely print text handling unicode encoding issues."""
        try:
            print(text)
        except UnicodeEncodeError:
            # Fall back to ASCII-only printing
            print(text.encode('ascii', 'ignore').decode('ascii'))
    
    def generate_report(self):
        """Generate a comprehensive statistics report."""
        summary = self.calculate_summary_statistics()
        
        if not summary:
            self.safe_print("No data to generate report")
            return
        
        self.safe_print("\n" + "="*80)
        self.safe_print("VOLATILITYHUNTER DAILY TRADING LOG ANALYSIS REPORT")
        self.safe_print("="*80)
        self.safe_print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.safe_print(f"Period: {self.all_stats[0]['date']} to {self.all_stats[-1]['date']}")
        self.safe_print("="*80)
        
        self.safe_print("\nOVERALL STATISTICS")
        self.safe_print("-" * 80)
        self.safe_print(f"Total Trading Days: {summary['total_days']}")
        self.safe_print(f"Successful Days: {summary['successful_days']} ({summary['success_rate']:.1f}%)")
        self.safe_print(f"Failed Days: {summary['failed_days']} ({100 - summary['success_rate']:.1f}%)")
        
        self.safe_print("\nPORTFOLIO STATISTICS")
        self.safe_print("-" * 80)
        self.safe_print(f"Average Starting Cash: ${summary['avg_starting_cash']:,.2f}")
        self.safe_print(f"Average Ending Cash: ${summary['avg_ending_cash']:,.2f}")
        self.safe_print(f"Average Ending Total Portfolio Value: ${summary['avg_ending_total']:,.2f}")
        
        self.safe_print("\nTRADING ACTIVITY")
        self.safe_print("-" * 80)
        self.safe_print(f"Total Entries: {summary['total_entries']}")
        self.safe_print(f"Total Exits: {summary['total_exits']}")
        self.safe_print(f"Total Exit Signals: {summary['total_exit_signals']}")
        self.safe_print(f"Total Candidates Scanned: {summary['total_candidates']}")
        self.safe_print(f"Average Entries per Day: {summary['avg_entries_per_day']:.2f}")
        self.safe_print(f"Average Exits per Day: {summary['avg_exits_per_day']:.2f}")
        
        self.safe_print("\nORDER EXECUTION")
        self.safe_print("-" * 80)
        self.safe_print(f"Total Orders Placed: {summary['total_orders_placed']}")
        self.safe_print(f"Total Orders Filled: {summary['total_orders_filled']}")
        self.safe_print(f"Total Orders Cancelled: {summary['total_orders_cancelled']}")
        self.safe_print(f"Total Order Errors: {summary['total_order_errors']}")
        self.safe_print(f"Order Fill Rate: {summary['order_fill_rate']:.1f}%")
        
        self.safe_print("\nERROR STATISTICS")
        self.safe_print("-" * 80)
        self.safe_print(f"Total Warnings: {summary['total_warnings']}")
        self.safe_print(f"Total API Errors: {summary['total_api_errors']}")
        self.safe_print(f"Total Tickers Failed to Fetch: {summary['total_tickers_failed']}")
        
        self.safe_print("\nPERFORMANCE")
        self.safe_print("-" * 80)
        self.safe_print(f"Average Execution Time: {summary['avg_execution_time']:.2f} seconds")
        
        self.safe_print("\nMARKET CONDITIONS")
        self.safe_print("-" * 80)
        self.safe_print("Regime Distribution:")
        for regime, count in summary['regime_distribution'].items():
            self.safe_print(f"  {regime}: {count} days ({count/summary['total_days']*100:.1f}%)")
        
        self.safe_print("\nMarket Status Distribution:")
        for status, count in summary['market_status_distribution'].items():
            self.safe_print(f"  {status}: {count} days ({count/summary['total_days']*100:.1f}%)")
        
        self.safe_print("\nERROR PATTERNS")
        self.safe_print("-" * 80)
        self.safe_print(f"Connection Errors: {len(summary['error_patterns']['connection_errors'])}")
        self.safe_print(f"Data Errors: {len(summary['error_patterns']['data_errors'])}")
        self.safe_print(f"Order Errors: {len(summary['error_patterns']['order_errors'])}")
        self.safe_print(f"System Errors: {len(summary['error_patterns']['system_errors'])}")
        self.safe_print(f"Other Errors: {len(summary['error_patterns']['other_errors'])}")
        
        # Show recent errors
        if summary['error_patterns']['connection_errors']:
            self.safe_print("\nRecent Connection Errors:")
            for date, error in summary['error_patterns']['connection_errors'][-5:]:
                self.safe_print(f"  {date}: {error[:100]}...")
        
        if summary['error_patterns']['data_errors']:
            self.safe_print("\nRecent Data Errors:")
            for date, error in summary['error_patterns']['data_errors'][-5:]:
                self.safe_print(f"  {date}: {error[:100]}...")
        
        self.safe_print("\n" + "="*80)
        self.safe_print("DETAILED DAILY BREAKDOWN")
        self.safe_print("="*80)
        
        for stats in self.all_stats:
            status = "SUCCESS" if stats['success'] else "FAILED"
            self.safe_print(f"\n{stats['date']}: {status}")
            self.safe_print(f"  Positions: {stats['starting_positions']} -> {stats['ending_positions']}")
            self.safe_print(f"  Cash: ${stats['starting_cash']:,.2f} -> ${stats['ending_cash']:,.2f}")
            self.safe_print(f"  Total: ${stats['ending_total']:,.2f}")
            self.safe_print(f"  Entries: {stats['entries']}, Exits: {stats['exits']}")
            self.safe_print(f"  Candidates: {stats['candidates']}, Scanned: {stats['tickers_scanned']}")
            self.safe_print(f"  Orders: {stats['orders_placed']} placed, {stats['orders_filled']} filled")
            self.safe_print(f"  Time: {stats['execution_time']:.1f}s, Regime: {stats['regime']}")
            if stats['error']:
                try:
                    self.safe_print(f"  Error: {stats['error'][:100]}")
                except UnicodeEncodeError:
                    self.safe_print(f"  Error: [Encoding error in message]")
        
        self.safe_print("\n" + "="*80)
        self.safe_print("END OF REPORT")
        self.safe_print("="*80)
        
        return summary

def main():
    """Main execution function."""
    analyzer = LogAnalyzer()
    analyzer.analyze_all_logs()
    summary = analyzer.generate_report()
    
    # Save summary to JSON
    output_file = "temp/ws_log_analysis_summary.json"
    with open(output_file, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    analyzer.safe_print(f"\nSummary saved to: {output_file}")

if __name__ == "__main__":
    main()