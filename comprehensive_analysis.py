import pandas as pd
import numpy as np
from crucible_engine import CrucibleEngine
import os
from datetime import datetime

def run_comprehensive_analysis():
    """Run comprehensive backtest analysis of VolatilityHunter strategy"""
    
    print("🚀 STARTING COMPREHENSIVE VOLATILITYHUNTER ANALYSIS")
    print("=" * 80)
    
    # Initialize engine
    engine = CrucibleEngine()
    
    # Get all available tickers
    tickers = [f.replace('.parquet', '') for f in os.listdir('data') if f.endswith('.parquet')]
    print(f"📊 Total tickers available: {len(tickers)}")
    
    # Run full backtest for both versions
    print("\n🔄 RUNNING FULL BACKTEST...")
    
    start_time = datetime.now()
    
    # v6.0 Analysis
    print("📈 Processing v6.0 (Pattern Hunter)...")
    v60_trades = []
    v60_processed = 0
    
    for ticker in tickers:
        try:
            df = engine.load_data(ticker)
            if df is not None and len(df) >= 252:
                trades = engine.simulate_trading(df, ticker, 'v6.0')
                v60_trades.extend(trades)
                v60_processed += 1
                
                if v60_processed % 500 == 0:
                    print(f"  Processed {v60_processed}/{len(tickers)} tickers...")
                    
        except Exception as e:
            print(f"  Error with {ticker}: {e}")
    
    # v6.5 Analysis
    print("📈 Processing v6.5 (Power Hunter)...")
    v65_trades = []
    v65_processed = 0
    
    for ticker in tickers:
        try:
            df = engine.load_data(ticker)
            if df is not None and len(df) >= 252:
                trades = engine.simulate_trading(df, ticker, 'v6.5')
                v65_trades.extend(trades)
                v65_processed += 1
                
                if v65_processed % 500 == 0:
                    print(f"  Processed {v65_processed}/{len(tickers)} tickers...")
                    
        except Exception as e:
            print(f"  Error with {ticker}: {e}")
    
    end_time = datetime.now()
    processing_time = (end_time - start_time).total_seconds()
    
    print(f"\n⏱️  Processing completed in {processing_time:.1f} seconds")
    
    # Analyze results
    analyze_results(v60_trades, v65_trades, "v6.0", "v6.5")

