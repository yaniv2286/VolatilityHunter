"""
VolatilityHunter - Unified Execution Engine
3-Pillar Architecture: Trading Execution Engine with Mode Switching
"""

import os
os.environ['TOKENIZERS_PARALLELISM'] = 'false'
import os
import sys
import argparse
from datetime import datetime

# FORCE WORKING DIRECTORY TO SCRIPT LOCATION
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)
print(f"Working Directory set to: {os.getcwd()}")

# CRITICAL: Setup logging FIRST before any other imports that might use logging
from src.notifications import setup_logging
setup_logging()

from src.config import STOCK_LIST, STOCK_UNIVERSE_MODE, TICKER_FILTERS, TICKER_LIST_FILE, DATA_SOURCE
from src.strategy_v7_2 import analyze_stock_v7_2, check_exit_conditions_v7_2, add_indicators_v7_2
from src.notifications import log_info, log_error, log_warning
from src.ticker_manager import TickerManager
from src.technical_utils import get_position_risk_data, calculate_atr, calculate_sma_200
from src.execution import get_executor
from src.tracker import Portfolio
from src.email_notifier import EmailNotifier
from src.shields import apply_universal_shields
import json


class DataLoaderFactory:
    """Factory for creating appropriate data loaders based on mode"""
    
    @staticmethod
    def create_loader(mode: str, target_date: str = None):
        """
        Create data loader based on execution mode
        
        Args:
            mode: Execution mode ('live', 'sim', 'backtest')
            target_date: Target date for sim mode (YYYY-MM-DD)
        
        Returns:
            Data loader instance
        """
        if mode == 'sim':
            # Import SimulatedParquetLoader for simulation mode
            from simulation.simulated_data_loader import SimulatedParquetLoader
            return SimulatedParquetLoader(target_date)
        else:
            # Use standard Tiingo loader for live and backtest modes
            from src.data_loader_factory import get_data_loader
            return get_data_loader()


class PortfolioManagerFactory:
    """Factory for creating appropriate portfolio managers based on mode"""
    
    @staticmethod
    def create_portfolio(mode: str):
        """
        Create portfolio manager based on execution mode
        
        Args:
            mode: Execution mode ('live', 'sim', 'backtest')
        
        Returns:
            Portfolio instance
        """
        if mode == 'sim':
            # Use simulation portfolio
            sim_dir = os.path.join(script_dir, 'simulation')
            portfolio_file = os.path.join(sim_dir, "portfolio_sim.json")
            
            # Create portfolio_sim.json if it doesn't exist
            if not os.path.exists(portfolio_file):
                clean_portfolio = {
                    "cash": 100000.0,
                    "positions": {},
                    "trade_history": [],
                    "total_value": 100000.0,
                    "last_updated": datetime.now().isoformat(),
                    "execution_mode": "SIMULATION"
                }
                with open(portfolio_file, 'w') as f:
                    json.dump(clean_portfolio, f, indent=2)
                log_info(f"Created simulation portfolio: {portfolio_file}")
            
            return Portfolio(portfolio_file)
        else:
            # Use live portfolio
            return Portfolio()


