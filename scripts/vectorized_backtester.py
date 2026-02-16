"""
Vectorized Backtester for 20-Year Historical Analysis
Institutional-grade backtesting with pure Pandas vectorization
"""

import pandas as pd
import numpy as np
from pathlib import Path
from datetime import datetime
import sys
import os
import json
from typing import Dict, List, Tuple, Any

# Add src to path for imports
sys.path.append(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))

from src.strategy_v7_2 import analyze_stock_v7_2
from src.shields import apply_universal_shields
from src.notifications import log_info, log_error, log_warning
from src.storage import DataStorage

class VectorizedBacktester:
    """Institutional-grade vectorized backtesting engine"""
    
    def __init__(self, initial_capital: float = 100000):
        """
        Initialize the vectorized backtester
        
        Args:
            initial_capital: Starting capital for backtest
        """
        self.initial_capital = initial_capital
        self.storage = DataStorage()
        
        # Performance tracking
        self.results = {
            'total_return': 0.0,
            'cagr': 0.0,
            'max_drawdown': 0.0,
            'win_rate': 0.0,
            'profit_factor': 0.0,
            'sharpe_ratio': 0.0,
            'total_trades': 0,
            'winning_trades': 0,
            'losing_trades': 0,
            'final_equity': 0.0,
            'equity_curve': [],
            'trades': [],
            'daily_returns': []
        }
    
    def load_20yr_data(self, ticker: str) -> pd.DataFrame:
        """
        Load 20-year historical data for a ticker
        
        Args:
            ticker: Stock ticker symbol
            
        Returns:
            DataFrame with 20-year historical data
        """
        try:
            # Try to load 20-year parquet file first
            data_dir = Path(os.path.join(os.path.dirname(__file__), '..', 'data'))
            parquet_file = data_dir / f"{ticker.lower()}_20yr.parquet"
            
            if parquet_file.exists():
                df = pd.read_parquet(parquet_file)
                log_info(f"Loaded 20-year data for {ticker}: {len(df)} days")
                return df
            else:
                # Fallback to regular data storage
                log_warning(f"20-year data not found for {ticker}, using regular storage")
                
                # Load directly from parquet to avoid storage normalization issues
                regular_parquet = data_dir / f"{ticker.lower()}.parquet"
                if regular_parquet.exists():
                    df = pd.read_parquet(regular_parquet)
                    
                    # Handle date column properly
                    if 'date' in df.columns:
                        df['date'] = pd.to_datetime(df['date'])
                        df = df.set_index('date')
                    
                    # Filter for last 5 years if no 20-year data
                    start_date = datetime.now() - pd.DateOffset(years=5)
                    if hasattr(df.index, 'tz') and df.index.tz is not None:
                        # Handle timezone-aware dates
                        start_date = pd.Timestamp(start_date).tz_localize(df.index.tz)
                    else:
                        start_date = pd.Timestamp(start_date)
                    df = df[df.index >= start_date]
                    log_info(f"Loaded regular data for {ticker}: {len(df)} days")
                    return df
                
                # Last resort: use storage
                df = self.storage.load_data(ticker)
                if df is not None:
                    # Filter for last 5 years if no 20-year data
                    start_date = datetime.now() - pd.DateOffset(years=5)
                    if hasattr(df['date'], 'dt') and hasattr(df['date'].iloc[0], 'tz') and df['date'].iloc[0].tz is not None:
                        # Handle timezone-aware dates
                        start_date = pd.Timestamp(start_date).tz_localize(df['date'].iloc[0].tz)
                    else:
                        start_date = pd.Timestamp(start_date)
                    df = df[df['date'] >= start_date]
                    df = df.set_index('date')
                    log_info(f"Loaded storage data for {ticker}: {len(df)} days")
                return df
                
        except Exception as e:
            log_error(f"Error loading data for {ticker}: {e}")
            return None
    
    def generate_signals(self, df: pd.DataFrame, ticker: str) -> pd.Series:
        """
        Generate buy/sell signals using TRUE vectorized logic
        
        Args:
            df: Historical price data
            ticker: Stock ticker symbol
            
        Returns:
            Series with signals (1=Buy, -1=Sell, 0=Hold)
        """
        try:
            # CRITICAL FIX: Handle timezone issues
            if hasattr(df.index, 'tz') and df.index.tz is not None:
                # Convert timezone-aware to timezone-naive for comparison
                df = df.copy()
                df.index = df.index.tz_localize(None)
            
            # Add indicators using existing v7.2 logic
            from src.strategy_v7_2 import add_indicators_v7_2
            df_with_indicators = add_indicators_v7_2(df.copy())
            
            # CRITICAL FIX: Add CAGR calculation (missing from add_indicators_v7_2)
            # Calculate 252-day rolling CAGR
            returns_252 = df_with_indicators['adjClose'].pct_change(252)
            df_with_indicators['cagr'] = returns_252.rolling(252, min_periods=1).apply(
                lambda x: (1 + x.iloc[-1]) ** (252/252) - 1 if len(x) > 0 and not pd.isna(x.iloc[-1]) else 0
            )
            
            # DEBUG: Check for NaN values
            nan_count = df_with_indicators.isnull().sum().sum()
            log_info(f"DEBUG: {ticker} indicators NaN count: {nan_count}")
            
            # DEBUG: Check specific columns
            stoch_k_nan = df_with_indicators['stoch_k'].isnull().sum()
            sma_200_nan = df_with_indicators['sma_200'].isnull().sum()
            volume_sma_nan = df_with_indicators['volume_sma'].isnull().sum()  # FIXED: volume_sma not volume_sma_30
            cagr_nan = df_with_indicators['cagr'].isnull().sum()
            
            log_info(f"DEBUG: {ticker} - StochK NaN: {stoch_k_nan}, SMA200 NaN: {sma_200_nan}, VolSMA NaN: {volume_sma_nan}, CAGR NaN: {cagr_nan}")
            
            # TRUE VECTORIZED CONDITIONS (as specified in requirements)
            
            # 1. Generate Entry Signals (1 = Buy)
            buy_conditions = (
                (df_with_indicators['stoch_k'] >= 32) & 
                (df_with_indicators['stoch_k'] <= 80) &
                (df_with_indicators['volume'] > df_with_indicators['volume_sma'] * 1.5) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_200']) &
                (df_with_indicators['cagr'] > 0.15)  # 15% CAGR threshold
            )
            
            # 2. Power Stock Promotion Logic (Automatic upgrade to is_power_stock = True)
            power_stock_conditions = (
                (df_with_indicators['stoch_k'] > 80) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_25']) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_50']) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_100']) &
                (df_with_indicators['adjClose'] > df_with_indicators['sma_200']) &
                (df_with_indicators['stoch_k'] > df_with_indicators['stoch_d'])  # Blueprint Crossover
            )
            
            # 3. State Mask Implementation using .ffill() as dictated by Architect
            # Track Power Stock state with forward-fill persistence
            power_stock_check = power_stock_conditions.rolling(window=2).apply(
                lambda x: x.all() if len(x) == 2 else False, raw=False
            ).fillna(False)
            
            # Convert to boolean series for proper masking
            is_power_stock = power_stock_check.astype(bool).ffill()
            
            # 4. Dual-Exit Architecture Implementation
            # Standard Exit Conditions (FIXED: Less noisy exits)
            standard_sell_conditions = (
                ((df_with_indicators['stoch_k'] < df_with_indicators['stoch_d']) & 
                 (df_with_indicators['stoch_k'] > 70)) |  # Only exit on overbought crossover
                (df_with_indicators['adjClose'] < df_with_indicators['sma_200'])   # SMA 200 Break
            )
            
            # Power Shield Exit Conditions (SMA 200 breaks ignored)
            power_sell_conditions = (
                (df_with_indicators['adjClose'] < df_with_indicators['sma_25']) |   # SMA 25 Break
                (df_with_indicators['adjClose'] < df_with_indicators['atr'] * 3.0)   # 3.0x ATR Trailing Stop
            )
            
            # 5. Apply Dual-Exit Logic with State Mask
            # Use .where() to apply conditional logic based on Power Stock state
            sell_conditions = standard_sell_conditions.where(~is_power_stock, power_sell_conditions)
            
            # CRITICAL FIX: Prevent buy and sell on same day
            buy_signals = buy_conditions.copy()
            sell_signals = sell_conditions.copy()
            
            # If buy and sell on same day, prioritize sell (exit first)
            same_day_conflict = buy_signals & sell_signals
            buy_signals = buy_signals & ~same_day_conflict
            
            # 6. Create signal series
            signals = pd.Series(0, index=df_with_indicators.index)
            signals.loc[buy_signals] = 1
            signals.loc[sell_signals] = -1
            
            # CRITICAL FIX: Ensure signals index matches df index for timezone compatibility
            signals.index = df.index
            
            # DEBUG: Power Stock Analysis
            power_stock_count = is_power_stock.sum()
            standard_sell_count = standard_sell_conditions.sum()
            power_sell_count = power_sell_conditions.sum()
            final_sell_count = sell_conditions.sum()
            
            log_info(f"DEBUG: {ticker} - Power Stock promotions: {power_stock_count}")
            log_info(f"DEBUG: {ticker} - Standard sell conditions: {standard_sell_count}")
            log_info(f"DEBUG: {ticker} - Power sell conditions: {power_sell_count}")
            log_info(f"DEBUG: {ticker} - Final sell conditions (dual-exit): {final_sell_count}")
            
            # Store Power Stock count for diagnostics
            self._last_power_stock_count = power_stock_count
            
            log_info(f"Generated {signals.sum()} BUY signals, {(-signals).sum()} SELL signals for {ticker}")
            return signals
            
        except Exception as e:
            log_error(f"Error generating signals for {ticker}: {e}")
            import traceback
            log_error(f"Traceback: {traceback.format_exc()}")
            return pd.Series(0, index=df.index)
    
    def calculate_positions(self, signals: pd.Series) -> pd.Series:
        """
        Calculate positions with proper position management
        
        Args:
            signals: Signal series (1=Buy, -1=Sell, 0=Hold)
            
        Returns:
            Position series (0=No position, 1=Long position)
        """
        # 2. Hold Position (Prevent infinite buying)
        positions = signals.replace(0, np.nan).ffill().fillna(0)
        positions = positions.clip(lower=0)  # Only hold Longs
        
        return positions
    
    def calculate_returns(self, df: pd.DataFrame, positions: pd.Series) -> pd.Series:
        """
        Calculate mark-to-market P&L
        
        Args:
            df: Price data with adjClose
            positions: Position series
            
        Returns:
            Strategy returns series
        """
        # 3. Mark-to-Market Daily P&L (No cumsum on total profit!)
        daily_returns = df['adjClose'].pct_change()
        strategy_returns = positions.shift(1) * daily_returns
        
        return strategy_returns
    
    def calculate_equity_curve(self, strategy_returns: pd.Series) -> pd.Series:
        """
        Calculate compounding equity curve
        
        Args:
            strategy_returns: Daily strategy returns
            
        Returns:
            Equity curve series
        """
        # 4. Compounding Equity Curve
        equity = self.initial_capital * (1 + strategy_returns.fillna(0)).cumprod()
        return equity
    
    def calculate_performance_metrics(self, equity_curve: pd.Series, strategy_returns: pd.Series) -> Dict[str, float]:
        """
        Calculate institutional performance metrics
        
        Args:
            equity_curve: Equity curve series
            strategy_returns: Daily strategy returns
            
        Returns:
            Dictionary with performance metrics
        """
        try:
            total_return = (equity_curve.iloc[-1] / equity_curve.iloc[0]) - 1
            
            # CAGR calculation
            days = len(equity_curve)
            years = days / 252  # Trading days per year
            cagr = (equity_curve.iloc[-1] / equity_curve.iloc[0]) ** (1/years) - 1
            
            # Max Drawdown
            rolling_max = equity_curve.expanding().max()
            drawdown = (equity_curve - rolling_max) / rolling_max
            max_drawdown = drawdown.min()
            
            # Win Rate
            non_zero_returns = strategy_returns[strategy_returns != 0]
            if len(non_zero_returns) > 0:
                positive_returns = non_zero_returns[non_zero_returns > 0]
                win_rate = len(positive_returns) / len(non_zero_returns)
            else:
                win_rate = 0.0
            
            # Sharpe Ratio (assuming 0% risk-free rate)
            if strategy_returns.std() > 0:
                sharpe_ratio = strategy_returns.mean() / strategy_returns.std() * np.sqrt(252)
            else:
                sharpe_ratio = 0.0
            
            # Profit Factor
            positive_returns = strategy_returns[strategy_returns > 0]
            negative_returns = strategy_returns[strategy_returns < 0]
            
            if len(negative_returns) > 0:
                profit_factor = positive_returns.sum() / abs(negative_returns.sum())
            else:
                profit_factor = float('inf') if len(positive_returns) > 0 else 0.0
            
            return {
                'total_return': total_return,
                'cagr': cagr,
                'max_drawdown': max_drawdown,
                'win_rate': win_rate,
                'sharpe_ratio': sharpe_ratio,
                'profit_factor': profit_factor,
                'final_equity': equity_curve.iloc[-1]
            }
            
        except Exception as e:
            log_error(f"Error calculating performance metrics: {e}")
            return {}
    
    def extract_trades(self, df: pd.DataFrame, signals: pd.Series, positions: pd.Series) -> List[Dict]:
        """
        Extract individual trades from signals and positions
        
        Args:
            df: Price data
            signals: Signal series
            positions: Position series
            
        Returns:
            List of trade dictionaries
        """
        trades = []
        entry_trade = None
        
        # Find entry and exit points
        position_changes = positions.diff()
        
        for date, change in position_changes.items():
            if change > 0:  # Entry
                entry_price = df.loc[date, 'adjClose']
                entry_trade = {
                    'ticker': df.iloc[0].get('ticker', 'UNKNOWN'),
                    'entry_date': date,
                    'entry_price': entry_price,
                    'shares': 100,  # Default position size
                    'entry_value': entry_price * 100
                }
                
            elif change < 0 and entry_trade is not None:  # Exit
                exit_price = df.loc[date, 'adjClose']
                
                # Calculate P&L
                pnl = (exit_price - entry_trade['entry_price']) * entry_trade['shares']
                pnl_percent = (exit_price - entry_trade['entry_price']) / entry_trade['entry_price'] * 100
                
                completed_trade = {
                    'ticker': entry_trade['ticker'],
                    'entry_date': entry_trade['entry_date'],
                    'exit_date': date,
                    'entry_price': entry_trade['entry_price'],
                    'exit_price': exit_price,
                    'shares': entry_trade['shares'],
                    'pnl': pnl,
                    'pnl_percent': pnl_percent,
                    'is_winner': pnl > 0
                }
                
                trades.append(completed_trade)
                entry_trade = None
        
        return trades
    
    def export_to_tradingview(self, trades: List[Dict]) -> pd.DataFrame:
        """
        Export trades in TradingView compatible format
        
        Args:
            trades: List of trade dictionaries
            
        Returns:
            DataFrame with TradingView format
        """
        if not trades:
            return pd.DataFrame()
        
        tradingview_df = pd.DataFrame(trades)
        
        # Select and rename columns
        tradingview_df = tradingview_df[['ticker', 'date', 'action', 'shares', 'price']].copy()
        tradingview_df.columns = ['Symbol', 'Date', 'Side', 'Qty', 'Price']
        
        # Convert Side to Buy/Sell format
        tradingview_df['Side'] = tradingview_df['Side'].replace({'BUY': 'Buy', 'SELL': 'Sell'})
        
        return tradingview_df
    
    def backtest_single_ticker(self, ticker: str, start_date: str = None, end_date: str = None) -> Dict[str, Any]:
        """
        Run backtest for a single ticker
        
        Args:
            ticker: Stock ticker symbol
            start_date: Start date for backtest (YYYY-MM-DD)
            end_date: End date for backtest (YYYY-MM-DD)
            
        Returns:
            Dictionary with backtest results
        """
        try:
            log_info(f"Starting backtest for {ticker}")
            
            # Load data
            df = self.load_20yr_data(ticker)
            if df is None or df.empty:
                log_error(f"No data available for {ticker}")
                return {}
            
            # Handle date column - if it exists, set it as index
            if 'date' in df.columns:
                df['date'] = pd.to_datetime(df['date'])
                # CRITICAL FIX: Handle timezone issues
                if hasattr(df['date'].iloc[0], 'tz') and df['date'].iloc[0].tz is not None:
                    df['date'] = df['date'].dt.tz_localize(None)
                df = df.set_index('date')
            
            # Add ticker to dataframe for reference
            df['ticker'] = ticker
            
            # Filter by date range if specified
            if start_date:
                # Handle timezone conversion for start_date
                start_date = pd.Timestamp(start_date)
                if hasattr(df.index, 'tz') and df.index.tz is not None:
                    if start_date.tz is None:
                        start_date = start_date.tz_localize(df.index.tz)
                    else:
                        start_date = start_date.tz_convert(df.index.tz)
                df = df[df.index >= start_date]
            if end_date:
                # Handle timezone conversion for end_date
                end_date = pd.Timestamp(end_date)
                if hasattr(df.index, 'tz') and df.index.tz is not None:
                    if end_date.tz is None:
                        end_date = end_date.tz_localize(df.index.tz)
                    else:
                        end_date = end_date.tz_convert(df.index.tz)
                df = df[df.index <= end_date]
            
            if len(df) < 100:  # Need minimum data
                log_error(f"Insufficient data for {ticker}: {len(df)} days")
                return {}
            
            # Generate signals
            signals = self.generate_signals(df, ticker)
            
            # Store Power Stock promotion count for diagnostics
            power_stock_promotions = 0
            if hasattr(self, '_last_power_stock_count'):
                power_stock_promotions = self._last_power_stock_count
            
            # Calculate positions
            positions = self.calculate_positions(signals)
            
            # Calculate returns
            strategy_returns = self.calculate_returns(df, positions)
            
            # Calculate equity curve
            equity_curve = self.calculate_equity_curve(strategy_returns)
            
            # Calculate performance metrics
            metrics = self.calculate_performance_metrics(equity_curve, strategy_returns)
            
            # Extract trades
            trades = self.extract_trades(df, signals, positions)
            
            # Return comprehensive results
            return {
                'ticker': ticker,
                'start_date': df.index[0].strftime('%Y-%m-%d'),
                'end_date': df.index[-1].strftime('%Y-%m-%d'),
                'total_days': len(df),
                'signals': signals,
                'positions': positions,
                'equity_curve': equity_curve,
                'strategy_returns': strategy_returns,
                'trades': trades,
                'metrics': metrics,
                'power_stock_promotions': power_stock_promotions,
                'total_trades': len(trades)
            }
            
            log_info(f"Backtest completed for {ticker}: Final equity ${equity_curve.iloc[-1]:,.2f}")
            
            return results
            
        except Exception as e:
            log_error(f"Error in backtest for {ticker}: {e}")
            return {}
    
    def generate_tearsheet(self, results: Dict[str, Any]) -> str:
        """
        Generate institutional tearsheet report
        
        Args:
            results: Backtest results
            
        Returns:
            Formatted tearsheet string
        """
        if not results:
            return "No results available"
        
        metrics = results.get('metrics', {})
        
        tearsheet = f"""
============================================================
📊 VOLATILITYHUNTER VECTORIZED BACKTEST RESULTS
============================================================

📈 PERFORMANCE SUMMARY
• Ticker: {results.get('ticker', 'N/A')}
• Period: {results.get('start_date', 'N/A')} to {results.get('end_date', 'N/A')}
• Total Days: {results.get('total_days', 0):,}

💰 FINANCIAL METRICS
• Initial Capital: ${self.initial_capital:,.2f}
• Final Equity: ${metrics.get('final_equity', 0):,.2f}
• Total Return: {metrics.get('total_return', 0):.2%}
• CAGR: {metrics.get('cagr', 0):.2%}

📊 RISK METRICS
• Max Drawdown: {metrics.get('max_drawdown', 0):.2%}
• Sharpe Ratio: {metrics.get('sharpe_ratio', 0):.2f}
• Win Rate: {metrics.get('win_rate', 0):.2%}
• Profit Factor: {metrics.get('profit_factor', 0):.2f}

🔄 TRADING ACTIVITY
• Total Trades: {len(results.get('trades', []))}
• Buy Trades: {len([t for t in results.get('trades', []) if t['action'] == 'BUY'])}
• Sell Trades: {len([t for t in results.get('trades', []) if t['action'] == 'SELL'])}

============================================================
"""
        
        return tearsheet

