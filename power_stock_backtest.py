#!/usr/bin/env python3
"""
VolatilityHunter Power Stock Verification Backtest
Comparing v6.0 (Pattern Hunter) vs v6.5 (Power Hunter)
"""

import os
import pandas as pd
import numpy as np
import logging
from datetime import datetime, timedelta
from tqdm import tqdm
from src.strategy import add_indicators, calculate_stochastic, calculate_multiple_smas, calculate_volume_sma
from src.technical_utils import calculate_atr

# Check if patterns module is available
try:
    import sys
    sys.path.append('.')
    from patterns import detect_patterns
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class PowerStockBacktestEngine:
    def __init__(self, starting_capital=100000, position_size=0.25):
        self.starting_capital = starting_capital
        self.position_size = position_size
        self.data_dir = 'data'
        
    def load_ticker_data(self, ticker):
        """Load and validate parquet data for a ticker"""
        try:
            file_path = os.path.join(self.data_dir, f"{ticker.lower()}.parquet")
            if not os.path.exists(file_path):
                return None
                
            df = pd.read_parquet(file_path)
            
            # Validate required columns
            required_cols_lower = ['close', 'high', 'low', 'volume']
            
            if not all(col in df.columns for col in required_cols_lower):
                logger.warning(f"Missing required columns in {ticker}")
                return None
                
            # Ensure data is sorted by date
            if 'date' in df.columns:
                df = df.sort_values('date')
                df.set_index('date', inplace=True)
            
            # Convert to numeric
            for col in required_cols_lower:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna(subset=required_cols_lower)
            
            if len(df) < 12:
                logger.warning(f"Insufficient data for {ticker}: {len(df)} days")
                return None
                
            return df
            
        except Exception as e:
            logger.error(f"Error loading {ticker}: {e}")
            return None
    
    def calculate_indicators(self, df):
        """Calculate indicators using core strategy logic with adjusted columns"""
        df = df.copy()

        # Import core strategy functions
        from src.strategy import add_indicators, calculate_stochastic, calculate_multiple_smas, calculate_volume_sma

        # Use core strategy's add_indicators function
        df = add_indicators(df)

        # Add additional indicators needed for Power Stock detection
        # Calculate CAGR using adjusted close
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'

        available_days = len(df)
        if available_days < 12:
            df['cagr'] = 0.0
        else:
            # Use available data period
            days_to_use = available_days
            start_price = df[close_col].iloc[0]
            end_price = df[close_col].iloc[-1]

            if start_price <= 0:
                df['cagr'] = 0.0
            else:
                actual_years = days_to_use / 252
                cagr = (end_price / start_price) ** (1/actual_years) - 1
                df['cagr'] = cagr * 100  # Convert to percentage

        # Calculate ATR
        atr_series = calculate_atr(df)
        df['atr'] = atr_series

        # Standardize column names for consistency
        if 'Stochastic_K' in df.columns:
            df['stoch_k'] = df['Stochastic_K']
        if 'Stochastic_D' in df.columns:
            df['stoch_d'] = df['Stochastic_D']
        if 'Volume_SMA_30' in df.columns:
            df['volume_sma_30'] = df['Volume_SMA_30']
        if 'SMA_200' in df.columns:
            df['sma_200'] = df['SMA_200']
        if 'SMA_25' in df.columns:
            df['sma_25'] = df['SMA_25']
        if 'SMA_50' in df.columns:
            df['sma_50'] = df['SMA_50']
        if 'SMA_100' in df.columns:
            df['sma_100'] = df['SMA_100']

        return df
    
    def detect_power_stock(self, df, date_idx):
        """Detect if stock is in Power Stock mode at given date"""
        if date_idx < 10:  # Need enough data
            return False
        
        current_row = df.iloc[date_idx]
        
        # Use adjusted columns if available, otherwise regular columns
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        price = current_row[close_col]
        stoch_k = current_row['stoch_k']
        sma_25 = current_row['sma_25']
        sma_50 = current_row['sma_50']
        sma_100 = current_row['sma_100']
        sma_200 = current_row['sma_200']
        volume = current_row['volume']
        volume_sma = current_row['volume_sma_30']
        
        return (
            stoch_k > 80 and  # Extreme overbought
            price > sma_25 and price > sma_50 and price > sma_100 and price > sma_200 and  # Vertical trend
            volume > volume_sma  # Volume momentum
        )
    
    def generate_v60_signals(self, df):
        """Generate signals for v6.0 (Pattern Hunter)"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        # A+ Wealth Builder Entry Rules
        entry_condition = (
            (df['close'] > df['sma_200']) & 
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &  # Sweet spot [32-80]
            (df['volume_sma_30'] > 0) & (df['volume'] > df['volume_sma_30']) &  # Volume momentum
            (df['cagr'] > 15.0)  # Quality filter
        )
        
        # Apply pattern detection
        if PATTERNS_AVAILABLE and len(df) >= 10:
            pattern_entries = []
            
            for i in range(len(df)):
                if entry_condition.iloc[i]:
                    # Get window for pattern detection
                    window_start = max(0, i - 9)
                    window_end = i + 1
                    pattern_df = df.iloc[window_start:window_end].copy()
                    
                    if len(pattern_df) >= 10:
                        patterns = detect_patterns(pattern_df)
                        has_pattern = patterns['is_engulfing'] or patterns['is_w_pattern']
                        
                        if has_pattern:
                            pattern_entries.append(i)
            
            final_entries = pd.Series(False, index=df.index)
            for entry_idx in pattern_entries:
                final_entries.iloc[entry_idx] = True
            
            signals.loc[final_entries, 'signal'] = 1
        else:
            signals.loc[entry_condition, 'signal'] = 1
        
        # Exit conditions
        exit_trend = df['close'] < df['sma_200']
        signals.loc[exit_trend, 'signal'] = -1
        
        return signals
    
    def generate_v65_signals(self, df):
        """Generate signals for v6.5 (Power Hunter)"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        # A+ Wealth Builder Entry Rules (same as v6.0)
        entry_condition = (
            (df['close'] > df['sma_200']) & 
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &  # Sweet spot [32-80]
            (df['volume_sma_30'] > 0) & (df['volume'] > df['volume_sma_30']) &  # Volume momentum
            (df['cagr'] > 15.0)  # Quality filter
        )
        
        # Apply pattern detection
        if PATTERNS_AVAILABLE and len(df) >= 10:
            pattern_entries = []
            
            for i in range(len(df)):
                if entry_condition.iloc[i]:
                    window_start = max(0, i - 9)
                    window_end = i + 1
                    pattern_df = df.iloc[window_start:window_end].copy()
                    
                    if len(pattern_df) >= 10:
                        patterns = detect_patterns(pattern_df)
                        has_pattern = patterns['is_engulfing'] or patterns['is_w_pattern']
                        
                        if has_pattern:
                            pattern_entries.append(i)
            
            final_entries = pd.Series(False, index=df.index)
            for entry_idx in pattern_entries:
                final_entries.iloc[entry_idx] = True
            
            signals.loc[final_entries, 'signal'] = 1
        else:
            signals.loc[entry_condition, 'signal'] = 1
        
        # Exit conditions with Power Stock Shield
        # First, mark standard SMA 200 breaks for all positions
        exit_trend = df['close'] < df['sma_200']
        signals.loc[exit_trend, 'signal'] = -1
        
        # Now apply Power Stock Shield - remove SMA 200 exits ONLY for Power Stocks
        for i in range(len(df)):
            if signals.iloc[i]['signal'] == -1:  # Check exit signals
                # Look back to see if there's an active position that became a Power Stock
                for j in range(max(0, i-100), i):  # Look back up to 100 days
                    if signals.iloc[j]['signal'] == 1:  # Found entry
                        # Check if this position became a Power Stock before exit
                        became_power_stock = False
                        for k in range(j+1, i):
                            if self.detect_power_stock(df, k):
                                became_power_stock = True
                                break

                        if became_power_stock:
                            # Remove the SMA 200 exit for this Power Stock
                            signals.iloc[i, signals.columns.get_loc('signal')] = 0
                            break
        
        return signals
    
    def simulate_trading(self, df, ticker, version='v6.0'):
        """Simulate trading for a single ticker"""
        df = df.copy()
        df = self.calculate_indicators(df)
        
        # Choose signal generation based on version
        if version == 'v6.0':
            signals = self.generate_v60_signals(df)
        else:  # v6.5
            signals = self.generate_v65_signals(df)
        
        if signals['signal'].sum() == 0:
            return []
        
        trades = []
        position = None
        
        for i, (date, row) in enumerate(df.iterrows()):
            signal = signals.loc[date, 'signal']
            
            # Entry signal
            if signal == 1 and position is None:
                # Use adjusted close if available, otherwise regular close
                close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
                position = {
                    'entry_date': date,
                    'entry_price': row[close_col],
                    'entry_idx': i,
                    'is_power_stock': False,  # Will be updated during holding
                    'version': version
                }
                
            # Check for Power Stock activation during position
            elif position is not None and version == 'v6.5':
                # Update Power Stock status during holding period
                if self.detect_power_stock(df, i):
                    position['is_power_stock'] = True
            
            # Exit signal - check directly instead of relying on signals DataFrame
            elif position is not None:
                current_price = row['close']
                is_power_stock = position.get('is_power_stock', False)
                
                # Exit conditions based on Power Stock status
                should_exit = False
                exit_reason = ''
                
                if is_power_stock:
                    # Power Stock Shield: exit only if price < SMA 25
                    sma_25 = row['sma_25']
                    if not pd.isna(sma_25) and current_price < sma_25:
                        should_exit = True
                        exit_reason = 'POWER_STOCK_SMA_25_BREAK'
                    # Fallback: Exit if price < SMA 200 (emergency exit)
                    elif not pd.isna(row['sma_200']) and current_price < row['sma_200']:
                        should_exit = True
                        exit_reason = 'POWER_STOCK_EMERGENCY_EXIT'
                else:
                    # Regular exit: SMA 200 break
                    sma_200 = row['sma_200']
                    if not pd.isna(sma_200) and current_price < sma_200:
                        should_exit = True
                        exit_reason = 'SMA_200_BREAK'
                
                if should_exit:
                    # Close the position
                    position['exit_date'] = date
                    position['exit_price'] = current_price
                    position['exit_reason'] = exit_reason
                    position['duration'] = (date - position['entry_date']).days
                    
                    # Calculate return
                    position['return'] = (position['exit_price'] - position['entry_price']) / position['entry_price']
                    
                    trades.append(position)
                    position = None
        
        return trades
    
    def calculate_portfolio_performance(self, all_trades):
        """Calculate comprehensive portfolio performance"""
        if not all_trades:
            return self.get_empty_performance()
        
        trades_df = pd.DataFrame(all_trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['return'] > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # Win/Loss analysis
        avg_win_pct = winning_trades['return'].mean() * 100 if len(winning_trades) > 0 else 0.0
        losing_trades = trades_df[trades_df['return'] <= 0]
        avg_loss_pct = losing_trades['return'].mean() * 100 if len(losing_trades) > 0 else 0.0
        
        # Duration analysis
        avg_trade_duration = trades_df['duration'].mean()
        
        # Power Stock analysis
        power_stock_trades = trades_df[trades_df['is_power_stock'] == True]
        power_stock_count = len(power_stock_trades)
        power_stock_win_rate = (power_stock_trades['return'] > 0).sum() / power_stock_count if power_stock_count > 0 else 0.0
        power_stock_avg_duration = power_stock_trades['duration'].mean() if power_stock_count > 0 else 0.0
        
        # Portfolio equity curve
        equity = [self.starting_capital]
        for trade in all_trades:
            if trade.get('exit_reason'):  # Check if trade is closed
                position_size = self.starting_capital * self.position_size
                proceeds = position_size * (1 + trade['return'])
                equity.append(equity[-1] - position_size + proceeds)
        
        equity_series = pd.Series(equity)
        returns = equity_series.pct_change().dropna()
        
        # Performance metrics
        if len(equity_series) > 1:
            total_days = len(equity_series) - 1
            cagr = (equity_series.iloc[-1] / equity_series.iloc[0]) ** (252/total_days) - 1 if total_days > 0 else 0.0
            
            rolling_max = equity_series.expanding().max()
            drawdown = (equity_series - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if len(returns) > 1 and returns.std() > 0 else 0.0
            mar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0.0
        else:
            cagr = max_drawdown = sharpe_ratio = mar_ratio = 0.0
        
        return {
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'mar_ratio': mar_ratio,
            'total_trades': total_trades,
            'win_rate': win_rate,
            'avg_win_pct': avg_win_pct,
            'avg_loss_pct': avg_loss_pct,
            'avg_trade_duration': avg_trade_duration,
            'power_stock_trades': power_stock_count,
            'power_stock_win_rate': power_stock_win_rate,
            'power_stock_avg_duration': power_stock_avg_duration
        }
    
    def get_empty_performance(self):
        """Return empty performance metrics"""
        return {
            'cagr': 0.0,
            'max_drawdown': 0.0,
            'sharpe_ratio': 0.0,
            'mar_ratio': 0.0,
            'total_trades': 0,
            'win_rate': 0.0,
            'avg_win_pct': 0.0,
            'avg_loss_pct': 0.0,
            'avg_trade_duration': 0.0,
            'power_stock_trades': 0,
            'power_stock_win_rate': 0.0,
            'power_stock_avg_duration': 0.0
        }
    
    def print_comparison_results(self, v60_performance, v65_performance, power_stock_activations):
        """Print comparison results table"""
        print(f"\n{'='*70}")
        print("v6.0 vs v6.5 COMPARISON RESULTS")
        print('='*70)
        
        metrics = [
            ('CAGR', 'cagr', '{:.2%}'),
            ('Max Drawdown', 'max_drawdown', '{:.2%}'),
            ('Sharpe Ratio', 'sharpe_ratio', '{:.2f}'),
            ('MAR Ratio', 'mar_ratio', '{:.2f}'),
            ('Total Trades', 'total_trades', '{:.0f}'),
            ('Win Rate', 'win_rate', '{:.2%}'),
            ('Avg Win %', 'avg_win_pct', '{:.2f}%'),
            ('Avg Loss %', 'avg_loss_pct', '{:.2f}%'),
            ('Avg Duration', 'avg_trade_duration', '{:.1f} days'),
            ('Power Stock Trades', 'power_stock_trades', '{:.0f}'),
            ('PS Win Rate', 'power_stock_win_rate', '{:.2%}'),
            ('PS Avg Duration', 'power_stock_avg_duration', '{:.1f} days')
        ]
        
        print(f"{'Metric':<25} {'v6.0':<15} {'v6.5':<15} {'Change':<15}")
        print('-' * 70)
        
        for metric_name, metric_key, format_str in metrics:
            v60_val = v60_performance[metric_key]
            v65_val = v65_performance[metric_key]
            
            if metric_key in ['max_drawdown', 'avg_loss_pct']:
                change = ((v65_val - v60_val) / abs(v60_val) * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            elif metric_key == 'total_trades':
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            else:
                change = ((v65_val - v60_val) / abs(v60_val) * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            
            print(f"{metric_name:<25} {format_str.format(v60_val):<15} {format_str.format(v65_val):<15} {change_str:<15}")
        
        print(f"\nPower Stock Activations: {power_stock_activations:,}")
        
        # Check if goals are met
        cagr_goal = 0.1786  # 17.86%
        win_rate_goal = 0.2270  # 22.70%
        
        v60_cAGR_met = v60_performance['cagr'] >= cagr_goal
        v60_win_rate_met = v60_performance['win_rate'] >= win_rate_goal
        v65_cagr_met = v65_performance['cagr'] >= cagr_goal
        v65_win_rate_met = v65_performance['win_rate'] >= win_rate_goal
        
        print(f"\nGOAL CHECK:")
        print(f"v6.0: CAGR {'✓' if v60_cAGR_met else '✗'} ({v60_performance['cagr']:.2%} vs {cagr_goal:.2%}), Win Rate {'✓' if v60_win_rate_met else '✗'} ({v60_performance['win_rate']:.2%} vs {win_rate_goal:.2%})")
        print(f"v6.5: CAGR {'✓' if v65_cagr_met else '✗'} ({v65_performance['cagr']:.2%} vs {cagr_goal:.2%}), Win Rate {'✓' if v65_win_rate_met else '✗'} ({v65_performance['win_rate']:.2%} vs {win_rate_goal:.2%})")
    
    def run_power_stock_verification(self):
        """Run comprehensive Power Stock verification backtest"""
        print("VolatilityHunter Power Stock Verification Backtest")
        print("=" * 70)
        print("Comparing v6.0 (Pattern Hunter) vs v6.5 (Power Hunter)")
        print("=" * 70)
        
        # Get all tickers
        tickers = [f.replace('.parquet', '') for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        
        # Filter out invalid tickers
        invalid_tickers = {'nan', 'spy', 'null', '', 'none'}
        tickers = [t.upper() for t in tickers if t.lower() not in invalid_tickers and len(t) > 0]
        
        print(f"Found {len(tickers)} tickers")
        
        # Suppress logging for cleaner output
        logging.getLogger().setLevel(logging.ERROR)
        
        v60_trades = []
        v65_trades = []
        power_stock_activations = []
        
        for ticker in tqdm(tickers, desc="Power Stock Analysis"):
            try:
                df = self.load_ticker_data(ticker)
                if df is None or len(df) < 12:
                    continue
                
                # v6.0 (Pattern Hunter)
                v60_trades.extend(self.simulate_trading(df, ticker, 'v6.0'))
                
                # v6.5 (Power Hunter)
                v65_trades.extend(self.simulate_trading(df, ticker, 'v6.5'))
                
                # Track Power Stock activations
                df_indicators = self.calculate_indicators(df)
                for i in range(len(df_indicators)):
                    if self.detect_power_stock(df_indicators, i):
                        power_stock_activations.append({
                            'ticker': ticker,
                            'date': df_indicators.index[i],
                            'price': df_indicators['close'].iloc[i],
                            'stoch_k': df_indicators['stoch_k'].iloc[i]
                        })
            except Exception as e:
                continue
        
        # Restore logging level
        logging.getLogger().setLevel(logging.INFO)
        
        print(f"v6.0 trades: {len(v60_trades)}")
        print(f"v6.5 trades: {len(v65_trades)}")
        print(f"Power Stock activations: {len(power_stock_activations)}")
        
        # Calculate performance metrics
        v60_performance = self.calculate_portfolio_performance(v60_trades) if v60_trades else self.get_empty_performance()
        v65_performance = self.calculate_portfolio_performance(v65_trades) if v65_trades else self.get_empty_performance()
        
        # Print comparison results
        self.print_comparison_results(v60_performance, v65_performance, len(power_stock_activations))
        
        return {
            'v60_performance': v60_performance,
            'v65_performance': v65_performance,
            'v60_trades': v60_trades,
            'v65_trades': v65_trades,
            'power_stock_activations': power_stock_activations
        }

if __name__ == "__main__":
    engine = PowerStockBacktestEngine()
    results = engine.run_power_stock_verification()
