#!/usr/bin/env python3
"""
Time-Shifted Forward Test - Replay Loop
Runs daily simulations from 2026-01-01 to today with proper delays.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime, timedelta
from typing import List

# Add src to path for imports (need to go up one level from simulation/)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.notifications import log_info, log_warning, log_error
from src.email_notifier import EmailNotifier
import smtplib

def reset_simulation_portfolio():
    """
    Reset portfolio_sim.json to exactly $100,000 cash and 0 positions.
    """
    sim_dir = os.path.dirname(os.path.abspath(__file__))
    sim_portfolio_file = os.path.join(sim_dir, "portfolio_sim.json")
    
    # Create clean portfolio state
    clean_portfolio = {
        "cash": 100000.0,
        "positions": {},
        "trade_history": [],
        "total_value": 100000.0,
        "last_updated": datetime.now().isoformat(),
        "execution_mode": "SIMULATION"
    }
    
    # Save clean portfolio
    with open(sim_portfolio_file, 'w') as f:
        json.dump(clean_portfolio, f, indent=2)
    
    log_info(f"Reset simulation portfolio: ${clean_portfolio['cash']:,.2f} cash, 0 positions")
    print(f"[OK] Reset simulation portfolio to ${clean_portfolio['cash']:,.2f} cash")


def get_trading_days(start_date: str, end_date: str) -> List[str]:
    """
    Generate list of valid trading days (weekdays) between start_date and end_date.
    Excludes weekends.
    
    Args:
        start_date: Start date in YYYY-MM-DD format
        end_date: End date in YYYY-MM-DD format
        
    Returns:
        List of trading day strings in YYYY-MM-DD format
    """
    start = datetime.strptime(start_date, '%Y-%m-%d')
    end = datetime.strptime(end_date, '%Y-%m-%d')
    
    trading_days = []
    current = start
    
    while current <= end:
        # Only include weekdays (Monday=0, Friday=4)
        if current.weekday() < 5:
            trading_days.append(current.strftime('%Y-%m-%d'))
        
        current += timedelta(days=1)
    
    return trading_days


def run_simulation_for_date(target_date: str) -> tuple:
    """
    Run simulation for a single date using unified main.py and collect daily summary.
    
    Args:
        target_date: Target date in YYYY-MM-DD format
        
    Returns:
        Tuple: (success: bool, daily_summary: dict or None)
    """
    try:
        # Run unified main.py in simulation mode
        cmd = [sys.executable, 'main_unified.py', '--mode', 'sim', '--date', target_date]
        
        log_info(f"Running simulation for {target_date}...")
        print(f"\n📅 Running simulation for {target_date}")
        
        result = subprocess.run(
            cmd,
            cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),  # Run from VolatilityHunter root
            capture_output=True,
            text=True,
            timeout=300  # 5 minute timeout per simulation
        )
        
        if result.returncode == 0:
            log_info(f"Simulation successful for {target_date}")
            print(f"[OK] Simulation completed for {target_date}")
            
            # Parse daily summary from output
            daily_summary = parse_daily_summary(result.stdout, target_date)
            return True, daily_summary
        else:
            log_error(f"Simulation failed for {target_date}: {result.stderr}")
            print(f"[ERROR] Simulation failed for {target_date}")
            return False, None
            
    except subprocess.TimeoutExpired:
        log_error(f"Simulation timeout for {target_date}")
        print(f"[ERROR] Simulation timeout for {target_date}")
        return False, None
    except Exception as e:
        log_error(f"Error running simulation for {target_date}: {e}")
        print(f"[ERROR] Error running simulation: {e}")
        return False, None


def parse_daily_summary(output, target_date):
    """
    Parse portfolio summary from simulation output.
    
    Args:
        output: Subprocess stdout text
        target_date: Target date string
        
    Returns:
        Dict with daily summary data
    """
    summary = {
        'date': target_date,
        'portfolio_value': 0.0,
        'cash': 0.0,
        'positions': 0,
        'trades': 0
    }
    
    lines = output.split('\n')
    for line in lines:
        if '[PORTFOLIO] Value:' in line:
            try:
                # Extract: [PORTFOLIO] Value: $96,078.19 | Positions: 3
                value_part = line.split('Value: $')[1].split(' |')[0]
                summary['portfolio_value'] = float(value_part.replace(',', ''))
            except:
                pass
        elif '[PORTFOLIO] Final Cash:' in line or 'Cash:' in line:
            try:
                # Extract cash value
                if 'Cash:' in line:
                    cash_part = line.split('Cash: $')[1].split(' |')[0]
                    summary['cash'] = float(cash_part.replace(',', ''))
            except:
                pass
        elif 'Positions:' in line:
            try:
                # Extract position count
                pos_part = line.split('Positions: ')[1]
                summary['positions'] = int(pos_part)
            except:
                pass
        elif '[TRADES]' in line:
            try:
                # Extract trade count: [TRADES] 8 BUY signals, 7 exits
                trades_part = line.split('[TRADES] ')[1].split(' BUY signals')[0]
                buy_trades = int(trades_part)
                exits_part = line.split('BUY signals, ')[1].split(' exits')[0]
                exit_trades = int(exits_part)
                summary['trades'] = buy_trades + exit_trades
            except:
                pass
    
    return summary


def send_master_email_report(daily_summaries, start_date, end_date, successful_runs, failed_runs):
    """
    Send consolidated master email report with log attachment.
    
    Args:
        daily_summaries: List of daily summary dictionaries
        start_date: Simulation start date
        end_date: Simulation end date
        successful_runs: Number of successful runs
        failed_runs: Number of failed runs
    """
    try:
        # Initialize email notifier
        email_notifier = EmailNotifier()
        
        # Create master report content
        report_subject = f"VolatilityHunter: Simulation Report [{start_date} to {end_date}]"
        
        # Build summary table
        report_body = f"""
