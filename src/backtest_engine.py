#!/usr/bin/env python3
"""
VolatilityHunter Backtesting Engine
Comprehensive historical performance analysis for all available data
"""

import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import json
from typing import Dict, List, Tuple, Any

from src.strategy import analyze_stock, scan_all_stocks
from src.storage import DataStorage
from src.tracker import Portfolio
from src.notifications import log_info, log_error, log_warning
from src.log_collector import LogCollector
from src.email_notifier import EmailNotifier

class BacktestEngine:
    def __init__(self, initial_capital: float = 100000, max_positions: int = 10):
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        self.storage = DataStorage()
        
        # Performance tracking
        self.results = {
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'total_return': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'avg_win': 0.0,
            'avg_loss': 0.0,
            'profit_factor': 0.0,
            'trade_history': [],
            'daily_returns': [],
            'portfolio_values': []
        }
        
    def get_historical_data_range(self, ticker: str) -> Tuple[pd.DataFrame, List[str]]:
        """Get available trading days for backtesting"""
        df = self.storage.load_data(ticker)
        if df is None or len(df) < 200:
            return None, []
        
        # Get all unique dates from the data
        dates = df.index.strftime('%Y-%m-%d').tolist()
        return df, dates
    
    def simulate_day(self, date: str, portfolio: Portfolio, all_data: Dict[str, pd.DataFrame]) -> Dict:
        """Simulate trading for a single day"""
        day_results = {
            'date': date,
            'signals': {'BUY': [], 'SELL': [], 'HOLD': []},
            'trades_executed': [],
            'portfolio_value': 0,
            'cash': portfolio.state['cash'],
            'positions': len(portfolio.state['positions'])
        }
        
        # Get current prices for all stocks
        current_prices = {}
        for ticker, df in all_data.items():
            if date in df.index:
                current_prices[ticker] = df.loc[date, 'Close']
        
        # Generate signals for this day
        day_data = {}
        for ticker, df in all_data.items():
            if date in df.index:
                # Get data up to this date
                mask = df.index <= date
                day_data[ticker] = df[mask].copy()
        
        if day_data:
            signals = scan_all_stocks(day_data)
            day_results['signals'] = signals
            
            # Process signals with portfolio
            buy_signals = sorted(signals['BUY'], key=lambda x: x.get('quality_score', 0), reverse=True)
            sell_signals = signals['SELL']
            
            # Execute trades
            trades = portfolio.process_signals(buy_signals, sell_signals, current_prices)
            day_results['trades_executed'] = trades
        
        # Update portfolio value
        portfolio_value = portfolio.update_portfolio_valuation(current_prices)
        day_results['portfolio_value'] = portfolio_value
        
        return day_results
    
    def run_backtest(self, start_date: str = None, end_date: str = None) -> Dict:
        """Run complete backtest on all available data"""
        log_info("Starting comprehensive backtest...")
        
        # Get all available tickers
        all_tickers = []
        ticker_files = self.storage.list_files()
        for file in ticker_files:
            if file.endswith('_1d_full.csv'):
                ticker = file.replace('_1d_full.csv', '')
                all_tickers.append(ticker)
        
        log_info(f"Found {len(all_tickers)} tickers for backtesting")
        
        # Load historical data for all tickers
        all_data = {}
        for ticker in all_tickers:
            df, dates = self.get_historical_data_range(ticker)
            if df is not None:
                all_data[ticker] = df
        
        log_info(f"Loaded data for {len(all_data)} tickers")
        
        # Determine date range
        if not start_date or not end_date:
            all_dates = set()
            for df in all_data.values():
                all_dates.update(df.index.strftime('%Y-%m-%d').tolist())
            
            if all_dates:
                sorted_dates = sorted(list(all_dates))
                start_date = start_date or sorted_dates[0]
                end_date = end_date or sorted_dates[-1]
        
        log_info(f"Backtesting period: {start_date} to {end_date}")
        
        # Initialize portfolio
        portfolio = Portfolio()
        portfolio.state['cash'] = self.initial_capital
        
        # Run day-by-day simulation
        trading_days = []
        current_date = pd.to_datetime(start_date)
        end_date_dt = pd.to_datetime(end_date)
        
        while current_date <= end_date_dt:
            date_str = current_date.strftime('%Y-%m-%d')
            
            # Check if this is a trading day (has data)
            is_trading_day = any(date_str in df.index for df in all_data.values())
            if is_trading_day:
                trading_days.append(date_str)
            
            current_date += timedelta(days=1)
        
        log_info(f"Found {len(trading_days)} trading days")
        
        # Simulate each trading day
        for i, date in enumerate(trading_days):
            if i % 50 == 0:
                log_info(f"Processing day {i+1}/{len(trading_days)}: {date}")
            
            try:
                day_result = self.simulate_day(date, portfolio, all_data)
                
                # Track portfolio value
                self.results['portfolio_values'].append({
                    'date': date,
                    'value': day_result['portfolio_value']
                })
                
                # Calculate daily return
                if len(self.results['portfolio_values']) > 1:
                    prev_value = self.results['portfolio_values'][-2]['value']
                    curr_value = day_result['portfolio_value']
                    daily_return = (curr_value - prev_value) / prev_value
                    self.results['daily_returns'].append(daily_return)
                
                # Track trades
                for trade in day_result['trades_executed'].get('buys', []) + day_result['trades_executed'].get('sells', []):
                    self.results['trade_history'].append(trade)
                    self.results['total_trades'] += 1
                    
            except Exception as e:
                log_error(f"Error processing day {date}: {e}")
                continue
        
        # Calculate performance metrics
        self._calculate_performance_metrics()
        
        log_info("Backtest completed successfully")
        return self.results
    
    def _calculate_performance_metrics(self):
        """Calculate comprehensive performance metrics"""
        if not self.results['portfolio_values']:
            return
        
        # Total return
        final_value = self.results['portfolio_values'][-1]['value']
        self.results['total_return'] = ((final_value - self.initial_capital) / self.initial_capital) * 100
        
        # Win/loss analysis
        profitable_trades = [t for t in self.results['trade_history'] if t.get('profit_loss', 0) > 0]
        losing_trades = [t for t in self.results['trade_history'] if t.get('profit_loss', 0) < 0]
        
        self.results['winning_trades'] = len(profitable_trades)
        self.results['losing_trades'] = len(losing_trades)
        self.results['win_rate'] = (len(profitable_trades) / max(len(self.results['trade_history']), 1)) * 100
        
        # Average win/loss
        if profitable_trades:
            self.results['avg_win'] = np.mean([t['profit_loss'] for t in profitable_trades])
        if losing_trades:
            self.results['avg_loss'] = np.mean([t['profit_loss'] for t in losing_trades])
        
        # Profit factor
        total_wins = sum(t['profit_loss'] for t in profitable_trades) if profitable_trades else 0
        total_losses = abs(sum(t['profit_loss'] for t in losing_trades)) if losing_trades else 1
        self.results['profit_factor'] = total_wins / total_losses if total_losses > 0 else 0
        
        # Maximum drawdown
        portfolio_values = [pv['value'] for pv in self.results['portfolio_values']]
        peak = np.maximum.accumulate(portfolio_values)
        drawdown = (peak - portfolio_values) / peak * 100
        self.results['max_drawdown'] = np.max(drawdown)
        
        # Sharpe ratio (simplified)
        if self.results['daily_returns']:
            daily_returns = np.array(self.results['daily_returns'])
            excess_return = np.mean(daily_returns)  # Assuming 0% risk-free rate
            volatility = np.std(daily_returns)
            self.results['sharpe_ratio'] = (excess_return / volatility) * np.sqrt(252) if volatility > 0 else 0
    
    def generate_report(self) -> str:
        """Generate comprehensive backtest report"""
        report = []
        report.append("=" * 60)
        report.append("VOLATILITYHUNTER COMPREHENSIVE BACKTEST REPORT")
        report.append("=" * 60)
        report.append(f"Initial Capital: ${self.initial_capital:,.2f}")
        report.append(f"Total Trading Days: {len(self.results['portfolio_values'])}")
        report.append("")
        
        # Performance Summary
        report.append("PERFORMANCE SUMMARY:")
        report.append(f"Total Return: {self.results['total_return']:.2f}%")
        report.append(f"Max Drawdown: {self.results['max_drawdown']:.2f}%")
        report.append(f"Sharpe Ratio: {self.results['sharpe_ratio']:.2f}")
        report.append("")
        
        # Trading Statistics
        report.append("TRADING STATISTICS:")
        report.append(f"Total Trades: {self.results['total_trades']}")
        report.append(f"Winning Trades: {self.results['winning_trades']}")
        report.append(f"Losing Trades: {self.results['losing_trades']}")
        report.append(f"Win Rate: {self.results['win_rate']:.2f}%")
        report.append(f"Average Win: ${self.results['avg_win']:.2f}")
        report.append(f"Average Loss: ${self.results['avg_loss']:.2f}")
        report.append(f"Profit Factor: {self.results['profit_factor']:.2f}")
        report.append("")
        
        # Final Portfolio Value
        if self.results['portfolio_values']:
            final_value = self.results['portfolio_values'][-1]['value']
            report.append(f"Final Portfolio Value: ${final_value:,.2f}")
            report.append(f"Total P&L: ${final_value - self.initial_capital:,.2f}")
        
        return "\n".join(report)

def run_complete_backtest():
    """Main function to run comprehensive backtest"""
    try:
        log_info("Starting VolatilityHunter comprehensive backtest...")
        
        # Initialize backtest engine
        engine = BacktestEngine(initial_capital=100000, max_positions=10)
        
        # Run backtest
        results = engine.run_backtest()
        
        # Generate report
        report = engine.generate_report()
        log_info("Backtest completed successfully")
        print(report)
        
        # Save results
        results_file = f"backtest_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(results_file, 'w') as f:
            # Convert non-serializable objects
            serializable_results = results.copy()
            serializable_results['trade_history'] = [
                {k: str(v) if isinstance(v, (datetime, pd.Timestamp)) else v 
                 for k, v in trade.items()} 
                for trade in results['trade_history']
            ]
            json.dump(serializable_results, f, indent=2)
        
        log_info(f"Backtest results saved to {results_file}")
        
        return results
        
    except Exception as e:
        log_error(f"Backtest failed: {e}")
        raise

if __name__ == "__main__":
    run_complete_backtest()
