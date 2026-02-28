#!/usr/bin/env python3
"""
FINAL CAGR OPTIMIZATION - Working Strategy
Fix all issues and achieve 20%+ CAGR target
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.strategy_v7_2 import add_indicators_v7_2
from src.notifications import log_info, log_error

class FinalOptimizedStrategy:
    """Final optimized strategy for 20%+ CAGR"""
    
    def __init__(self):
        self.name = "Final Optimized v8.2"
        self.target_cagr = 0.20
        
    def add_all_indicators(self, df):
        """Add all necessary indicators"""
        df = df.copy()
        
        # Add base indicators from v7.2
        df = add_indicators_v7_2(df)
        
        # Add missing SMA_20
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        df['sma_20'] = df[close_col].rolling(20).mean()
        
        # Add RSI
        delta = df[close_col].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Add MACD
        exp1 = df[close_col].ewm(span=12).mean()
        exp2 = df[close_col].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Add momentum
        df['price_momentum'] = df[close_col] / df[close_col].rolling(10).mean() - 1
        
        # Volume analysis
        volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
        df['volume_sma'] = df[volume_col].rolling(20).mean()
        df['volume_ratio'] = df[volume_col] / df['volume_sma']
        
        return df
    
    def generate_final_signals(self, df, ticker):
        """Generate final optimized signals"""
        try:
            # Add all indicators
            df = self.add_all_indicators(df)
            
            # Define columns
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
            
            # FINAL OPTIMIZED ENTRY CONDITIONS
            
            # 1. Liquidity (relaxed)
            df['dollar_volume'] = df[close_col] * df[volume_col]
            liquidity_pass = df['dollar_volume'] >= 100000
            
            # 2. Price (relaxed)
            price_pass = df[close_col] <= 2000
            
            # 3. Trend (relaxed)
            trend_pass = df[close_col] > df['sma_20']
            
            # 4. Stochastic (very wide range)
            stoch_entry = (df['stoch_k'] >= 5) & (df['stoch_k'] <= 95)
            
            # 5. Volume (relaxed)
            volume_ok = df['volume_ratio'] >= 0.8
            
            # 6. Momentum (relaxed)
            momentum_ok = df['price_momentum'] > -0.1
            rsi_ok = (df['rsi'] >= 20) & (df['rsi'] <= 90)
            
            # 7. MACD (relaxed)
            macd_ok = df['macd'] > df['macd_signal'] - 0.5
            
            # COMBINED ENTRY CONDITIONS
            entry_conditions = (
                liquidity_pass &
                price_pass &
                trend_pass &
                stoch_entry &
                volume_ok &
                momentum_ok &
                rsi_ok &
                macd_ok
            )
            
            # EXIT CONDITIONS
            stoch_overbought = df['stoch_k'] > 95
            rsi_overbought = df['rsi'] > 85
            macd_bearish = df['macd'] < df['macd_signal'] - 0.3
            momentum_negative = df['price_momentum'] < -0.15
            
            exit_conditions = (
                stoch_overbought |
                rsi_overbought |
                macd_bearish |
                momentum_negative
            )
            
            # Generate signals
            signals = pd.Series(0, index=df.index)
            signals.loc[entry_conditions] = 1
            signals.loc[exit_conditions] = -1
            
            # Prevent same-day buy/sell
            buy_signals = signals == 1
            sell_signals = signals == -1
            same_day = buy_signals & sell_signals
            signals.loc[same_day] = 0
            
            # Debug info
            total_days = len(df)
            buy_count = (signals == 1).sum()
            sell_count = (signals == -1).sum()
            
            log_info(f"FINAL STRATEGY {ticker}:")
            log_info(f"  • Entry Pass Rate: {entry_conditions.sum()/total_days*100:.1f}%")
            log_info(f"  • Buy Signals: {buy_count} ({buy_count/total_days*100:.1f}% of days)")
            log_info(f"  • Signal Frequency: {buy_count/total_days*252:.1f} buys/year")
            
            return signals
            
        except Exception as e:
            log_error(f"Error generating final signals for {ticker}: {e}")
            return pd.Series(0, index=df.index)
    
    def calculate_positions(self, signals, df):
        """Calculate positions with proper execution"""
        try:
            positions = pd.Series(0.0, index=df.index)
            
            # Position sizing
            base_position = 0.05  # 5% risk per trade (more aggressive)
            
            # Execute positions
            current_position = 0.0
            
            for i in range(len(signals)):
                if signals.iloc[i] == 1 and current_position == 0:
                    # Entry
                    current_position = base_position
                elif signals.iloc[i] == -1 and current_position > 0:
                    # Exit
                    current_position = 0.0
                
                positions.iloc[i] = current_position
            
            return positions
            
        except Exception as e:
            log_error(f"Error calculating positions: {e}")
            return pd.Series(0.0, index=df.index)
    
    def backtest_final_strategy(self, ticker, start_date='2018-01-01', end_date='2023-12-31'):
        """Backtest final strategy"""
        try:
            print(f"\n🎯 FINAL STRATEGY TEST: {ticker}")
            print("-" * 50)
            
            # Load data
            from scripts.vectorized_backtester import VectorizedBacktester
            backtester = VectorizedBacktester(initial_capital=100000)
            df = backtester.load_20yr_data(ticker)
            
            if df is None or df.empty:
                return None
            
            # Filter date range
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            
            df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # Generate signals
            signals = self.generate_final_signals(df, ticker)
            
            # Calculate positions
            positions = self.calculate_positions(signals, df)
            
            # Calculate returns
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            strategy_returns = positions * df[close_col].pct_change()
            
            # Calculate equity curve
            equity_curve = 100000 * (1 + strategy_returns).cumprod()
            
            # Calculate metrics
            metrics = self.calculate_metrics(equity_curve, strategy_returns)
            
            # Extract trades
            trades = self.extract_trades(df, signals, positions)
            
            # Display results
            print(f"🎯 FINAL PERFORMANCE:")
            print(f"  • Total Return: {metrics['total_return']*100:.1f}%")
            print(f"  • CAGR: {metrics['cagr']*100:.2f}%")
            print(f"  • Win Rate: {metrics['win_rate']*100:.1f}%")
            print(f"  • Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  • Max Drawdown: {metrics['max_drawdown']*100:.1f}%")
            print(f"  • Final Equity: ${metrics['final_equity']:,.2f}")
            print(f"  • Total Trades: {len(trades)}")
            
            # Signal frequency
            buy_signals = (signals == 1).sum()
            signal_frequency = buy_signals / len(signals) * 252
            print(f"  • Signal Frequency: {signal_frequency:.1f} buys/year")
            
            # Assessment
            if metrics['cagr'] >= 0.20:
                print(f"  ✅ EXCELLENT: 20%+ CAGR!")
            elif metrics['cagr'] >= 0.15:
                print(f"  🚀 GOOD: 15%+ CAGR!")
            elif metrics['cagr'] >= 0.10:
                print(f"  ⚠️  MODERATE: 10%+ CAGR")
            else:
                print(f"  ❌ POOR: <10% CAGR")
            
            return {
                'ticker': ticker,
                'metrics': metrics,
                'signal_frequency': signal_frequency,
                'total_trades': len(trades)
            }
            
        except Exception as e:
            print(f"❌ Error testing {ticker}: {e}")
            return None
    
    def calculate_metrics(self, equity_curve, strategy_returns):
        """Calculate performance metrics"""
        try:
            equity_clean = equity_curve.dropna()
            returns_clean = strategy_returns.dropna()
            
            if len(equity_clean) < 2:
                return self.get_default_metrics()
            
            # Total return
            total_return = (equity_clean.iloc[-1] / equity_clean.iloc[0]) - 1
            
            # CAGR
            days = len(equity_clean)
            years = days / 252
            if years > 0 and equity_clean.iloc[0] > 0:
                cagr = (equity_clean.iloc[-1] / equity_clean.iloc[0]) ** (1/years) - 1
            else:
                cagr = 0.0
            
            # Max drawdown
            rolling_max = equity_clean.expanding().max()
            drawdown = (equity_clean - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Win rate
            non_zero_returns = returns_clean[returns_clean != 0]
            if len(non_zero_returns) > 0:
                positive_returns = non_zero_returns[non_zero_returns > 0]
                win_rate = len(positive_returns) / len(non_zero_returns)
            else:
                win_rate = 0.0
            
            # Sharpe ratio
            if returns_clean.std() > 0:
                sharpe_ratio = returns_clean.mean() / returns_clean.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
            
            # Profit factor
            positive_returns = returns_clean[returns_clean > 0]
            negative_returns = returns_clean[returns_clean < 0]
            
            if len(negative_returns) > 0 and negative_returns.sum() != 0:
                profit_factor = abs(positive_returns.sum() / negative_returns.sum())
            else:
                profit_factor = float('inf') if len(positive_returns) > 0 else 0.0
            
            return {
                'total_return': total_return,
                'cagr': cagr,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'win_rate': win_rate,
                'profit_factor': profit_factor,
                'final_equity': equity_clean.iloc[-1],
                'total_trades': len(non_zero_returns)
            }
            
        except Exception as e:
            log_error(f"Error calculating metrics: {e}")
            return self.get_default_metrics()
    
    def get_default_metrics(self):
        """Default metrics"""
        return {
            'total_return': 0.0,
            'cagr': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'final_equity': 100000.0,
            'total_trades': 0
        }
    
    def extract_trades(self, df, signals, positions):
        """Extract trades"""
        trades = []
        
        for i, (date, position) in enumerate(positions.items()):
            if position > 0 and (i == 0 or positions.iloc[i-1] == 0):
                # Entry
                close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'action': 'BUY',
                    'price': df.loc[date, close_col],
                    'shares': 100
                })
            elif position == 0 and i > 0 and positions.iloc[i-1] > 0:
                # Exit
                close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
                trades.append({
                    'date': date.strftime('%Y-%m-%d'),
                    'action': 'SELL',
                    'price': df.loc[date, close_col],
                    'shares': 100
                })
        
        return trades

def main():
    """Main execution"""
    print("🎯 FINAL CAGR OPTIMIZATION - PHASE 3")
    print("=" * 70)
    
    strategy = FinalOptimizedStrategy()
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    results = []
    
    for ticker in tickers:
        result = strategy.backtest_final_strategy(ticker)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print(f"\n🎯 FINAL OPTIMIZATION SUMMARY:")
        print("=" * 60)
        
        avg_cagr = np.mean([r['metrics']['cagr'] for r in results])
        avg_return = np.mean([r['metrics']['total_return'] for r in results])
        avg_win_rate = np.mean([r['metrics']['win_rate'] for r in results])
        avg_signal_freq = np.mean([r['signal_frequency'] for r in results])
        total_trades = sum([r['total_trades'] for r in results])
        
        print(f"📊 AVERAGE PERFORMANCE:")
        print(f"  • CAGR: {avg_cagr*100:.2f}%")
        print(f"  • Total Return: {avg_return*100:.1f}%")
        print(f"  • Win Rate: {avg_win_rate*100:.1f}%")
        print(f"  • Signal Frequency: {avg_signal_freq:.1f} buys/year")
        print(f"  • Total Trades: {total_trades}")
        
        print(f"\n📈 INDIVIDUAL RESULTS:")
        for result in results:
            ticker = result['ticker']
            cagr = result['metrics']['cagr'] * 100
            trades = result['total_trades']
            print(f"  • {ticker}: {cagr:.1f}% CAGR, {trades} trades")
        
        # Final assessment
        print(f"\n🎯 FINAL OPTIMIZATION ASSESSMENT:")
        if avg_cagr >= 0.20:
            print(f"  ✅ TARGET ACHIEVED: 20%+ CAGR!")
            print(f"  🎉 OPTIMIZATION SUCCESS!")
        elif avg_cagr >= 0.15:
            print(f"  🚀 GOOD PROGRESS: 15%+ CAGR")
        elif avg_cagr >= 0.10:
            print(f"  ⚠️  MODERATE: 10%+ CAGR")
        else:
            print(f"  ❌ NEEDS MORE WORK: <10% CAGR")
        
        # Comparison to original
        improvement = avg_cagr - 0.058
        improvement_factor = avg_cagr / 0.058 if 0.058 > 0 else 0
        
        print(f"\n🚀 FINAL PERFORMANCE IMPROVEMENT:")
        print(f"  • Original CAGR: 5.80% (Pathetic)")
        print(f"  • Final CAGR: {avg_cagr*100:.2f}%")
        print(f"  • Improvement: {improvement*100:+.2f}%")
        print(f"  • Improvement Factor: {improvement_factor:.1f}x better!")
        
        print(f"\n💡 OPTIMIZATION ACHIEVEMENTS:")
        print(f"  ✅ Fixed signal frequency issues")
        print(f"  ✅ Expanded stochastic range (5-95)")
        print(f"  ✅ Relaxed all entry conditions")
        print(f"  ✅ Added proper position execution")
        print(f"  ✅ Increased position sizing to 5%")
        print(f"  ✅ Added momentum indicators")

if __name__ == "__main__":
    main()
