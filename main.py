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
from src.strategy_v7_2 import analyze_stock_v7_2, check_exit_conditions_v7_2, add_indicators_v7_2
from src.notifications import log_info, log_error, log_warning
from src.ticker_manager import TickerManager
from src.technical_utils import get_position_risk_data, calculate_atr, calculate_sma_200
from src.execution import get_executor
from src.tracker import Portfolio
from src.email_notifier import EmailNotifier

def scan_all_stocks_v7_2(stock_data_dict):
    """
    v7.2: Scan all stocks using Hybrid Blueprint Logic
    """
    results = {
        'BUY': [],
        'SELL': [],
        'HOLD': [],
        'ERROR': []
    }
    
    for ticker, df in stock_data_dict.items():
        try:
            analysis = analyze_stock_v7_2(df, ticker)
            signal = analysis['signal']
            
            result = {
                'ticker': ticker,
                'signal': signal,
                'reason': analysis['reason'],
                'indicators': analysis['indicators'],
                'quality_score': analysis.get('quality_score', 0),
                'is_power_stock': analysis.get('is_power_stock', False)  # v7.2: Power Stock status
            }
            
            if signal in ['BUY', 'SELL', 'HOLD', 'INSUFFICIENT_DATA']:
                if signal == 'INSUFFICIENT_DATA':
                    results['ERROR'].append(result)
                else:
                    results[signal].append(result)
                    
                if signal in ['BUY', 'SELL']:
                    from src.notifications import alert_signal
                    alert_signal(
                        ticker,
                        signal,
                        analysis['indicators'].get('price', 0),
                        analysis['indicators']
                    )
            
        except Exception as e:
            log_error(f"Error analyzing {ticker}: {e}")
            results['ERROR'].append({
                'ticker': ticker,
                'signal': 'ERROR',
                'reason': str(e),
                'indicators': {}
            })
    
    return results

def get_portfolio_summary_v7_2(scan_results):
    """v7.2: Get portfolio summary with Power Stock tracking"""
    summary = {
        'total_stocks': sum(len(v) for v in scan_results.values()),
        'buy_signals': len(scan_results.get('BUY', [])),
        'sell_signals': len(scan_results.get('SELL', [])),
        'hold_signals': len(scan_results.get('HOLD', [])),
        'errors': len(scan_results.get('ERROR', [])),
        'buy_list': [s['ticker'] for s in scan_results.get('BUY', [])],
        'sell_list': [s['ticker'] for s in scan_results.get('SELL', [])],
        'power_stocks': [s['ticker'] for s in scan_results.get('BUY', []) if s.get('is_power_stock', False)]
    }
    return summary

