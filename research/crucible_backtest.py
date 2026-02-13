#!/usr/bin/env python3
"""
VolatilityHunter Crucible Backtest Engine
Full-pipeline, 20-year historical backtest on all 2867 tickers
v6.5 A+ Wealth Builder (Phase 1 Patterns + Phase 2 Power Stock + Phase 3 Safety Valve)

Targets: >25% CAGR and <20% Max Drawdown
Architecture: Fail-Fast Concurrency with Extreme Memory Management
"""

import os
import sys
import pandas as pd
import numpy as np
import gc
import traceback
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
import warnings
warnings.filterwarnings('ignore')

# Import core components
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

class CrucibleBacktestEngine:
    def __init__(self):
        self.data_dir = 'data'
        self.starting_capital = 100000
        self.position_size = 0.25
        self.max_workers = min(8, os.cpu_count() or 4)  # Use up to 8 workers
        
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
                return None
                
            # Ensure data is sorted by date
            if 'date' in df.columns:
                df = df.sort_values('date')
                df.set_index('date', inplace=True)
            
            # Convert to numeric
            for col in required_cols_lower:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            
            df = df.dropna(subset=required_cols_lower)
            
            # For crucible backtest, we need at least 50 days for SMA 25
            if len(df) < 50:
                return None
                
            return df
            
        except Exception as e:
            return None
    
    def calculate_indicators_vectorized(self, df):
        """Calculate all indicators using 100% vectorized operations"""
        df = df.copy()
        
        # Use core strategy's add_indicators function (vectorized)
        df = add_indicators(df)
        
        # Calculate CAGR (vectorized)
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        df['cagr'] = (df[close_col] / df[close_col].iloc[0]) ** (252 / pd.Series(range(len(df)), index=df.index)) - 1
        df['cagr'] = df['cagr'] * 100  # Convert to percentage
        
        # Calculate ATR (vectorized)
        df['atr'] = calculate_atr(df)
        
        # Standardize column names
        column_mapping = {
            'Stochastic_K': 'stoch_k',
            'Stochastic_D': 'stoch_d',
            'Volume_SMA_30': 'volume_sma_30',
            'SMA_200': 'sma_200',
            'SMA_25': 'sma_25',
            'SMA_50': 'sma_50',
            'SMA_100': 'sma_100'
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        # Ensure Stochastic is clipped to prevent extreme values
        df['stoch_k'] = df['stoch_k'].clip(0, 100)
        df['stoch_d'] = df['stoch_d'].clip(0, 100)
        
        return df
    
    def detect_power_stock_vectorized(self, df):
        """Vectorized Power Stock detection"""
        return (
            (df['stoch_k'] > 80) &
            (df['close'] > df['sma_25']) &
            (df['close'] > df['sma_50']) &
            (df['close'] > df['sma_100']) &
            (df['close'] > df['sma_200']) &
            (df['volume'] > df['volume_sma_30'])
        )
    
    def check_entry_conditions(self, df, i):
        """Check if entry conditions are met at index i"""
        if i < 10:  # Need enough data for patterns
            return False, None
            
        row = df.iloc[i]
        
        # A+ Wealth Builder Entry Rules (all 5 rules)
        entry_condition = (
            (row['close'] > row['sma_200']) and
            (32 <= row['stoch_k'] <= 80) and
            (row['volume_sma_30'] > 0) and
            (row['volume'] > row['volume_sma_30']) and
            (row['cagr'] > 15.0)
        )
        
        if not entry_condition:
            return False, None
        
        # Check for patterns (if available)
        if PATTERNS_AVAILABLE and len(df) >= 10:
            window_start = max(0, i - 9)
            window_end = i + 1
            pattern_df = df.iloc[window_start:window_end].copy()
            
            if len(pattern_df) >= 10:
                patterns = detect_patterns(pattern_df)
                has_pattern = patterns['is_engulfing'] or patterns['is_w_pattern']
                
                if has_pattern:
                    return True, 'PATTERN_ENTRY'
        
        return False, None
    
    def check_exit_conditions(self, df, i, position, is_power_stock):
        """Check exit conditions with Power Stock Shield"""
        current_price = df.iloc[i]['close']
        current_row = df.iloc[i]
        
        # Earnings exit (48h before) - placeholder for now
        # TODO: Implement earnings date checking
        
        # Trailing stop (3.0x ATR)
        if 'peak_price' in position and 'atr_at_entry' in position:
            trailing_stop = position['peak_price'] - (3.0 * position['atr_at_entry'])
            if current_price < trailing_stop:
                return True, 'TRAILING_STOP'
        
        # Power Stock Shield logic
        if is_power_stock:
            # Exit only if price < SMA 25
            sma_25 = current_row['sma_25']
            if not pd.isna(sma_25) and current_price < sma_25:
                return True, 'POWER_STOCK_SMA_25_BREAK'
        else:
            # Standard exit: SMA 200 break
            sma_200 = current_row['sma_200']
            if not pd.isna(sma_200) and current_price < sma_200:
                return True, 'SMA_200_BREAK'
        
        return False, None
    
    def simulate_trading_vectorized(self, df, ticker):
        """Vectorized trading simulation for a single ticker"""
        trades = []
        position = None
        
        for i in range(len(df)):
            # Entry logic
            if position is None:
                should_enter, reason = self.check_entry_conditions(df, i)
                if should_enter:
                    close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
                    entry_price = df.iloc[i][close_col]
                    
                    position = {
                        'ticker': ticker,
                        'entry_date': df.index[i],
                        'entry_price': entry_price,
                        'entry_idx': i,
                        'is_power_stock': False,
                        'peak_price': entry_price,
                        'atr_at_entry': df.iloc[i]['atr'],
                        'reason': reason
                    }
            
            # Check for Power Stock promotion
            elif position is not None and not position['is_power_stock']:
                power_stocks = self.detect_power_stock_vectorized(df)
                if power_stocks.iloc[i]:
                    position['is_power_stock'] = True
            
            # Exit logic
            elif position is not None:
                # Update peak price for trailing stop
                current_price = df.iloc[i]['close']
                if current_price > position['peak_price']:
                    position['peak_price'] = current_price
                
                should_exit, exit_reason = self.check_exit_conditions(
                    df, i, position, position['is_power_stock']
                )
                
                if should_exit:
                    # Close position
                    position['exit_date'] = df.index[i]
                    position['exit_price'] = current_price
                    position['exit_reason'] = exit_reason
                    position['duration'] = (df.index[i] - position['entry_date']).days
                    position['return'] = (current_price - position['entry_price']) / position['entry_price']
                    
                    trades.append(position)
                    position = None
        
        return trades
    
    def calculate_portfolio_metrics(self, all_trades):
        """Calculate portfolio performance metrics"""
        if not all_trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'cagr': 0.0,
                'max_drawdown': 0.0,
                'sharpe_ratio': 0.0,
                'avg_trade_duration': 0.0,
                'power_stock_trades': 0,
                'power_stock_win_rate': 0.0
            }
        
        trades_df = pd.DataFrame(all_trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['return'] > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # Power Stock analysis
        power_stock_trades = trades_df[trades_df['is_power_stock'] == True]
        ps_win_rate = (power_stock_trades['return'] > 0).sum() / len(power_stock_trades) if len(power_stock_trades) > 0 else 0.0
        
        # Portfolio equity curve
        equity = [self.starting_capital]
        for trade in all_trades:
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
        else:
            cagr = max_drawdown = sharpe_ratio = 0.0
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'avg_trade_duration': trades_df['duration'].mean() if 'duration' in trades_df.columns else 0.0,
            'power_stock_trades': len(power_stock_trades),
            'power_stock_win_rate': ps_win_rate
        }
    
    def process_ticker_worker(self, ticker):
        """Worker function for processing a single ticker"""
        try:
            # Load data
            df = self.load_ticker_data(ticker)
            if df is None:
                return {'ticker': ticker, 'status': 'NO_DATA'}
            
            # Calculate indicators
            df_indicators = self.calculate_indicators_vectorized(df)
            
            # Simulate trading
            trades = self.simulate_trading_vectorized(df_indicators, ticker)
            
            # Clean up memory
            del df
            del df_indicators
            gc.collect()
            
            return {
                'ticker': ticker,
                'status': 'SUCCESS',
                'trades': trades,
                'trade_count': len(trades)
            }
            
        except Exception as e:
            # Fail-fast: return fatal error with full traceback
            return {
                'ticker': ticker,
                'status': 'FATAL_ERROR',
                'error': str(e),
                'traceback': traceback.format_exc()
            }
    
    def run_crucible_backtest(self):
        """Run the full Crucible Backtest with fail-fast concurrency"""
        print("🔥 VOLATILITYHUNTER CRUCIBLE BACKTEST")
        print("=" * 70)
        print("v6.5 A+ Wealth Builder (Patterns + Power Stock + Safety Valve)")
        print(f"Targets: >25% CAGR, <20% Max Drawdown")
        print(f"Workers: {self.max_workers} (ProcessPoolExecutor)")
        print("=" * 70)
        
        # Get all tickers
        tickers = [f.replace('.parquet', '') for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        tickers = [t.upper() for t in tickers if len(t) > 0]
        
        print(f"📊 Processing {len(tickers)} tickers...")
        
        # Process with fail-fast concurrency
        all_trades = []
        processed_count = 0
        error_count = 0
        
        with ProcessPoolExecutor(max_workers=self.max_workers) as executor:
            # Submit all tasks
            future_to_ticker = {
                executor.submit(self.process_ticker_worker, ticker): ticker
                for ticker in tickers
            }
            
            # Process as completed with progress bar
            with tqdm(total=len(tickers), desc="Processing tickers") as pbar:
                for future in as_completed(future_to_ticker):
                    ticker = future_to_ticker[future]
                    
                    try:
                        result = future.result(timeout=300)  # 5 minute timeout per ticker
                        
                        # FAIL-FAST: Check for fatal error
                        if result['status'] == 'FATAL_ERROR':
                            print(f"\n❌ FATAL ERROR in {ticker}: {result['error']}")
                            print(f"📍 Traceback:\n{result['traceback']}")
                            
                            # TRUE HARD STOP: Kill everything immediately
                            print("\n🛑 FAIL-FAST TRIGGERED: Killing all processes...")
                            executor.shutdown(wait=False, cancel_futures=True)
                            os._exit(1)  # Instant kill, no cleanup
                        
                        # Process successful result
                        if result['status'] == 'SUCCESS':
                            all_trades.extend(result['trades'])
                            processed_count += 1
                            
                            # Update progress with details
                            pbar.set_postfix({
                                'Processed': processed_count,
                                'Trades': len(all_trades),
                                'Errors': error_count
                            })
                        else:
                            error_count += 1
                        
                        pbar.update(1)
                        
                    except Exception as e:
                        print(f"\n❌ UNHANDLED ERROR in {ticker}: {e}")
                        print("📍 Traceback:")
                        traceback.print_exc()
                        
                        # TRUE HARD STOP: Kill everything immediately
                        print("\n🛑 UNHANDLED ERROR: Killing all processes...")
                        executor.shutdown(wait=False, cancel_futures=True)
                        os._exit(1)
        
        print(f"\n✅ Backtest completed!")
        print(f"📊 Processed: {processed_count}/{len(tickers)} tickers")
        print(f"📈 Total Trades: {len(all_trades)}")
        print(f"❌ Errors: {error_count}")
        
        # Calculate final metrics
        metrics = self.calculate_portfolio_metrics(all_trades)
        
        # Print results
        self.print_crucible_results(metrics)
        
        return metrics
    
    def print_crucible_results(self, metrics):
        """Print the Crucible Backtest results"""
        print(f"\n{'='*70}")
        print("🔥 CRUCIBLE BACKTEST RESULTS")
        print('='*70)
        
        print(f"📊 Total Trades: {metrics['total_trades']:,}")
        print(f"🎯 Win Rate: {metrics['win_rate']:.2%}")
        print(f"📈 CAGR: {metrics['cagr']:.2%}")
        print(f"📉 Max Drawdown: {metrics['max_drawdown']:.2%}")
        print(f"⚡ Sharpe Ratio: {metrics['sharpe_ratio']:.2f}")
        print(f"⏱️ Avg Trade Duration: {metrics['avg_trade_duration']:.1f} days")
        print(f"🔥 Power Stock Trades: {metrics['power_stock_trades']}")
        print(f"🎯 PS Win Rate: {metrics['power_stock_win_rate']:.2%}")
        
        # Check if targets are met
        cagr_target = 0.25  # 25%
        drawdown_target = -0.20  # -20%
        
        cagr_met = metrics['cagr'] >= cagr_target
        drawdown_met = metrics['max_drawdown'] >= drawdown_target
        
        print(f"\n🎯 TARGET CHECK:")
        print(f"CAGR {'✅' if cagr_met else '❌'} ({metrics['cagr']:.2%} vs {cagr_target:.2%})")
        print(f"Max Drawdown {'✅' if drawdown_met else '❌'} ({metrics['max_drawdown']:.2%} vs {drawdown_target:.2%})")
        
        if cagr_met and drawdown_met:
            print(f"\n🏆 CRUCIBLE PASSED: Both targets achieved!")
        else:
            print(f"\n⚠️ CRUCIBLE FAILED: Targets not met")

if __name__ == "__main__":
    engine = CrucibleBacktestEngine()
    results = engine.run_crucible_backtest()
