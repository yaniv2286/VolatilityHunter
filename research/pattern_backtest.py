#!/usr/bin/env python3
"""
VolatilityHunter Pattern Recognition Backtest
Compare v5.5 (Base) vs v6.0 (Patterns) performance
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime
import glob
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
from tqdm import tqdm
warnings.filterwarnings('ignore')

# Import pattern detection for Phase 1 Visual Pattern Recognition
try:
    from src.strategy import detect_patterns
    PATTERNS_AVAILABLE = True
except ImportError:
    print("Warning: Could not import detect_patterns from src.strategy")
    PATTERNS_AVAILABLE = False

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PatternBacktestEngine:
    """Backtesting engine for Pattern Recognition comparison"""
    
    def __init__(self, data_dir='data/', starting_capital=100000, max_positions=10):
        self.data_dir = data_dir
        self.starting_capital = starting_capital
        self.max_positions = max_positions
        self.position_size = 0.10  # 10% allocation per trade
        self.transaction_cost = 0.0001  # 0.01% slippage/fee
        
    def load_ticker_data(self, ticker):
        """Load and validate parquet data for a ticker"""
        try:
            file_path = os.path.join(self.data_dir, f"{ticker.lower()}.parquet")
            if not os.path.exists(file_path):
                return None
                
            df = pd.read_parquet(file_path)
            
            # Validate required columns (handle both uppercase and lowercase)
            required_cols_lower = ['close', 'high', 'low', 'volume']
            required_cols_upper = ['Close', 'High', 'Low', 'Volume']
            
            # Check for lowercase columns
            if all(col in df.columns for col in required_cols_lower):
                df = df.rename(columns={
                    'close': 'Close',
                    'high': 'High',
                    'low': 'Low',
                    'volume': 'Volume'
                })
            # Check for uppercase columns
            elif not all(col in df.columns for col in required_cols_upper):
                logger.warning(f"Missing required columns in {ticker}")
                return None
                
            # Ensure data is sorted by date
            if 'date' in df.columns:
                df = df.sort_values('date')
                df.set_index('date', inplace=True)
            
            # Convert to numeric if needed
            for col in ['Close', 'High', 'Low', 'Volume']:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            # Remove any NaN values
            df = df.dropna(subset=['Close', 'High', 'Low', 'Volume'])
            
            if len(df) < 12:
                logger.warning(f"Insufficient data for {ticker}: {len(df)} days")
                return None
                
            return df
            
        except Exception as e:
            logger.error(f"Error loading {ticker}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calculate technical indicators"""
        # Calculate SMA 200
        sma_period = min(200, len(df) // 2)
        if sma_period < 5:
            sma_period = 5
        df['sma_200'] = df['Close'].rolling(window=sma_period, min_periods=1).mean()
        
        # Calculate Stochastic (10,3,3) - A+ Wealth Builder
        k_period = 10
        d_period = 3
        smooth = 3
        
        low_min = df['Low'].rolling(window=k_period).min()
        high_max = df['High'].rolling(window=k_period).max()
        
        # Handle division by zero
        denominator = high_max - low_min
        denominator = denominator.replace(0, np.nan)  # Avoid division by zero
        
        k_raw = 100 * ((df['Close'] - low_min) / denominator)
        k_smooth = k_raw.rolling(window=smooth).mean()
        df['stoch_k'] = k_smooth
        df['stoch_d'] = k_smooth.rolling(window=d_period).mean()
        
        # Calculate Volume SMA 30
        df['volume_sma_30'] = df['Volume'].rolling(window=30, min_periods=1).mean()
        
        # Calculate CAGR (2-year)
        if len(df) >= 50:
            lookback = min(504, len(df) // 2)  # 2 years of trading days
            if lookback >= 10:
                start_price = df['Close'].iloc[-lookback]
                if start_price > 0:
                    end_price = df['Close'].iloc[-1]
                    years = lookback / 252  # Trading days per year
                    df['cagr'] = ((end_price / start_price) ** (1/years) - 1) * 100
                else:
                    df['cagr'] = 0.0
            else:
                df['cagr'] = 0.0
        else:
            df['cagr'] = 0.0
        
        return df
    
    def generate_base_signals(self, df):
        """Generate base A+ Wealth Builder signals (v5.5)"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        # A+ Wealth Builder Entry Rules (v5.5)
        entry_condition = (
            (df['Close'] > df['sma_200']) & 
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &  # Sweet spot [32-80]
            (df['volume_sma_30'] > 0) & (df['Volume'] > df['volume_sma_30']) &  # Volume momentum
            (df['cagr'] > 15.0)  # Quality filter
        )
        
        # Exit conditions
        exit_trend = df['Close'] < df['sma_200']
        
        signals.loc[entry_condition, 'signal'] = 1
        signals.loc[exit_trend, 'signal'] = -1
        
        return signals
    
    def generate_pattern_signals(self, df):
        """Generate signals with Phase 1 Visual Pattern Recognition (v6.0)"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        # A+ Wealth Builder Entry Rules (same as base)
        entry_condition = (
            (df['Close'] > df['sma_200']) & 
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &  # Sweet spot [32-80]
            (df['volume_sma_30'] > 0) & (df['Volume'] > df['volume_sma_30']) &  # Volume momentum
            (df['cagr'] > 15.0)  # Quality filter
        )
        
        # Exit conditions
        exit_trend = df['Close'] < df['sma_200']
        
        # Apply pattern detection to entry signals
        if PATTERNS_AVAILABLE and len(df) >= 10:
            pattern_entries = []
            
            for i in range(len(df)):
                if entry_condition.iloc[i]:
                    # Get window for pattern detection
                    window_start = max(0, i - 9)  # Need 10 days for pattern detection
                    window_end = i + 1
                    pattern_df = df.iloc[window_start:window_end].copy()
                    
                    if len(pattern_df) >= 10:
                        patterns = detect_patterns(pattern_df)
                        has_pattern = patterns['is_engulfing'] or patterns['is_w_pattern']
                        
                        if has_pattern:
                            pattern_entries.append(i)
            
            # Create final entry signals with pattern requirement
            final_entries = pd.Series(False, index=df.index)
            for entry_idx in pattern_entries:
                final_entries.iloc[entry_idx] = True
            
            signals.loc[final_entries, 'signal'] = 1
        else:
            # Fallback to base condition if patterns not available
            signals.loc[entry_condition, 'signal'] = 1
        
        signals.loc[exit_trend, 'signal'] = -1
        
        return signals
    
    def simulate_trading(self, df, ticker, use_patterns=False):
        """Simulate trading for a single ticker"""
        df = df.copy()
        
        # Calculate indicators first
        df = self.calculate_indicators(df)
        
        # Choose signal generation method
        if use_patterns:
            signals = self.generate_pattern_signals(df)
        else:
            signals = self.generate_base_signals(df)
        
        if signals['signal'].sum() == 0:  # No signals
            return []
        
        trades = []
        position = None
        
        for date, row in signals.iterrows():
            signal = row['signal']
            
            # Get corresponding price data
            if date in df.index:
                current_row = df.loc[date]
                current_price = current_row['Close']
            else:
                continue
            
            # Entry signal
            if signal == 1 and position is None:
                position = 'long'
                entry_price = current_price
                entry_date = date
                
                # Record entry
                trades.append({
                    'ticker': ticker,
                    'entry_date': entry_date,
                    'entry_price': entry_price,
                    'type': 'BUY',
                    'has_pattern': use_patterns  # Track if this used patterns
                })
                
            # Exit signal
            elif signal == -1 and position == 'long':
                exit_price = current_price * (1 - self.transaction_cost)
                exit_date = date
                
                # Record exit
                trades.append({
                    'ticker': ticker,
                    'entry_date': entry_date,
                    'exit_date': exit_date,
                    'entry_price': entry_price,
                    'exit_price': exit_price,
                    'type': 'SELL',
                    'reason': 'TREND_BREAK',
                    'has_pattern': use_patterns
                })
                
                position = None
        
        return trades
    
    def calculate_portfolio_performance(self, all_trades):
        """Calculate portfolio performance metrics"""
        if not all_trades:
            return {
                'cagr': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'mar_ratio': 0.0,
                'total_trades': 0,
                'win_rate': 0.0,
                'portfolio_history': pd.DataFrame()
            }
        
        # Convert to DataFrame
        trades_df = pd.DataFrame(all_trades)
        
        # Calculate returns
        trades_df['return'] = (trades_df['exit_price'] - trades_df['entry_price']) / trades_df['entry_price']
        
        # Portfolio equity curve
        equity = [self.starting_capital]
        positions = {}
        
        for _, trade in trades_df.iterrows():
            if trade['type'] == 'BUY':
                position_size = self.starting_capital * self.position_size
                positions[trade['ticker']] = {
                    'shares': position_size / trade['entry_price'],
                    'entry_price': trade['entry_price']
                }
                equity.append(equity[-1])  # No change on entry
            else:  # SELL
                if trade['ticker'] in positions:
                    pos = positions.pop(trade['ticker'])
                    proceeds = pos['shares'] * trade['exit_price']
                    equity.append(equity[-1] - (pos['shares'] * pos['entry_price']) + proceeds)
                else:
                    equity.append(equity[-1])
        
        equity_series = pd.Series(equity)
        
        # Calculate metrics
        returns = equity_series.pct_change().dropna()
        
        # CAGR
        total_days = len(equity_series) - 1
        if total_days > 0:
            cagr = (equity_series.iloc[-1] / equity_series.iloc[0]) ** (252/total_days) - 1
        else:
            cagr = 0.0
        
        # Max Drawdown
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Sharpe Ratio
        if len(returns) > 1 and returns.std() > 0:
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252)
        else:
            sharpe_ratio = 0.0
        
        # MAR Ratio
        if max_drawdown != 0:
            mar_ratio = cagr / abs(max_drawdown)
        else:
            mar_ratio = 0.0
        
        # Win Rate
        winning_trades = trades_df[trades_df['return'] > 0]
        win_rate = len(winning_trades) / len(trades_df) if len(trades_df) > 0 else 0.0
        
        return {
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'mar_ratio': mar_ratio,
            'total_trades': len(trades_df),
            'win_rate': win_rate,
            'portfolio_history': equity_series
        }
    
    def run_comparison_backtest(self):
        """Run comparison backtest between base and pattern strategies"""
        print("VolatilityHunter Pattern Recognition Backtest")
        print("="*60)
        print("Comparing v5.5 (Base) vs v6.0 (Patterns)")
        print("="*60)
        
        # Get all tickers
        parquet_files = glob.glob(os.path.join(self.data_dir, "*.parquet"))
        tickers = [os.path.basename(f).replace('.parquet', '').upper() for f in parquet_files]
        print(f"Found {len(tickers)} tickers")
        
        # Process tickers with progress bar
        base_trades = []
        pattern_trades = []
        
        # Temporarily set logging to WARNING level to avoid interfering with progress bar
        original_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.WARNING)
        
        for ticker in tqdm(tickers, desc="Processing Tickers", unit="ticker"):
            df = self.load_ticker_data(ticker)
            if df is not None:
                # Base strategy (v5.5)
                base_trades.extend(self.simulate_trading(df, ticker, use_patterns=False))
                
                # Pattern strategy (v6.0)
                pattern_trades.extend(self.simulate_trading(df, ticker, use_patterns=True))
        
        # Restore original logging level
        logging.getLogger().setLevel(original_level)
        
        print(f"Base strategy trades: {len(base_trades)}")
        print(f"Pattern strategy trades: {len(pattern_trades)}")
        
        # Calculate performance
        base_performance = self.calculate_portfolio_performance(base_trades)
        pattern_performance = self.calculate_portfolio_performance(pattern_trades)
        
        # Generate comparison report
        print("\n" + "="*60)
        print("COMPARISON RESULTS")
        print("="*60)
        
        print(f"\n{'Metric':<20} {'v5.5 (Base)':<15} {'v6.0 (Patterns)':<15} {'Change':<15}")
        print("-" * 65)
        
        metrics = [
            ('CAGR', 'cagr', '{:.2%}'),
            ('Max Drawdown', 'max_drawdown', '{:.2%}'),
            ('Sharpe Ratio', 'sharpe_ratio', '{:.2f}'),
            ('MAR Ratio', 'mar_ratio', '{:.2f}'),
            ('Total Trades', 'total_trades', '{:.0f}'),
            ('Win Rate', 'win_rate', '{:.2%}')
        ]
        
        for metric_name, metric_key, format_str in metrics:
            base_val = base_performance[metric_key]
            pattern_val = pattern_performance[metric_key]
            
            if metric_key == 'max_drawdown':
                change = ((pattern_val - base_val) / abs(base_val) * 100) if base_val != 0 else 0
                change_str = f"{change:+.1f}%"
            elif metric_key == 'total_trades':
                change = ((pattern_val - base_val) / base_val * 100) if base_val != 0 else 0
                change_str = f"{change:+.1f}%"
            else:
                change = ((pattern_val - base_val) / abs(base_val) * 100) if base_val != 0 else 0
                change_str = f"{change:+.1f}%"
            
            print(f"{metric_name:<20} {format_str.format(base_val):<15} {format_str.format(pattern_val):<15} {change_str:<15}")
        
        # Save results to CSV
        results_df = pd.DataFrame([
            {
                'Strategy': 'v5.5 (Base)',
                'CAGR': base_performance['cagr'],
                'Max_Drawdown': base_performance['max_drawdown'],
                'Sharpe_Ratio': base_performance['sharpe_ratio'],
                'MAR_Ratio': base_performance['mar_ratio'],
                'Total_Trades': base_performance['total_trades'],
                'Win_Rate': base_performance['win_rate']
            },
            {
                'Strategy': 'v6.0 (Patterns)',
                'CAGR': pattern_performance['cagr'],
                'Max_Drawdown': pattern_performance['max_drawdown'],
                'Sharpe_Ratio': pattern_performance['sharpe_ratio'],
                'MAR_Ratio': pattern_performance['mar_ratio'],
                'Total_Trades': pattern_performance['total_trades'],
                'Win_Rate': pattern_performance['win_rate']
            }
        ])
        
        results_df.to_csv('pattern_recognition_backtest.csv', index=False)
        print(f"\nResults saved to: pattern_recognition_backtest.csv")
        
        # Analysis
        print("\n" + "="*60)
        print("ANALYSIS")
        print("="*60)
        
        trade_reduction = ((pattern_performance['total_trades'] - base_performance['total_trades']) / base_performance['total_trades'] * 100)
        win_rate_change = (pattern_performance['win_rate'] - base_performance['win_rate']) * 100
        
        print(f"Trade Count Reduction: {trade_reduction:+.1f}%")
        print(f"Win Rate Change: {win_rate_change:+.1f}%")
        
        if pattern_performance['mar_ratio'] > base_performance['mar_ratio']:
            print("✅ MAR Ratio IMPROVED - Patterns added value!")
        else:
            print("⚠️ MAR Ratio decreased - Patterns may be too restrictive")
        
        if pattern_performance['max_drawdown'] > base_performance['max_drawdown']:
            print("✅ Max Drawdown IMPROVED - Patterns saved from bad entries!")
        else:
            print("⚠️ Max Drawdown worsened")
        
        return {
            'base': base_performance,
            'pattern': pattern_performance,
            'results_df': results_df
        }

if __name__ == "__main__":
    engine = PatternBacktestEngine()
    results = engine.run_comparison_backtest()
