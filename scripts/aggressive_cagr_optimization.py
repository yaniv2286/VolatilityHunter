#!/usr/bin/env python3
"""
AGGRESSIVE CAGR OPTIMIZATION - Phase 2
Fix position execution and implement aggressive trading strategy
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

class AggressiveOptimizedStrategy:
    """Aggressive optimization for 20%+ CAGR target"""
    
    def __init__(self):
        self.name = "Aggressive Optimized v8.1"
        self.target_cagr = 0.20  # 20% target
        
    def add_aggressive_indicators(self, df):
        """Add aggressive indicators for more signals"""
        df = df.copy()
        
        # Add base indicators
        df = add_indicators_v7_2(df)
        
        # Add RSI
        delta = df['adjClose'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Add MACD
        exp1 = df['adjClose'].ewm(span=12).mean()
        exp2 = df['adjClose'].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        
        # Add momentum indicators
        df['momentum_5'] = df['adjClose'].pct_change(5)
        df['momentum_10'] = df['adjClose'].pct_change(10)
        df['momentum_20'] = df['adjClose'].pct_change(20)
        
        # Volume analysis
        volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
        df['volume_sma'] = df[volume_col].rolling(20).mean()
        df['volume_ratio'] = df[volume_col] / df['volume_sma']
        
        # Price momentum
        df['price_momentum'] = df['adjClose'] / df['adjClose'].rolling(10).mean() - 1
        
        return df
    
    def generate_aggressive_signals(self, df, ticker):
        """Generate aggressive signals for maximum trading frequency"""
        try:
            # Add indicators
            df = self.add_aggressive_indicators(df)
            
            # Define columns
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
            
            # AGGRESSIVE ENTRY CONDITIONS - Much more relaxed!
            
            # 1. Basic liquidity (very relaxed)
            df['dollar_volume'] = df[close_col] * df[volume_col]
            liquidity_pass = df['dollar_volume'] >= 100000  # $100K minimum
            
            # 2. Price check (very relaxed)
            price_pass = df[close_col] <= 2000  # $2000 max
            
            # 3. Trend check (relaxed)
            trend_pass = df[close_col] > df['sma_20']  # 20-day SMA
            
            # 4. VERY EXPANDED Stochastic range
            stoch_entry = (df['stoch_k'] >= 10) & (df['stoch_k'] <= 95)  # 10-95 range!
            
            # 5. Volume confirmation (relaxed)
            volume_ok = df['volume_ratio'] >= 1.0  # Just average volume
            
            # 6. Momentum confirmation (relaxed)
            momentum_ok = df['price_momentum'] > -0.05  # Not too negative
            rsi_ok = (df['rsi'] >= 25) & (df['rsi'] <= 85)  # Very wide RSI range
            
            # 7. MACD confirmation (relaxed)
            macd_ok = df['macd'] > df['macd_signal'] - 0.1  # Slightly bearish allowed
            
            # COMBINED ENTRY CONDITIONS (Very Aggressive)
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
            
            # AGGRESSIVE EXIT CONDITIONS
            
            # Multiple exit signals
            stoch_overbought = df['stoch_k'] > 90  # Very overbought
            rsi_overbought = df['rsi'] > 80
            macd_bearish = df['macd'] < df['macd_signal'] - 0.2  # Strong bearish
            momentum_negative = df['price_momentum'] < -0.1  # Strong negative momentum
            
            # Quick profit taking
            quick_profit = df['price_momentum'] > 0.05  # 5% quick profit
            
            # Combined exit conditions
            exit_conditions = (
                stoch_overbought |
                rsi_overbought |
                macd_bearish |
                momentum_negative |
                quick_profit
            )
            
            # Generate signals
            signals = pd.Series(0, index=df.index)
            
            # Entry signals
            signals.loc[entry_conditions] = 1
            
            # Exit signals
            signals.loc[exit_conditions] = -1
            
            # Prevent same-day buy/sell
            buy_signals = signals == 1
            sell_signals = signals == -1
            same_day = buy_signals & sell_signals
            signals.loc[same_day] = 0
            
            # Debug information
            total_days = len(df)
            buy_count = (signals == 1).sum()
            sell_count = (signals == -1).sum()
            
            log_info(f"AGGRESSIVE STRATEGY {ticker}:")
            log_info(f"  • Entry Conditions Pass Rate: {entry_conditions.sum()/total_days*100:.1f}%")
            log_info(f"  • Buy Signals: {buy_count} ({buy_count/total_days*100:.1f}% of days)")
            log_info(f"  • Sell Signals: {sell_count} ({sell_count/total_days*100:.1f}% of days)")
            log_info(f"  • Signal Frequency: {buy_count/total_days*252:.1f} buys per year")
            
            return signals
            
        except Exception as e:
            log_error(f"Error generating aggressive signals for {ticker}: {e}")
            return pd.Series(0, index=df.index)
    
    def calculate_aggressive_positions(self, signals, df):
        """Calculate positions with aggressive sizing"""
        try:
            positions = pd.Series(0.0, index=df.index)  # Use float dtype
            
            # Aggressive position sizing (3% risk per trade)
            base_position = 0.03  # 3% risk per trade
            
            # Volatility adjustment
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            volatility = df[close_col].pct_change().rolling(20).std() * np.sqrt(252)
            vol_adjustment = 0.25 / volatility  # Target 25% volatility
            vol_adjustment = vol_adjustment.clip(0.5, 2.0)
            
            # Calculate position sizes
            position_sizes = base_position * vol_adjustment
            
            # Execute positions based on signals
            current_position = 0.0
            
            for i in range(len(signals)):
                if signals.iloc[i] == 1 and current_position == 0:
                    # Entry signal
                    current_position = position_sizes.iloc[i]
                elif signals.iloc[i] == -1 and current_position > 0:
                    # Exit signal
                    current_position = 0.0
                
                positions.iloc[i] = current_position
            
            return positions
            
        except Exception as e:
            log_error(f"Error calculating aggressive positions: {e}")
            return pd.Series(0.0, index=df.index)
    
    def backtest_aggressive_strategy(self, ticker, start_date='2018-01-01', end_date='2023-12-31'):
        """Backtest aggressive strategy"""
        try:
            print(f"\n🚀 AGGRESSIVE STRATEGY TEST: {ticker}")
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
            
            # Generate aggressive signals
            signals = self.generate_aggressive_signals(df, ticker)
            
            # Calculate aggressive positions
            positions = self.calculate_aggressive_positions(signals, df)
            
            # Calculate returns
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            strategy_returns = positions * df[close_col].pct_change()
            
            # Calculate equity curve
            equity_curve = 100000 * (1 + strategy_returns).cumprod()
            
            # Calculate performance metrics
            metrics = self.calculate_metrics(equity_curve, strategy_returns)
            
            # Extract trades
            trades = self.extract_trades(df, signals, positions)
            
            # Display results
            print(f"🎯 AGGRESSIVE PERFORMANCE:")
            print(f"  • Total Return: {metrics['total_return']*100:.1f}%")
            print(f"  • CAGR: {metrics['cagr']*100:.2f}%")
            print(f"  • Win Rate: {metrics['win_rate']*100:.1f}%")
            print(f"  • Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
            print(f"  • Max Drawdown: {metrics['max_drawdown']*100:.1f}%")
            print(f"  • Profit Factor: {metrics['profit_factor']:.2f}")
            print(f"  • Final Equity: ${metrics['final_equity']:,.2f}")
            print(f"  • Total Trades: {len(trades)}")
            
            # Signal frequency
            buy_signals = (signals == 1).sum()
            total_days = len(signals)
            signal_frequency = buy_signals / total_days * 252
            
            print(f"\n🔄 SIGNAL ANALYSIS:")
            print(f"  • Buy Signals: {buy_signals} ({buy_signals/total_days*100:.1f}% of days)")
            print(f"  • Signal Frequency: {signal_frequency:.1f} buys per year")
            
            # Trade analysis
            if trades:
                trade_pnl = []
                for i in range(0, len(trades)-1, 2):
                    if i+1 < len(trades):
                        buy_trade = trades[i]
                        sell_trade = trades[i+1]
                        if buy_trade['action'] == 'BUY' and sell_trade['action'] == 'SELL':
                            pnl = (sell_trade['price'] - buy_trade['price']) / buy_trade['price'] * 100
                            trade_pnl.append(pnl)
                
                if trade_pnl:
                    avg_pnl = np.mean(trade_pnl)
                    win_rate_trades = len([p for p in trade_pnl if p > 0]) / len(trade_pnl) * 100
                    print(f"\n💰 TRADE ANALYSIS:")
                    print(f"  • Average Trade P&L: {avg_pnl:.2f}%")
                    print(f"  • Trade Win Rate: {win_rate_trades:.1f}%")
                    print(f"  • Best Trade: {max(trade_pnl):.2f}%")
                    print(f"  • Worst Trade: {min(trade_pnl):.2f}%")
            
            # Performance assessment
            if metrics['cagr'] >= 0.20:
                print(f"  ✅ EXCELLENT: 20%+ CAGR achieved!")
            elif metrics['cagr'] >= 0.15:
                print(f"  🚀 GOOD: 15%+ CAGR achieved!")
            elif metrics['cagr'] >= 0.10:
                print(f"  ⚠️  MODERATE: 10%+ CAGR achieved")
            else:
                print(f"  ❌ POOR: <10% CAGR - needs more optimization")
            
            return {
                'ticker': ticker,
                'metrics': metrics,
                'signal_frequency': signal_frequency,
                'total_trades': len(trades),
                'signals': signals,
                'positions': positions
            }
            
        except Exception as e:
            print(f"❌ Error testing {ticker}: {e}")
            return None
    
    def calculate_metrics(self, equity_curve, strategy_returns):
        """Calculate performance metrics"""
        try:
            # Clean data
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
    print("🚀 AGGRESSIVE CAGR OPTIMIZATION - PHASE 2")
    print("=" * 70)
    
    strategy = AggressiveOptimizedStrategy()
    
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    results = []
    
    for ticker in tickers:
        result = strategy.backtest_aggressive_strategy(ticker)
        if result:
            results.append(result)
    
    # Summary
    if results:
        print(f"\n🎯 AGGRESSIVE OPTIMIZATION SUMMARY:")
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
            signal_freq = result['signal_frequency']
            trades = result['total_trades']
            print(f"  • {ticker}: {cagr:.1f}% CAGR, {signal_freq:.1f} buys/year, {trades} trades")
        
        # Assessment
        print(f"\n🎯 AGGRESSIVE OPTIMIZATION ASSESSMENT:")
        if avg_cagr >= 0.20:
            print(f"  ✅ TARGET ACHIEVED: 20%+ CAGR!")
            print(f"  🎉 AGGRESSIVE STRATEGY SUCCESS!")
        elif avg_cagr >= 0.15:
            print(f"  🚀 GOOD PROGRESS: 15%+ CAGR")
            print(f"  💡 Close to target!")
        elif avg_cagr >= 0.10:
            print(f"  ⚠️  MODERATE: 10%+ CAGR")
            print(f"  🔧 More aggression needed")
        else:
            print(f"  ❌ STILL POOR: <10% CAGR")
            print(f"  🚨 Maximum aggression required!")
        
        # Comparison
        improvement = avg_cagr - 0.058
        improvement_factor = avg_cagr / 0.058 if 0.058 > 0 else 0
        
        print(f"\n🚀 PERFORMANCE IMPROVEMENT:")
        print(f"  • Original CAGR: 5.80% (Pathetic)")
        print(f"  • Aggressive CAGR: {avg_cagr*100:.2f}%")
        print(f"  • Improvement: {improvement*100:+.2f}%")
        print(f"  • Improvement Factor: {improvement_factor:.1f}x better!")

if __name__ == "__main__":
    main()
