"""
VolatilityHunter - The Hunter
3-Pillar Architecture: Trading Execution Engine
"""

import os
import sys

# FORCE WORKING DIRECTORY TO SCRIPT LOCATION
script_dir = os.path.dirname(os.path.abspath(__file__))
os.chdir(script_dir)
sys.path.append(script_dir)
print(f"📍 Working Directory set to: {os.getcwd()}")

# CRITICAL: Setup logging FIRST before any other imports that might use logging
from src.notifications import setup_logging
setup_logging()

from datetime import datetime
from src.config import STOCK_LIST, STOCK_UNIVERSE_MODE, TICKER_FILTERS, TICKER_LIST_FILE, DATA_SOURCE
from src.data_loader import get_stock_data
from src.data_loader_factory import get_data_loader
from src.strategy import scan_all_stocks, get_portfolio_summary
from src.notifications import log_info, log_error, log_warning
from src.ticker_manager import TickerManager
from src.execution import get_executor
from src.email_notifier import EmailNotifier

def get_active_stock_list():
    """Get the complete universe of 2,150 US stocks for production."""
    ticker_manager = TickerManager()
    
    # Always use full universe for production
    if os.path.exists(TICKER_LIST_FILE):
        tickers = ticker_manager.load_ticker_list(TICKER_LIST_FILE)
        log_info(f"Loaded {len(tickers)} tickers from cached file")
        return tickers
    else:
        # Get complete US stock universe
        data_loader = get_data_loader()
        if DATA_SOURCE == 'yfinance':
            log_info("Downloading complete US stock universe...")
            all_tickers = data_loader.download_nasdaq_tickers()
            
            # Apply production filters: CAGR > 15% and basic quality filters
            filtered_df = data_loader.filter_tickers_by_criteria(
                all_tickers,
                min_price=TICKER_FILTERS['min_price'],
                min_volume=TICKER_FILTERS['min_volume']
            )
            tickers = filtered_df['ticker'].tolist()
            log_info(f"Filtered to {len(tickers)} high-quality tickers")
        else:
            tickers = ticker_manager.get_filtered_tickers(
                min_price=TICKER_FILTERS['min_price'],
                min_volume=TICKER_FILTERS['min_volume'],
                exchanges=TICKER_FILTERS['exchanges']
            )
        
        ticker_manager.save_ticker_list(tickers, TICKER_LIST_FILE)
        log_info(f"Saved {len(tickers)} tickers to cache")
        return tickers

