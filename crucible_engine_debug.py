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
        """Load and validate ticker data with 252-day minimum requirement"""
        file_path = os.path.join(self.data_dir, f"{ticker.lower()}.parquet")
        
        if not os.path.exists(file_path):
            return None
            
        try:
            df = pd.read_parquet(file_path)
            
            if len(df) < 252:
                return None
                
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
        
        df = add_indicators(df)
        atr_series = calculate_atr(df)
        df['atr'] = atr_series
        
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        df['cagr'] = (df[close_col] / df[close_col].shift(252) - 1) * 100
        df['cagr'] = df['cagr'].fillna(0.0)
        
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
        """Detect if stock is in Power Stock state"""
        if idx < 1:
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
        """Generate trading signals for specified version"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        
        entry_condition = (
            (df[close_col] > df['sma_200']) &
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &
            (df['volume'] > df['volume_sma_30']) &
            (df['cagr'] > 15.0)
        )
        
        signals.loc[entry_condition, 'signal'] = 1
        
        return signals
    
    def simulate_trading(self, df: pd.DataFrame, ticker: str, version: str = 'v6.0') -> List[Dict]:
        """Simulate trading for single ticker with dynamic position sizing - DEBUG VERSION"""
        
        print(f"  DEBUG: Starting simulation for {ticker} {version}")
        
        df = self.calculate_indicators(df)
        signals = self.generate_signals(df, version)
        
        print(f"  DEBUG: Signals generated, entry signals: {signals['signal'].sum()}")
        
        trades = []
        position = None
        portfolio_equity = self.initial_capital
        close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
        
        df['highest_price'] = df[close_col].expanding().max()
        
        entry_count = 0
        exit_count = 0
        trade_append_count = 0
        
        for row_idx, row in enumerate(df.itertuples()):
            date = getattr(row, 'Index')
            current_price = getattr(row, close_col)
            
            # Entry signal
            if signals.loc[date, 'signal'] == 1 and position is None:
                entry_count += 1
                print(f"  DEBUG: Entry #{entry_count} at {date.date()}, price ${current_price:.2f}")
                
                try:
                    risk_amount = portfolio_equity * 0.01
                    atr_value = getattr(row, 'atr')
                    
                    if atr_value <= 0:
                        shares_to_buy = 100
                    else:
                        atr_stop_distance = 3.0 * atr_value
                        shares_to_buy = risk_amount / atr_stop_distance
                    
                    position_cost = shares_to_buy * current_price
                    max_position_cost = portfolio_equity * 0.10
                    
                    if position_cost > max_position_cost:
                        shares_to_buy = max_position_cost / current_price
                        position_cost = max_position_cost
                    
                    if shares_to_buy <= 0:
                        shares_to_buy = 100
                    
                    position = {
                        'ticker': ticker,
                        'entry_date': date,
                        'entry_price': current_price,
                        'shares': shares_to_buy,
                        'entry_cost': shares_to_buy * current_price,
                        'highest_price': current_price,
                        'atr_at_entry': getattr(row, 'atr'),
                        'version': version,
                        'is_power_stock': False
                    }
                    portfolio_equity -= position['entry_cost']
                    
                    print(f"  DEBUG: Position created, shares: {shares_to_buy:.2f}, cost: ${position['entry_cost']:.2f}")
                    
                except Exception as e:
                    print(f"  DEBUG: Error in position sizing: {e}")
                    shares_to_buy = 100
                    position = {
                        'ticker': ticker,
                        'entry_date': date,
                        'entry_price': current_price,
                        'shares': shares_to_buy,
                        'entry_cost': shares_to_buy * current_price,
                        'highest_price': current_price,
                        'atr_at_entry': getattr(row, 'atr'),
                        'version': version,
                        'is_power_stock': False
                    }
                    portfolio_equity -= position['entry_cost']
            
            # Track Power Stock status and update highest price
            elif position is not None and version == 'v6.5':
                if self.detect_power_stock(df, df.index.get_loc(date)):
                    position['is_power_stock'] = True
                    print(f"  DEBUG: Power Stock detected at {date.date()}")
                
                if current_price > position['highest_price']:
                    position['highest_price'] = current_price
            
            # Exit logic
            elif position is not None:
                should_exit = False
                exit_reason = ''
                
                if version == 'v6.0':
                    if current_price < getattr(row, 'sma_200'):
                        should_exit = True
                        exit_reason = 'SMA_200_BREAK'
                    elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                        should_exit = True
                        exit_reason = 'ATR_STOP'
                        
                else:  # v6.5
                    is_power_stock = position.get('is_power_stock', False)
                    
                    if is_power_stock:
                        if current_price < getattr(row, 'sma_25'):
                            should_exit = True
                            exit_reason = 'POWER_STOCK_SMA_25_BREAK'
                        elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                            should_exit = True
                            exit_reason = 'POWER_STOCK_ATR_STOP'
                    else:
                        if current_price < getattr(row, 'sma_200'):
                            should_exit = True
                            exit_reason = 'SMA_200_BREAK'
                        elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                            should_exit = True
                            exit_reason = 'ATR_STOP'
                
                if should_exit:
                    exit_count += 1
                    print(f"  DEBUG: Exit #{exit_count} at {date.date()}, price ${current_price:.2f}, reason: {exit_reason}")
                    
                    try:
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
                        
                        trades.append(trade)
                        trade_append_count += 1
                        print(f"  DEBUG: Trade appended, total trades: {len(trades)}")
                        
                        position = None
                        print(f"  DEBUG: Position reset to None")
                        
                    except Exception as e:
                        print(f"  DEBUG: Error creating trade: {e}")
                        position = None
        
        print(f"  DEBUG: Simulation complete - Entries: {entry_count}, Exits: {exit_count}, Trades: {len(trades)}")
        return trades

# Test the debug version
if __name__ == "__main__":
    engine = CrucibleEngine()
    df = engine.load_data('se')
    
    print('🔍 TESTING DEBUG VERSION')
    print('=' * 60)
    
    v65_trades = engine.simulate_trading(df, 'se', 'v6.5')
    print(f'\nFinal result: {len(v65_trades)} trades')
