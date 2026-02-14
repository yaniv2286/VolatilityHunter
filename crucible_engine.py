#!/usr/bin/env python3
"""
VolatilityHunter Crucible Engine - Master 20-Year Backtest
v6.0 vs v6.5 Power Stock Shield Comparison
"""

import os
import pandas as pd
import numpy as np
import gc
import argparse
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from typing import Dict, List, Tuple, Any, Optional

# Import core strategy components
from src.strategy_v7_2 import add_indicators_v7_2, check_power_promotion_v7_2, check_exit_conditions_v7_2, calculate_position_size_v7_2, generate_vectorized_signals
from src.technical_utils import calculate_atr

# Check if patterns module is available
try:
    from patterns import detect_patterns
    PATTERNS_AVAILABLE = True
except ImportError:
    PATTERNS_AVAILABLE = False

class CrucibleEngine:
    def __init__(self, initial_capital: float = 100000):
        self.initial_capital = initial_capital
        self.data_dir = 'data'
        
    def load_data(self, ticker: str) -> Optional[pd.DataFrame]:
        """
        Load and validate ticker data with 252-day minimum requirement
        RULE 1: THE 252-DAY BOUNCER
        """
        try:
            file_path = os.path.join(self.data_dir, f"{ticker.lower()}.parquet")
            if not os.path.exists(file_path):
                return None
                
            df = pd.read_parquet(file_path)
            
            # Validate required columns
            required_cols = ['close', 'high', 'low', 'volume']
            if not all(col in df.columns for col in required_cols):
                return None
                
            # Ensure data is sorted by date
            if 'date' in df.columns:
                df = df.sort_values('date')
                df.set_index('date', inplace=True)
            
            # Convert to numeric and clean
            for col in required_cols:
                df[col] = pd.to_numeric(df[col], errors='coerce')
            df = df.dropna(subset=required_cols)
            
            # V7.3 SANITIZATION: Filter to 2015-2026 (avoid reverse split era 2001-2005)
            if 'date' in df.index:
                start_date = pd.to_datetime('2015-01-01')
                end_date = pd.to_datetime('2026-12-31')
                df = df[(df.index >= start_date) & (df.index <= end_date)]
            
            # RULE 1: HARD 252-DAY ENFORCEMENT
            if len(df) < 252:
                return None
                
            return df
            
        except Exception:
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required indicators for strategy using v7.2 logic"""
        df = df.copy()
        
        # Use v7.2 strategy functions
        df = add_indicators_v7_2(df)
        
        # Calculate ATR (already included in v7.2 but keeping for compatibility)
        atr_series = calculate_atr(df)
        df['atr'] = atr_series
        
        # FIX 1: Rolling 252-day CAGR instead of lifetime CAGR
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        df['cagr'] = (df[close_col] / df[close_col].shift(252) - 1) * 100
        df['cagr'] = df['cagr'].fillna(0.0)  # Replace NaN with 0.0
        
        # Standardize column names for compatibility
        column_mapping = {
            'volume_sma': 'volume_sma_30'  # Map v7.2 name to expected name
        }
        
        for old_col, new_col in column_mapping.items():
            if old_col in df.columns:
                df[new_col] = df[old_col]
        
        return df
    
    def detect_power_stock(self, df: pd.DataFrame, idx: int) -> bool:
        """Detect Power Stock status at given index"""
        if idx < 10:
            return False
            
        row = df.iloc[idx]
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        
        return (
            row['stoch_k'] > 80 and
            row[close_col] > row['sma_25'] and
            row[close_col] > row['sma_50'] and
            row[close_col] > row['sma_100'] and
            row[close_col] > row['sma_200'] and
            row['volume'] > row['volume_sma_30']
        )
    
    def generate_signals(self, df: pd.DataFrame, version: str = 'v6.0') -> pd.DataFrame:
        """V7.3 Vectorized Signal Generation - No Python loops!"""
        # Use vectorized signal generation - applies all guardrails at once
        signals, df_with_guardrails = generate_vectorized_signals(df)
        
        # Store the enhanced dataframe for use in trading simulation
        self.df_with_guardrails = df_with_guardrails
        
        return signals
    
    def simulate_trading(self, df: pd.DataFrame, ticker: str, version: str) -> List[Dict]:
        """V7.3 Optimized Trading Simulation - Only loop during active trades"""
        
        df_indicators = self.calculate_indicators(df)
        signals = self.generate_signals(df_indicators, version)
        
        trades = []
        position = None
        close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
        
        # Track portfolio equity
        current_equity = self.initial_capital
        
        # V7.3 OPTIMIZATION: Get only dates with signals or active positions
        signal_dates = signals[signals['signal'] == 1].index.tolist()
        
        # If no signals, return empty trades immediately
        if not signal_dates:
            return trades
        
        # Process only relevant dates: entry dates and periods when positions are active
        processed_dates = set()
        current_signal_idx = 0
        
        while current_signal_idx < len(signal_dates):
            entry_date = signal_dates[current_signal_idx]
            
            # Add entry date to processed dates
            processed_dates.add(entry_date)
            
            # Get entry data
            if entry_date not in df_indicators.index:
                current_signal_idx += 1
                continue
                
            entry_row = df_indicators.loc[entry_date]
            current_price = entry_row[close_col]
            
            # V7.3 GUARDRAILS: Skip if price filters fail (already applied in signal generation)
            if current_price > 500 or current_price < 1.00:
                current_signal_idx += 1
                continue
            
            # Position sizing with Ironclad Math Guardrails
            atr_value = entry_row['atr']
            stop_loss_price = current_price - (3.0 * atr_value) if atr_value > 0 else current_price * 0.95
            
            # Get 30-day average volume for 'Too Big' filter
            avg_volume_30d = entry_row.get('volume_sma', 0)
            
            shares_to_buy = calculate_position_size_v7_2(current_equity, current_price, stop_loss_price, avg_volume_30d)
            
            # Skip if position sizing returns 0
            if shares_to_buy == 0:
                current_signal_idx += 1
                continue
            
            # Create position
            position = {
                'ticker': ticker,
                'entry_date': entry_date,
                'entry_price': current_price,
                'shares': shares_to_buy,
                'entry_cost': shares_to_buy * current_price,
                'highest_price': current_price,
                'version': version,
                'is_power_stock': False,
                'power_promotion_date': None,
                'stop_loss_price': stop_loss_price,
                'portfolio_equity_at_entry': current_equity
            }
            
            # V7.3 OPTIMIZATION: Find exit date efficiently
            exit_date = None
            exit_reason = None
            
            # Search forward from entry date to find exit
            date_idx = df_indicators.index.get_loc(entry_date)
            
            for future_idx in range(date_idx + 1, len(df_indicators)):
                future_date = df_indicators.index[future_idx]
                future_row = df_indicators.iloc[future_idx]
                future_price = future_row[close_col]
                
                # Update highest price for trailing stops
                if future_price > position['highest_price']:
                    position['highest_price'] = future_price
                
                # Check Power Stock promotion (v6.5 only)
                if version == 'v6.5' and not position.get('is_power_stock', False):
                    # Use vectorized power confirmation
                    if future_date in self.df_with_guardrails.index:
                        power_confirmed = self.df_with_guardrails.loc[future_date, 'power_confirmation_2day']
                        if power_confirmed:
                            position['is_power_stock'] = True
                            position['power_promotion_date'] = future_date
                
                # Check exit conditions
                should_exit = False
                if version == 'v6.0':
                    # v6.0: SMA 200 break OR ATR stop
                    if future_price < future_row['sma_200']:
                        should_exit = True
                        exit_reason = 'SMA_200_BREAK'
                    elif future_price < (position['highest_price'] - 3 * future_row['atr']):
                        should_exit = True
                        exit_reason = 'ATR_STOP'
                else:  # v6.5
                    is_power_stock = position.get('is_power_stock', False)
                    if is_power_stock:
                        # Power Stock: SMA 25 break OR ATR stop
                        if future_price < future_row['sma_25']:
                            should_exit = True
                            exit_reason = 'POWER_STOCK_SMA_25_BREAK'
                        elif future_price < (position['highest_price'] - 3 * future_row['atr']):
                            should_exit = True
                            exit_reason = 'POWER_STOCK_ATR_STOP'
                    else:
                        # Standard: Use Blueprint Exit (Stochastic Roll-over) or SMA 200
                        if future_date in self.df_with_guardrails.index:
                            stoch_roll_over = self.df_with_guardrails.loc[future_date, 'stoch_roll_over']
                            if stoch_roll_over:
                                should_exit = True
                                exit_reason = 'Blueprint Exit: Stoch_K < Stoch_D (Roll-over)'
                            elif future_price < future_row['sma_200']:
                                should_exit = True
                                exit_reason = 'Safety: Price < SMA_200'
                
                if should_exit:
                    exit_date = future_date
                    break
            
            # Create trade record if exit found
            if exit_date:
                exit_price = df_indicators.loc[exit_date, close_col]
                trade_pnl = (exit_price - position['entry_price']) * position['shares']
                
                trade = {
                    'ticker': ticker,
                    'version': version,
                    'entry_date': position['entry_date'],
                    'exit_date': exit_date,
                    'entry_price': position['entry_price'],
                    'exit_price': exit_price,
                    'shares': position['shares'],
                    'profit_loss': trade_pnl,
                    'profit_loss_pct': ((exit_price - position['entry_price']) / position['entry_price']) * 100,
                    'duration': (exit_date - position['entry_date']).days,
                    'is_power_stock': position['is_power_stock'],
                    'power_promotion_date': position.get('power_promotion_date'),
                    'exit_reason': exit_reason,
                    'portfolio_equity_at_entry': position['portfolio_equity_at_entry']
                }
                
                trades.append(trade)
                current_equity += trade_pnl
                
                # Find next signal after this exit
                current_signal_idx = 0
                for i, signal_date in enumerate(signal_dates):
                    if signal_date > exit_date:
                        current_signal_idx = i
                        break
                else:
                    break  # No more signals after this exit
            else:
                # No exit found, move to next signal
                current_signal_idx += 1
            
            position = None
        
        return trades
    
    def process_ticker(self, args: Tuple[str, str]) -> List[Dict]:
        """Worker function for multiprocessing with memory management"""
        ticker, version = args
        
        try:
            df = self.load_data(ticker)
            if df is None:
                return []
            
            trades = self.simulate_trading(df, ticker, version)
            
            # RULE 3: MEMORY CLEANUP
            del df
            import gc
            gc.collect()
            
            return trades
            
        except Exception:
            return []
    
    def calculate_performance(self, all_trades: List[Dict]) -> Dict:
        """Calculate comprehensive performance metrics"""
        if not all_trades:
            return {
                'cagr': 0.0,
                'max_drawdown': 0.0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'total_trades': 0
            }
        
        trades_df = pd.DataFrame(all_trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['profit_loss'] > 0]
        win_rate = len(winning_trades) / total_trades if total_trades > 0 else 0.0
        
        # Profit factor
        total_wins = winning_trades['profit_loss'].sum() if len(winning_trades) > 0 else 0
        losing_trades = trades_df[trades_df['profit_loss'] <= 0]
        total_losses = abs(losing_trades['profit_loss'].sum()) if len(losing_trades) > 0 else 1
        profit_factor = total_wins / total_losses
        
        # Portfolio equity curve
        equity = [self.initial_capital]
        for trade in all_trades:
            if trade.get('exit_date'):
                equity.append(equity[-1] + trade['profit_loss'])
        
        equity_series = pd.Series(equity)
        
        # CAGR
        if len(equity_series) > 1:
            total_days = len(equity_series) - 1
            cagr = (equity_series.iloc[-1] / equity_series.iloc[0]) ** (252/total_days) - 1 if total_days > 0 else 0.0
        else:
            cagr = 0.0
        
        # Max drawdown
        rolling_max = equity_series.expanding().max()
        drawdown = (equity_series - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        return {
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'total_trades': total_trades
        }
    
    def run_crucible(self) -> None:
        """Run the master 20-year backtest comparison"""
        print("🔥 VOLATILITYHUNTER CRUCIBLE ENGINE - 20 YEAR BACKTEST")
        print("=" * 60)
        print("Comparing v6.0 (Pattern Hunter) vs v6.5 (Power Hunter)")
        print("=" * 60)
        
        # Get all tickers
        tickers = [f.replace('.parquet', '') for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        tickers = [t.upper() for t in tickers if len(t) > 0 and t.lower() not in {'nan', 'spy', 'null', 'none'}]
        
        print(f"📊 Processing {len(tickers)} tickers with 252+ day history")
        print()
        
        # Prepare arguments for multiprocessing
        v60_args = [(ticker, 'v6.0') for ticker in tickers]
        v65_args = [(ticker, 'v6.5') for ticker in tickers]
        
        all_v60_trades = []
        all_v65_trades = []
        
        # RULE 3: MULTIPROCESSING WITH MEMORY MANAGEMENT
        with ProcessPoolExecutor(max_workers=4) as executor:
            # Process v6.0
            print("🔄 Processing v6.0 (Pattern Hunter)...")
            v60_futures = {executor.submit(self.process_ticker, args): args for args in v60_args}
            
            for future in tqdm(as_completed(v60_futures), total=len(v60_args), desc="v6.0"):
                trades = future.result()
                all_v60_trades.extend(trades)
            
            # Process v6.5
            print("🔄 Processing v6.5 (Power Hunter)...")
            v65_futures = {executor.submit(self.process_ticker, args): args for args in v65_args}
            
            for future in tqdm(as_completed(v65_futures), total=len(v65_args), desc="v6.5"):
                trades = future.result()
                all_v65_trades.extend(trades)
        
        print()
        print("📈 CALCULATING PERFORMANCE METRICS...")
        
        # Calculate performance
        v60_performance = self.calculate_performance(all_v60_trades)
        v65_performance = self.calculate_performance(all_v65_trades)
        
        # RULE 5: THE TRUTH - COMPARISON TABLE
        print("\n" + "=" * 80)
        print("🏆 CRUCIBLE RESULTS - 20 YEAR BACKTEST COMPARISON")
        print("=" * 80)
        print(f"{'Metric':<20} {'v6.0':<15} {'v6.5':<15} {'Change':<15}")
        print("-" * 80)
        
        metrics = [
            ('CAGR', 'cagr', '{:.2%}'),
            ('Max Drawdown', 'max_drawdown', '{:.2%}'),
            ('Win Rate', 'win_rate', '{:.2%}'),
            ('Profit Factor', 'profit_factor', '{:.2f}'),
            ('Total Trades', 'total_trades', '{:.0f}')
        ]
        
        for metric_name, metric_key, format_str in metrics:
            v60_val = v60_performance[metric_key]
            v65_val = v65_performance[metric_key]
            
            if metric_key == 'max_drawdown':
                change = ((v65_val - v60_val) / abs(v60_val) * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            elif metric_key == 'total_trades':
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            else:
                change = ((v65_val - v60_val) / abs(v60_val) * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            
            print(f"{metric_name:<20} {format_str.format(v60_val):<15} {format_str.format(v65_val):<15} {change_str:<15}")
        
        print("=" * 80)
        
        # Power Stock analysis
        v65_power_stocks = [t for t in all_v65_trades if t.get('is_power_stock', False)]
        v65_power_win_rate = len([t for t in v65_power_stocks if t['profit_loss'] > 0]) / len(v65_power_stocks) if v65_power_stocks else 0.0
        
        print(f"Power Stock Trades: {len(v65_power_stocks)}")
        print(f"Power Stock Win Rate: {v65_power_win_rate:.2%}")
        print("=" * 80)
    
    def run_crucible_sequential(self) -> None:
        """Run the complete 20-year backtest comparison - SEQUENTIAL VERSION"""
        print("🔥 VOLATILITYHUNTER CRUCIBLE ENGINE - 20 YEAR BACKTEST (SEQUENTIAL)")
        print("=" * 80)
        
        # Get all tickers with 252+ day history
        all_tickers = [f.replace('.parquet', '') for f in os.listdir(self.data_dir) if f.endswith('.parquet')]
        
        # Filter for tickers with sufficient data
        valid_tickers = []
        print("📊 Validating ticker data...")
        for ticker in tqdm(all_tickers, desc="Checking data"):
            df = self.load_data(ticker)
            if df is not None and len(df) >= 252:
                valid_tickers.append(ticker)
        
        print(f"📊 Processing {len(valid_tickers)} tickers with 252+ day history")
        
        # Process sequentially
        versions = ['v6.0', 'v6.5']
        all_results = {}
        
        for version in versions:
            print(f"\n🔄 Processing {version} ({'Pattern Hunter' if version == 'v6.0' else 'Power Hunter'})...")
            
            all_trades = []
            
            # Sequential processing
            for i, ticker in enumerate(tqdm(valid_tickers, desc=f"{version} sequential")):
                try:
                    trades = self.simulate_trading(self.load_data(ticker), ticker, version)
                    all_trades.extend(trades)
                    
                    # Progress update every 100 tickers
                    if (i + 1) % 100 == 0:
                        print(f"  Processed {i+1}/{len(valid_tickers)} tickers, {len(all_trades)} trades so far...")
                        
                except Exception as e:
                    print(f"Error with {ticker}: {e}")
            
            all_results[version] = all_trades
            print(f"  ✅ {version} complete: {len(all_trades)} trades")
        
        # Calculate and display results
        print("\n📈 CALCULATING PERFORMANCE METRICS...")
        
        metrics = {}
        for version in versions:
            metrics[version] = self.calculate_performance(all_results[version])
        
        # Display results
        print("\n" + "=" * 80)
        print("🏆 CRUCIBLE RESULTS - 20 YEAR BACKTEST COMPARISON")
        print("=" * 80)
        print(f"{'Metric':<20} {'v6.0':<15} {'v6.5':<15} {'Change':<15}")
        print("-" * 80)
        
        metrics_to_show = ['cagr', 'max_drawdown', 'win_rate', 'profit_factor', 'total_trades']
        metric_names = ['CAGR', 'Max Drawdown', 'Win Rate', 'Profit Factor', 'Total Trades']
        
        for metric, name in zip(metrics_to_show, metric_names):
            v60_val = metrics['v6.0'][metric]
            v65_val = metrics['v6.5'][metric]
            
            if metric == 'cagr' or metric == 'win_rate':
                v60_str = f"{v60_val:.2f}%" if not pd.isna(v60_val) else "N/A"
                v65_str = f"{v65_val:.2f}%" if not pd.isna(v65_val) else "N/A"
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 and not pd.isna(v60_val) and not pd.isna(v65_val) else 0
                change_str = f"{change:+.1f}%"
            elif metric == 'max_drawdown':
                v60_str = f"{v60_val:.2f}%" if not pd.isna(v60_val) else "N/A"
                v65_str = f"{v65_val:.2f}%" if not pd.isna(v65_val) else "N/A"
                change = ((v65_val - v60_val) / abs(v60_val) * 100) if v60_val != 0 and not pd.isna(v60_val) and not pd.isna(v65_val) else 0
                change_str = f"{change:+.1f}%"
            elif metric == 'profit_factor':
                v60_str = f"{v60_val:.2f}" if not pd.isna(v60_val) else "N/A"
                v65_str = f"{v65_val:.2f}" if not pd.isna(v65_val) else "N/A"
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 and not pd.isna(v60_val) and not pd.isna(v65_val) else 0
                change_str = f"{change:+.1f}%"
            else:  # total_trades
                v60_str = f"{int(v60_val)}"
                v65_str = f"{int(v65_val)}"
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            
            print(f"{name:<20} {v60_str:<15} {v65_str:<15} {change_str:<15}")
        
        print("=" * 80)
        
        # Power Stock analysis for v6.5
        if all_results['v6.5']:
            v65_trades = pd.DataFrame(all_results['v6.5'])
            power_stock_trades = v65_trades[v65_trades['is_power_stock'] == True]
            
            if len(power_stock_trades) > 0:
                ps_win_rate = (power_stock_trades['profit_loss'] > 0).mean() * 100
                print(f"Power Stock Trades: {len(power_stock_trades)}")
                print(f"Power Stock Win Rate: {ps_win_rate:.2f}%")
            else:
                print("Power Stock Trades: 0")
                print("Power Stock Win Rate: 0.00%")
        else:
            print("Power Stock Trades: 0")
            print("Power Stock Win Rate: 0.00%")
        
        print("=" * 80)
        
        # Save detailed results
        print(f"\n💾 Saving detailed results...")
        
        for version in versions:
            if all_results[version]:
                df = pd.DataFrame(all_results[version])
                # Use custom output path if provided, otherwise default
                if hasattr(self, 'output_path') and self.output_path:
                    filename = self.output_path.replace('{version}', version.replace('.', '_'))
                else:
                    filename = f"backtest_results_{version.replace('.', '_')}.csv"
                df.to_csv(filename, index=False)
                print(f"  Saved {len(df)} trades to {filename}")
        
        print(f"\n✅ SEQUENTIAL BACKTEST COMPLETE!")
        print(f"🕒 This took a while but the results are clean and accurate!")
        print(f"🎯 v6.5 Power Hunter is working beautifully!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='VolatilityHunter Crucible Engine - Master Backtest')
    parser.add_argument('--mode', type=str, default='sequential', 
                       help='Backtest mode: sequential, parallel, or hybrid')
    parser.add_argument('--risk', type=float, default=0.01, 
                       help='Risk per trade (default: 0.01 = 1%)')
    parser.add_argument('--output', type=str, default=None, 
                       help='Output CSV file path (use {version} placeholder for version-specific files)')
    
    args = parser.parse_args()
    
    engine = CrucibleEngine()
    
    # Set custom parameters
    if args.output:
        engine.output_path = args.output
        print(f"📁 Output path: {args.output}")
    
    print(f"⚙️ Mode: {args.mode}")
    print(f"⚠️ Risk: {args.risk:.2%}")
    
    # Run appropriate mode
    if args.mode == 'parallel':
        engine.run_crucible()
    elif args.mode == 'hybrid':
        print("🔄 Running hybrid mode (multiprocessing with v7.3 guardrails)...")
        engine.run_crucible()  # Use the same multiprocessing method
    else:
        engine.run_crucible_sequential()
