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

def _check_needs_full_refresh(stock_list, sample_size=50, min_rows=200):
    """Check if most stocks need a full data refresh by sampling."""
    from src.storage import DataStorage
    storage = DataStorage()
    
    sample = stock_list[:sample_size]
    sufficient_count = 0
    
    for ticker in sample:
        df = storage.load_data(ticker)
        if df is not None and len(df) >= min_rows:
            sufficient_count += 1
    
    pct_sufficient = sufficient_count / len(sample) * 100
    log_info(f"[DATA CHECK] {sufficient_count}/{len(sample)} sampled stocks have >= {min_rows} rows ({pct_sufficient:.0f}%)")
    
    # If less than 50% of sampled stocks have enough data, trigger full refresh
    needs_refresh = pct_sufficient < 50
    if needs_refresh:
        log_info(f"[DATA CHECK] Full refresh needed - only {pct_sufficient:.0f}% have sufficient data")
    else:
        log_info(f"[DATA CHECK] Incremental update sufficient - {pct_sufficient:.0f}% have enough data")
    
    return needs_refresh

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
        
        # Step 2: Check if full refresh is needed (auto-detect insufficient data)
        data_loader = get_data_loader()
        needs_full_refresh = _check_needs_full_refresh(stock_list)
        
        if needs_full_refresh:
            log_info("[AUTO-BACKFILL] Most stocks lack historical data. Running full 2-year refresh...")
            print("[AUTO-BACKFILL] Downloading 2 years of history for all stocks...")
            update_result = data_loader.update_all_stocks(
                stock_list=stock_list,
                full_refresh=True
            )
        else:
            log_info("Starting incremental data update...")
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
        # Sort BUY signals by quality score (highest first)
        buy_signals = sorted(scan_results.get('BUY', []),
                           key=lambda x: x.get('quality_score', 0), reverse=True)
        sell_signals = scan_results.get('SELL', [])
        trades = portfolio.process_signals(buy_signals, sell_signals)
        
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
        print(f"[OK] Full refresh complete: {result['updated']}/{result['total']} stocks")
        
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
    
    # Check if this was just the initial scan (no scheduled jobs yet)
    # If so, exit after completion
    if len(schedule.jobs) > 0:
        print("\nScheduler is now running. Press Ctrl+C to stop.")
        while True:
            schedule.run_pending()
            time.sleep(60)  # Check every minute
    else:
        print("\nInitial scan completed. Exiting...")
        sys.exit(0)

if __name__ == "__main__":
    try:
        run_scheduler()
    except KeyboardInterrupt:
        print("\n\nScheduler stopped by user.")
        sys.exit(0)
