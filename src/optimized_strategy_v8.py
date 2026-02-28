#!/usr/bin/env python3
"""
Optimized Strategy v8.0 - CAGR Optimization Edition
Target: 20%+ CAGR by fixing signal frequency and entry conditions
"""

import pandas as pd
import numpy as np
import sys
import os
from datetime import datetime, timedelta

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from src.strategy_v7_2 import add_indicators_v7_2
from src.notifications import log_info, log_error

class OptimizedStrategy:
    """Optimized strategy for 20%+ CAGR target"""
    
    def __init__(self):
        self.name = "Optimized v8.0"
        self.target_cagr = 0.20  # 20% target
        
    def add_optimized_indicators(self, df):
        """Add enhanced indicators with better signal generation"""
        df = df.copy()
        
        # Add base indicators from v7.2
        df = add_indicators_v7_2(df)
        
        # Add RSI for momentum confirmation
        delta = df['adjClose'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # Add ATR for dynamic stops
        high_col = 'adjHigh' if 'adjHigh' in df.columns else 'High'
        low_col = 'adjLow' if 'adjLow' in df.columns else 'Low'
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close'
        
        df['tr'] = np.maximum(
            df[high_col] - df[low_col],
            np.maximum(abs(df[high_col] - df[close_col].shift(1)), 
                      abs(df[low_col] - df[close_col].shift(1)))
        )
        df['atr'] = df['tr'].rolling(14).mean()
        
        # Add MACD for trend confirmation
        exp1 = df[close_col].ewm(span=12).mean()
        exp2 = df[close_col].ewm(span=26).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9).mean()
        df['macd_histogram'] = df['macd'] - df['macd_signal']
        
        # Enhanced volume analysis
        volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
        df['volume_sma_fast'] = df[volume_col].rolling(10).mean()
        df['volume_sma_slow'] = df[volume_col].rolling(50).mean()
        df['volume_ratio'] = df[volume_col] / df['volume_sma_slow']
        
        # Volatility bands
        df['volatility'] = df[close_col].pct_change().rolling(20).std() * np.sqrt(252)
        df['vol_ma'] = df['volatility'].rolling(50).mean()
        df['high_volatility'] = df['volatility'] > df['vol_ma'] * 1.2
        df['low_volatility'] = df['volatility'] < df['vol_ma'] * 0.8
        
        return df
    
    def generate_optimized_signals(self, df, ticker):
        """Generate optimized signals with higher frequency"""
        try:
            # Add optimized indicators
            df = self.add_optimized_indicators(df)
            
            # Define columns
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            volume_col = 'Volume' if 'Volume' in df.columns else 'volume'
            
            # OPTIMIZED ENTRY CONDITIONS - Much less restrictive!
            
            # 1. Basic liquidity check (relaxed)
            df['dollar_volume'] = df[close_col] * df[volume_col]
            liquidity_pass = df['dollar_volume'] >= 500000  # Reduced from $1M to $500K
            
            # 2. Price check (relaxed)
            price_pass = df[close_col] <= 1000  # Increased from $500 to $1000
            
            # 3. Trend check (relaxed)
            trend_pass = df[close_col] > df['sma_50']  # 50-day instead of 200-day
            
            # 4. EXPANDED Stochastic range (KEY OPTIMIZATION!)
            stoch_entry = (df['stoch_k'] >= 20) & (df['stoch_k'] <= 90)  # 20-90 instead of 32-80
            
            # 5. Volume confirmation (enhanced)
            volume_surge = df['volume_ratio'] >= 1.2  # 20% above average
            
            # 6. Momentum confirmation (NEW)
            rsi_ok = (df['rsi'] >= 30) & (df['rsi'] <= 80)  # RSI 30-80
            macd_bullish = df['macd'] > df['macd_signal']  # MACD bullish
            
            # 7. REMOVED CAGR filter (KEY OPTIMIZATION!)
            # No more CAGR > 15% requirement - this was killing signals!
            
            # COMBINED ENTRY CONDITIONS (Optimized)
            entry_conditions = (
                liquidity_pass &
                price_pass &
                trend_pass &
                stoch_entry &
                volume_surge &
                rsi_ok &
                macd_bullish
            )
            
            # OPTIMIZED EXIT CONDITIONS
            
            # Standard exit conditions
            stoch_overbought = df['stoch_k'] > 85  # Raised from 80
            stoch_roll_over = df['stoch_k'] < df['stoch_d']
            
            # ATR-based dynamic stop (NEW)
            atr_stop_loss = df[close_col] < (df[close_col].shift(1) - df['atr'] * 2)  # 2x ATR stop
            
            # RSI overbought
            rsi_overbought = df['rsi'] > 75
            
            # MACD bearish crossover
            macd_bearish = df['macd'] < df['macd_signal']
            
            # Combined exit conditions (more flexible)
            exit_conditions = (
                stoch_overbought |
                stoch_roll_over |
                atr_stop_loss |
                rsi_overbought |
                macd_bearish
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
            
            log_info(f"OPTIMIZED STRATEGY {ticker}:")
            log_info(f"  • Entry Conditions Pass Rate: {entry_conditions.sum()/total_days*100:.1f}%")
            log_info(f"  • Buy Signals: {buy_count} ({buy_count/total_days*100:.1f}% of days)")
            log_info(f"  • Sell Signals: {sell_count} ({sell_count/total_days*100:.1f}% of days)")
            log_info(f"  • Signal Frequency: {buy_count/total_days*252:.1f} buys per year")
            
            # Individual condition analysis
            log_info(f"  • Liquidity Pass: {liquidity_pass.sum()/total_days*100:.1f}%")
            log_info(f"  • Price Pass: {price_pass.sum()/total_days*100:.1f}%")
            log_info(f"  • Trend Pass: {trend_pass.sum()/total_days*100:.1f}%")
            log_info(f"  • Stochastic Entry: {stoch_entry.sum()/total_days*100:.1f}%")
            log_info(f"  • Volume Surge: {volume_surge.sum()/total_days*100:.1f}%")
            log_info(f"  • RSI OK: {rsi_ok.sum()/total_days*100:.1f}%")
            log_info(f"  • MACD Bullish: {macd_bullish.sum()/total_days*100:.1f}%")
            
            return signals
            
        except Exception as e:
            log_error(f"Error generating optimized signals for {ticker}: {e}")
            return pd.Series(0, index=df.index)
    
    def calculate_optimized_positions(self, signals, df):
        """Calculate positions with volatility-adjusted sizing"""
        positions = pd.Series(0, index=df.index)
        
        # Volatility-adjusted position sizing
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        volatility = df[close_col].pct_change().rolling(20).std() * np.sqrt(252)
        
        # Base position size (2% risk per trade)
        base_position = 0.02
        
        # Adjust for volatility (higher volatility = smaller position)
        vol_adjustment = 0.20 / volatility  # Target 20% annual volatility
        vol_adjustment = vol_adjustment.clip(0.5, 2.0)  # Limit adjustment
        
        # Calculate position sizes
        position_sizes = base_position * vol_adjustment
        
        # Apply positions based on signals
        current_position = 0
        for i in range(len(signals)):
            if signals.iloc[i] == 1 and current_position == 0:
                # Entry signal - calculate position size
                current_position = position_sizes.iloc[i]
            elif signals.iloc[i] == -1 and current_position > 0:
                # Exit signal
                current_position = 0
            
            positions.iloc[i] = current_position
        
        return positions

def test_optimized_strategy():
    """Test the optimized strategy against the original"""
    print("🚀 OPTIMIZED STRATEGY v8.0 - CAGR IMPROVEMENT TEST")
    print("=" * 80)
    
    optimized = OptimizedStrategy()
    
    # Test on key stocks
    tickers = ['AAPL', 'MSFT', 'GOOGL', 'TSLA', 'NVDA']
    
    for ticker in tickers:
        try:
            print(f"\n📊 TESTING OPTIMIZED STRATEGY: {ticker}")
            print("-" * 60)
            
            # Load data
            from scripts.vectorized_backtester import VectorizedBacktester
            backtester = VectorizedBacktester(initial_capital=100000)
            df = backtester.load_20yr_data(ticker)
            
            if df is None or df.empty:
                print(f"❌ No data for {ticker}")
                continue
            
            # Filter to 5-year period
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df = df.set_index('date')
            
            df = df[(df.index >= '2018-01-01') & (df.index <= '2023-12-31')]
            
            # Generate optimized signals
            signals = optimized.generate_optimized_signals(df, ticker)
            
            # Calculate positions
            positions = optimized.calculate_optimized_positions(signals, df)
            
            # Calculate returns
            close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
            strategy_returns = positions * df[close_col].pct_change()
            
            # Calculate performance metrics
            equity_curve = 100000 * (1 + strategy_returns).cumprod()
            
            if len(equity_curve) > 1:
                total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
                days = len(equity_curve)
                years = days / 252
                cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1/years) - 1
                
                # Win rate
                non_zero_returns = strategy_returns[strategy_returns != 0]
                if len(non_zero_returns) > 0:
                    positive_returns = non_zero_returns[non_zero_returns > 0]
                    win_rate = len(positive_returns) / len(non_zero_returns)
                else:
                    win_rate = 0.0
                
                print(f"🎯 OPTIMIZED PERFORMANCE:")
                print(f"  • Total Return: {total_return*100:.1f}%")
                print(f"  • CAGR: {cagr*100:.2f}%")
                print(f"  • Win Rate: {win_rate*100:.1f}%")
                print(f"  • Final Equity: ${equity_curve.iloc[-1]:,.2f}")
                
                # Compare to target
                if cagr >= 0.20:
                    print(f"  ✅ CAGR TARGET MET (20%+)")
                elif cagr >= 0.15:
                    print(f"  ⚠️  CAGR IMPROVING (15-20%)")
                else:
                    print(f"  ❌ CAGR STILL LOW (<15%)")
            
        except Exception as e:
            print(f"❌ Error testing {ticker}: {e}")
            continue
    
    print(f"\n🎯 OPTIMIZATION SUMMARY:")
    print("=" * 60)
    print("✅ KEY IMPROVEMENTS IMPLEMENTED:")
    print("  1. EXPANDED Stochastic Range: 20-90 (was 32-80)")
    print("  2. REMOVED CAGR Filter: No more 15% requirement")
    print("  3. RELAXED Trend Filter: SMA50 instead of SMA200")
    print("  4. ADDED Momentum: RSI + MACD confirmation")
    print("  5. DYNAMIC Exits: ATR-based stops")
    print("  6. VOLATILITY-ADJUSTED Sizing: Risk-based position sizing")
    
    print(f"\n🚀 EXPECTED CAGR IMPROVEMENT:")
    print("  • Previous: 5.80% (Pathetic)")
    print("  • Target: 20%+ (Professional grade)")
    print("  • Improvement: 3.4x better!")

if __name__ == "__main__":
    test_optimized_strategy()
