#!/usr/bin/env python3
"""
Diagnostic Exit Check Script
Analyzes why AEHR, HCSG, and WDC have been held for 33 days in BEAR regime.

Requirements:
- Read-only (no imports from src/strategy_engine.py)
- Check TIME_STOP_DAYS = 10 and HARD_STOP_PCT = 8%
- Evaluate exit signals on May 13 and May 15 (blackout dates)
- Output clean markdown table

Author: VolatilityHunter Diagnostic Module
Version: 1.0
Date: 2026-05-18
"""

import json
import pandas as pd
from datetime import datetime, timedelta
from pathlib import Path

# Constants (from strategy_engine.py v8.1)
TIME_STOP_DAYS = 10
HARD_STOP_PCT = 8.0
OVERBOUGHT_EXIT = 78

ROOT = Path(__file__).parent.parent
DATA_DIR = ROOT / "data"

def load_portfolio():
    """Load portfolio.json to get position details."""
    portfolio_path = DATA_DIR / "portfolio.json"
    with open(portfolio_path, 'r') as f:
        return json.load(f)

def load_ticker_data(ticker):
    """Load parquet data for a ticker."""
    parquet_path = DATA_DIR / f"{ticker}.parquet"
    df = pd.read_parquet(parquet_path)
    if 'date' in df.columns:
        df['date'] = pd.to_datetime(df['date'])
        df = df.set_index('date')
    if hasattr(df.index, 'tz') and df.index.tz is not None:
        df.index = df.index.tz_localize(None)
    df = df[~df.index.duplicated(keep='last')]
    df.sort_index(inplace=True)
    return df

def calculate_stochastic(df, period=14):
    """Calculate Stochastic Oscillator."""
    low_min = df['low'].rolling(window=period).min()
    high_max = df['high'].rolling(window=period).max()
    stoch = 100 * (df['close'] - low_min) / (high_max - low_min)
    return stoch

def count_market_days(start_date, end_date, df):
    """Count actual market days between two dates using parquet data."""
    start = pd.to_datetime(start_date)
    end = pd.to_datetime(end_date)
    
    # Filter to date range
    mask = (df.index >= start) & (df.index <= end)
    market_days = df[mask].shape[0]
    
    return market_days

def check_exit_criteria(ticker, position, df, current_date):
    """Check if position meets exit criteria."""
    entry_date = pd.to_datetime(position['entry_date'])
    entry_price = position['entry_price']
    stop_loss = position.get('stop_loss_price', entry_price * (1 - HARD_STOP_PCT / 100))
    
    # Get current price
    current_row = df[df.index <= current_date].iloc[-1]
    current_price = current_row['close']
    
    # Calculate metrics
    holding_days = count_market_days(entry_date, current_date, df)
    pnl_pct = ((current_price - entry_price) / entry_price) * 100
    
    # Calculate stochastic
    df_calc = df[df.index <= current_date].copy()
    df_calc['stoch'] = calculate_stochastic(df_calc)
    current_stoch = df_calc['stoch'].iloc[-1]
    
    # Check exit conditions
    time_stop_hit = holding_days >= TIME_STOP_DAYS
    hard_stop_hit = current_price <= stop_loss
    overbought_exit_hit = current_stoch >= OVERBOUGHT_EXIT
    
    return {
        'ticker': ticker,
        'entry_date': entry_date.strftime('%Y-%m-%d'),
        'entry_price': entry_price,
        'current_price': current_price,
        'stop_loss': stop_loss,
        'holding_days': holding_days,
        'pnl_pct': pnl_pct,
        'current_stoch': current_stoch,
        'time_stop_hit': time_stop_hit,
        'hard_stop_hit': hard_stop_hit,
        'overbought_exit_hit': overbought_exit_hit,
        'should_exit': time_stop_hit or hard_stop_hit or overbought_exit_hit
    }

def check_blackout_dates(ticker, position, df):
    """Check if exit signals were generated on May 13 or May 15."""
    blackout_dates = [
        datetime(2026, 5, 13),
        datetime(2026, 5, 15)
    ]
    
    results = []
    for date in blackout_dates:
        try:
            result = check_exit_criteria(ticker, position, df, date)
            results.append({
                'date': date.strftime('%Y-%m-%d'),
                'should_exit': result['should_exit'],
                'time_stop': result['time_stop_hit'],
                'hard_stop': result['hard_stop_hit'],
                'overbought': result['overbought_exit_hit'],
                'holding_days': result['holding_days'],
                'pnl_pct': result['pnl_pct'],
                'stoch': result['current_stoch']
            })
        except Exception as e:
            results.append({
                'date': date.strftime('%Y-%m-%d'),
                'error': str(e)
            })
    
    return results

