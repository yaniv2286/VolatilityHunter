#!/usr/bin/env python3
"""
VolatilityHunter Main Entry Point
Unified entry point for both manual execution and Task Scheduler
"""

import sys
import os
import argparse
from datetime import datetime
from typing import Dict, Any

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.config_manager import get_config, is_simulation, is_production
from src.backtest_engine import run_complete_backtest
from src.strategy import scan_all_stocks
from src.tracker import Portfolio
from src.smart_data_loader_factory import get_data_loader
from src.storage import DataStorage
from src.notifications import log_info, log_error, log_warning, alert_signal, alert_error
from src.log_collector import LogCollector
from src.email_notifier import EmailNotifier

class VolatilityHunter:
    """Main VolatilityHunter application"""
    
    def __init__(self):
        self.config = get_config()
        self.storage = DataStorage()
        self.start_time = datetime.now()
        
    def run_backtest_mode(self) -> Dict[str, Any]:
        """Run in backtesting mode"""
        log_info("Starting VolatilityHunter in BACKTEST mode")
        
        try:
            results = run_complete_backtest()
            
            # Send email with backtest results
            if self.config.config.email_enabled:
                self._send_backtest_email(results)
            
            return results
            
        except Exception as e:
            log_error(f"Backtest failed: {e}")
            raise
    
    def run_trading_mode(self) -> Dict[str, Any]:
        """Run in trading mode (simulation or production)"""
        mode_str = "SIMULATION" if is_simulation() else "PRODUCTION"
        log_info(f"Starting VolatilityHunter in {mode_str} mode")
        
        results = {
            'mode': mode_str,
            'start_time': self.start_time.strftime('%Y-%m-%d %H:%M:%S'),
            'data_updated': False,
            'signals_generated': False,
            'trades_executed': False,
            'email_sent': False,
            'errors': [],
            'portfolio_summary': {}
        }
        
        try:
            # Step 1: Update data
            log_info("Step 1: Updating market data...")
            data_loader = get_data_loader()
            
            # Display data source information
            if hasattr(data_loader, 'get_data_source_info'):
                source_info = data_loader.get_data_source_info()
                log_info(f"Data Source: {source_info['source']} ({source_info['reason']})")
            
            # Get stock list for data loader
            from src.ticker_manager import TickerManager
            ticker_manager = TickerManager()
            stock_list = ticker_manager.get_filtered_tickers()
            
            update_stats = data_loader.update_all_stocks(stock_list)
            results['data_updated'] = True
            results['update_stats'] = update_stats
            log_info(f"Data update completed: {update_stats}")
            
            # Step 2: Generate signals
            log_info("Step 2: Generating trading signals...")
            all_data = self._load_all_stock_data()
            signals = scan_all_stocks(all_data)
            results['signals'] = signals
            results['signals_generated'] = True
            
            # Log signals
            for signal_type, signal_list in signals.items():
                if signal_list:
                    log_info(f"Generated {len(signal_list)} {signal_type} signals")
                    for signal in signal_list[:3]:  # Log first 3 of each type
                        # Get price from indicators or use 0 if not available
                        price = signal.get('indicators', {}).get('price', 0)
                        indicators_str = str(signal.get('indicators', {}))
                        alert_signal(signal['ticker'], signal_type, price, indicators_str)
            
            # Step 3: Execute trades (if not in backtest mode)
            if not self.config.config.backtest_enabled:
                log_info("Step 3: Executing trades...")
                portfolio = Portfolio()
                
                # Get current prices
                current_prices = self._get_current_prices(all_data)
                
                # Process signals
                buy_signals = sorted(signals['BUY'], key=lambda x: x.get('quality_score', 0), reverse=True)
                sell_signals = signals['SELL']
                
                trades = portfolio.process_signals(buy_signals, sell_signals, current_prices)
                results['trades'] = trades
                results['trades_executed'] = True
                
                # Update portfolio valuation
                portfolio_summary = portfolio.update_portfolio_valuation()
                results['portfolio_summary'] = portfolio_summary
                log_info(f"Portfolio updated: ${portfolio_summary['total_value']:,.2f}")
            
            # Step 4: Send email report
            if self.config.config.email_enabled:
                log_info("Step 4: Sending email report...")
                self._send_trading_email(results)
                results['email_sent'] = True
            
            log_info(f"VolatilityHunter {mode_str} run completed successfully")
            return results
            
        except Exception as e:
            error_msg = f"Trading mode execution failed: {e}"
            log_error(error_msg)
            results['errors'].append(error_msg)
            
            # Send error email
            if self.config.config.email_enabled:
                self._send_error_email(results)
            
            raise
    
    def run_quick_dryrun(self) -> Dict[str, Any]:
        """Run quick dryrun to verify system health"""
        log_info("Starting VolatilityHunter quick dryrun...")
        
        results = {
            'dryrun': True,
            'start_time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'checks': {}
        }
        
        try:
            # Check 1: Configuration
            log_info("Check 1: Configuration...")
            self.config.print_configuration()
            results['checks']['configuration'] = 'PASS'
            
            # Check 2: Data access
            log_info("Check 2: Data access...")
            test_tickers = ['AAPL', 'MSFT', 'GOOGL']
            data_accessible = 0
            for ticker in test_tickers:
                try:
                    df = self.storage.load_data(ticker)
                    if df is not None and len(df) > 0:
                        data_accessible += 1
                        log_info(f"  {ticker}: ✅ {len(df)} rows available")
                    else:
                        log_info(f"  {ticker}: ❌ No data")
                except Exception as e:
                    log_info(f"  {ticker}: ❌ Error - {e}")
            
            results['checks']['data_access'] = f'PASS ({data_accessible}/{len(test_tickers)} tickers)'
            
            # Check 3: Strategy engine
            log_info("Check 3: Strategy engine...")
            try:
                from src.strategy import analyze_stock
                df = self.storage.load_data('AAPL')
                if df is not None:
                    analysis = analyze_stock(df, 'AAPL')
                    log_info(f"  Strategy test: ✅ {analysis['signal']} - {analysis['reason']}")
                    results['checks']['strategy'] = 'PASS'
                else:
                    results['checks']['strategy'] = 'FAIL - No data'
            except Exception as e:
                log_info(f"  Strategy test: ❌ {e}")
                results['checks']['strategy'] = f'FAIL - {e}'
            
            # Check 4: Portfolio system
            log_info("Check 4: Portfolio system...")
            try:
                portfolio = Portfolio()
                log_info(f"  Portfolio: ✅ ${portfolio.state['cash']:,.2f} cash, {len(portfolio.state['positions'])} positions")
                results['checks']['portfolio'] = 'PASS'
            except Exception as e:
                log_info(f"  Portfolio: ❌ {e}")
                results['checks']['portfolio'] = f'FAIL - {e}'
            
            # Check 5: Email system
            log_info("Check 5: Email system...")
            if self.config.config.email_enabled:
                results['checks']['email'] = 'ENABLED'
            else:
                results['checks']['email'] = 'DISABLED'
            
            # Overall status
            all_checks = list(results['checks'].values())
            failed_checks = [c for c in all_checks if 'FAIL' in str(c)]
            
            if not failed_checks:
                log_info("✅ DRYRUN PASSED - System is healthy and ready")
                results['status'] = 'PASS'
            else:
                log_warning(f"⚠️ DRYRUN ISSUES - {len(failed_checks)} checks failed")
                results['status'] = 'FAIL'
            
            return results
            
        except Exception as e:
            log_error(f"Dryrun failed: {e}")
            results['status'] = 'ERROR'
            results['error'] = str(e)
            return results
    
    def _load_all_stock_data(self) -> Dict[str, Any]:
        """Load all available stock data"""
        all_data = {}
        ticker_list = self.storage.list_available_tickers()
        
        for ticker in ticker_list:
            try:
                df = self.storage.load_data(ticker)
                if df is not None and len(df) > 0:
                    all_data[ticker] = df
            except Exception as e:
                log_warning(f"Failed to load {ticker}: {e}")
        
        log_info(f"Loaded {len(all_data)} tickers for analysis")
        return all_data
    
    def _get_current_prices(self, all_data: Dict[str, Any]) -> Dict[str, float]:
        """Get current prices for all stocks"""
        current_prices = {}
        for ticker, df in all_data.items():
            if len(df) > 0:
                current_prices[ticker] = df.iloc[-1]['Close']
        return current_prices
    
    def _send_trading_email(self, results: Dict[str, Any]):
        """Send trading execution email"""
        try:
            # Get recent logs
            log_collector = LogCollector()
            logs = log_collector.get_recent_logs(hours=24)
            formatted_logs = log_collector.format_logs_for_email(logs)
            
            # Create email content
            subject = f"VolatilityHunter {results['mode']} Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body = []
            body.append("VOLATILITYHUNTER EXECUTION REPORT")
            body.append("=" * 50)
            body.append(f"Mode: {results['mode']}")
            body.append(f"Start Time: {results['start_time']}")
            body.append("")
            
            # Data update status
            if results.get('data_updated'):
                stats = results.get('update_stats', {})
                body.append("DATA UPDATE:")
                body.append(f"  Processed: {stats.get('processed', 0)} stocks")
                body.append(f"  Updated: {stats.get('updated', 0)} stocks")
                body.append(f"  Errors: {stats.get('errors', 0)} stocks")
                body.append("")
            
            # Signals summary
            if results.get('signals_generated'):
                signals = results.get('signals', {})
                body.append("SIGNALS GENERATED:")
                for signal_type, signal_list in signals.items():
                    if signal_list:
                        body.append(f"  {signal_type}: {len(signal_list)} signals")
                        # Show top 3 signals
                        if signal_type in ['BUY', 'SELL']:
                            for i, signal in enumerate(signal_list[:3]):
                                body.append(f"    {i+1}. {signal['ticker']} - {signal['reason']}")
                body.append("")
            
            # Portfolio summary
            if results.get('portfolio_summary'):
                portfolio = results['portfolio_summary']
                body.append("PORTFOLIO SUMMARY:")
                body.append(f"  Total Value: ${portfolio.get('total_value', 0):,.2f}")
                body.append(f"  Cash: ${portfolio.get('cash', 0):,.2f}")
                body.append(f"  Positions: {portfolio.get('position_count', 0)}")
                body.append(f"  Daily P&L: ${portfolio.get('daily_pnl', 0):,.2f} ({portfolio.get('daily_pnl_pct', 0):.2f}%)")
                body.append("")
            
            # Add logs
            body.append("RECENT LOGS:")
            body.append(formatted_logs)
            
            # Send email
            email_body = "\n".join(body)
            send_email(subject, email_body, attach_log_file=True)
            
            log_info("Trading report email sent successfully")
            
        except Exception as e:
            log_error(f"Failed to send trading email: {e}")
    
    def _send_backtest_email(self, results: Dict[str, Any]):
        """Send backtest results email"""
        try:
            subject = f"VolatilityHunter Backtest Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body = []
            body.append("VOLATILITYHUNTER BACKTEST REPORT")
            body.append("=" * 50)
            body.append(f"Initial Capital: ${results['initial_capital']:,.2f}")
            body.append(f"Total Return: {results['total_return']:.2f}%")
            body.append(f"Max Drawdown: {results['max_drawdown']:.2f}%")
            body.append(f"Sharpe Ratio: {results['sharpe_ratio']:.2f}")
            body.append("")
            body.append("TRADING STATISTICS:")
            body.append(f"  Total Trades: {results['total_trades']}")
            body.append(f"  Win Rate: {results['win_rate']:.2f}%")
            body.append(f"  Profit Factor: {results['profit_factor']:.2f}")
            body.append("")
            
            email_body = "\n".join(body)
            send_email(subject, email_body, attach_log_file=True)
            
            log_info("Backtest report email sent successfully")
            
        except Exception as e:
            log_error(f"Failed to send backtest email: {e}")
    
    def _send_error_email(self, results: Dict[str, Any]):
        """Send error notification email"""
        try:
            subject = f"VolatilityHunter ERROR Report - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
            
            body = []
            body.append("VOLATILITYHUNTER ERROR REPORT")
            body.append("=" * 50)
            body.append(f"Mode: {results.get('mode', 'Unknown')}")
            body.append(f"Start Time: {results.get('start_time', 'Unknown')}")
            body.append("")
            
            if results.get('errors'):
                body.append("ERRORS ENCOUNTERED:")
                for error in results['errors']:
                    body.append(f"  • {error}")
                body.append("")
            
            # Get recent logs
            log_collector = LogCollector()
            logs = log_collector.get_recent_logs(hours=24)
            formatted_logs = log_collector.format_logs_for_email(logs)
            body.append("RECENT LOGS:")
            body.append(formatted_logs)
            
            email_body = "\n".join(body)
            send_email(subject, email_body, attach_log_file=True)
            
            log_info("Error report email sent successfully")
            
        except Exception as e:
            log_error(f"Failed to send error email: {e}")