def scan_all_stocks_v7_2(stock_data_dict, reference_date: str):
    """
    v7.2: Scan all stocks using Hybrid Blueprint Logic with universal shields
    """
    results = {
        'BUY': [],
        'SELL': [],
        'HOLD': [],
        'ERROR': [],
        'SHIELD_REJECTED': []
    }
    
    # Major tickers for verbose diagnostics
    verbose_tickers = ['AAPL', 'MSFT', 'GOOGL', 'AMZN', 'TSLA', 'NVDA', 'META', 'BRK.B', 'JPM', 'V']
    
    for ticker, df in stock_data_dict.items():
        try:
            # Apply universal shields first
            shields = apply_universal_shields(ticker, reference_date)
            
            if not all(shields.values()):
                # Shield rejected - log and skip
                failed_shields = [name for name, safe in shields.items() if not safe]
                results['SHIELD_REJECTED'].append({
                    'ticker': ticker,
                    'reason': f"Shields failed: {', '.join(failed_shields)}",
                    'shields': shields
                })
                
                # Verbose logging for major tickers
                if ticker in verbose_tickers:
                    print(f"[VERBOSE] {ticker}: SHIELD REJECTED - {failed_shields}")
                    print(f"[VERBOSE] {ticker}: Shields details: {shields}")
                
                continue
            
            # Shields passed - proceed with analysis
            analysis = analyze_stock_v7_2(df, ticker)
            signal = analysis['signal']
            
            result = {
                'ticker': ticker,
                'signal': signal,
                'reason': analysis['reason'],
                'indicators': analysis['indicators'],
                'shields': shields
            }
            
            results[signal].append(result)
            
            # Verbose logging for major tickers
            if ticker in verbose_tickers:
                print(f"[VERBOSE] {ticker}: {signal} - {analysis['reason']}")
                indicators = analysis['indicators']
                print(f"[VERBOSE] {ticker}: Price=${indicators.get('price', 'N/A'):.2f}, SMA200=${indicators.get('sma_200', 'N/A'):.2f}, StochK={indicators.get('stoch_k', 'N/A'):.1f}, Volume={indicators.get('volume', 'N/A'):,}")
                print(f"[VERBOSE] {ticker}: Volume Gate: {indicators.get('volume', 0) > (indicators.get('volume_sma', 0) * 1.5)}, Trend Gate: {indicators.get('price', 0) > indicators.get('sma_200', 0)}")
            
        except Exception as e:
            log_error(f"Error analyzing {ticker}: {e}")
            results['ERROR'].append({
                'ticker': ticker,
                'error': str(e)
            })
            
            # Verbose logging for major tickers
            if ticker in verbose_tickers:
                print(f"[VERBOSE] {ticker}: ERROR - {e}")
    
    return results


