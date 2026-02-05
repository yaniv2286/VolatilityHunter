#!/usr/bin/env python3
"""
Task Scheduler Verification Script
Verifies all components are working for automated daily execution
"""

import sys
import os
import subprocess
from datetime import datetime
sys.path.append('src')

def check_python_environment():
    """Check Python and virtual environment."""
    print("🐍 Python Environment Check:")
    print("-" * 40)
    
    # Check Python version
    python_version = sys.version
    print(f"Python Version: {python_version}")
    
    # Check if in virtual environment
    if hasattr(sys, 'real_prefix') or (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("✅ Virtual Environment: Active")
    else:
        print("⚠️  Virtual Environment: Not detected")
    
    # Check key packages
    try:
        import pandas
        print(f"✅ Pandas: {pandas.__version__}")
    except ImportError:
        print("❌ Pandas: Not installed")
    
    try:
        import yfinance
        print(f"✅ YFinance: {yfinance.__version__}")
    except ImportError:
        print("❌ YFinance: Not installed")
    
    print()

def check_project_files():
    """Check essential project files."""
    print("📁 Project Files Check:")
    print("-" * 40)
    
    essential_files = [
        'main.py',
        'src/tracker.py',
        'src/strategy.py',
        'src/email_notifier.py',
        'data/portfolio.json',
        '.env',
        'task_scheduler_run.ps1',
        'setup_scheduler.ps1'
    ]
    
    for file_path in essential_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
    
    print()

def check_portfolio_state():
    """Check portfolio configuration."""
    print("💼 Portfolio State Check:")
    print("-" * 40)
    
    try:
        from src.tracker import Portfolio
        portfolio = Portfolio()
        
        print(f"✅ Portfolio loaded successfully")
        print(f"   Cash: ${portfolio.state['cash']:,.2f}")
        print(f"   Positions: {len(portfolio.state['positions'])}/10")
        print(f"   Trade History: {len(portfolio.state['trade_history'])} trades")
        
        # Check position quality
        if portfolio.state['positions']:
            quality_scores = [pos['quality_score'] for pos in portfolio.state['positions'].values()]
            avg_quality = sum(quality_scores) / len(quality_scores)
            print(f"   Avg Quality Score: {avg_quality:.2f}")
        
    except Exception as e:
        print(f"❌ Portfolio error: {e}")
    
    print()

def check_email_configuration():
    """Check email configuration."""
    print("📧 Email Configuration Check:")
    print("-" * 40)
    
    try:
        from src.email_notifier import EmailNotifier
        from src.config import SENDER_EMAIL, RECIPIENT_EMAIL
        
        notifier = EmailNotifier()
        
        print(f"✅ Email Notifier: Configured")
        print(f"   SMTP Server: {notifier.smtp_server}")
        print(f"   Sender: {SENDER_EMAIL}")
        print(f"   Recipient: {RECIPIENT_EMAIL}")
        
    except Exception as e:
        print(f"❌ Email configuration error: {e}")
    
    print()

def check_data_availability():
    """Check data availability."""
    print("📊 Data Availability Check:")
    print("-" * 40)
    
    try:
        from src.data_loader import get_stock_data
        
        # Test with a common stock
        test_ticker = "AAPL"
        df = get_stock_data(test_ticker)
        
        if df is not None and len(df) > 0:
            print(f"✅ {test_ticker}: {len(df)} days of data")
            print(f"   Latest: {df.iloc[-1]['Close']:.2f}")
        else:
            print(f"❌ {test_ticker}: No data available")
        
    except Exception as e:
        print(f"❌ Data check error: {e}")
    
    print()

def check_task_scheduler_files():
    """Check Task Scheduler specific files."""
    print("⏰ Task Scheduler Files Check:")
    print("-" * 40)
    
    scheduler_files = [
        'task_scheduler_run.ps1',
        'task_scheduler_run.bat',
        'setup_scheduler.ps1',
        'TASK_SCHEDULER_GUIDE.md'
    ]
    
    for file_path in scheduler_files:
        if os.path.exists(file_path):
            print(f"✅ {file_path}")
        else:
            print(f"❌ {file_path}")
    
    print()

def run_quick_test():
    """Run a quick system test."""
    print("🧪 Quick System Test:")
    print("-" * 40)
    
    try:
        # Test strategy analysis
        from src.strategy import analyze_stock
        from src.data_loader import get_stock_data
        
        test_ticker = "AAPL"
        df = get_stock_data(test_ticker)
        
        if df is not None:
            analysis = analyze_stock(df)
            print(f"✅ Strategy Analysis: {analysis['signal']} for {test_ticker}")
            print(f"   Reason: {analysis['reason']}")
        else:
            print(f"❌ Strategy Analysis: No data for {test_ticker}")
        
    except Exception as e:
        print(f"❌ Quick test error: {e}")
    
    print()

def main():
    """Run all verification checks."""
    print("=" * 60)
    print("VOLATILITYHUNTER TASK SCHEDULER VERIFICATION")
    print("=" * 60)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Run all checks
    check_python_environment()
    check_project_files()
    check_portfolio_state()
    check_email_configuration()
    check_data_availability()
    check_task_scheduler_files()
    run_quick_test()
    
    print("=" * 60)
    print("VERIFICATION COMPLETE")
    print("=" * 60)
    print()
    print("Next Steps:")
    print("1. Run PowerShell as Administrator")
    print("2. Execute: powershell -ExecutionPolicy Bypass -File 'setup_scheduler.ps1'")
    print("3. Verify with: Get-ScheduledTask -TaskName 'VolatilityHunter Daily'")
    print()
    print("Manual Test Run:")
    print("powershell -ExecutionPolicy Bypass -File 'task_scheduler_run.ps1' -Test")
    print()
    print("Daily execution will run at 9:00 AM automatically!")

if __name__ == "__main__":
    main()
