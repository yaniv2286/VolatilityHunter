"""
VolatilityHunter - Standalone Trading Bot
Simple automation script for swing trading strategy
"""

from datetime import datetime
import sys
import os
from src.config import STOCK_LIST, STOCK_UNIVERSE_MODE, TICKER_FILTERS, TICKER_LIST_FILE, DATA_SOURCE
from src.data_loader import get_stock_data
from src.data_loader_factory import get_data_loader
from src.strategy import scan_all_stocks, get_portfolio_summary
from src.notifications import log_info, log_error
from src.ticker_manager import TickerManager
from src.tracker import Portfolio
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
    """Main execution flow for VolatilityHunter."""
    print("="*60)
    print("VolatilityHunter - Standalone Trading Bot")
    print("="*60)
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data Source: {DATA_SOURCE}")
    
    try:
        # Step 1: Initialize
        print("\n[STEP 1] Initializing...")
        log_info("Initializing VolatilityHunter...")
        
        # Clear log file to start fresh for this session
        try:
            with open('volatility_hunter.log', 'w') as f:
                f.write(f"VolatilityHunter Session Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
                f.write("="*60 + "\n")
            log_info("Log file cleared for new session")
        except Exception as e:
            log_warning(f"Could not clear log file: {e}")
        
        # Load portfolio and initialize components
        portfolio = Portfolio()
        data_loader = get_data_loader()
        email_notifier = EmailNotifier()
        
        print(f"  - Portfolio: ${portfolio.state['cash']:,.2f} cash, {len(portfolio.state['positions'])} positions")
        
        # Get active stock list
        active_stocks = get_active_stock_list()
        print(f"  - Stock Universe: {STOCK_UNIVERSE_MODE} ({len(active_stocks)} stocks)")
        log_info(f"Monitoring {len(active_stocks)} stocks")
        
        # Step 2: Update market data
        print("\n[STEP 2] Updating market data...")
        log_info("Starting market data update...")
        
        update_result = data_loader.update_all_stocks(
            stock_list=active_stocks,
            full_refresh=False
        )
        
        print(f"  - Updated: {update_result['updated']}/{update_result['total']} stocks")
        log_info(f"Data update complete: {update_result['updated']}/{update_result['total']} stocks")
        
        # Step 3: Update portfolio valuation
        print("\n[STEP 3] Updating portfolio valuation...")
        log_info("Updating portfolio valuation with current market prices...")
        
        portfolio_summary = portfolio.update_portfolio_valuation()
        
        print(f"  - Total Value: ${portfolio_summary['total_value']:,.2f}")
        print(f"  - Total Return: ${portfolio_summary['total_return_dollars']:,.2f} ({portfolio_summary['total_return_pct']:+.2f}%)")
        print(f"  - Positions: {portfolio_summary['num_positions']}/10")
        print(f"  - Cash: ${portfolio_summary['cash']:,.2f}")
        
        # Step 4: Scan for signals
        print("\n[STEP 4] Scanning for trading signals...")
        log_info("Scanning for trading signals...")
        
        stock_data = {}
        for ticker in active_stocks:
            df = get_stock_data(ticker)
            if df is not None:
                stock_data[ticker] = df
        
        scan_results = scan_all_stocks(stock_data)
        summary = get_portfolio_summary(scan_results)
        
        print(f"  - Total Stocks: {summary['total_stocks']}")
        print(f"  - BUY Signals: {summary['buy_signals']}")
        print(f"  - SELL Signals: {summary['sell_signals']}")
        print(f"  - HOLD Signals: {summary['hold_signals']}")
        print(f"  - Errors: {summary['errors']}")
        
        log_info(f"Scan complete: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL")
        
        # Step 5: Process trades
        print("\n[STEP 5] Processing paper trading...")
        log_info("Processing paper trading signals...")
        
        # Sort BUY signals by quality score (highest first)
        buy_signals = sorted(scan_results.get('BUY', []), 
                           key=lambda x: x.get('quality_score', 0), reverse=True)
        sell_signals = scan_results.get('SELL', [])
        
        executed_trades = portfolio.process_signals(buy_signals, sell_signals)
        
        print(f"  - Buys Executed: {len(executed_trades['buys'])}")
        print(f"  - Sells Executed: {len(executed_trades['sells'])}")
        
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
        
        # Step 6: Send email report
        print("\n[STEP 6] Sending email report...")
        log_info("Sending comprehensive email notification...")
        
        try:
            email_sent = email_notifier.send_comprehensive_scan_results(
                scan_results=scan_results,
                summary=summary,
                portfolio_summary=portfolio_summary,
                executed_trades=executed_trades,
                attach_log_file=True
            )
            
            if email_sent:
                print("  - Email sent successfully!")
                print("  - Log file attached: Yes")
                log_info("Comprehensive email notification sent successfully")
            else:
                print("  - Failed to send email")
                log_error("Failed to send email notification")
                
        except Exception as e:
            print(f"  - Email error: {e}")
            log_error(f"Email sending error: {e}")
        
        # Step 7: Final summary
        print("\n[STEP 7] Final Summary")
        print("="*60)
        print(f"[OK] VolatilityHunter completed successfully!")
        print(f"[DATA] Market Data: {update_result['updated']}/{update_result['total']} stocks updated")
        print(f"[SIGNALS] Signals: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL")
        print(f"[PORTFOLIO] Portfolio: ${portfolio_summary['total_value']:,.2f} ({portfolio_summary['total_return_pct']:+.2f}%)")
        print(f"[EMAIL] Email: {'Sent' if email_sent else 'Failed'}")
        print(f"[DURATION] Total runtime: {datetime.now() - datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)}")
        print("="*60)
        
        log_info("VolatilityHunter execution completed successfully")
        
        # Exit cleanly - linear execution complete
        sys.exit(0)
        
    except Exception as e:
        print(f"\n[ERROR] VolatilityHunter execution failed: {e}")
        log_error(f"VolatilityHunter execution failed: {e}")
        print("="*60)
        sys.exit(1)

if __name__ == '__main__':
    main()