VolatilityHunter Time-Shifted Simulation - Master Report
=====================================================
Period: {start_date} to {end_date}
Execution Mode: SIMULATION

Simulation Summary:
- Total Trading Days: {len(daily_summaries)}
- Successful Runs: {successful_runs}
- Failed Runs: {failed_runs}
- Success Rate: {successful_runs/(successful_runs+failed_runs)*100:.1f}%

Daily Portfolio Progression:
Date        | Portfolio Value | Cash    | Positions | Trades
------------|----------------|---------|-----------|--------
"""
        
        # Add daily data to table
        for summary in daily_summaries:
            date = summary['date']
            value = summary['portfolio_value']
            cash = summary['cash']
            positions = summary['positions']
            trades = summary['trades']
            
            report_body += f"{date} | ${value:>11,.2f} | ${cash:>7,.2f} | {positions:>9} | {trades:>6}\n"
        
        # Add final statistics
        if daily_summaries:
            first_value = daily_summaries[0]['portfolio_value']
            final_value = daily_summaries[-1]['portfolio_value']
            total_return = final_value - 100000  # Started with $100k
            return_pct = (total_return / 100000) * 100
            
            report_body += f"""
Final Statistics:
- Starting Value: $100,000.00
- Final Value: ${final_value:,.2f}
- Total Return: ${total_return:,.2f} ({return_pct:+.2f}%)
- Best Day: ${max(s['portfolio_value'] for s in daily_summaries):,.2f}
- Worst Day: ${min(s['portfolio_value'] for s in daily_summaries):,.2f}
"""
        
        # Prepare log file attachment
        log_file_path = None
        try:
            # Create simulation log file path
            logs_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'logs')
            os.makedirs(logs_dir, exist_ok=True)
            
            # Create consolidated log file
            log_file_path = os.path.join(logs_dir, f"VH_Sim_Full_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.log")
            
            # Collect all log entries from simulation period
            with open(log_file_path, 'w') as log_file:
                log_file.write(f"VolatilityHunter Simulation Log - {start_date} to {end_date}\n")
                log_file.write("="*60 + "\n\n")
                
                # Add daily summaries to log
                for summary in daily_summaries:
                    log_file.write(f"Date: {summary['date']}\n")
                    log_file.write(f"Portfolio Value: ${summary['portfolio_value']:,.2f}\n")
                    log_file.write(f"Cash: ${summary['cash']:,.2f}\n")
                    log_file.write(f"Positions: {summary['positions']}\n")
                    log_file.write(f"Trades: {summary['trades']}\n")
                    log_file.write("-" * 40 + "\n")
        
        except Exception as e:
            log_warning(f"Could not create log attachment: {e}")
        
        # Send email with attachment
        attachments = [log_file_path] if log_file_path and os.path.exists(log_file_path) else []
        
        success = email_notifier.send_email(report_subject, report_body, attachments)
        
        if success:
            log_info("Master simulation report sent successfully via SMTP")
        else:
            log_error("Email notifier returned False - check SMTP configuration")
            
    except smtplib.SMTPAuthenticationError as e:
        log_error(f"SMTP Authentication Error: {e}")
        print(f"[SMTP ERROR] Authentication failed: {e}")
    except smtplib.SMTPRecipientsRefused as e:
        log_error(f"SMTP Recipients Refused: {e}")
        print(f"[SMTP ERROR] Recipients refused: {e}")
    except smtplib.SMTPSenderRefused as e:
        log_error(f"SMTP Sender Refused: {e}")
        print(f"[SMTP ERROR] Sender refused: {e}")
    except smtplib.SMTPServerDisconnected as e:
        log_error(f"SMTP Server Disconnected: {e}")
        print(f"[SMTP ERROR] Server disconnected: {e}")
    except smtplib.SMTPException as e:
        log_error(f"SMTP Error: {e}")
        print(f"[SMTP ERROR] General SMTP error: {e}")
    except ConnectionError as e:
        log_error(f"Connection Error: {e}")
        print(f"[SMTP ERROR] Connection failed: {e}")
    except TimeoutError as e:
        log_error(f"Timeout Error: {e}")
        print(f"[SMTP ERROR] Connection timeout: {e}")
    except Exception as e:
        log_error(f"Unexpected email error: {e}")
        print(f"[EMAIL ERROR] Unexpected error: {e}")


def main():
    """Main entry point for simulation loop."""
    print("="*80)
    print("VolatilityHunter - Time-Shifted Forward Test")
    print("Replay Loop: Daily Simulation from 2026-01-01 to Today")
    print("="*80)
    
    # Configuration
    start_date = "2026-01-01"
    end_date = datetime.now().strftime('%Y-%m-%d')  # Today
    delay_between_runs = 15  # 15 seconds to prevent SMTP rate limits
    
    print(f"Start Date: {start_date}")
    print(f"End Date: {end_date}")
    print(f"Delay between runs: {delay_between_runs} seconds")
    print()
    
    # Step 1: Reset simulation portfolio
    print("[STEP] Step 1: Resetting simulation portfolio...")
    reset_simulation_portfolio()
    
    # Step 2: Generate trading days
    print("[STEP] Step 2: Generating trading days...")
    trading_days = get_trading_days(start_date, end_date)
    total_days = len(trading_days)
    
    print(f"Generated {total_days} trading days")
    print(f"First day: {trading_days[0]}")
    print(f"Last day: {trading_days[-1]}")
    print()
    
    # Step 3: Run simulation loop
    print("[START] Step 3: Starting simulation loop...")
    print("="*80)
    
    successful_runs = 0
    failed_runs = 0
    daily_summaries = []  # Collect daily summaries
    
    for i, target_date in enumerate(trading_days, 1):
        print(f"\n[PROGRESS] {i}/{total_days} ({i/total_days*100:.1f}%)")
        
        # Run simulation for this date and collect summary
        success, daily_summary = run_simulation_for_date(target_date)
        
        if success:
            successful_runs += 1
            if daily_summary:
                daily_summaries.append(daily_summary)
                print(f"[SUMMARY] {target_date}: ${daily_summary['portfolio_value']:,.2f} | {daily_summary['positions']} positions | {daily_summary['trades']} trades")
        else:
            failed_runs += 1
        
        # Add delay between runs (except for the last one)
        if i < total_days:
            print(f"[DELAY] Waiting {delay_between_runs} seconds...")
            time.sleep(delay_between_runs)
    
    # Step 4: Send consolidated master email
    print("\n" + "="*80)
    print("[EMAIL] Sending consolidated simulation report...")
    print("="*80)
    
    try:
        send_master_email_report(daily_summaries, start_date, end_date, successful_runs, failed_runs)
        print("[EMAIL] Master report sent successfully!")
    except Exception as e:
        log_error(f"Failed to send master email: {e}")
        print(f"[EMAIL ERROR] Failed to send master email: {e}")
    
    # Step 5: Final summary
    print("\n" + "="*80)
    print("[COMPLETE] SIMULATION COMPLETE")
    print("="*80)
    print(f"Total Trading Days: {total_days}")
    print(f"Successful Runs: {successful_runs}")
    print(f"Failed Runs: {failed_runs}")
    print(f"Success Rate: {successful_runs/total_days*100:.1f}%")
    print()
    
    # Load final portfolio state
    try:
        sim_dir = os.path.dirname(os.path.abspath(__file__))
        sim_portfolio_file = os.path.join(sim_dir, "portfolio_sim.json")
        
        with open(sim_portfolio_file, 'r') as f:
            final_portfolio = json.load(f)
        
        final_value = final_portfolio.get('total_value', 0)
        final_cash = final_portfolio.get('cash', 0)
        final_positions = len(final_portfolio.get('positions', {}))
        total_return = final_value - 100000  # Started with $100k
        
        print(f"[PORTFOLIO] Final Portfolio Value: ${final_value:,.2f}")
        print(f"[PORTFOLIO] Final Cash: ${final_cash:,.2f}")
        print(f"[PORTFOLIO] Final Positions: {final_positions}")
        print(f"[PORTFOLIO] Total Return: ${total_return:,.2f} ({total_return/100000*100:.2f}%)")
        
    except Exception as e:
        log_error(f"Error loading final portfolio state: {e}")
        print(f"[ERROR] Error loading final portfolio state: {e}")
    
    print("="*80)
    print("[COMPLETE] Time-Shifted Forward Test Complete!")
    print(f"[INFO] Simulation results saved in: simulation/portfolio_sim.json")
    print("="*80)


if __name__ == "__main__":
    main()
