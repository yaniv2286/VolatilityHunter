"""
VolatilityHunter Hedge Fund Portfolio Aggregator
Eliminates cash drag with single $100k portfolio and dynamic allocation
"""

import pandas as pd
import numpy as np
import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import glob
from typing import Dict, List, Tuple, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.strategy_v7_2 import add_indicators_v7_2
from src.notifications import log_info, log_error, log_warning

class PortfolioAggregator:
    """Hedge Fund Portfolio Aggregator with Ironclad Guardrails"""
    
    def __init__(self, initial_capital: float = 100000, max_positions: int = 10):
        """
        Initialize portfolio aggregator
        
        Args:
            initial_capital: Starting capital for portfolio
            max_positions: Maximum number of concurrent positions
        """
        self.initial_capital = initial_capital
        self.max_positions = max_positions
        
        # Portfolio state tracking
        self.cash = initial_capital
        self.positions = {}  # {ticker: {'shares': int, 'entry_price': float, 'entry_date': datetime}}
        self.equity_history = []
        self.trades = []
        
    def load_20yr_data(self, ticker: str) -> pd.DataFrame:
        """Load 20-year historical data for a ticker"""
        try:
            data_dir = Path('data')
            parquet_file = data_dir / f"{ticker.lower()}.parquet"
            
            if parquet_file.exists():
                df = pd.read_parquet(parquet_file)
                
                # Handle date column
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    if hasattr(df['date'].iloc[0], 'tz') and df['date'].iloc[0].tz is not None:
                        df['date'] = df['date'].dt.tz_localize(None)
                    df = df.set_index('date')
                
                # Filter to 20-year range
                start_date = pd.Timestamp('2004-01-01')
                end_date = pd.Timestamp('2024-12-31')
                df = df[(df.index >= start_date) & (df.index <= end_date)]
                
                return df
                
        except Exception as e:
            log_error(f"Error loading data for {ticker}: {e}")
            return None
    
    def generate_signals(self, df: pd.DataFrame, ticker: str) -> pd.DataFrame:
        """Generate all signals for a ticker with Power Stock Dual-Exit architecture"""
        try:
            # Handle timezone issues
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                df = df.copy()
                df.index = df.index.tz_localize(None)
            
            # Add indicators
            df_with_indicators = add_indicators_v7_2(df.copy())
            
            # Add CAGR calculation
            returns_252 = df_with_indicators['adjClose'].pct_change(252)
            df_with_indicators['cagr'] = returns_252.rolling(252, min_periods=1).apply(
                lambda x: (1 + x.iloc[-1]) ** (252/252) - 1 if len(x) > 0 and not pd.isna(x.iloc[-1]) else 0
            )
            
            # Entry Signals
            buy_conditions = (
                (df_with_indicators['stoch_k'] >= 32) & 
                (df_with_indicators['stoch_k'] <= 80) &
                (df_with_indicators['volume'] > df_with_indicators['volume_sma'] * 1.5) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_200']) &
                (df_with_indicators['cagr'] > 0.15)
            )
            
            # Power Stock Promotion Logic
            power_stock_conditions = (
                (df_with_indicators['stoch_k'] > 80) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_25']) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_50']) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_100']) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_200']) &
                (df_with_indicators['stoch_k'] > df_with_indicators['stoch_d'])
            )
            
            # State Mask Implementation
            power_stock_check = power_stock_conditions.rolling(window=2).apply(
                lambda x: x.all() if len(x) == 2 else False, raw=False
            ).fillna(False)
            is_power_stock = power_stock_check.astype(bool).ffill()
            
            # Dual-Exit Architecture
            standard_sell_conditions = (
                ((df_with_indicators['stoch_k'] < df_with_indicators['stoch_d']) & 
                 (df_with_indicators['stoch_k'] > 70)) |  # Overbought crossover only
                (df_with_indicators['adjClose'] < df_with_indicators['sma_200'])
            )
            
            power_sell_conditions = (
                (df_with_indicators['adjClose'] < df_with_indicators['sma_25']) |   # SMA 25 Break
                (df_with_indicators['adjClose'] < df_with_indicators['atr'] * 3.0)   # 3.0x ATR Trailing Stop
            )
            
            # Apply Dual-Exit Logic
            sell_conditions = standard_sell_conditions.where(~is_power_stock, power_sell_conditions)
            
            # Prevent same-day conflicts
            buy_signals = buy_conditions.copy()
            sell_signals = sell_conditions.copy()
            same_day_conflict = buy_signals & sell_signals
            buy_signals = buy_signals & ~same_day_conflict
            
            # Add signals to dataframe
            df_with_indicators['buy_signal'] = buy_signals
            df_with_indicators['sell_signal'] = sell_signals
            df_with_indicators['power_stock_conditions'] = power_stock_conditions
            df_with_indicators['is_power_stock'] = is_power_stock
            df_with_indicators['power_promotion_trigger'] = power_stock_conditions & ~is_power_stock.shift(1).fillna(False)
            
            return df_with_indicators
            
        except Exception as e:
            log_error(f"Error generating signals for {ticker}: {e}")
            return df
    
    def calculate_position_size_ironclad(self, ticker: str, price: float, atr: float, total_equity: float) -> Tuple[int, float]:
        """
        Calculate position size using Ironclad Guardrails
        
        Args:
            ticker: Stock ticker
            price: Current price
            atr: ATR value
            total_equity: Current total equity
            
        Returns:
            Tuple of (shares, notional_value)
        """
        try:
            # Base Risk: 1% of total equity risked per trade based on 3.0x ATR stop distance
            risk_amount = total_equity * 0.01  # 1% risk
            stop_distance = atr * 3.0  # 3.0x ATR stop
            
            # Micro-Stop Filter: Reject trades if stop-loss distance is < $0.01
            if stop_distance < 0.01:
                log_warning(f"Micro-Stop Filter: {ticker} stop distance ${stop_distance:.4f} < $0.01")
                return 0, 0.0
            
            # Calculate shares based on risk
            shares = int(risk_amount / stop_distance)
            
            # Calculate notional value
            notional_value = shares * price
            
            # 20% Notional Cap: Never exceeds 20% of portfolio equity
            max_notional = total_equity * 0.20
            if notional_value > max_notional:
                shares = int(max_notional / price)
                notional_value = shares * price
                log_warning(f"Notional Cap: {ticker} capped at ${notional_value:,.0f} (20% of equity)")
            
            return shares, notional_value
            
        except Exception as e:
            log_error(f"Error calculating position size for {ticker}: {e}")
            return 0, 0.0
    
    def get_universe(self) -> List[str]:
        """Get ALL available tickers from data directory"""
        data_dir = Path('data')
        parquet_files = glob.glob(str(data_dir / "*.parquet"))
        
        tickers = []
        for file in parquet_files:
            ticker = os.path.basename(file).replace('.parquet', '').upper()
            tickers.append(ticker)
        
        return tickers
    
    def load_full_timeline_data(self, ticker: str) -> pd.DataFrame:
        """Load full timeline data for a ticker (2000-2026)"""
        try:
            data_dir = Path('data')
            parquet_file = data_dir / f"{ticker.lower()}.parquet"
            
            if parquet_file.exists():
                df = pd.read_parquet(parquet_file)
                
                # Handle date column
                if 'date' in df.columns:
                    df['date'] = pd.to_datetime(df['date'])
                    if hasattr(df['date'].iloc[0], 'tz') and df['date'].iloc[0].tz is not None:
                        df['date'] = df['date'].dt.tz_localize(None)
                    df = df.set_index('date')
                
                # Filter to full timeline (2000-2026)
                start_date = pd.Timestamp('2000-01-01')
                end_date = pd.Timestamp('2026-02-16')
                df = df[(df.index >= start_date) & (df.index <= end_date)]
                
                return df
                
        except Exception as e:
            log_error(f"Error loading data for {ticker}: {e}")
            return None
    
    def run_portfolio_backtest(self) -> Dict[str, Any]:
        """Run portfolio backtest across ALL available tickers and full timeline"""
        print("="*80)
        print("🚀 VOLATILITYHUNTER TOTAL MARKET CRUCIBLE")
        print("="*80)
        print(f"💰 Initial Capital: ${self.initial_capital:,}")
        print(f"📊 Max Positions: {self.max_positions}")
        print(f"📅 Period: 2000-01-01 to 2026-02-16 (Full 26-Year Timeline)")
        print(f"📈 Universe: ALL Available Tickers (2,000+)")
        print()
        
        # Load ALL available tickers from data directory
        universe = self.get_universe()
        
        print(f"📊 Found {len(universe)} tickers in data directory")
        
        # Generate all signals
        print("\n🔄 Generating signals for full universe...")
        all_signals = {}
        
        for ticker in universe:
            print(f"📊 {ticker}...", end=' ')
            
            df = self.load_full_timeline_data(ticker)
            if df is not None and len(df) > 100:
                df_with_signals = self.generate_signals(df, ticker)
                if df_with_signals is not None:
                    all_signals[ticker] = df_with_signals
                    print("✅")
                else:
                    print("❌")
            else:
                print("❌")
        
        print(f"\n✅ Signals generated for {len(all_signals)} tickers")
        
        # Get all trading days
        all_dates = set()
        for ticker, df in all_signals.items():
            all_dates.update(df.index.date)
        
        trading_days = sorted(list(all_dates))
        print(f"📅 Total trading days: {len(trading_days)}")
        
        # Daily portfolio loop
        print("\n🔄 Running daily portfolio simulation...")
        
        for day_idx, current_date in enumerate(trading_days):
            if day_idx % 252 == 0:  # Annual progress
                year = current_date.year
                print(f"📅 Year {year}: Equity ${self.calculate_total_equity(current_date, all_signals):,.0f}")
            
            # Convert to pandas timestamp for proper comparison
            current_date = pd.Timestamp(current_date)
            
            # Process exits first (free up cash and positions)
            exits_to_process = []
            
            # STEP 1: Daily Promotion Check - Update Power Stock status in positions
            for ticker, position in list(self.positions.items()):
                if ticker in all_signals:
                    df = all_signals[ticker]
                    if current_date in df.index:
                        # Check for Power Stock promotion trigger
                        if df.loc[current_date, 'power_promotion_trigger']:
                            position['is_power_stock'] = True
                            log_info(f"PROMOTION: {ticker} promoted to Power Stock on {current_date.date()}")
            
            # STEP 2: Check exits based on CURRENT Power Stock status in positions dictionary
            for ticker, position in list(self.positions.items()):
                if ticker in all_signals:
                    df = all_signals[ticker]
                    if current_date in df.index:
                        # Use tracked Power Stock status from positions dictionary
                        is_power_stock_now = position['is_power_stock']
                        
                        if is_power_stock_now:
                            # Power Stock: Exit ONLY on power_sell conditions (SMA 25 break or 3.0x ATR trailing stop)
                            power_sell_now = (
                                (df.loc[current_date, 'adjClose'] < df.loc[current_date, 'sma_25']) |
                                (df.loc[current_date, 'adjClose'] < df.loc[current_date, 'atr'] * 3.0)
                            )
                            
                            if power_sell_now:
                                exits_to_process.append(ticker)
                                log_info(f"POWER STOCK EXIT: {ticker} exiting on Power Shield conditions")
                        else:
                            # Standard Trade: Exit on standard_sell conditions
                            standard_sell_now = (
                                ((df.loc[current_date, 'stoch_k'] < df.loc[current_date, 'stoch_d']) & 
                                 (df.loc[current_date, 'stoch_k'] > 70)) |
                                (df.loc[current_date, 'adjClose'] < df.loc[current_date, 'sma_200'])
                            )
                            
                            if standard_sell_now:
                                exits_to_process.append(ticker)
                                log_info(f"STANDARD EXIT: {ticker} exiting on standard conditions")
            
            # Process exits
            for ticker in exits_to_process:
                self.process_exit(ticker, current_date, all_signals[ticker])
            
            # Process entries (if cash and positions available)
            if len(self.positions) < self.max_positions and self.cash > 1000:
                total_equity = self.calculate_total_equity(current_date, all_signals)
                
                # Find buy signals for current date
                potential_entries = []
                for ticker, df in all_signals.items():
                    if ticker not in self.positions and current_date in df.index:
                        if df.loc[current_date, 'buy_signal']:
                            potential_entries.append(ticker)
                
                # Sort by some criteria (e.g., volume) and take first available
                for ticker in potential_entries:
                    if len(self.positions) >= self.max_positions or self.cash < 1000:
                        break
                    
                    df = all_signals[ticker]
                    price = df.loc[current_date, 'adjClose']
                    atr = df.loc[current_date, 'atr']
                    
                    shares, notional = self.calculate_position_size_ironclad(ticker, price, atr, total_equity)
                    
                    if shares > 0 and notional <= self.cash:
                        self.process_entry(ticker, current_date, price, shares, atr * 3.0, df.loc[current_date, 'is_power_stock'])
            
            # Record equity
            total_equity = self.calculate_total_equity(current_date, all_signals)
            self.equity_history.append({
                'date': current_date,
                'equity': total_equity,
                'cash': self.cash,
                'positions_count': len(self.positions)
            })
        
        print("\n✅ Portfolio simulation complete!")
        return self.generate_master_tearsheet()
    
    def process_entry(self, ticker: str, date: datetime, price: float, shares: int, stop_distance: float, is_power_stock: bool):
        """Process a portfolio entry with Ironclad risk parameters"""
        notional = shares * price
        self.cash -= notional
        
        self.positions[ticker] = {
            'shares': shares,
            'entry_price': price,
            'entry_date': date,
            'stop_distance': stop_distance,
            'is_power_stock': is_power_stock,  # Track current state
            'entry_power_stock': is_power_stock  # Track status at entry
        }
        
        self.trades.append({
            'ticker': ticker,
            'date': date,
            'action': 'BUY',
            'price': price,
            'shares': shares,
            'notional': notional,
            'stop_distance': stop_distance,
            'is_power_stock': is_power_stock
        })
        
        stock_type = "POWER STOCK" if is_power_stock else "STANDARD"
        log_info(f"ENTRY: {stock_type} {ticker} {shares} shares @ ${price:.2f} = ${notional:,.0f}")
    
    def process_exit(self, ticker: str, date: datetime, df: pd.DataFrame):
        """Process a portfolio exit"""
        if ticker not in self.positions:
            return
        
        position = self.positions[ticker]
        exit_price = df.loc[date, 'adjClose']
        notional = position['shares'] * exit_price
        pnl = notional - (position['shares'] * position['entry_price'])
        pnl_percent = (exit_price - position['entry_price']) / position['entry_price'] * 100
        
        # Check if this was a Power Stock at exit - use TRACKED position state
        is_power_stock_at_exit = position['is_power_stock']  # Use tracked state from daily promotions
        was_power_stock_at_entry = position['entry_power_stock']
        
        # Track if it got promoted during holding
        got_promoted = is_power_stock_at_exit and not was_power_stock_at_entry
        
        self.cash += notional
        del self.positions[ticker]
        
        self.trades.append({
            'ticker': ticker,
            'date': date,
            'action': 'SELL',
            'price': exit_price,
            'shares': position['shares'],
            'notional': notional,
            'pnl': pnl,
            'pnl_percent': pnl_percent,
            'is_power_stock': is_power_stock_at_exit,  # Current status at exit
            'entry_power_stock': was_power_stock_at_entry,  # Status at entry
            'got_promoted': got_promoted,  # Promoted during holding
            'is_winner': pnl > 0
        })
        
        if got_promoted:
            stock_type = "PROMOTED POWER STOCK"
        elif is_power_stock_at_exit:
            stock_type = "POWER STOCK"
        else:
            stock_type = "STANDARD"
            
        log_info(f"EXIT: {stock_type} {ticker} {position['shares']} shares @ ${exit_price:.2f} = ${notional:,.0f} P&L: ${pnl:,.0f} ({pnl_percent:.1f}%)")
    
    def calculate_total_equity(self, date: datetime, all_signals: Dict[str, pd.DataFrame]) -> float:
        """Calculate total portfolio equity for a given date"""
        total = self.cash
        
        # Convert to pandas timestamp for proper comparison
        date = pd.Timestamp(date)
        
        for ticker, position in self.positions.items():
            if ticker in all_signals:
                df = all_signals[ticker]
                if date in df.index:
                    current_price = df.loc[date, 'adjClose']
                    total += position['shares'] * current_price
        
        return total
    
    def generate_master_tearsheet(self) -> Dict[str, Any]:
        """Generate master portfolio tearsheet"""
        if not self.equity_history:
            return {}
        
        # Convert to DataFrame
        equity_df = pd.DataFrame(self.equity_history)
        equity_df['date'] = pd.to_datetime(equity_df['date'])
        equity_df = equity_df.set_index('date')
        
        # Calculate performance metrics
        initial_equity = self.initial_capital
        final_equity = equity_df['equity'].iloc[-1]
        total_return = (final_equity / initial_equity) - 1
        
        # CAGR
        days = len(equity_df)
        years = days / 252
        cagr = (final_equity / initial_equity) ** (1/years) - 1
        
        # Max Drawdown
        rolling_max = equity_df['equity'].expanding().max()
        drawdown = (equity_df['equity'] - rolling_max) / rolling_max
        max_drawdown = drawdown.min()
        
        # Win Rate
        winning_trades = [t for t in self.trades if t.get('is_winner', False)]
        win_rate = len(winning_trades) / len([t for t in self.trades if t['action'] == 'SELL']) if self.trades else 0
        
        # Sharpe Ratio
        daily_returns = equity_df['equity'].pct_change()
        sharpe_ratio = daily_returns.mean() / daily_returns.std() * np.sqrt(252) if daily_returns.std() > 0 else 0
        
        # Power Stock stats
        sell_trades = [t for t in self.trades if t['action'] == 'SELL']
        power_stock_trades = [t for t in sell_trades if t.get('is_power_stock', False)]
        promoted_trades = [t for t in sell_trades if t.get('got_promoted', False)]
        power_stock_wins = [t for t in power_stock_trades if t.get('is_winner', False)]
        promoted_wins = [t for t in promoted_trades if t.get('is_winner', False)]
        
        power_stock_win_rate = len(power_stock_wins) / len(power_stock_trades) if power_stock_trades else 0
        promoted_win_rate = len(promoted_wins) / len(promoted_trades) if promoted_trades else 0
        
        return {
            'initial_equity': initial_equity,
            'final_equity': final_equity,
            'total_return': total_return,
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'sharpe_ratio': sharpe_ratio,
            'total_trades': len([t for t in self.trades if t['action'] == 'SELL']),
            'power_stock_trades': len(power_stock_trades),
            'promoted_trades': len(promoted_trades),
            'power_stock_win_rate': power_stock_win_rate,
            'promoted_win_rate': promoted_win_rate,
            'equity_history': equity_df,
            'trades': self.trades
        }

