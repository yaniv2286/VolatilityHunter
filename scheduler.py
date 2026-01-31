"""
Daily Scheduler for VolatilityHunter
Runs daily updates and scans, sends email notifications
"""

import schedule
import time
from datetime import datetime
import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader_factory import get_data_loader
from src.data_loader import get_stock_data
from src.strategy import scan_all_stocks, get_portfolio_summary
from src.email_notifier import EmailNotifier
from src.tracker import Portfolio
from src.notifications import log_info, log_error
from src.config import DATA_SOURCE

def get_active_stock_list():
    """Get the active stock list."""
    from main import get_active_stock_list as get_list
    return get_list()

def daily_job():
    """Main daily job: update data, scan, and send email."""
    print("="*60)
    print(f"VolatilityHunter Daily Job Started")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Data Source: {DATA_SOURCE}")
    print("="*60)
    
    try:
        # Step 1: Get stock list
        log_info("Getting active stock list...")
        stock_list = get_active_stock_list()
        log_info(f"Monitoring {len(stock_list)} stocks")
        
        # Step 2: Update data (incremental)
        log_info("Starting incremental data update...")
        data_loader = get_data_loader()
        update_result = data_loader.update_all_stocks(
            stock_list=stock_list,
            full_refresh=False
        )
        log_info(f"Data update complete: {update_result['updated']}/{update_result['total']} stocks")
        
        # Step 3: Scan for signals
        log_info("Scanning for trading signals...")
        stock_data = {}
        for ticker in stock_list:
            df = get_stock_data(ticker)
            if df is not None:
                stock_data[ticker] = df
        
        scan_results = scan_all_stocks(stock_data)
        summary = get_portfolio_summary(scan_results)
        
        log_info(f"Scan complete: {summary['buy_signals']} BUY, {summary['sell_signals']} SELL")
        
        # Step 4: Process paper trading
        log_info("Processing paper trading signals...")
        portfolio = Portfolio()
        trades = portfolio.process_signals(scan_results['BUY'], scan_results['SELL'])
        
        # Get current prices for portfolio positions
        current_prices = {}
        for ticker in portfolio.get_current_positions():
            if ticker in stock_data:
                df = stock_data[ticker]
                if len(df) > 0:
                    current_prices[ticker] = df.iloc[-1]['Close']
        
        portfolio_summary = portfolio.get_summary(current_prices)
        log_info(f"Portfolio: ${portfolio_summary['total_value']:.2f} ({portfolio_summary['total_return_pct']:.2f}%)")
        
        # Step 5: Send email notification
        log_info("Sending email notification...")
        notifier = EmailNotifier()
        email_sent = notifier.send_scan_results(scan_results, summary, portfolio_summary)
        
        if email_sent:
            log_info("Email notification sent successfully")
        else:
            log_error("Failed to send email notification")
        
        # Print summary
        print("\n" + "="*60)
        print("Daily Job Complete!")
        print("="*60)
        print(f"Stocks Updated: {update_result['updated']}/{update_result['total']}")
        print(f"BUY Signals: {summary['buy_signals']}")
        print(f"SELL Signals: {summary['sell_signals']}")
        print(f"Email Sent: {'Yes' if email_sent else 'No'}")
        print("="*60 + "\n")
        
    except Exception as e:
        log_error(f"Daily job failed: {e}")
        print(f"ERROR: {e}")

def weekly_full_update():
    """Weekly full data refresh."""
    print("="*60)
    print(f"VolatilityHunter Weekly Full Update")
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("="*60)
    
    try:
        stock_list = get_active_stock_list()
        log_info(f"Starting full refresh for {len(stock_list)} stocks...")
        
        data_loader = get_data_loader()
        result = data_loader.update_all_stocks(
            stock_list=stock_list,
            full_refresh=True
        )
        
        log_info(f"Full refresh complete: {result['updated']}/{result['total']} stocks")
        print(f"✓ Full refresh complete: {result['updated']}/{result['total']} stocks")
        
    except Exception as e:
        log_error(f"Weekly update failed: {e}")
        print(f"ERROR: {e}")

def run_scheduler():
    """Run the scheduler."""
    print("="*60)
    print("VolatilityHunter Scheduler Started")
    print("="*60)
    print(f"Data Source: {DATA_SOURCE}")
    print(f"Schedule:")
    print("  - Daily scan: Every day at 9:00 AM")
    print("  - Weekly full update: Every Sunday at 6:00 AM")
    print("="*60 + "\n")
    
    # Schedule daily job at 9:00 AM
    schedule.every().day.at("09:00").do(daily_job)
    
    # Schedule weekly full update on Sunday at 6:00 AM
    schedule.every().sunday.at("06:00").do(weekly_full_update)
    
    # Run once immediately for testing
    print("Running initial scan...")
    daily_job()
    
    # Keep running
    print("\nScheduler is now running. Press Ctrl+C to stop.")
    while True:
        schedule.run_pending()
        time.sleep(60)  # Check every minute

if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user.")
        sys.exit(0)
