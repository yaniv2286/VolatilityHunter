#!/usr/bin/env python3
"""
Time-Shifted Forward Test - Shadow Execution Script
Simulates daily trading execution for a specific target date without mutating core logic.
"""

import os
import sys
import argparse
from datetime import datetime
from typing import Dict, Any

# Add src to path for imports (need to go up one level from simulation/)
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from simulation.simulated_data_loader import SimulatedParquetLoader
from src.strategy_v7_2 import analyze_stock_v7_2, add_indicators_v7_2, check_exit_conditions_v7_2
from src.execution import PaperExecutor
from src.tracker import Portfolio
from src.notifications import log_info, log_warning, log_error
from src.config_manager import get_config
from src.email_notifier import EmailNotifier
import json
import smtplib


def get_active_stock_list():
    """Get the complete universe of 2,149 US stocks for simulation."""
    from src.ticker_manager import TickerManager
    
    ticker_manager = TickerManager()
    tickers = ticker_manager.get_filtered_tickers()
    
    log_info(f"Loaded {len(tickers)} tickers for simulation")
    return tickers


def simulate_trading_day(target_date: str):
    """
    Simulate trading execution for a specific target date.
    Uses exact same strategy logic as main.py but with simulated data.
    """
    print(f"="*60)
    print(f"VolatilityHunter - Time-Shifted Simulation")
    print(f"Target Date: {target_date}")
    print(f"Started: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"="*60)
    
    try:
        # Step 1: Initialize simulated data loader
        log_info(f"Initializing SimulatedParquetLoader for {target_date}")
        sim_loader = SimulatedParquetLoader(target_date)
        
        # Step 2: Initialize simulated portfolio (portfolio_sim.json)
        sim_dir = os.path.join(os.getcwd(), 'simulation')
        sim_portfolio_file = os.path.join(sim_dir, "portfolio_sim.json")
        
        # Create portfolio_sim.json if it doesn't exist
        if not os.path.exists(sim_portfolio_file):
            clean_portfolio = {
                "cash": 100000.0,
                "positions": {},
                "trade_history": [],
                "total_value": 100000.0,
                "last_updated": datetime.now().isoformat(),
                "execution_mode": "SIMULATION"
            }
            with open(sim_portfolio_file, 'w') as f:
                json.dump(clean_portfolio, f, indent=2)
            log_info(f"Created simulation portfolio: {sim_portfolio_file}")
        
        # Create simulated executor
        executor = PaperExecutor(portfolio_file=sim_portfolio_file)
        log_info(f"Initialized simulated portfolio: {sim_portfolio_file}")
        
        # Step 3: Load stock universe
        log_info("Loading stock universe...")
        tickers = get_active_stock_list()
        
        # Step 4: Scan stocks with simulated data
        log_info(f"Scanning {len(tickers)} stocks with data truncated to {target_date}...")
        
        buy_signals = []
        stock_data = {}
        
        for ticker in tickers:
            try:
                # Load simulated data (truncated to target_date)
                df = sim_loader.load_data(ticker)
                if df is not None and len(df) > 0:
                    stock_data[ticker] = df
                    
                    # Analyze with exact same strategy logic
                    analysis = analyze_stock_v7_2(df, ticker)
                    signal = analysis.get('signal', 'HOLD')
                    
                    if signal == 'BUY':
                        buy_signals.append({
                            'ticker': ticker,
                            'price': analysis['indicators']['price'],
                            'indicators': analysis['indicators'],
                            'quality_score': analysis.get('quality_score', 0),
                            'reason': analysis.get('reason', 'BUY signal detected')
                        })
                        
            except Exception as e:
                log_error(f"Error analyzing {ticker}: {e}")
                continue
        
        # Step 5: Check exit conditions for existing positions
        log_info("Checking exit conditions for existing positions...")
        
        # Load portfolio directly from file
        with open(sim_portfolio_file, 'r') as f:
            portfolio = json.load(f)
        
        positions_to_close = []
        
        for ticker, position in portfolio.get('positions', {}).items():
            if ticker in stock_data:
                df = stock_data[ticker]
                df_with_indicators = add_indicators_v7_2(df)
                
                should_exit, exit_reason = check_exit_conditions_v7_2(df_with_indicators, position)
                
                if should_exit:
                    latest = df_with_indicators.iloc[-1]
                    exit_price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
                    positions_to_close.append((ticker, exit_price, exit_reason))
        
        # Step 6: Execute trades
        log_info(f"Executing trades: {len(buy_signals)} BUY signals, {len(positions_to_close)} exits")
        
        # Process exits first
        for ticker, exit_price, reason in positions_to_close:
            position = portfolio['positions'][ticker]
            shares = position['shares']
            
            # Create sell signal
            sell_signal = {
                'ticker': ticker,
                'action': 'SELL',
                'price': exit_price,
                'indicators': {'price': exit_price},
                'reason': reason
            }
            
            result = executor.execute_sell(sell_signal, position)
            log_info(f"[SIM SELL] {ticker}: {shares} shares @ ${exit_price:.2f} ({reason})")
        
        # Process buys
        available_cash = portfolio.get('cash', 100000.0)
        current_positions = len(portfolio.get('positions', {}))
        max_positions = 10  # Strict position cap guardrail
        
        log_info(f"Position check: {current_positions}/{max_positions} positions filled")
        
        for signal in buy_signals[:10]:  # Limit to top 10 for simulation
            ticker = signal['ticker']
            
            # Check position cap guardrail
            if current_positions >= max_positions:
                log_info(f"Position cap reached ({max_positions}), skipping {ticker}")
                break
            
            # Skip if already holding
            if ticker in portfolio['positions']:
                continue
            
            # Create buy signal
            buy_signal = {
                'ticker': ticker,
                'action': 'BUY',
                'price': signal['price'],
                'indicators': signal['indicators'],
                'reason': signal['reason']
            }
            
            result = executor.execute_buy(buy_signal, available_cash)
            log_info(f"[SIM BUY] {ticker}: @ ${signal['price']:.2f} ({signal['reason']})")
            
            # Update available cash and position count
            if result.get('success', False):
                available_cash = result.get('remaining_cash', available_cash)
                current_positions += 1
                log_info(f"Position count updated: {current_positions}/{max_positions}")
                
                # Check if we've reached the cap after this trade
                if current_positions >= max_positions:
                    log_info(f"Position cap reached ({max_positions}), stopping further buys")
                    break
        
        # Step 7: Update portfolio valuation
        log_info("Updating portfolio valuation...")
        
        # Load final portfolio directly from file
        with open(sim_portfolio_file, 'r') as f:
            final_portfolio = json.load(f)
        
        cash = final_portfolio.get('cash', 0)
        positions = final_portfolio.get('positions', {})
        positions_count = len(positions)
        
        # Calculate total portfolio value dynamically
        total_value = cash  # Start with cash
        position_values = []
        
        for ticker, position in positions.items():
            shares = position.get('shares', 0)
            if shares > 0:
                # Get current price using simulated data loader
                current_price = sim_loader.get_latest_price(ticker)
                if current_price and current_price > 0:
                    position_value = shares * current_price
                    total_value += position_value
                    position_values.append(f"{ticker}: {shares} shares @ ${current_price:.2f} = ${position_value:.2f}")
                else:
                    log_warning(f"Could not get current price for {ticker}")
        
        log_info(f"Portfolio valuation: Cash=${cash:.2f}, Positions=${total_value-cash:.2f}, Total=${total_value:.2f}")
        
        # Update the portfolio file with correct total value
        final_portfolio['total_value'] = total_value
        with open(sim_portfolio_file, 'w') as f:
            json.dump(final_portfolio, f, indent=2)
        
        # Step 8: Skip daily email (consolidated mode)
        log_info("Skipping daily email (consolidation mode)")
        print(f"[EMAIL] Daily email skipped (will be sent in consolidated report)")
        
        print(f"\n[OK] Simulation completed for {target_date}")
        print(f"[PORTFOLIO] Value: ${total_value:,.2f} | Positions: {positions_count}")
        print(f"[TRADES] {len(buy_signals)} BUY signals, {len(positions_to_close)} exits")
        
        return True
        
    except Exception as e:
        log_error(f"Simulation failed for {target_date}: {e}")
        print(f"[ERROR] Simulation failed: {e}")
        return False


def main():
    """Main entry point for simulation script."""
    parser = argparse.ArgumentParser(description='Time-Shifted Forward Test Simulation')
    parser.add_argument('--date', required=True, help='Target date in YYYY-MM-DD format')
    
    args = parser.parse_args()
    
    # Validate date format
    try:
        datetime.strptime(args.date, '%Y-%m-%d')
    except ValueError:
        print("Error: Date must be in YYYY-MM-DD format")
        sys.exit(1)
    
    # Run simulation
    success = simulate_trading_day(args.date)
    
    if success:
        print(f"\n[OK] Simulation completed successfully for {args.date}")
    else:
        print(f"\n[ERROR] Simulation failed for {args.date}")
        sys.exit(1)


if __name__ == "__main__":
    main()
