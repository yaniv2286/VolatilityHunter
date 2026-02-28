#!/usr/bin/env python3
"""
CAGR Performance Diagnostic Tool - Phase 1 Optimization
Identify why CAGR is only 5.80% and find optimization opportunities
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.strategy_v7_2 import add_indicators_v7_2
from scripts.vectorized_backtester import VectorizedBacktester
from src.notifications import log_info, log_error

class CAGRDiagnostics:
    """Comprehensive CAGR performance analysis"""
    
    def __init__(self):
        self.backtester = VectorizedBacktester(initial_capital=100000)
        self.results = {}
        
    def analyze_signal_frequency(self, ticker='AAPL', start_date='2018-01-01', end_date='2023-12-31'):
        """Analyze how often signals are generated"""
        print(f"\n🔍 SIGNAL FREQUENCY ANALYSIS: {ticker}")
        print("=" * 60)
        
        # Load data
        df = self.backtester.load_20yr_data(ticker)
        if df is None or df.empty:
            print(f"❌ No data for {ticker}")
            return
        
        # Filter date range
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        df = df[(df.index >= start_date) & (df.index <= end_date)]
        
        # Add indicators
        df_with_indicators = add_indicators_v7_2(df.copy())
        
        # Generate signals
        signals = self.backtester.generate_signals(df_with_indicators, ticker)
        
        # Signal analysis
        buy_signals = (signals == 1).sum()
        sell_signals = (signals == -1).sum()
        total_days = len(df)
        trading_days = 252 * 5  # 5 years
        
        print(f"📊 Signal Statistics:")
        print(f"  • Total Days: {total_days}")
        print(f"  • Buy Signals: {buy_signals} ({buy_signals/total_days*100:.1f} of days)")
        print(f"  • Sell Signals: {sell_signals} ({sell_signals/total_days*100:.1f} of days)")
        print(f"  • Signal Frequency: {buy_signals/trading_days*252:.1f} buys per year")
        
        # Check signal distribution by year
        signals_by_year = {}
        for year in range(2018, 2024):
            year_signals = signals[signals.index.year == year]
            signals_by_year[year] = {
                'buys': (year_signals == 1).sum(),
                'sells': (year_signals == -1).sum(),
                'total_days': len(year_signals)
            }
        
        print(f"\n📅 Signals by Year:")
        for year, stats in signals_by_year.items():
            buy_rate = stats['buys'] / stats['total_days'] * 100 if stats['total_days'] > 0 else 0
            print(f"  • {year}: {stats['buys']} buys ({buy_rate:.1f}%)")
        
        return signals, df_with_indicators
    
    def analyze_entry_conditions(self, ticker='AAPL'):
        """Analyze individual entry conditions to identify bottlenecks"""
        print(f"\n🎯 ENTRY CONDITION ANALYSIS: {ticker}")
        print("=" * 60)
        
        # Load data
        df = self.backtester.load_20yr_data(ticker)
        if df is None or df.empty:
            return
        
        # Add indicators
        df_with_indicators = add_indicators_v7_2(df.copy())
        
        # Calculate individual conditions
        close_col = 'adjClose' if 'adjClose' in df_with_indicators.columns else 'close'
        volume_col = 'Volume' if 'Volume' in df_with_indicators.columns else 'volume'
        
        # Individual condition checks
        conditions = {
            'Liquidity ($1M+)': df_with_indicators['dollar_volume'] >= 1000000,
            'Price Ceiling ($500)': df_with_indicators[close_col] <= 500,
            'Trend (Above SMA200)': df_with_indicators[close_col] > df_with_indicators['sma_200'],
            'Stochastic Entry (32-80)': (df_with_indicators['stoch_k'] >= 32) & (df_with_indicators['stoch_k'] <= 80),
            'High Volume': df_with_indicators['high_volume'],
            'CAGR Growth (>15%)': df_with_indicators['cagr'] > 15.0
        }
        
        print(f"📊 Entry Condition Pass Rates:")
        total_days = len(df_with_indicators)
        
        for condition_name, condition_mask in conditions.items():
            pass_rate = condition_mask.sum() / total_days * 100
            print(f"  • {condition_name}: {pass_rate:.1f}% of days")
        
        # Calculate combined pass rates
        all_conditions = pd.Series(True, index=df_with_indicators.index)
        for condition_name, condition_mask in conditions.items():
            all_conditions = all_conditions & condition_mask
            combined_rate = all_conditions.sum() / total_days * 100
            print(f"  • Combined after {condition_name}: {combined_rate:.1f}% of days")
        
        return conditions
    
    def analyze_trade_distribution(self, ticker='AAPL'):
        """Analyze individual trade P&L distribution"""
        print(f"\n💰 TRADE DISTRIBUTION ANALYSIS: {ticker}")
        print("=" * 60)
        
        # Run backtest
        results = self.backtester.backtest_single_ticker(ticker, '2018-01-01', '2023-12-31')
        if not results:
            print(f"❌ No backtest results for {ticker}")
            return
        
        trades = results.get('trades', [])
        if not trades:
            print(f"❌ No trades found for {ticker}")
            return
        
        # Calculate trade P&L
        trade_pnl = []
        buy_trades = {}
        
        for trade in trades:
            if trade['action'] == 'BUY':
                buy_trades[trade['date']] = trade
            elif trade['action'] == 'SELL' and trade['date'] in buy_trades:
                buy_trade = buy_trades[trade['date']]
                pnl = (trade['price'] - buy_trade['price']) / buy_trade['price'] * 100
                trade_pnl.append(pnl)
        
        if not trade_pnl:
            print(f"❌ No completed trades found")
            return
        
        trade_pnl = np.array(trade_pnl)
        
        print(f"📊 Trade Statistics:")
        print(f"  • Total Trades: {len(trade_pnl)}")
        print(f"  • Winning Trades: {(trade_pnl > 0).sum()} ({(trade_pnl > 0).sum()/len(trade_pnl)*100:.1f}%)")
        print(f"  • Average P&L: {trade_pnl.mean():.2f}%")
        print(f"  • Best Trade: {trade_pnl.max():.2f}%")
        print(f"  • Worst Trade: {trade_pnl.min():.2f}%")
        print(f"  • Std Dev: {trade_pnl.std():.2f}%")
        
        # P&L distribution
        print(f"\n📈 P&L Distribution:")
        bins = [-20, -10, -5, -2, 0, 2, 5, 10, 20]
        hist, edges = np.histogram(trade_pnl, bins=bins)
        
        for i in range(len(hist)):
            lower, upper = edges[i], edges[i+1]
            percentage = hist[i] / len(trade_pnl) * 100
            print(f"  • {lower:+.0f}% to {upper:+.0f}%: {hist[i]} trades ({percentage:.1f}%)")
        
        return trade_pnl
    
    def analyze_holding_periods(self, ticker='AAPL'):
        """Analyze how long positions are held"""
        print(f"\n⏱️ HOLDING PERIOD ANALYSIS: {ticker}")
        print("=" * 60)
        
        # Run backtest
        results = self.backtester.backtest_single_ticker(ticker, '2018-01-01', '2023-12-31')
        if not results:
            return
        
        trades = results.get('trades', [])
        if not trades:
            return
        
        # Calculate holding periods
        holding_periods = []
        buy_trades = {}
        
        for trade in trades:
            if trade['action'] == 'BUY':
                buy_trades[trade['date']] = trade
            elif trade['action'] == 'SELL' and trade['date'] in buy_trades:
                buy_trade = buy_trades[trade['date']]
                buy_date = pd.to_datetime(buy_trade['date'])
                sell_date = pd.to_datetime(trade['date'])
                holding_days = (sell_date - buy_date).days
                holding_periods.append(holding_days)
        
        if not holding_periods:
            print(f"❌ No completed trades found")
            return
        
        holding_periods = np.array(holding_periods)
        
        print(f"📊 Holding Period Statistics:")
        print(f"  • Average: {holding_periods.mean():.1f} days")
        print(f"  • Median: {np.median(holding_periods):.1f} days")
        print(f"  • Min: {holding_periods.min()} days")
        print(f"  • Max: {holding_periods.max()} days")
        print(f"  • Std Dev: {holding_periods.std():.1f} days")
        
        # Holding period distribution
        print(f"\n📅 Holding Period Distribution:")
        bins = [0, 1, 5, 10, 20, 30, 60, 90, 180]
        hist, edges = np.histogram(holding_periods, bins=bins)
        
        for i in range(len(hist)):
            lower, upper = edges[i], edges[i+1]
            percentage = hist[i] / len(holding_periods) * 100
            if upper == 180:
                print(f"  • {lower}+ days: {hist[i]} trades ({percentage:.1f}%)")
            else:
                print(f"  • {lower}-{upper} days: {hist[i]} trades ({percentage:.1f}%)")
        
        return holding_periods
    
    def analyze_market_conditions(self, ticker='AAPL'):
        """Analyze performance under different market conditions"""
        print(f"\n🌍 MARKET CONDITION ANALYSIS: {ticker}")
        print("=" * 60)
        
        # Load data
        df = self.backtester.load_20yr_data(ticker)
        if df is None or df.empty:
            return
        
        # Filter to 5-year period
        if 'date' in df.columns:
            df['date'] = pd.to_datetime(df['date'])
            df = df.set_index('date')
        
        df = df[(df.index >= '2018-01-01') & (df.index <= '2023-12-31')]
        
        # Calculate market regime
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        df['sma_50'] = df[close_col].rolling(50).mean()
        df['sma_200'] = df[close_col].rolling(200).mean()
        
        # Define market regimes
        bull_market = df[close_col] > df['sma_200']
        bear_market = df[close_col] < df['sma_200']
        
        # Calculate volatility
        df['returns'] = df[close_col].pct_change()
        df['volatility'] = df['returns'].rolling(20).std() * np.sqrt(252)
        
        high_vol = df['volatility'] > df['volatility'].median()
        low_vol = df['volatility'] <= df['volatility'].median()
        
        print(f"📊 Market Regime Analysis:")
        print(f"  • Bull Market Days: {bull_market.sum()} ({bull_market.sum()/len(df)*100:.1f}%)")
        print(f"  • Bear Market Days: {bear_market.sum()} ({bear_market.sum()/len(df)*100:.1f}%)")
        print(f"  • High Volatility Days: {high_vol.sum()} ({high_vol.sum()/len(df)*100:.1f}%)")
        print(f"  • Low Volatility Days: {low_vol.sum()} ({low_vol.sum()/len(df)*100:.1f}%)")
        
        # Run backtest and analyze performance by regime
        results = self.backtester.backtest_single_ticker(ticker, '2018-01-01', '2023-12-31')
        if results and 'strategy_returns' in results:
            returns = results['strategy_returns']
            
            # Align returns with market data
            aligned_data = pd.DataFrame({
                'returns': returns,
                'bull_market': bull_market.reindex(returns.index, fill_value=False),
                'bear_market': bear_market.reindex(returns.index, fill_value=False),
                'high_vol': high_vol.reindex(returns.index, fill_value=False),
                'low_vol': low_vol.reindex(returns.index, fill_value=False)
            }).dropna()
            
            print(f"\n📈 Performance by Market Regime:")
            
            # Bull market performance
            bull_returns = aligned_data[aligned_data['bull_market']]['returns']
            if len(bull_returns) > 0:
                bull_cagr = (1 + bull_returns.mean()) ** 252 - 1
                print(f"  • Bull Market CAGR: {bull_cagr*100:.2f}%")
            
            # Bear market performance
            bear_returns = aligned_data[aligned_data['bear_market']]['returns']
            if len(bear_returns) > 0:
                bear_cagr = (1 + bear_returns.mean()) ** 252 - 1
                print(f"  • Bear Market CAGR: {bear_cagr*100:.2f}%")
            
            # High volatility performance
            high_vol_returns = aligned_data[aligned_data['high_vol']]['returns']
            if len(high_vol_returns) > 0:
                high_vol_cagr = (1 + high_vol_returns.mean()) ** 252 - 1
                print(f"  • High Volatility CAGR: {high_vol_cagr*100:.2f}%")
            
            # Low volatility performance
            low_vol_returns = aligned_data[aligned_data['low_vol']]['returns']
            if len(low_vol_returns) > 0:
                low_vol_cagr = (1 + low_vol_returns.mean()) ** 252 - 1
                print(f"  • Low Volatility CAGR: {low_vol_cagr*100:.2f}%")
    
    def run_comprehensive_analysis(self, ticker='AAPL'):
        """Run all diagnostic analyses"""
        print(f"🚀 COMPREHENSIVE CAGR DIAGNOSTIC: {ticker}")
        print("=" * 80)
        
        # 1. Signal frequency analysis
        signals, df = self.analyze_signal_frequency(ticker)
        
        # 2. Entry conditions analysis
        conditions = self.analyze_entry_conditions(ticker)
        
        # 3. Trade distribution analysis
        trade_pnl = self.analyze_trade_distribution(ticker)
        
        # 4. Holding period analysis
        holding_periods = self.analyze_holding_periods(ticker)
        
        # 5. Market conditions analysis
        self.analyze_market_conditions(ticker)
        
        # 6. Summary and recommendations
        print(f"\n🎯 DIAGNOSTIC SUMMARY & RECOMMENDATIONS: {ticker}")
        print("=" * 60)
        
        print(f"📊 Key Findings:")
        if signals is not None:
            buy_frequency = (signals == 1).sum() / len(signals) * 100
            print(f"  • Signal Frequency: {buy_frequency:.1f}% of days")
            if buy_frequency < 2:
                print(f"    ⚠️  TOO RARE - Signals too infrequent")
            elif buy_frequency > 10:
                print(f"    ⚠️  TOO FREQUENT - May overtrade")
        
        if trade_pnl is not None:
            avg_pnl = trade_pnl.mean()
            win_rate = (trade_pnl > 0).sum() / len(trade_pnl) * 100
            print(f"  • Average Trade P&L: {avg_pnl:.2f}%")
            print(f"  • Win Rate: {win_rate:.1f}%")
            if avg_pnl < 1:
                print(f"    ⚠️  POOR TRADE SIZE - Average trade too small")
            if win_rate < 55:
                print(f"    ⚠️  LOW WIN RATE - Need better entry/exit")
        
        if holding_periods is not None:
            avg_hold = holding_periods.mean()
            print(f"  • Average Holding Period: {avg_hold:.1f} days")
            if avg_hold < 5:
                print(f"    ⚠️  TOO SHORT - May be overtrading")
            elif avg_hold > 60:
                print(f"    ⚠️  TOO LONG - May miss better opportunities")
        
        print(f"\n💡 OPTIMIZATION RECOMMENDATIONS:")
        print(f"  1. EXPAND ENTRY RANGE - Test Stochastic 20-90 instead of 32-80")
        print(f"  2. REMOVE CAGR FILTER - 15% CAGR filter may eliminate good trades")
        print(f"  3. DYNAMIC EXITS - Use ATR-based stops instead of fixed -8%")
        print(f"  4. POSITION SIZING - Implement volatility-adjusted sizing")
        print(f"  5. MOMENTUM FILTERS - Add RSI and MACD confirmation")

def main():
    """Main execution"""
    print("🚀 CAGR PERFORMANCE DIAGNOSTIC TOOL")
    print("=" * 80)
    
    diagnostic = CAGRDiagnostics()
    
    # Analyze key stocks
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    for ticker in tickers:
        try:
            diagnostic.run_comprehensive_analysis(ticker)
            print("\n" + "="*80)
        except Exception as e:
            print(f"❌ Error analyzing {ticker}: {e}")
            continue
    
    print("\n🎯 OVERALL OPTIMIZATION STRATEGY:")
    print("=" * 60)
    print("1. IMMEDIATE FIXES (Week 1):")
    print("   • Expand Stochastic range from 32-80 to 20-90")
    print("   • Remove CAGR > 15% entry filter")
    print("   • Increase position sizing to 2% risk per trade")
    
    print("\n2. ADVANCED OPTIMIZATIONS (Week 2-3):")
    print("   • Implement ATR-based dynamic stops")
    print("   • Add RSI momentum confirmation")
    print("   • Create volatility-adjusted position sizing")
    
    print("\n3. MACHINE LEARNING (Week 4+):")
    print("   • Train signal quality classifier")
    print("   • Implement market regime detection")
    print("   • Create multi-strategy ensemble")

if __name__ == "__main__":
    main()