def send_email(subject: str, body: str, attach_log_file: bool = False):
    """Simple email sending function"""
    try:
        notifier = EmailNotifier()
        # Use the comprehensive email method
        notifier.send_comprehensive_scan_results(
            scan_results={},
            summary=body,
            portfolio_summary=None,
            executed_trades=None,
            attach_log_file=attach_log_file
        )
        return True
    except Exception as e:
        log_error(f"Failed to send email: {e}")
        return False

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='VolatilityHunter Trading System')
    parser.add_argument('--mode', choices=['trading', 'backtest', 'dryrun'], 
                       default='trading', help='Execution mode')
    parser.add_argument('--config', help='Configuration file path')
    
    args = parser.parse_args()
    
    try:
        # Initialize VolatilityHunter
        vh = VolatilityHunter()
        
        # Run based on mode
        if args.mode == 'backtest':
            results = vh.run_backtest_mode()
        elif args.mode == 'dryrun':
            results = vh.run_quick_dryrun()
        else:  # trading
            results = vh.run_trading_mode()
        
        # Print summary
        print("\n" + "=" * 60)
        print("VOLATILITYHUNTER EXECUTION SUMMARY")
        print("=" * 60)
        print(f"Mode: {args.mode.upper()}")
        print(f"Start Time: {vh.start_time.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration: {datetime.now() - vh.start_time}")
        
        if args.mode == 'dryrun':
            print(f"Status: {results.get('status', 'Unknown')}")
            print("Checks:")
            for check, status in results.get('checks', {}).items():
                print(f"  {check}: {status}")
        
        print("=" * 60)
        
        return 0
        
    except Exception as e:
        log_error(f"VolatilityHunter execution failed: {e}")
        print(f"ERROR: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())