def main():
    """Main execution engine with mode switching"""
    
    # Parse command line arguments
    parser = argparse.ArgumentParser(description='VolatilityHunter Unified Execution Engine')
    parser.add_argument('--mode', choices=['live', 'sim', 'backtest'], default='live',
                       help='Execution mode (default: live)')
    parser.add_argument('--date', type=str, help='Target date for sim mode (YYYY-MM-DD)')
    
    args = parser.parse_args()
    
    mode = args.mode
    target_date = args.date
    reference_date = target_date if mode == 'sim' else datetime.now().strftime('%Y-%m-%d')
    
    print("="*80)
    print("VolatilityHunter - Unified Execution Engine")
    print(f"Mode: {mode.upper()}")
    if mode == 'sim':
        print(f"Target Date: {target_date}")
    print("="*80)
    
    # Critical: Initialize execution tracking
    execution_failed = False
    traceback_details = None
    
    try:
        # Step 1: Dependency Injection - Create appropriate components
        print("[STEP 1] Initializing Components...")
        
        # Create data loader based on mode
        data_loader = DataLoaderFactory.create_loader(mode, target_date)
        print(f"  - Data Loader: {'SimulatedParquetLoader' if mode == 'sim' else 'TiingoDataLoader'}")
        
        # Create portfolio manager based on mode
        portfolio = PortfolioManagerFactory.create_portfolio(mode)
        portfolio_file = "portfolio_sim.json" if mode == 'sim' else "portfolio.json"
        print(f"  - Portfolio Manager: {portfolio_file}")
        
        # Create executor
        portfolio_file_path = os.path.join(script_dir, 'simulation', 'portfolio_sim.json') if mode == 'sim' else 'data/portfolio.json'
        executor = get_executor(portfolio_file=portfolio_file_path)
        print(f"  - Executor: Paper Trading ({portfolio_file_path})")
        
        # Step 2: Load Stock Universe
        print("[STEP 2] Loading Stock Universe...")
        ticker_manager = TickerManager()
        tickers = ticker_manager.get_filtered_tickers()
        print(f"  - Loaded {len(tickers)} tickers")
        
        # Step 3: Load Market Data
        print("[STEP 3] Loading Market Data...")
        stock_data_dict = {}
        
        if mode == 'sim':
            # Simulation mode - use SimulatedParquetLoader with progress logging
            total_tickers = len(tickers)
            batch_size = 100  # Log progress every 100 tickers
            
            for i, ticker in enumerate(tickers):
                df = data_loader.load_data(ticker)
                if df is not None and not df.empty:
                    stock_data_dict[ticker] = df
                
                # Log batch progress
                if (i + 1) % batch_size == 0 or (i + 1) == total_tickers:
                    progress = (i + 1) / total_tickers * 100
                    print(f"  - Processed {i + 1}/{total_tickers} tickers ({progress:.1f}%) - {len(stock_data_dict)} loaded")
        else:
            # Live mode - use standard data loader
            data_loader_instance = data_loader
            update_result = data_loader_instance.update_all_stocks(tickers)
            stock_data_dict = data_loader_instance.get_all_data()
        
        print(f"  - Loaded data for {len(stock_data_dict)} stocks")
        
        # Step 4: Scan for Signals with Universal Shields
        print("[STEP 4] Scanning for Signals...")
        scan_results = scan_all_stocks_v7_2(stock_data_dict, reference_date)
        
        summary = {
            'total_scanned': len(stock_data_dict),
            'buy_signals': len(scan_results['BUY']),
            'sell_signals': len(scan_results['SELL']),
            'hold_signals': len(scan_results['HOLD']),
            'errors': len(scan_results['ERROR']),
            'shield_rejected': len(scan_results['SHIELD_REJECTED'])
        }
        
        print(f"  - Total Scanned: {summary['total_scanned']}")
        print(f"  - BUY Signals: {summary['buy_signals']}")
        print(f"  - SELL Signals: {summary['sell_signals']}")
        print(f"  - Shield Rejected: {summary['shield_rejected']}")
        print(f"  - Errors: {summary['errors']}")
        
        # Step 5: Execute Trades
        print("[STEP 5] Executing Trades...")
        executed_trades = {'buys': [], 'sells': []}
        
        # Load current portfolio
        current_portfolio = portfolio.state
        available_cash = current_portfolio.get('cash', 100000.0)
        current_positions = current_portfolio.get('positions', {})
        
        # Process exits first
        for signal in scan_results['SELL']:
            ticker = signal['ticker']
            if ticker in current_positions:
                position = current_positions[ticker]
                exit_price = signal['indicators']['price']
                
                sell_signal = {
                    'ticker': ticker,
                    'action': 'SELL',
                    'price': exit_price,
                    'indicators': signal['indicators'],
                    'reason': signal['reason']
                }
                
                result = executor.execute_sell(sell_signal, position)
                if result.get('success', False):
                    executed_trades['sells'].append(result)
                    log_info(f"Executed SELL: {ticker} @ ${exit_price:.2f}")
        
        # Process buys with position cap
        max_positions = 10
        current_position_count = len(current_positions)
        
        for signal in scan_results['BUY'][:10]:  # Limit to top 10
            ticker = signal['ticker']
            
            # Check position cap
            if current_position_count >= max_positions:
                log_info(f"Position cap reached ({max_positions}), skipping {ticker}")
                break
            
            # Skip if already holding
            if ticker in current_positions:
                continue
            
            buy_price = signal['indicators']['price']
            
            # Calculate trade cost first
            position_size = executor.calculate_position_size(signal, available_cash)
            trade_cost = position_size
            
            # CRITICAL: Check real-time cash before executing
            if available_cash < trade_cost:
                log_info(f"[CASH LIMIT] Out of cash: need ${trade_cost:.2f}, have ${available_cash:.2f} - skipping {ticker}")
                break
            
            buy_signal = {
                'ticker': ticker,
                'action': 'BUY',
                'price': buy_price,
                'indicators': signal['indicators'],
                'reason': signal['reason']
            }
            
            result = executor.execute_buy(buy_signal, available_cash)
            if result.get('success', False):
                executed_trades['buys'].append(result)
                # CRITICAL: Update available_cash immediately after each trade
                available_cash = result.get('remaining_cash', available_cash)
                current_position_count += 1
                log_info(f"Executed BUY: {ticker} @ ${buy_price:.2f} - Remaining cash: ${available_cash:.2f}")
                
                # Check position cap
                if current_position_count >= max_positions:
                    log_info(f"Position cap reached ({max_positions}), stopping further buys")
                    break
        
        print(f"  - Executed {len(executed_trades['buys'])} buys, {len(executed_trades['sells'])} sells")
        
        # Step 6: Update Portfolio Valuation
        print("[STEP 6] Updating Portfolio Valuation...")
        
        # CRITICAL FIX: Reload portfolio state after trade execution
        # The executor modifies the portfolio file, but portfolio.state is stale
        portfolio.state = portfolio._load_state()
        
        # Load updated portfolio
        updated_portfolio = portfolio.state
        
        # Calculate total value dynamically
        cash = updated_portfolio.get('cash', 0.0)
        positions = updated_portfolio.get('positions', {})
        total_value = cash
        
        for ticker, position in positions.items():
            shares = position.get('shares', 0)
            if shares > 0:
                if mode == 'sim':
                    # Use simulated data loader for current price
                    current_price = data_loader.get_latest_price(ticker)
                else:
                    # Use standard data loader for current price
                    df = stock_data_dict.get(ticker)
                    if df is not None and not df.empty:
                        # Try different price column names
                        for col in ['adjClose', 'Close', 'close', 'price']:
                            if col in df.columns:
                                current_price = df[col].iloc[-1]
                                break
                
                if current_price and current_price > 0:
                    position_value = shares * current_price
                    total_value += position_value
        
        # Update portfolio with correct total value
        portfolio.state['total_value'] = total_value
        portfolio._save_state()
        
        updated_portfolio_summary = portfolio.get_summary()
        print(f"  - Portfolio Value: ${total_value:,.2f}")
        print(f"  - Cash: ${cash:,.2f}")
        print(f"  - Positions: {len(positions)}")
        
        # Step 7: Send Report
        print("[STEP 7] Sending Report...")
        email_sent = False
        
        try:
            email_notifier = EmailNotifier()
            
            # Send comprehensive report in ALL modes
            subject = f"VolatilityHunter Daily Report: {mode.upper()}"
            
            email_sent = email_notifier.send_comprehensive_scan_results(
                scan_results=scan_results,
                summary=summary,
                portfolio_summary=updated_portfolio_summary,
                executed_trades=executed_trades,
                attach_log_file=True
            )
            
            if email_sent:
                print("  - Daily report sent successfully!")
                print("  - Log file attached: Yes")
            else:
                print("  - Failed to send daily report")
        
        except Exception as e:
            print(f"  - Email error: {e}")
            log_error(f"Daily report email error: {e}")
        
        # Step 8: Final Summary
        print("\n[STEP 8] Final Summary")
        print("="*80)
        print(f"[OK] VolatilityHunter completed successfully!")
        print(f"[MODE] Execution: {mode.upper()}")
        if mode == 'sim':
            print(f"[DATE] Target: {target_date}")
        print(f"[DATA] Market Data: {len(stock_data_dict)} stocks loaded")
        print(f"[SIGNALS] Signals: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL")
        print(f"[SHIELDS] Rejected: {summary['shield_rejected']}")
        print(f"[TRADES] Executed: {len(executed_trades['buys'])} buys, {len(executed_trades['sells'])} sells")
        print(f"[PORTFOLIO] Value: ${total_value:,.2f}")
        print(f"[EMAIL] Report: {'Sent' if email_sent else 'Skipped' if mode == 'sim' else 'Failed'}")
        print("="*80)
        
        log_info(f"VolatilityHunter execution completed successfully in {mode.upper()} mode")
        
        # Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        # CRITICAL: Enhanced exception handling with full traceback
        execution_failed = True
        import traceback
        traceback_details = traceback.format_exc()
        
        print(f"\n[ERROR] VolatilityHunter execution failed: {e}")
        log_error(f"FATAL: {str(e)}", exc_info=True)
        print("="*80)
        sys.exit(1)
        
    finally:
        # CRITICAL: Guaranteed cleanup and error notification
        try:
            if execution_failed and traceback_details:
                # Force send error email on failure
                try:
                    email_notifier = EmailNotifier()
                    error_subject = f"VolatilityHunter CRITICAL ERROR - {mode.upper()} mode"
                    email_notifier.send_error_email(
                        subject=error_subject,
                        error_message=str(e) if 'e' in locals() else "Unknown error",
                        traceback_details=traceback_details,
                        mode=mode
                    )
                    print("[CRITICAL] Error notification sent")
                except Exception as email_error:
                    print(f"[CRITICAL] Failed to send error notification: {email_error}")
                    log_error(f"Failed to send error notification: {email_error}")
            
            # CRITICAL: Flush all logging buffers (V5 Critical Lesson)
            try:
                import logging
                logging.shutdown()
                print("[CRITICAL] Logging buffers flushed to disk")
            except Exception as log_error:
                print(f"[CRITICAL] Failed to shutdown logging: {log_error}")
            
        except Exception as cleanup_error:
            print(f"[CRITICAL] Cleanup error: {cleanup_error}")
            # Last resort - don't let cleanup errors hide original errors


if __name__ == '__main__':
    main()