def analyze_results(trades_v1, trades_v2, name_v1, name_v2):
    """Comprehensive analysis of backtest results"""
    
    print(f"\n📊 COMPREHENSIVE PERFORMANCE ANALYSIS")
    print("=" * 80)
    
    # Convert to DataFrames
    df_v1 = pd.DataFrame(trades_v1) if trades_v1 else pd.DataFrame()
    df_v2 = pd.DataFrame(trades_v2) if trades_v2 else pd.DataFrame()
    
    # Basic metrics
    print(f"\n📈 BASIC PERFORMANCE METRICS")
    print("-" * 50)
    
    print(f"{name_v1}:")
    if len(df_v1) > 0:
        win_rate = (df_v1['profit_loss'] > 0).mean() * 100
        avg_trade = df_v1['profit_loss'].mean()
        total_trades = len(df_v1)
        total_pnl = df_v1['profit_loss'].sum()
        
        print(f"  Total Trades: {total_trades:,}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Average Trade: ${avg_trade:.2f}")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        
        if len(df_v1[df_v1['profit_loss'] > 0]) > 0:
            avg_win = df_v1[df_v1['profit_loss'] > 0]['profit_loss'].mean()
            print(f"  Average Win: ${avg_win:.2f}")
        
        if len(df_v1[df_v1['profit_loss'] < 0]) > 0:
            avg_loss = df_v1[df_v1['profit_loss'] < 0]['profit_loss'].mean()
            print(f"  Average Loss: ${avg_loss:.2f}")
        
        # Profit Factor
        wins = df_v1[df_v1['profit_loss'] > 0]['profit_loss'].sum()
        losses = abs(df_v1[df_v1['profit_loss'] < 0]['profit_loss'].sum())
        profit_factor = wins / losses if losses > 0 else float('inf')
        print(f"  Profit Factor: {profit_factor:.2f}")
        
        # Duration
        avg_duration = df_v1['duration'].mean()
        print(f"  Average Duration: {avg_duration:.1f} days")
        
    else:
        print("  No trades generated")
    
    print(f"\n{name_v2}:")
    if len(df_v2) > 0:
        win_rate = (df_v2['profit_loss'] > 0).mean() * 100
        avg_trade = df_v2['profit_loss'].mean()
        total_trades = len(df_v2)
        total_pnl = df_v2['profit_loss'].sum()
        
        print(f"  Total Trades: {total_trades:,}")
        print(f"  Win Rate: {win_rate:.2f}%")
        print(f"  Average Trade: ${avg_trade:.2f}")
        print(f"  Total P&L: ${total_pnl:,.2f}")
        
        if len(df_v2[df_v2['profit_loss'] > 0]) > 0:
            avg_win = df_v2[df_v2['profit_loss'] > 0]['profit_loss'].mean()
            print(f"  Average Win: ${avg_win:.2f}")
        
        if len(df_v2[df_v2['profit_loss'] < 0]) > 0:
            avg_loss = df_v2[df_v2['profit_loss'] < 0]['profit_loss'].mean()
            print(f"  Average Loss: ${avg_loss:.2f}")
        
        # Profit Factor
        wins = df_v2[df_v2['profit_loss'] > 0]['profit_loss'].sum()
        losses = abs(df_v2[df_v2['profit_loss'] < 0]['profit_loss'].sum())
        profit_factor = wins / losses if losses > 0 else float('inf')
        print(f"  Profit Factor: {profit_factor:.2f}")
        
        # Duration
        avg_duration = df_v2['duration'].mean()
        print(f"  Average Duration: {avg_duration:.1f} days")
        
        # Power Stock analysis for v6.5
        if 'is_power_stock' in df_v2.columns:
            power_stock_trades = df_v2[df_v2['is_power_stock'] == True]
            if len(power_stock_trades) > 0:
                ps_win_rate = (power_stock_trades['profit_loss'] > 0).mean() * 100
                print(f"  Power Stock Trades: {len(power_stock_trades)}")
                print(f"  Power Stock Win Rate: {ps_win_rate:.2f}%")
        
    else:
        print("  No trades generated")
    
    # Monthly performance analysis (for v6.0 if it has trades)
    if len(df_v1) > 0:
        print(f"\n📅 MONTHLY PERFORMANCE ANALYSIS ({name_v1})")
        print("-" * 50)
        
        df_v1['month'] = pd.to_datetime(df_v1['exit_date']).dt.to_period('M')
        monthly_pnl = df_v1.groupby('month')['profit_loss'].sum()
        
        print(f"  Average Monthly P&L: ${monthly_pnl.mean():.2f}")
        print(f"  Positive Months: {(monthly_pnl > 0).sum()}/{len(monthly_pnl)} ({(monthly_pnl > 0).mean() * 100:.1f}%)")
        print(f"  Best Month: ${monthly_pnl.max():.2f}")
        print(f"  Worst Month: ${monthly_pnl.min():.2f}")
        print(f"  Monthly Volatility: ${monthly_pnl.std():.2f}")
    
    # Top performers analysis
    if len(df_v1) > 0:
        print(f"\n🏆 TOP PERFORMERS ({name_v1})")
        print("-" * 50)
        
        ticker_performance = df_v1.groupby('ticker')['profit_loss'].agg(['sum', 'count', 'mean'])
        ticker_performance.columns = ['Total P&L', 'Trade Count', 'Avg Trade']
        ticker_performance = ticker_performance.sort_values('Total P&L', ascending=False)
        
        print("  Top 10 by Total P&L:")
        for i, (ticker, row) in enumerate(ticker_performance.head(10).iterrows()):
            print(f"    {i+1:2d}. {ticker:<6} | P&L: ${row['Total P&L']:>8.2f} | Trades: {row['Trade Count']:>3} | Avg: ${row['Avg Trade']:>6.2f}")
        
        print("\n  Bottom 10 by Total P&L:")
        for i, (ticker, row) in enumerate(ticker_performance.tail(10).iterrows()):
            print(f"    {i+1:2d}. {ticker:<6} | P&L: ${row['Total P&L']:>8.2f} | Trades: {row['Trade Count']:>3} | Avg: ${row['Avg Trade']:>6.2f}")
    
    # Exit reason analysis
    if len(df_v1) > 0 and 'exit_reason' in df_v1.columns:
        print(f"\n🚪 EXIT REASON ANALYSIS ({name_v1})")
        print("-" * 50)
        
        exit_analysis = df_v1.groupby('exit_reason').agg({
            'profit_loss': ['count', 'sum', 'mean'],
            'duration': 'mean'
        }).round(2)
        
        print(exit_analysis)
    
    # Optimization recommendations
    print(f"\n💡 OPTIMIZATION RECOMMENDATIONS")
    print("-" * 50)
    
    if len(df_v1) > 0:
        win_rate = (df_v1['profit_loss'] > 0).mean() * 100
        avg_win = df_v1[df_v1['profit_loss'] > 0]['profit_loss'].mean() if len(df_v1[df_v1['profit_loss'] > 0]) > 0 else 0
        avg_loss = df_v1[df_v1['profit_loss'] < 0]['profit_loss'].mean() if len(df_v1[df_v1['profit_loss'] < 0]) > 0 else 0
        
        if win_rate < 40:
            print("  🔴 LOW WIN RATE: Consider tightening entry criteria")
        elif win_rate > 60:
            print("  🟢 HIGH WIN RATE: Consider loosening entry criteria for more opportunities")
        
        if avg_win > 0 and avg_loss < 0:
            reward_risk_ratio = abs(avg_win / avg_loss)
            if reward_risk_ratio < 1.5:
                print("  🔴 POOR RISK/REWARD: Consider improving exit timing")
            else:
                print("  🟢 GOOD RISK/REWARD: Current exit logic working well")
        
        if len(df_v1) < 1000:
            print("  🔴 LOW TRADE COUNT: Strategy may be too restrictive")
        elif len(df_v1) > 50000:
            print("  🟡 HIGH TRADE COUNT: Consider filtering for quality over quantity")
    
    print(f"\n✅ COMPREHENSIVE ANALYSIS COMPLETE")
    print("=" * 80)

if __name__ == "__main__":
    run_comprehensive_analysis()