def main():
    print("="*80)
    print("DIAGNOSTIC EXIT CHECK - BEAR REGIME LONG-HELD POSITIONS")
    print("="*80)
    print(f"Analysis Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Exit Criteria: TIME_STOP={TIME_STOP_DAYS} days | HARD_STOP={HARD_STOP_PCT}% | OVERBOUGHT={OVERBOUGHT_EXIT}")
    print("="*80)
    print()
    
    # Load portfolio
    portfolio = load_portfolio()
    positions = portfolio.get('positions', {})
    
    # Target tickers
    target_tickers = ['AEHR', 'HCSG', 'WDC']
    
    # Current date (May 18, 2026)
    current_date = datetime(2026, 5, 18)
    
    print("## CURRENT STATUS (May 18, 2026)")
    print()
    print("| Ticker | Entry Date | Entry $ | Current $ | Stop $ | Days | P&L % | Stoch | Time? | Hard? | Over? | Exit? |")
    print("|--------|------------|---------|-----------|--------|------|-------|-------|-------|-------|-------|-------|")
    
    for ticker in target_tickers:
        if ticker not in positions:
            print(f"| {ticker} | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | N/A | NOT IN PORTFOLIO |")
            continue
        
        position = positions[ticker]
        df = load_ticker_data(ticker)
        result = check_exit_criteria(ticker, position, df, current_date)
        
        print(f"| {result['ticker']} | "
              f"{result['entry_date']} | "
              f"${result['entry_price']:.2f} | "
              f"${result['current_price']:.2f} | "
              f"${result['stop_loss']:.2f} | "
              f"{result['holding_days']} | "
              f"{result['pnl_pct']:+.2f}% | "
              f"{result['current_stoch']:.1f} | "
              f"{'YES' if result['time_stop_hit'] else 'NO'} | "
              f"{'YES' if result['hard_stop_hit'] else 'NO'} | "
              f"{'YES' if result['overbought_exit_hit'] else 'NO'} | "
              f"**{'EXIT' if result['should_exit'] else 'HOLD'}** |")
    
    print()
    print("## BLACKOUT DATE ANALYSIS")
    print()
    
    for ticker in target_tickers:
        if ticker not in positions:
            continue
        
        print(f"### {ticker}")
        print()
        print("| Date | Exit? | Time? | Hard? | Over? | Days | P&L % | Stoch |")
        print("|------|-------|-------|-------|-------|------|-------|-------|")
        
        position = positions[ticker]
        df = load_ticker_data(ticker)
        blackout_results = check_blackout_dates(ticker, position, df)
        
        for result in blackout_results:
            if 'error' in result:
                print(f"| {result['date']} | ERROR | - | - | - | - | - | {result['error']} |")
            else:
                print(f"| {result['date']} | "
                      f"**{'EXIT' if result['should_exit'] else 'HOLD'}** | "
                      f"{'YES' if result['time_stop'] else 'NO'} | "
                      f"{'YES' if result['hard_stop'] else 'NO'} | "
                      f"{'YES' if result['overbought'] else 'NO'} | "
                      f"{result['holding_days']} | "
                      f"{result['pnl_pct']:+.2f}% | "
                      f"{result['stoch']:.1f} |")
        print()
    
    print("="*80)
    print("DIAGNOSTIC SUMMARY")
    print("="*80)
    print()
    print("**Key Findings:**")
    print("1. All three positions have exceeded TIME_STOP_DAYS (10 days)")
    print("2. Check if exit signals were properly generated on May 13 and May 15")
    print("3. Verify if BEAR regime prevented exits or if there was a logic issue")
    print()
    print("**Next Steps:**")
    print("- Review strategy_engine.py exit logic for BEAR regime")
    print("- Check daily_trading_loop.py execution logs for May 13 and May 15")
    print("- Verify run_manifest files for those dates")
    print("="*80)

if __name__ == "__main__":
    main()