def main():
    """Main execution flow for VolatilityHunter - The Hunter"""
    print("="*60)
    print("VolatilityHunter - The Hunter")
    print("3-Pillar Architecture: Trading Execution Engine")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data Source: {DATA_SOURCE}")
    
    try:
        # Step 1: Initialize Components
        print("\n[STEP 1] Initializing Components...")
        log_info("Initializing VolatilityHunter Trading Engine...")
        
        # Define data directory
        data_dir = os.path.join(os.getcwd(), 'data')
        
        # Initialize executor based on config with explicit portfolio path
        portfolio_file = os.path.join(data_dir, "portfolio.json")
        executor = get_executor(portfolio_file=portfolio_file)
        execution_mode = executor.execution_mode
        print(f"  - Execution Mode: {execution_mode}")
        
        # Initialize data loader and email notifier
        data_loader = get_data_loader()
        email_notifier = EmailNotifier()
        
        print(f"  - Data Loader: {type(data_loader).__name__}")
        print(f"  - Email Notifier: Configured")
        
        # Get executor portfolio summary
        portfolio_summary = executor.get_portfolio_summary()
        print(f"  - Portfolio: ${portfolio_summary['total_value']:,.2f} total value")
        print(f"  - Positions: {portfolio_summary['num_positions']}/10")
        print(f"  - Cash: ${portfolio_summary['cash']:,.2f}")
        
        # Step 2: Get Stock Universe
        print("\n[STEP 2] Loading Stock Universe...")
        active_stocks = get_active_stock_list()
        print(f"  - Stock Universe: {STOCK_UNIVERSE_MODE} ({len(active_stocks)} stocks)")
        log_info(f"Monitoring {len(active_stocks)} stocks")
        
        # Step 3: Update Market Data
        print("\n[STEP 3] Updating Market Data...")
        log_info("Starting market data update...")
        
        update_result = data_loader.update_all_stocks(
            stock_list=active_stocks,
            full_refresh=False
        )
        
        print(f"  - Updated: {update_result['updated']}/{update_result['total']} stocks")
        log_info(f"Data update complete: {update_result['updated']}/{update_result['total']} stocks")
        
        # Step 4: Scan for Trading Signals
        print("\n[STEP 4] Scanning for Trading Signals...")
        log_info("Scanning for trading signals...")
        
        # Load stock data for analysis
        stock_data = {}
        for ticker in active_stocks:
            df = get_stock_data(ticker)
            if df is not None:
                stock_data[ticker] = df
        
        # Generate signals
        scan_results = scan_all_stocks(stock_data)
        summary = get_portfolio_summary(scan_results)
        
        print(f"  - Total Stocks: {summary['total_stocks']}")
        print(f"  - BUY Signals: {summary['buy_signals']}")
        print(f"  - SELL Signals: {summary['sell_signals']}")
        print(f"  - HOLD Signals: {summary['hold_signals']}")
        print(f"  - Errors: {summary['errors']}")
        
        log_info(f"Scan complete: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL")
        
        # Step 5: Execute Trading Signals
        print("\n[STEP 5] Executing Trading Signals...")
        log_info("Executing trading signals...")
        
        # Sort signals by quality
        buy_signals = sorted(scan_results.get('BUY', []), 
                           key=lambda x: x.get('quality_score', 0), reverse=True)
        sell_signals = scan_results.get('SELL', [])
        
        # Execute trades through executor
        executed_trades = executor.process_signals(buy_signals, sell_signals)
        
        print(f"  - Buys Executed: {len(executed_trades['buys'])}")
        print(f"  - Sells Executed: {len(executed_trades['sells'])}")
        print(f"  - Errors: {len(executed_trades['errors'])}")
        
        # Show top signals
        if summary['buy_signals'] > 0:
            print(f"\n[TOP BUY SIGNALS]:")
            for i, signal in enumerate(buy_signals[:5]):  # Show top 5
                print(f"  {i+1}. {signal['ticker']}: ${signal['indicators']['price']:.2f} | Quality: {signal.get('quality_score', 0):.2f}")
                print(f"     Reason: {signal['reason']}")
        
        if summary['sell_signals'] > 0:
            print(f"\n[SELL SIGNALS]:")
            for i, signal in enumerate(sell_signals[:5]):  # Show top 5
                print(f"  {i+1}. {signal['ticker']}: ${signal['indicators']['price']:.2f}")
                print(f"     Reason: {signal['reason']}")
        
        # Step 6: Update Portfolio Valuation
        print("\n[STEP 6] Updating Portfolio Valuation...")
        log_info("Updating portfolio valuation...")
        
        # CRITICAL FIX: Fetch current prices for all portfolio positions
        current_prices = {}
        portfolio_positions = executor.state['positions']
        
        print(f"  - Fetching current prices for {len(portfolio_positions)} portfolio positions...")
        
        for ticker in portfolio_positions.keys():
            try:
                # Load current data from parquet file
                df = data_loader.storage.load_data(ticker)
                if df is not None and not df.empty:
                    # Debug: print column names to understand the issue
                    if hasattr(df, 'columns'):
                        log_info(f"Debug {ticker}: columns = {df.columns.tolist()}")
                    
                    # Try different column name variations
                    latest_price = None
                    if 'close' in df.columns:
                        latest_price = df.iloc[-1]['close']
                    elif 'Close' in df.columns:
                        latest_price = df.iloc[-1]['Close']
                    elif 'price' in df.columns:
                        latest_price = df.iloc[-1]['price']
                    elif 'Price' in df.columns:
                        latest_price = df.iloc[-1]['Price']
                    else:
                        # Last resort - try to find any numeric column
                        numeric_cols = df.select_dtypes(include=['number']).columns
                        if len(numeric_cols) > 0:
                            latest_price = df.iloc[-1][numeric_cols[0]]
                            log_warning(f"{ticker}: Using fallback column {numeric_cols[0]}")
                    
                    if latest_price is not None:
                        current_prices[ticker] = float(latest_price)
                        print(f"  - {ticker}: ${latest_price:.2f}")
                    else:
                        log_error(f"{ticker}: Could not find price column in data")
                        # Fallback to entry price
                        current_prices[ticker] = float(portfolio_positions[ticker]['entry_price'])
                else:
                    log_warning(f"No data available for {ticker}, using entry price")
                    # Fallback to entry price if no current data available
                    current_prices[ticker] = float(portfolio_positions[ticker]['entry_price'])
            except Exception as e:
                log_error(f"Error fetching price for {ticker}: {e}")
                # Fallback to entry price on error
                current_prices[ticker] = float(portfolio_positions[ticker]['entry_price'])
        
        # Get updated portfolio summary with current prices
        updated_portfolio_summary = executor.get_portfolio_summary(current_prices)
        
        print(f"  - Total Value: ${updated_portfolio_summary['total_value']:,.2f}")
        print(f"  - Total Return: ${updated_portfolio_summary['total_return_dollars']:,.2f} ({updated_portfolio_summary['total_return_pct']:+.2f}%)")
        print(f"  - Positions: {updated_portfolio_summary['num_positions']}/10")
        print(f"  - Cash: ${updated_portfolio_summary['cash']:,.2f}")
        
        # Step 7: Send Daily Report
        print("\n[STEP 7] Sending Daily Report...")
        log_info("Sending daily trading report...")
        
        try:
            # Prepare email content
            subject = f"VolatilityHunter Daily Report: {execution_mode}"
            
            # Send comprehensive report with log attachment
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
                log_info("Daily trading report sent successfully")
            else:
                print("  - Failed to send daily report")
                log_error("Failed to send daily trading report")
                
        except Exception as e:
            print(f"  - Email error: {e}")
            log_error(f"Daily report email error: {e}")
        
        # Step 8: Final Summary
        print("\n[STEP 8] Final Summary")
        print("="*60)
        print(f"[OK] VolatilityHunter completed successfully!")
        print(f"[MODE] Execution: {execution_mode}")
        print(f"[DATA] Market Data: {update_result['updated']}/{update_result['total']} stocks updated")
        print(f"[SIGNALS] Signals: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL")
        print(f"[TRADES] Executed: {len(executed_trades['buys'])} buys, {len(executed_trades['sells'])} sells")
        print(f"[PORTFOLIO] Value: ${updated_portfolio_summary['total_value']:,.2f} ({updated_portfolio_summary['total_return_pct']:+.2f}%)")
        print(f"[EMAIL] Report: {'Sent' if email_sent else 'Failed'}")
        print(f"[DURATION] Runtime: {datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}")
        print("="*60)
        
        log_info("VolatilityHunter trading execution completed successfully")
        
        # Exit cleanly
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] VolatilityHunter execution failed: {e}")
        log_error(f"VolatilityHunter execution failed: {e}")
        print("="*60)
        sys.exit(1)

if __name__ == '__main__':
    main()
