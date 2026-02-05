#!/usr/bin/env python3
"""
Performance Tracking System
Tracks portfolio performance against benchmarks
"""

import sys
import os
import json
from datetime import datetime, timedelta
sys.path.append('src')

from tracker import Portfolio
from data_loader import get_stock_data

class PerformanceTracker:
    """Track and analyze portfolio performance."""
    
    def __init__(self):
        self.portfolio = Portfolio()
        self.performance_file = "data/performance_tracker.json"
        self.load_performance_data()
    
    def load_performance_data(self):
        """Load historical performance data."""
        try:
            if os.path.exists(self.performance_file):
                with open(self.performance_file, 'r') as f:
                    self.performance_data = json.load(f)
            else:
                self.performance_data = {
                    'daily_snapshots': [],
                    'metrics': {
                        'total_trades': 0,
                        'winning_trades': 0,
                        'losing_trades': 0,
                        'total_profit_loss': 0.0,
                        'best_trade': 0.0,
                        'worst_trade': 0.0
                    }
                }
        except Exception as e:
            print(f"Error loading performance data: {e}")
            self.performance_data = {'daily_snapshots': [], 'metrics': {}}
    
    def save_performance_data(self):
        """Save performance data to file."""
        try:
            os.makedirs(os.path.dirname(self.performance_file), exist_ok=True)
            with open(self.performance_file, 'w') as f:
                json.dump(self.performance_data, f, indent=2)
        except Exception as e:
            print(f"Error saving performance data: {e}")
    
    def capture_daily_snapshot(self):
        """Capture current portfolio state as daily snapshot."""
        
        portfolio_summary = self.portfolio.get_summary()
        
        snapshot = {
            'date': datetime.now().strftime('%Y-%m-%d'),
            'portfolio_value': portfolio_summary['total_value'],
            'cash': self.portfolio.state['cash'],
            'positions_count': len(self.portfolio.state['positions']),
            'total_return_pct': portfolio_summary['total_return_pct'],
            'total_return_dollars': portfolio_summary['total_return_dollars']
        }
        
        # Add position details
        snapshot['positions'] = []
        for ticker, position in self.portfolio.state['positions'].items():
            current_value = position['shares'] * position['entry_price']
            snapshot['positions'].append({
                'ticker': ticker,
                'shares': position['shares'],
                'entry_price': position['entry_price'],
                'current_value': current_value,
                'quality_score': position['quality_score']
            })
        
        # Remove duplicate dates and add new snapshot
        self.performance_data['daily_snapshots'] = [
            s for s in self.performance_data['daily_snapshots'] 
            if s['date'] != snapshot['date']
        ]
        self.performance_data['daily_snapshots'].append(snapshot)
        
        # Keep only last 90 days
        self.performance_data['daily_snapshots'] = sorted(
            self.performance_data['daily_snapshots'], 
            key=lambda x: x['date']
        )[-90:]
        
        self.save_performance_data()
        return snapshot
    
    def analyze_trade_history(self):
        """Analyze trade history for performance metrics."""
        
        trade_history = self.portfolio.state['trade_history']
        
        if not trade_history:
            return
        
        # Filter only completed trades (with profit_loss)
        completed_trades = [t for t in trade_history if 'profit_loss' in t]
        
        if not completed_trades:
            return
        
        # Calculate metrics
        total_trades = len(completed_trades)
        winning_trades = len([t for t in completed_trades if t['profit_loss'] > 0])
        losing_trades = len([t for t in completed_trades if t['profit_loss'] < 0])
        
        total_profit_loss = sum(t['profit_loss'] for t in completed_trades)
        best_trade = max([t['profit_loss'] for t in completed_trades])
        worst_trade = min([t['profit_loss'] for t in completed_trades])
        
        # Update metrics
        self.performance_data['metrics'] = {
            'total_trades': total_trades,
            'winning_trades': winning_trades,
            'losing_trades': losing_trades,
            'win_rate': (winning_trades / total_trades * 100) if total_trades > 0 else 0,
            'total_profit_loss': total_profit_loss,
            'best_trade': best_trade,
            'worst_trade': worst_trade,
            'avg_trade': total_profit_loss / total_trades if total_trades > 0 else 0
        }
        
        self.save_performance_data()
    
    def generate_performance_report(self):
        """Generate comprehensive performance report."""
        
        self.capture_daily_snapshot()
        self.analyze_trade_history()
        
        print("=" * 60)
        print("VOLATILITYHUNTER PERFORMANCE REPORT")
        print("=" * 60)
        
        # Current status
        portfolio_summary = self.portfolio.get_summary()
        print(f"Portfolio Value: ${portfolio_summary['total_value']:,.2f}")
        print(f"Total Return: ${portfolio_summary['total_return_dollars']:,.2f} ({portfolio_summary['total_return_pct']:+.2f}%)")
        print(f"Current Positions: {len(self.portfolio.state['positions'])}/10")
        print(f"Cash Available: ${self.portfolio.state['cash']:,.2f}")
        
        # Trade metrics
        metrics = self.performance_data.get('metrics', {})
        if metrics:
            print(f"\nTRADE METRICS:")
            print("-" * 40)
            print(f"Total Trades: {metrics.get('total_trades', 0)}")
            print(f"Win Rate: {metrics.get('win_rate', 0):.1f}%")
            print(f"Winning Trades: {metrics.get('winning_trades', 0)}")
            print(f"Losing Trades: {metrics.get('losing_trades', 0)}")
            print(f"Total P/L: ${metrics.get('total_profit_loss', 0):,.2f}")
            print(f"Best Trade: ${metrics.get('best_trade', 0):,.2f}")
            print(f"Worst Trade: ${metrics.get('worst_trade', 0):,.2f}")
            print(f"Average Trade: ${metrics.get('avg_trade', 0):,.2f}")
        
        # Recent performance
        snapshots = self.performance_data.get('daily_snapshots', [])
        if len(snapshots) >= 2:
            print(f"\nRECENT PERFORMANCE:")
            print("-" * 40)
            
            # 7-day performance
            week_ago = datetime.now() - timedelta(days=7)
            week_snapshots = [s for s in snapshots if datetime.strptime(s['date'], '%Y-%m-%d') >= week_ago]
            
            if len(week_snapshots) >= 2:
                start_value = week_snapshots[0]['portfolio_value']
                end_value = week_snapshots[-1]['portfolio_value']
                week_return = ((end_value - start_value) / start_value) * 100
                print(f"7-Day Return: {week_return:+.2f}%")
            
            # 30-day performance
            month_ago = datetime.now() - timedelta(days=30)
            month_snapshots = [s for s in snapshots if datetime.strptime(s['date'], '%Y-%m-%d') >= month_ago]
            
            if len(month_snapshots) >= 2:
                start_value = month_snapshots[0]['portfolio_value']
                end_value = month_snapshots[-1]['portfolio_value']
                month_return = ((end_value - start_value) / start_value) * 100
                print(f"30-Day Return: {month_return:+.2f}%")
        
        print("=" * 60)

if __name__ == "__main__":
    tracker = PerformanceTracker()
    tracker.generate_performance_report()