def check_v7_2_exit_conditions(portfolio_positions, stock_data):
    """
    v7.2: Check exit conditions for all portfolio positions
    """
    positions_to_close = []
    
    for ticker, position in portfolio_positions.items():
        if ticker in stock_data:
            df = stock_data[ticker]
            df_with_indicators = add_indicators_v7_2(df)
            
            should_exit, exit_reason = check_exit_conditions_v7_2(df_with_indicators, position)
            
            if should_exit:
                latest = df_with_indicators.iloc[-1]
                current_price = latest['adjClose'] if 'adjClose' in latest else latest['close']
                positions_to_close.append((ticker, current_price, exit_reason))
    
    return positions_to_close


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
        
        # v7.2 HYBRID STRATEGY: EXIT ENGINE - Check existing positions BEFORE scanning for new buys
        print("\n[STEP 3A] v7.2 Hybrid Exit Engine...")
        log_info("Checking v7.2 exit conditions for existing positions...")
        
        portfolio_positions = executor.state['positions']
        executed_trades = {'sells': [], 'buys': []}  # Initialize executed trades
        
        if portfolio_positions:
            print(f"  - Checking {len(portfolio_positions)} open positions for v7.2 exit conditions...")
            
            # Load stock data for exit analysis
            exit_stock_data = {}
            for ticker in portfolio_positions.keys():
                df = get_stock_data(ticker)
                if df is not None:
                    exit_stock_data[ticker] = df
            
            # Check v7.2 exit conditions
            positions_to_close = check_v7_2_exit_conditions(portfolio_positions, exit_stock_data)
            
            if positions_to_close:
                print(f"  - Found {len(positions_to_close)} positions to close:")
                for ticker, exit_price, reason in positions_to_close:
                    print(f"    - {ticker}: ${exit_price:.2f} ({reason})")
                
                # Execute exit trades
                exit_trades = []
                for ticker, exit_price, reason in positions_to_close:
                    position = portfolio_positions[ticker]
                    
                    # Create sell signal
                    sell_signal = {
                        'ticker': ticker,
                        'indicators': {'price': exit_price},
                        'reason': reason
                    }
                    
                    # Execute sell
                    result = executor.execute_sell(sell_signal, position)
                    
                    if result['success']:
                        exit_trades.append(result['trade'])
                
                executed_trades['sells'].extend(exit_trades)
                print(f"  - Executed {len(exit_trades)} v7.2 exit trades")
            else:
                print(f"  - No v7.2 exit conditions triggered")
                log_info("No v7.2 exit conditions triggered for existing positions")
        else:
            print(f"  - No open positions to check")
            log_info("No open positions to check")
        
        # Step 4: Scan for Trading Signals using v7.2 Hybrid Strategy
        print("\n[STEP 4] Scanning for v7.2 Hybrid Trading Signals...")
        log_info("Scanning for v7.2 hybrid trading signals...")
        
        # Load stock data for analysis
        stock_data = {}
        for ticker in active_stocks:
            df = get_stock_data(ticker)
            if df is not None:
                stock_data[ticker] = df
        
        # Generate v7.2 signals
        scan_results = scan_all_stocks_v7_2(stock_data)
        summary = get_portfolio_summary_v7_2(scan_results)
        
        print(f"  - Total Stocks: {summary['total_stocks']}")
        print(f"  - BUY Signals: {summary['buy_signals']}")
        print(f"  - SELL Signals: {summary['sell_signals']}")
        print(f"  - HOLD Signals: {summary['hold_signals']}")
        print(f"  - Errors: {summary['errors']}")
        if summary['power_stocks']:
            print(f"  - Power Stocks: {len(summary['power_stocks'])} ({', '.join(summary['power_stocks'])})")
        
        log_info(f"v7.2 scan complete: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL, {len(summary['power_stocks'])} Power Stocks")
        
        # Step 5: Execute v7.2 Trading Signals
        print("\n[STEP 5] Executing v7.2 Trading Signals...")
        log_info("Executing v7.2 trading signals...")
        
        # Sort signals by quality (v7.2 includes Power Stock bonus)
        buy_signals = sorted(scan_results.get('BUY', []), 
                           key=lambda x: x.get('quality_score', 0), reverse=True)
        sell_signals = scan_results.get('SELL', [])
        
        # Add v7.2 specific data to buy signals
        for signal in buy_signals:
            ticker = signal['ticker']
            # v7.2: Indicators already include ATR, SMAs, and Power Stock status
            # No additional data loading needed
        
        # Process remaining signals through executor (v7.2 compatible)
        remaining_trades = executor.process_signals(buy_signals, sell_signals)
        
        # Combine exit trades and signal trades
        executed_trades['buys'].extend(remaining_trades.get('buys', []))
        executed_trades['sells'].extend(remaining_trades.get('sells', []))
        
        print(f"  - Exit Trades Executed: {len(executed_trades['sells'])}")
        print(f"  - Buy Trades Executed: {len(executed_trades['buys'])}")
        print(f"  - Total Trades Executed: {len(executed_trades['sells']) + len(executed_trades['buys'])}")
        
        # Show top v7.2 signals
        if summary['buy_signals'] > 0:
            print(f"\n[TOP v7.2 BUY SIGNALS]:")
            for i, signal in enumerate(buy_signals[:5]):  # Show top 5
                power_status = "POWER STOCK" if signal.get('is_power_stock', False) else "Standard"
                print(f"  {i+1}. {signal['ticker']}: ${signal['indicators']['price']:.2f} | Quality: {signal.get('quality_score', 0):.2f} | {power_status}")
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
