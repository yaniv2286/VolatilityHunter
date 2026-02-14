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
        file_path = os.path.join(self.data_dir, f"{ticker.lower()}.parquet")
        
        if not os.path.exists(file_path):
            return None
            
        try:
            df = pd.read_parquet(file_path)
            
            # RULE 1: HARD ENFORCEMENT - 252-day minimum
            if len(df) < 252:
                return None
                
            # Ensure date index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                df.set_index('date', inplace=True)
                
            return df
            
        except Exception as e:
            print(f"Error loading {ticker}: {e}")
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
        """
        Detect if stock is in Power Stock state (hyper-momentum)
        Power Stock criteria: Stoch > 80 + vertical trend + volume surge
        """
        if idx < 1:
            return False
            
        row = df.iloc[idx]
        prev_row = df.iloc[idx-1]
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
        """Simulate trading for single ticker with dynamic position sizing - FIXED VERSION"""
        df = self.calculate_indicators(df)
        signals = self.generate_signals(df, version)
        
        trades = []
        position = None
        portfolio_equity = self.initial_capital
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        
        # Track highest price for ATR stops
        df['highest_price'] = df[close_col].expanding().max()
        
        # Use itertuples for performance on 8.7 million rows
        for row in df.itertuples():
            date = getattr(row, 'Index')
            current_price = getattr(row, close_col)
            
            # Entry signal
            if signals.loc[date, 'signal'] == 1 and position is None:
                # RULE 2: DYNAMIC POSITION SIZING
                risk_amount = portfolio_equity * 0.01  # 1% risk
                atr_stop_distance = 3.0 * getattr(row, 'atr')
                shares_to_buy = risk_amount / atr_stop_distance
                
                # Cap at 10% of portfolio equity
                position_cost = shares_to_buy * current_price
                max_position_cost = portfolio_equity * 0.10
                
                if position_cost > max_position_cost:
                    shares_to_buy = max_position_cost / current_price
                    position_cost = max_position_cost
                
                position = {
                    'ticker': ticker,
                    'entry_date': date,
                    'entry_price': current_price,
                    'shares': shares_to_buy,
                    'entry_cost': position_cost,
                    'highest_price': current_price,
                    'atr_at_entry': getattr(row, 'atr'),
                    'version': version,
                    'is_power_stock': False
                }
                portfolio_equity -= position_cost
            
            # Track Power Stock status and update highest price
            elif position is not None and version == 'v6.5':
                if self.detect_power_stock(df, df.index.get_loc(date)):
                    position['is_power_stock'] = True
                # Update highest price
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
            
            # SEQUENTIAL EXIT LOGIC - Check exits only when in position
            elif position is not None:
                should_exit = False
                exit_reason = ''
                
                if version == 'v6.0':
                    # v6.0 Exit: SMA 200 break OR ATR stop
                    if current_price < getattr(row, 'sma_200'):
                        should_exit = True
                        exit_reason = 'SMA_200_BREAK'
                    elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                        should_exit = True
                        exit_reason = 'ATR_STOP'
                        
                else:  # v6.5
                    # v6.5 Power Shield Exit Logic
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
                    # Close the position
                    exit_price = current_price
                    exit_value = position['shares'] * exit_price
                    portfolio_equity += exit_value
                    
                    profit_loss = exit_value - position['entry_cost']
                    profit_loss_pct = (profit_loss / position['entry_cost']) * 100
                    
                    trade = {
                        'ticker': ticker,
                        'version': version,
                        'entry_date': position['entry_date'],
                        'exit_date': date,
                        'entry_price': position['entry_price'],
                        'exit_price': exit_price,
                        'shares': position['shares'],
                        'profit_loss': profit_loss,
                        'profit_loss_pct': profit_loss_pct,
                        'duration': (date - position['entry_date']).days,
                        'is_power_stock': position.get('is_power_stock', False),
                        'exit_reason': exit_reason
                    }
                    
                    # FIXED: Ensure trade is properly added
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
            
        except Exception as e:
            print(f"Error processing {ticker}: {e}")
            return []
    
    def calculate_performance_metrics(self, trades: List[Dict]) -> Dict[str, float]:
        """Calculate comprehensive performance metrics"""
        if not trades:
            return {
                'total_trades': 0,
                'win_rate': 0.0,
                'cagr': 0.0,
                'max_drawdown': 0.0,
                'profit_factor': 0.0,
                'avg_trade': 0.0,
                'avg_win': 0.0,
                'avg_loss': 0.0
            }
        
        trades_df = pd.DataFrame(trades)
        
        # Basic metrics
        total_trades = len(trades_df)
        winning_trades = trades_df[trades_df['profit_loss'] > 0]
        losing_trades = trades_df[trades_df['profit_loss'] < 0]
        
        win_rate = len(winning_trades) / total_trades * 100 if total_trades > 0 else 0
        avg_trade = trades_df['profit_loss'].mean()
        avg_win = winning_trades['profit_loss'].mean() if len(winning_trades) > 0 else 0
        avg_loss = losing_trades['profit_loss'].mean() if len(losing_trades) > 0 else 0
        
        # Profit factor
        total_wins = winning_trades['profit_loss'].sum()
        total_losses = abs(losing_trades['profit_loss'].sum())
        profit_factor = total_wins / total_losses if total_losses > 0 else float('inf')
        
        # Time-based metrics
        trades_df['exit_date'] = pd.to_datetime(trades_df['exit_date'])
        trades_df = trades_df.sort_values('exit_date')
        
        # Calculate daily equity curve
        start_date = trades_df['exit_date'].min()
        end_date = trades_df['exit_date'].max()
        days = (end_date - start_date).days
        
        if days > 0:
            # Simple CAGR calculation
            final_equity = self.initial_capital + trades_df['profit_loss'].sum()
            cagr = ((final_equity / self.initial_capital) ** (365.25 / days) - 1) * 100
        else:
            cagr = 0.0
        
        # Drawdown calculation
        trades_df['cumulative_pnl'] = trades_df['profit_loss'].cumsum()
        trades_df['running_max'] = trades_df['cumulative_pnl'].expanding().max()
        trades_df['drawdown'] = (trades_df['cumulative_pnl'] - trades_df['running_max']) / self.initial_capital * 100
        max_drawdown = trades_df['drawdown'].min()
        
        return {
            'total_trades': total_trades,
            'win_rate': win_rate,
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'profit_factor': profit_factor,
            'avg_trade': avg_trade,
            'avg_win': avg_win,
            'avg_loss': avg_loss
        }
    
    def run_crucible(self) -> None:
        """Run the complete 20-year backtest comparison"""
        print("🔥 VOLATILITYHUNTER CRUCIBLE ENGINE - 20 YEAR BACKTEST")
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
        
        # RULE 3: MULTIPROCESSING WITH MEMORY MANAGEMENT
        versions = ['v6.0', 'v6.5']
        all_results = {}
        
        for version in versions:
            print(f"\n🔄 Processing {version} ({'Pattern Hunter' if version == 'v6.0' else 'Power Hunter'})...")
            
            # Create arguments for multiprocessing
            args_list = [(ticker, version) for ticker in valid_tickers]
            
            # Process with multiprocessing
            all_trades = []
            
            with ProcessPoolExecutor(max_workers=4) as executor:
                futures = {executor.submit(self.process_ticker, args): args[0] for args in args_list}
                
                for future in tqdm(as_completed(futures), total=len(futures), desc=f"{version}"):
                    ticker = futures[future]
                    try:
                        trades = future.result()
                        all_trades.extend(trades)
                    except Exception as e:
                        print(f"Error with {ticker}: {e}")
            
            all_results[version] = all_trades
            
            # Memory cleanup
            del all_trades
            import gc
            gc.collect()
        
        # RULE 5: PERFORMANCE COMPARISON OUTPUT
        print("\n📈 CALCULATING PERFORMANCE METRICS...")
        
        metrics = {}
        for version in versions:
            metrics[version] = self.calculate_performance_metrics(all_results[version])
        
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
                v60_str = f"{v60_val:.2f}%"
                v65_str = f"{v65_val:.2f}%"
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            elif metric == 'max_drawdown':
                v60_str = f"{v60_val:.2f}%"
                v65_str = f"{v65_val:.2f}%"
                change = ((v65_val - v60_val) / abs(v60_val) * 100) if v60_val != 0 else 0
                change_str = f"{change:+.1f}%"
            elif metric == 'profit_factor':
                v60_str = f"{v60_val:.2f}"
                v65_str = f"{v65_val:.2f}"
                change = ((v65_val - v60_val) / v60_val * 100) if v60_val != 0 else 0
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

if __name__ == "__main__":
    engine = CrucibleEngine()
    engine.run_crucible()