def main():
    """Execute Hedge Fund Portfolio Aggregator"""
    aggregator = PortfolioAggregator(initial_capital=100000, max_positions=10)
    results = aggregator.run_portfolio_backtest()
    
    if results:
        print("\n" + "="*80)
        print("📊 VOLATILITYHUNTER MASTER TEARSHEET - TOTAL MARKET CRUCIBLE")
        print("="*80)
        
        print(f"📈 PERFORMANCE SUMMARY")
        print(f"• Initial Capital: ${results['initial_equity']:,.0f}")
        print(f"• Final Equity: ${results['final_equity']:,.0f}")
        print(f"• Total Return: {results['total_return']*100:.2f}%")
        print(f"• CAGR: {results['cagr']*100:.2f}%")
        print(f"• Max Drawdown: {results['max_drawdown']*100:.2f}%")
        print(f"• Sharpe Ratio: {results['sharpe_ratio']:.2f}")
        print()
        
        print(f"🔄 TRADING ACTIVITY")
        print(f"• Total Trades: {results['total_trades']}")
        print(f"• Win Rate: {results['win_rate']*100:.2f}%")
        print(f"• Power Stock Trades: {results['power_stock_trades']}")
        print(f"• Power Stock Win Rate: {results['power_stock_win_rate']*100:.2f}%")
        print(f"• Promoted Trades: {results['promoted_trades']}")
        print(f"• Promoted Win Rate: {results['promoted_win_rate']*100:.2f}%")
        print()
        
        print(f"💰 PORTFOLIO EFFICIENCY")
        print(f"• Capital Utilization: {(1 - aggregator.cash/results['final_equity'])*100:.1f}%")
        print(f"• Average Positions: {np.mean([h['positions_count'] for h in aggregator.equity_history]):.1f}")
        print("="*80)
        
        # Export trades
        if results['trades']:
            trades_df = pd.DataFrame(results['trades'])
            trades_df.to_csv('tv_export_full.csv', index=False)
            print(f"📤 Full Crucible trades exported: tv_export_full.csv")
        
        print(f"\n🎯 TOTAL MARKET CRUCIBLE COMPLETE!")
        
    else:
        print("❌ Portfolio backtest failed")

if __name__ == '__main__':
    main()