def main():
    """Main execution function"""
    print("="*80)
    print("🚀 VOLATILITYHUNTER VECTORIZED BACKTESTER")
    print("="*80)
    
    # Initialize backtester
    backtester = VectorizedBacktester(initial_capital=100000)
    
    # Run AAPL test (5 years: 2018-2023)
    print("\n📊 Running AAPL validation test (2018-2023)...")
    results = backtester.backtest_single_ticker('AAPL', start_date='2018-01-01', end_date='2023-12-31')
    
    if results:
        # Generate tearsheet
        tearsheet = backtester.generate_tearsheet(results)
        print(tearsheet)
        
        # CRUCIBLE DIAGNOSTICS - Print key metrics
        if 'metrics' in results:
            metrics = results['metrics']
            signals = results.get('signals', pd.Series())
            print(f"\n🔥 CRUCIBLE DIAGNOSTICS:")
            print(f"📊 Total BUY signals: {(-signals).sum()}")
            print(f"⚡ Power Stock promotions: {results.get('power_stock_promotions', 0)}")
            print(f"💰 Total Return: {metrics.get('total_return', 0) * 100:.2f}%")
            print(f"📈 CAGR: {metrics.get('cagr', 0) * 100:.2f}%")
            print(f"🎯 Max Drawdown: {metrics.get('max_drawdown', 0) * 100:.2f}%")
            print(f"🔄 Total Trades: {results.get('total_trades', 0)}")
            print("="*60)
        
        # Export to TradingView
        tradingview_df = backtester.export_to_tradingview(results.get('trades', []))
        if not tradingview_df.empty:
            output_file = 'aapl_tradingview_export.csv'
            tradingview_df.to_csv(output_file, index=False)
            print(f"📤 TradingView export saved to: {output_file}")
            print(f"📊 Export shape: {tradingview_df.shape}")
            print(f"📋 Sample trades:")
            print(tradingview_df.head())
        
        print("\n✅ AAPL validation test completed successfully!")
    else:
        print("\n❌ AAPL validation test failed!")
    
    print("="*80)

if __name__ == '__main__':
    main()
