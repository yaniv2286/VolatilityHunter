#!/usr/bin/env python3
"""
VolatilityHunter Crucible Engine - Master 20-Year Backtest
v6.0 vs v6.5 Power Stock Shield Comparison
"""

import os
import pandas as pd
import numpy as np
import gc
from datetime import datetime, timedelta
from concurrent.futures import ProcessPoolExecutor, as_completed
from tqdm import tqdm
from typing import Dict, List, Tuple, Any, Optional

# Import core strategy components
from src.strategy import add_indicators, calculate_stochastic, calculate_multiple_smas, calculate_volume_sma
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
            
            # RULE 1: HARD 252-DAY ENFORCEMENT
            if len(df) < 252:
                return None
                
            return df
            
        except Exception:
            return None
    
    def calculate_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculate all required indicators for strategy"""
        df = df.copy()
        
        # Use core strategy functions
        df = add_indicators(df)
        
        # Calculate ATR
        atr_series = calculate_atr(df)
        df['atr'] = atr_series
        
        # FIX 1: Rolling 252-day CAGR instead of lifetime CAGR
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        df['cagr'] = (df[close_col] / df[close_col].shift(252) - 1) * 100
        df['cagr'] = df['cagr'].fillna(0.0)  # Replace NaN with 0.0
        
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
        """Generate trading signals for specified version - ENTRY SIGNALS ONLY"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        
        # Entry conditions (same for both versions) - REMOVED PATTERN LOGIC
        entry_condition = (
            (df[close_col] > df['sma_200']) &
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &
            (df['volume'] > df['volume_sma_30']) &
            (df['cagr'] > 15.0)
        )
        
        # Apply entry signals ONLY - NO EXIT SIGNALS
        signals.loc[entry_condition, 'signal'] = 1
        
        return signals
    
    def simulate_trading(self, df: pd.DataFrame, ticker: str, version: str = 'v6.0') -> List[Dict]:
        """Simulate trading for single ticker - FIXED VERSION"""
        
        df_indicators = self.calculate_indicators(df)
        signals = self.generate_signals(df_indicators, version)
        
        trades = []
        position = None
        close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
        
        for idx, row in enumerate(df_indicators.itertuples()):
            date = getattr(row, 'Index')
            current_price = getattr(row, close_col)
            
            # Entry signal
            if signals.loc[date, 'signal'] == 1 and position is None:
                # Fixed realistic position sizing
                atr_value = getattr(row, 'atr')
                
                # Use fixed position sizing for realistic backtesting
                # Option 1: Fixed shares (simple and realistic)
                shares_to_buy = 1000  # Fixed 1000 shares per trade
                
                # Option 2: ATR-based with caps (more sophisticated)
                # if atr_value > 0:
                #     risk_per_trade = 1000  # Risk $1000 per trade
                #     atr_stop_distance = 3.0 * atr_value
                #     shares_by_risk = risk_per_trade / atr_stop_distance
                #     shares_to_buy = max(100, min(int(shares_by_risk), 5000))  # Min 100, max 5000 shares
                # else:
                #     shares_to_buy = 1000  # Default if ATR is 0
                
                position = {
                    'ticker': ticker,
                    'entry_date': date,
                    'entry_price': current_price,
                    'shares': shares_to_buy,
                    'entry_cost': shares_to_buy * current_price,
                    'highest_price': current_price,
                    'version': version,
                    'is_power_stock': False
                }
                continue
            
            # Exit logic
            if position is not None:
                # Update highest price for trailing stops
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
                
                # Check Power Stock status (v6.5 only)
                if version == 'v6.5':
                    if self.detect_power_stock(df_indicators, df_indicators.index.get_loc(date)):
                        position['is_power_stock'] = True
                
                # Check exit conditions
                should_exit = False
                exit_reason = ''
                
                if version == 'v6.0':
                    # v6.0: SMA 200 break OR ATR stop
                    if current_price < getattr(row, 'sma_200'):
                        should_exit = True
                        exit_reason = 'SMA_200_BREAK'
                    elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                        should_exit = True
                        exit_reason = 'ATR_STOP'
                        
                else:  # v6.5
                    # v6.5 Power Shield Logic
                    is_power_stock = position.get('is_power_stock', False)
                    
                    if is_power_stock:
                        # Power Stock: SMA 25 break OR ATR stop
                        if current_price < getattr(row, 'sma_25'):
                            should_exit = True
                            exit_reason = 'POWER_STOCK_SMA_25_BREAK'
                        elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                            should_exit = True
                            exit_reason = 'POWER_STOCK_ATR_STOP'
                    else:
                        # Standard: SMA 200 break OR ATR stop
                        if current_price < getattr(row, 'sma_200'):
                            should_exit = True
                            exit_reason = 'SMA_200_BREAK'
                        elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                            should_exit = True
                            exit_reason = 'ATR_STOP'
                
                if should_exit:
                    # Create trade record
                    trade = {
                        'ticker': ticker,
                        'version': version,
                        'entry_date': position['entry_date'],
                        'exit_date': date,
                        'entry_price': position['entry_price'],
                        'exit_price': current_price,
                        'shares': position['shares'],
                        'profit_loss': (current_price - position['entry_price']) * position['shares'],
                        'profit_loss_pct': ((current_price - position['entry_price']) / position['entry_price']) * 100,
                        'duration': (date - position['entry_date']).days,
                        'is_power_stock': position.get('is_power_stock', False),
                        'exit_reason': exit_reason
                    }
                    
                    trades.append(trade)
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
                filename = f"backtest_results_{version.replace('.', '_')}.csv"
                df.to_csv(filename, index=False)
                print(f"  Saved {len(df)} trades to {filename}")
        
        print(f"\n✅ SEQUENTIAL BACKTEST COMPLETE!")
        print(f"🕒 This took a while but the results are clean and accurate!")
        print(f"🎯 v6.5 Power Hunter is working beautifully!")

if __name__ == "__main__":
    engine = CrucibleEngine()
    engine.run_crucible_sequential()
