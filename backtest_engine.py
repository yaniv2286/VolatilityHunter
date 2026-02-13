#!/usr/bin/env python3
"""
VolatilityHunter Backtesting Engine
Vectorized backtesting for Wealth Builder strategy using parquet data
"""

import os
import sys
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
import glob
import logging
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
from tqdm import tqdm
warnings.filterwarnings('ignore')

# Import pattern detection for Phase 1 Visual Pattern Recognition
try:
    from src.strategy import detect_patterns
except ImportError:
    print("Warning: Could not import detect_patterns from src.strategy")
    detect_patterns = None

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class BacktestEngine:
    """Vectorized backtesting engine for Wealth Builder strategy"""
    
    def __init__(self, data_dir='data/', starting_capital=100000, max_positions=10):
        self.data_dir = data_dir
        self.starting_capital = starting_capital
        self.max_positions = max_positions
        self.position_size = 0.10  # 10% allocation per trade
        self.transaction_cost = 0.0001  # 0.01% slippage/fee
        self.trade_history = []
        self.portfolio_history = []
        
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
            
            if len(df) < 12:  # Need at least 12 days of data (what we have available)
                logger.warning(f"Insufficient data for {ticker}: {len(df)} days")
                return None
                
            return df
            
        except Exception as e:
            logger.error(f"Error loading {ticker}: {e}")
            return None
    
    def load_market_data(self):
        """Load SPY data for market regime filter"""
        try:
            spy_file = os.path.join(self.data_dir, 'SPY.parquet')
            if not os.path.exists(spy_file):
                logger.warning("SPY.parquet not found, market regime filter disabled")
                return None
            
            spy_df = pd.read_parquet(spy_file)
            
            # Check if date column exists and set as index
            if 'date' in spy_df.columns:
                spy_df['date'] = pd.to_datetime(spy_df['date'])
                spy_df.set_index('date', inplace=True)
            
            # Standardize column names
            spy_df.columns = [col.upper() for col in spy_df.columns]
            
            # Calculate SMA 200 for SPY
            sma_period = min(200, len(spy_df) // 2)
            if sma_period < 10:
                sma_period = 10
            
            spy_df['sma_200'] = spy_df['CLOSE'].rolling(window=sma_period, min_periods=1).mean()
            
            # Create market regime signals
            spy_df['market_bull'] = spy_df['CLOSE'] >= spy_df['sma_200']
            spy_df['market_cross_down'] = (spy_df['market_bull'] == False) & (spy_df['market_bull'].shift(1) == True)
            
            logger.info(f"Loaded SPY data with {len(spy_df)} days")
            logger.info(f"SPY date range: {spy_df.index[0]} to {spy_df.index[-1]}")
            logger.info(f"Market regime: {'Bull' if spy_df['market_bull'].iloc[-1] else 'Bear'}")
            logger.info(f"Bull market periods: {spy_df['market_bull'].sum()}/{len(spy_df)} ({spy_df['market_bull'].sum()/len(spy_df)*100:.1f}%)")
            
            return spy_df
            
        except Exception as e:
            logger.error(f"Error loading SPY data: {e}")
            return None
    
    def calculate_atr(self, df, period=14):
        """Calculate Average True Range (ATR)"""
        # Adjust period for limited data
        available_days = len(df)
        if available_days < 3:
            return None
            
        # Use smaller period for limited data
        actual_period = min(period, available_days - 1)
        if actual_period < 2:
            actual_period = 2
            
        # Calculate True Range
        df['prev_close'] = df['Close'].shift(1)
        
        high_low = df['High'] - df['Low']
        high_close = abs(df['High'] - df['prev_close'])
        low_close = abs(df['Low'] - df['prev_close'])
        
        df['tr'] = np.maximum.reduce([high_low, high_close, low_close])
        
        # Calculate ATR as simple moving average of TR
        df['atr'] = df['tr'].rolling(window=actual_period, min_periods=1).mean()
        
        return df
    
    def calculate_indicators(self, df):
        """Calculate SMA and Stochastic oscillator"""
        # Use shorter SMA for limited data
        sma_period = min(200, len(df) // 2)
        if sma_period < 10:
            sma_period = 10
            
        df['sma_200'] = df['Close'].rolling(window=sma_period, min_periods=1).mean()
        
        # Stochastic %K (10, 3, 3)
        low_min = df['Low'].rolling(window=10).min()
        high_max = df['High'].rolling(window=10).max()
        df['stoch_k'] = 100 * (df['Close'] - low_min) / (high_max - low_min)
        df['stoch_k'] = df['stoch_k'].rolling(window=3).mean()
        
        return df
    
    def calculate_cagr(self, df, years=2):
        """Calculate Compound Annual Growth Rate"""
        # Adjust for limited data
        available_days = len(df)
        if available_days < 12:
            return 0
            
        # Use available data period
        days_to_use = available_days
        start_price = df['Close'].iloc[0]
        end_price = df['Close'].iloc[-1]
        
        if start_price <= 0:
            return 0
            
        actual_years = days_to_use / 252
        cagr = (end_price / start_price) ** (1/actual_years) - 1
        return cagr
    
    def generate_signals(self, df):
        """Generate trading signals based on Wealth Builder strategy"""
        signals = pd.DataFrame(index=df.index)
        signals['signal'] = 0  # 0: hold, 1: buy, -1: sell
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Calculate CAGR filter (first 2 years)
        cagr = self.calculate_cagr(df)
        
        # Skip if CAGR < 15%
        if cagr < 0.15:
            return signals
        
        # Entry conditions (adjusted for limited data)
        sma_period = min(200, len(df) // 2)
        if sma_period < 5:
            sma_period = 5
            
        entry_condition = (
            (df['Close'] > df['sma_200']) & 
            (df['stoch_k'] > 32) & 
            (df['stoch_k'].shift(1) <= 32) &  # Cross above 32
            (df['Close'] <= 80)  # Price filter
        )
        
        # For very limited data, use simpler entry condition
        if len(df) < 20:
            entry_condition = (
                (df['Close'] > df['sma_200']) & 
                (df['stoch_k'] > 32) & 
                (df['Close'] <= 80)
            )
        
        # Exit conditions
        exit_trend = df['Close'] < df['sma_200']
        
        # Generate signals
        signals.loc[entry_condition, 'signal'] = 1
        signals.loc[exit_trend, 'signal'] = -1
        
        return signals
    
    def generate_signals_with_patterns(self, df):
        """Generate trading signals with Phase 1 Visual Pattern Recognition"""
        signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
        signals['signal'] = 0
        
        # Calculate indicators
        df = self.calculate_indicators(df)
        
        # Adjust SMA period for limited data
        sma_period = min(200, len(df) // 2)
        if sma_period < 5:
            sma_period = 5
        
        # A+ Wealth Builder Entry Rules (without patterns first)
        entry_condition = (
            (df['Close'] > df['sma_200']) & 
            (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &  # Sweet spot [32-80]
            (df['volume_sma_30'] > 0) & (df['Volume'] > df['volume_sma_30']) &  # Volume momentum
            (df['cagr'] > 15.0)  # Quality filter
        )
        
        # For very limited data, use simpler entry condition
        if len(df) < 20:
            entry_condition = (
                (df['Close'] > df['sma_200']) & 
                (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80)
            )
        
        # Exit conditions
        exit_trend = df['Close'] < df['sma_200']
        
        # Apply pattern detection to entry signals
        if detect_patterns is not None and len(df) >= 10:
            # Check patterns for each potential entry
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
            # Fallback to original entry condition if patterns not available
            signals.loc[entry_condition, 'signal'] = 1
        
        signals.loc[exit_trend, 'signal'] = -1
        
        return signals
    
    def simulate_trading(self, ticker_data, ticker, stop_type='fixed', atr_multiplier=3.0, market_data=None, use_market_filter=False):
        """Simulate trading for a single ticker with market regime filter"""
        df = ticker_data.copy()
        signals = self.generate_signals(df)
        
        if signals['signal'].sum() == 0:  # No signals
            return []
        
        # Calculate ATR if needed
        if stop_type == 'atr':
            df_with_atr = self.calculate_atr(df)
            if df_with_atr is None:
                logger.warning(f"Insufficient data for ATR calculation in {ticker}")
                return []
            df = df_with_atr
        
        # Merge market data if available
        if market_data is not None and use_market_filter:
            # Align market data with ticker data
            df = df.join(market_data[['market_bull', 'market_cross_down']], how='left')
            df['market_bull'] = df['market_bull'].fillna(True)  # Assume bull market if no data
            df['market_cross_down'] = df['market_cross_down'].fillna(False)
        
        trades = []
        position = None
        entry_price = 0
        peak_price = 0
        entry_date = None
        stop_loss = 0
        original_atr_multiplier = atr_multiplier
        
        # Debug: Print signal dates
        buy_dates = signals[signals['signal'] == 1].index.tolist()
        sell_dates = signals[signals['signal'] == -1].index.tolist()
        logger.info(f"{ticker}: Buy signals on {buy_dates}, Sell signals on {sell_dates}")
        
        for i, (date, row) in enumerate(df.iterrows()):
            current_price = row['Close']
            signal = signals.loc[date, 'signal'] if date in signals.index else 0
            
            # Market regime filter
            market_bull = True
            market_cross_down = False
            if use_market_filter and 'market_bull' in df.columns:
                market_bull = row['market_bull']
                market_cross_down = row['market_cross_down']
            
            # Emergency rule: tighten stops on market cross down
            if market_cross_down and position == 'long':
                atr_multiplier = original_atr_multiplier * 0.5  # Tighten by 50%
                logger.info(f"{ticker}: Market cross down detected, tightening ATR multiplier to {atr_multiplier:.1f}")
            
            # Entry signal (filtered by market regime)
            if signal == 1 and position is None:
                # Market regime filter: no new buys in bear market
                if use_market_filter and not market_bull:
                    logger.info(f"{ticker}: Entry signal blocked by market regime filter (bear market)")
                    continue
                
                position = 'long'
                entry_price = current_price * (1 + self.transaction_cost)
                peak_price = entry_price
                entry_date = date
                
                # Set initial stop loss
                if stop_type == 'fixed':
                    stop_loss = peak_price * 0.90  # 10% trailing stop
                elif stop_type == 'atr':
                    if not pd.isna(row['atr']):
                        stop_loss = peak_price - (row['atr'] * atr_multiplier)
                    else:
                        logger.warning(f"ATR not available for {ticker} on {date}")
                        stop_loss = peak_price * 0.90  # Fallback to fixed
                
                logger.info(f"{ticker}: ENTRY on {date} at ${entry_price:.2f}, Stop: ${stop_loss:.2f}, Market: {'Bull' if market_bull else 'Bear'}")
                
            # Exit conditions
            elif position == 'long':
                # Update peak price
                peak_price = max(peak_price, current_price)
                
                # Update trailing stop (only moves up, never down)
                if stop_type == 'fixed':
                    new_stop = peak_price * 0.90
                elif stop_type == 'atr':
                    if not pd.isna(row['atr']):
                        new_stop = peak_price - (row['atr'] * atr_multiplier)
                    else:
                        new_stop = stop_loss  # Keep current stop if ATR not available
                
                stop_loss = max(stop_loss, new_stop)  # Only move up
                
                # Trend exit
                if current_price < row['sma_200']:
                    exit_price = current_price * (1 - self.transaction_cost)
                    trades.append({
                        'ticker': ticker,
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'peak_price': peak_price,
                        'return': (exit_price - entry_price) / entry_price,
                        'exit_reason': 'trend',
                        'stop_type': stop_type,
                        'atr_multiplier': atr_multiplier if stop_type == 'atr' else None,
                        'market_filtered': use_market_filter
                    })
                    logger.info(f"{ticker}: EXIT on {date} at ${exit_price:.2f} (trend)")
                    position = None
                
                # Stop loss exit
                elif current_price < stop_loss:
                    exit_price = current_price * (1 - self.transaction_cost)
                    trades.append({
                        'ticker': ticker,
                        'entry_date': entry_date,
                        'exit_date': date,
                        'entry_price': entry_price,
                        'exit_price': exit_price,
                        'peak_price': peak_price,
                        'return': (exit_price - entry_price) / entry_price,
                        'exit_reason': 'stop_loss',
                        'stop_type': stop_type,
                        'atr_multiplier': atr_multiplier if stop_type == 'atr' else None,
                        'market_filtered': use_market_filter
                    })
                    logger.info(f"{ticker}: EXIT on {date} at ${exit_price:.2f} (stop loss at ${stop_loss:.2f})")
        
        return trades
    
    def process_single_ticker_with_patterns(self, ticker, stop_type='fixed', atr_multiplier=3.0, market_data=None, use_market_filter=False):
        """Process a single ticker with specified stop type and market filter"""
        try:
            df = self.load_ticker_data(ticker)
            if df is None:
                return []
            
            trades = self.simulate_trading_with_patterns(df, ticker, stop_type, atr_multiplier, market_data, use_market_filter)
            return trades
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            return []
    
    def process_all_tickers_with_patterns(self, stop_type='fixed', atr_multiplier=3.0, market_data=None, use_market_filter=False):
        """Process all tickers in parallel with specified stop type and market filter"""
        # Get all parquet files
        parquet_files = glob.glob(os.path.join(self.data_dir, "*.parquet"))
        tickers = [os.path.basename(f).replace('.parquet', '').upper() for f in parquet_files]
        
        logger.info(f"Processing {len(tickers)} tickers with {stop_type} stop...")
        if stop_type == 'atr':
            logger.info(f"ATR Multiplier: {atr_multiplier}")
        if use_market_filter:
            logger.info("Market regime filter: ENABLED")
        
        all_trades = []
        
        # Process in parallel with progress bar
        # Temporarily set logging to WARNING level to avoid interfering with progress bar
        original_level = logging.getLogger().level
        logging.getLogger().setLevel(logging.WARNING)
        
        with ProcessPoolExecutor(max_workers=4) as executor:
            futures = []
            
            # Submit all tasks
            for ticker in tickers:
                future = executor.submit(self.process_single_ticker, ticker, stop_type, atr_multiplier, market_data, use_market_filter)
                futures.append(future)
            
            # Process with progress bar
            for future in tqdm(as_completed(futures), total=len(tickers), desc="Backtesting Universe", unit="ticker"):
                try:
                    trades = future.result()
                    all_trades.extend(trades)
                except Exception as e:
                    tqdm.write(f"Error processing ticker: {e}")
        
        # Restore original logging level
        logging.getLogger().setLevel(original_level)
        
        self.trade_history = all_trades
        logger.info(f"Generated {len(all_trades)} trades")
        
        return all_trades
    
    def process_single_ticker(self, ticker, stop_type='fixed', atr_multiplier=3.0, market_data=None, use_market_filter=False):
        """Process a single ticker with specified stop type and market filter"""
        try:
            df = self.load_ticker_data(ticker)
            if df is None:
                return []
            
            trades = self.simulate_trading(df, ticker, stop_type, atr_multiplier, market_data, use_market_filter)
            return trades
            
        except Exception as e:
            logger.error(f"Error processing {ticker}: {e}")
            return []
    
    def generate_tradingview_export(self, trades, filename='tradingview_trades.csv'):
        """Generate TradingView-compatible trade log"""
        if not trades:
            logger.warning("No trades to export for TradingView")
            return
        
        # Convert to DataFrame
        df_trades = pd.DataFrame(trades)
        
        # Create TradingView format
        tv_trades = []
        
        for _, trade in df_trades.iterrows():
            # Entry trade
            tv_trades.append({
                'Symbol': trade['ticker'],
                'Side': 'buy',
                'Qty': 100,  # Fixed quantity for TradingView
                'Fill Price': trade['entry_price'],
                'Closing Time': trade['entry_date'].strftime('%Y-%m-%d %H:%M:%S')
            })
            
            # Exit trade
            tv_trades.append({
                'Symbol': trade['ticker'],
                'Side': 'sell',
                'Qty': 100,  # Fixed quantity for TradingView
                'Fill Price': trade['exit_price'],
                'Closing Time': trade['exit_date'].strftime('%Y-%m-%d %H:%M:%S')
            })
        
        # Create DataFrame and save
        tv_df = pd.DataFrame(tv_trades)
        tv_df.to_csv(filename, index=False)
        logger.info(f"TradingView export saved to {filename}")
        logger.info(f"Exported {len(tv_trades)} trades ({len(tv_trades)//2} positions)")
    
    def generate_comparison_report(self, results, filename='atr_comparison_report.csv'):
        """Generate detailed comparison report"""
        report_data = []
        
        for name, result in results.items():
            perf = result['performance']
            config = result['config']
            
            report_data.append({
                'Configuration': name,
                'Stop_Type': config['stop_type'],
                'ATR_Multiplier': config.get('atr_multiplier', 'N/A'),
                'CAGR': perf['cagr'],
                'Max_Drawdown': perf['max_drawdown'],
                'Sharpe_Ratio': perf['sharpe_ratio'],
                'Win_Rate': perf['win_rate'],
                'Total_Trades': perf['total_trades'],
                'Total_Return': perf['total_return'],
                'Profit_Factor': perf['profit_factor']
            })
        
        report_df = pd.DataFrame(report_data)
        report_df.to_csv(filename, index=False)
        logger.info(f"Comparison report saved to {filename}")
    
    def run_market_regime_comparison(self):
        """Run comparison between 5x ATR with and without market regime filter"""
        print("Running Market Regime Filter Comparison...")
        print("="*60)
        
        # Load market data
        market_data = self.load_market_data()
        if market_data is None:
            print("❌ SPY data not available, cannot run market regime comparison")
            return None
        
        # Test configurations
        configs = [
            {'stop_type': 'atr', 'atr_multiplier': 5.0, 'use_market_filter': False, 'name': '5x ATR (Original)'},
            {'stop_type': 'atr', 'atr_multiplier': 5.0, 'use_market_filter': True, 'name': '5x ATR + Market Filter'}
        ]
        
        results = {}
        
        for config in configs:
            print(f"\nTesting {config['name']}...")
            
            # Reset trade history
            self.trade_history = []
            
            # Process tickers
            trades = self.process_all_tickers(
                config['stop_type'], 
                config['atr_multiplier'], 
                market_data, 
                config['use_market_filter']
            )
            
            # Calculate performance
            performance = self.calculate_portfolio_performance(trades)
            
            results[config['name']] = {
                'performance': performance,
                'trades': trades,
                'config': config
            }
            
            print(f"  CAGR: {performance['cagr']:.2%}")
            print(f"  Max Drawdown: {performance['max_drawdown']:.2%}")
            print(f"  Total Trades: {performance['total_trades']}")
            
            # Check if goal is met
            if config['use_market_filter']:
                goal_met = performance['cagr'] > 0.20 and performance['max_drawdown'] > -0.25
                print(f"  Goal Met (CAGR > 20% & DD < 25%): {'✅ YES' if goal_met else '❌ NO'}")
        
        # Generate comparison table
        self.print_market_regime_comparison(results)
        
        # Generate comparison plot
        self.generate_market_regime_plot(results)
        
        return results
    
    def print_market_regime_comparison(self, results):
        """Print market regime comparison table"""
        print("\n" + "="*80)
        print("MARKET REGIME FILTER COMPARISON RESULTS")
        print("="*80)
        
        print(f"{'Configuration':<25} {'CAGR':<10} {'Max DD':<10} {'Sharpe':<8} {'Win Rate':<10} {'Trades':<8} {'Goal':<8}")
        print("-" * 80)
        
        for name, result in results.items():
            perf = result['performance']
            goal_met = perf['cagr'] > 0.20 and perf['max_drawdown'] > -0.25
            goal_text = '✅ YES' if goal_met else '❌ NO'
            
            print(f"{name:<25} {perf['cagr']:<10.2%} {perf['max_drawdown']:<10.2%} {perf['sharpe_ratio']:<8.2f} "
                  f"{perf['win_rate']:<10.2%} {perf['total_trades']:<8} {goal_text:<8}")
        
        print("="*80)
        
        # Analysis
        original = results['5x ATR (Original)']['performance']
        filtered = results['5x ATR + Market Filter']['performance']
        
        print(f"\nMARKET FILTER IMPACT ANALYSIS:")
        print("-" * 30)
        print(f"CAGR Change: {((filtered['cagr'] - original['cagr']) / original['cagr'] * 100):+.1f}%")
        print(f"Drawdown Change: {((filtered['max_drawdown'] - original['max_drawdown']) / abs(original['max_drawdown']) * 100):+.1f}%")
        print(f"Sharpe Change: {((filtered['sharpe_ratio'] - original['sharpe_ratio']) / original['sharpe_ratio'] * 100):+.1f}%")
        print(f"Trade Count Change: {((filtered['total_trades'] - original['total_trades']) / original['total_trades'] * 100):+.1f}%")
        
        # Recommendation
        goal_met = filtered['cagr'] > 0.20 and filtered['max_drawdown'] > -0.25
        if goal_met:
            print(f"\n🎯 GOAL ACHIEVED! Market filter successfully maintains CAGR > 20% while reducing drawdown < 25%")
        else:
            print(f"\n⚠️ Goal not achieved. Further optimization needed.")
    
    def generate_market_regime_plot(self, results):
        """Generate market regime comparison plot"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            plt.figure(figsize=(12, 8))
            
            for name, result in results.items():
                perf = result['performance']
                if not perf['portfolio_history'].empty:
                    portfolio_values = perf['portfolio_history']['portfolio_value']
                    # Normalize to starting value
                    normalized = portfolio_values / self.starting_capital
                    
                    plt.plot(perf['portfolio_history'].index, normalized, 
                            label=name, linewidth=2, alpha=0.8)
            
            plt.title('VolatilityHunter: Market Regime Filter Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Portfolio Value (Normalized)', fontsize=12)
            plt.legend(loc='upper left')
            plt.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            plt.gca().xaxis.set_major_locator(mdates.YearLocator())
            
            plt.tight_layout()
            plt.savefig('market_regime_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"\nMarket regime comparison plot saved to 'market_regime_comparison.png'")
            
        except ImportError:
            print("\nWarning: matplotlib not available for plotting")
        except Exception as e:
            print(f"\nError generating plot: {e}")
    
    def generate_market_regime_report(self, results, filename='market_regime_comparison_report.csv'):
        """Generate detailed market regime comparison report"""
        report_data = []
        
        for name, result in results.items():
            perf = result['performance']
            config = result['config']
            
            report_data.append({
                'Configuration': name,
                'Stop_Type': config['stop_type'],
                'ATR_Multiplier': config.get('atr_multiplier', 'N/A'),
                'Market_Filter': config.get('use_market_filter', False),
                'CAGR': perf['cagr'],
                'Max_Drawdown': perf['max_drawdown'],
                'Sharpe_Ratio': perf['sharpe_ratio'],
                'Win_Rate': perf['win_rate'],
                'Total_Trades': perf['total_trades'],
                'Total_Return': perf['total_return'],
                'Profit_Factor': perf['profit_factor'],
                'Goal_Met': perf['cagr'] > 0.20 and perf['max_drawdown'] > -0.25
            })
        
        report_df = pd.DataFrame(report_data)
        report_df.to_csv(filename, index=False)
        logger.info(f"Market regime comparison report saved to {filename}")
    
    def generate_volatility_sizing_report(self, results, filename='volatility_sizing_comparison_report.csv'):
        """Generate detailed volatility sizing comparison report"""
        report_data = []
        
        for name, result in results.items():
            perf = result['performance']
            config = result['config']
            
            report_data.append({
                'Configuration': name,
                'Stop_Type': config['stop_type'],
                'ATR_Multiplier': config.get('atr_multiplier', 'N/A'),
                'Market_Filter': config.get('use_market_filter', False),
                'Volatility_Sizing': config.get('use_volatility_sizing', False),
                'CAGR': perf['cagr'],
                'Max_Drawdown': perf['max_drawdown'],
                'Sharpe_Ratio': perf['sharpe_ratio'],
                'MAR_Ratio': perf['mar_ratio'],
                'Win_Rate': perf['win_rate'],
                'Total_Trades': perf['total_trades'],
                'Total_Return': perf['total_return'],
                'Profit_Factor': perf['profit_factor'],
                'Goal_Met': perf['mar_ratio'] > 1.0
            })
        
        report_df = pd.DataFrame(report_data)
        report_df.to_csv(filename, index=False)
        logger.info(f"Volatility sizing comparison report saved to {filename}")
    
    def run_comparison(self):
        """Run comparison between different stop types"""
        print("Running ATR Stop Comparison...")
        print("="*50)
        
        # Test configurations
        configs = [
            {'stop_type': 'fixed', 'atr_multiplier': None, 'name': '10% Fixed Stop'},
            {'stop_type': 'atr', 'atr_multiplier': 2.0, 'name': '2x ATR Stop'},
            {'stop_type': 'atr', 'atr_multiplier': 3.0, 'name': '3x ATR Stop'},
            {'stop_type': 'atr', 'atr_multiplier': 5.0, 'name': '5x ATR Stop'}
        ]
        
        results = {}
        
        for config in configs:
            print(f"\nTesting {config['name']}...")
            
            # Reset trade history
            self.trade_history = []
            
            # Process tickers
            trades = self.process_all_tickers(config['stop_type'], config['atr_multiplier'])
            
            # Calculate performance
            performance = self.calculate_portfolio_performance(trades)
            
            results[config['name']] = {
                'performance': performance,
                'trades': trades,
                'config': config
            }
            
            print(f"  CAGR: {performance['cagr']:.2%}")
            print(f"  Max Drawdown: {performance['max_drawdown']:.2%}")
            print(f"  Total Trades: {performance['total_trades']}")
        
        # Generate comparison table
        self.print_comparison_table(results)
        
        # Generate comparison plot
        self.generate_comparison_plot(results)
        
        return results
    
    def print_comparison_table(self, results):
        """Print comparison table of all configurations"""
        print("\n" + "="*80)
        print("ATR STOP COMPARISON RESULTS")
        print("="*80)
        
        print(f"{'Configuration':<15} {'CAGR':<10} {'Max DD':<10} {'Sharpe':<8} {'Win Rate':<10} {'Trades':<8}")
        print("-" * 80)
        
        for name, result in results.items():
            perf = result['performance']
            print(f"{name:<15} {perf['cagr']:<10.2%} {perf['max_drawdown']:<10.2%} {perf['sharpe_ratio']:<8.2f} "
                  f"{perf['win_rate']:<10.2%} {perf['total_trades']:<8}")
        
        print("="*80)
        
        # Find best configuration
        best_config = max(results.keys(), key=lambda k: results[k]['performance']['sharpe_ratio'])
        print(f"\nBest Configuration by Sharpe Ratio: {best_config}")
        print(f"  Sharpe: {results[best_config]['performance']['sharpe_ratio']:.2f}")
        print(f"  CAGR: {results[best_config]['performance']['cagr']:.2%}")
        print(f"  Max DD: {results[best_config]['performance']['max_drawdown']:.2%}")
    
    def generate_comparison_plot(self, results):
        """Generate comparison plot of equity curves"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            plt.figure(figsize=(12, 8))
            
            for name, result in results.items():
                perf = result['performance']
                if not perf['portfolio_history'].empty:
                    portfolio_values = perf['portfolio_history']['portfolio_value']
                    # Normalize to starting value
                    normalized = portfolio_values / self.starting_capital
                    
                    plt.plot(perf['portfolio_history'].index, normalized, 
                            label=name, linewidth=2, alpha=0.8)
            
            plt.title('VolatilityHunter: ATR Stop Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Portfolio Value (Normalized)', fontsize=12)
            plt.legend(loc='upper left')
            plt.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            plt.gca().xaxis.set_major_locator(mdates.YearLocator())
            
            plt.tight_layout()
            plt.savefig('atr_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"\nComparison plot saved to 'atr_comparison.png'")
            
        except ImportError:
            print("\nWarning: matplotlib not available for plotting")
        except Exception as e:
            print(f"\nError generating plot: {e}")
    
    def calculate_position_size(self, equity, atr, risk_per_trade=0.01, max_position_pct=0.15):
        """Calculate volatility-adjusted position size"""
        if atr <= 0:
            return 0
        
        # Calculate position size based on risk
        risk_amount = equity * risk_per_trade
        atr_distance = 3 * atr  # 3x ATR stop distance
        position_value = risk_amount / atr_distance
        
        # Cap at maximum position percentage
        max_position_value = equity * max_position_pct
        position_value = min(position_value, max_position_value)
        
        return position_value
    
    def calculate_portfolio_performance(self, trades, starting_equity=100000, use_volatility_sizing=False, market_data=None):
        """Calculate portfolio-level performance metrics with volatility sizing"""
        if not trades:
            return self._empty_performance()
        
        # Convert to DataFrame
        df_trades = pd.DataFrame(trades)
        df_trades['entry_date'] = pd.to_datetime(df_trades['entry_date'])
        df_trades['exit_date'] = pd.to_datetime(df_trades['exit_date'])
        
        # Sort by entry date
        df_trades = df_trades.sort_values('entry_date')
        
        # Initialize portfolio tracking
        portfolio_history = []
        current_equity = starting_equity
        peak_equity = starting_equity
        open_positions = {}
        risk_per_trade = 0.01  # Default 1% risk per trade
        
        # Get all unique dates
        all_dates = sorted(set(df_trades['entry_date'].tolist() + df_trades['exit_date'].tolist()))
        
        for date in all_dates:
            # Get trades for this date
            entries = df_trades[df_trades['entry_date'] == date]
            exits = df_trades[df_trades['exit_date'] == date]
            
            # Process exits first
            for _, exit_trade in exits.iterrows():
                ticker = exit_trade['ticker']
                if ticker in open_positions:
                    position = open_positions[ticker]
                    # Calculate P&L
                    entry_value = position['quantity'] * position['entry_price']
                    exit_value = position['quantity'] * exit_trade['exit_price']
                    pnl = exit_value - entry_value - (entry_value + exit_value) * self.transaction_cost
                    
                    current_equity += pnl
                    del open_positions[ticker]
            
            # Calculate current drawdown
            drawdown = (current_equity - peak_equity) / peak_equity
            
            # Apply drawdown throttle
            if drawdown <= -0.20:  # 20% drawdown - stop all new entries
                risk_per_trade = 0.0
            elif drawdown <= -0.15:  # 15% drawdown - reduce risk to 0.5%
                risk_per_trade = 0.005
            else:
                risk_per_trade = 0.01  # Normal 1% risk
            
            # Process entries
            for _, entry_trade in entries.iterrows():
                if risk_per_trade == 0:
                    # Skip entries due to drawdown throttle
                    continue
                
                ticker = entry_trade['ticker']
                
                # Calculate position size
                if use_volatility_sizing and 'atr_multiplier' in entry_trade:
                    # Get ATR at entry time (approximate using trade data)
                    atr_estimate = entry_trade['entry_price'] * 0.02  # Rough estimate
                    position_value = self.calculate_position_size(current_equity, atr_estimate, risk_per_trade)
                    quantity = position_value / entry_trade['entry_price']
                else:
                    # Fixed 10% position sizing
                    position_value = current_equity * 0.10
                    quantity = position_value / entry_trade['entry_price']
                
                # Check if we have enough equity
                required_equity = position_value * (1 + self.transaction_cost)
                if required_equity <= current_equity:
                    open_positions[ticker] = {
                        'ticker': ticker,
                        'quantity': quantity,
                        'entry_price': entry_trade['entry_price'],
                        'entry_date': entry_trade['entry_date'],
                        'value': position_value
                    }
                    current_equity -= required_equity
            
            # Update peak equity
            peak_equity = max(peak_equity, current_equity)
            
            # Record portfolio state
            portfolio_value = current_equity + sum(pos['quantity'] * self._get_current_price(pos['ticker'], date, df_trades) for pos in open_positions.values())
            portfolio_history.append({
                'date': date,
                'portfolio_value': portfolio_value,
                'peak_equity': peak_equity,
                'drawdown': drawdown,
                'open_positions': len(open_positions),
                'risk_per_trade': risk_per_trade
            })
        
        # Convert to DataFrame
        portfolio_df = pd.DataFrame(portfolio_history)
        portfolio_df.set_index('date', inplace=True)
        
        # Calculate final metrics
        if not portfolio_df.empty:
            final_value = portfolio_df['portfolio_value'].iloc[-1]
            total_return = (final_value - starting_equity) / starting_equity
            
            # Calculate CAGR
            days = (portfolio_df.index[-1] - portfolio_df.index[0]).days
            years = days / 365.25
            cagr = (final_value / starting_equity) ** (1/years) - 1 if years > 0 else 0
            
            # Calculate max drawdown
            max_drawdown = portfolio_df['drawdown'].min()
            
            # Calculate Sharpe ratio (simplified)
            returns = portfolio_df['portfolio_value'].pct_change().dropna()
            sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            
            # Calculate MAR ratio
            mar_ratio = cagr / abs(max_drawdown) if max_drawdown != 0 else 0
            
            # Calculate trade statistics
            winning_trades = df_trades[df_trades['return'] > 0]
            losing_trades = df_trades[df_trades['return'] <= 0]
            
            win_rate = len(winning_trades) / len(df_trades) if len(df_trades) > 0 else 0
            
            avg_win = winning_trades['return'].mean() if len(winning_trades) > 0 else 0
            avg_loss = losing_trades['return'].mean() if len(losing_trades) > 0 else 0
            
            profit_factor = (winning_trades['return'].sum() / abs(losing_trades['return'].sum())) if len(losing_trades) > 0 and losing_trades['return'].sum() != 0 else 0
        else:
            return self._empty_performance()
        
        return {
            'total_return': total_return,
            'cagr': cagr,
            'max_drawdown': max_drawdown,
            'sharpe_ratio': sharpe_ratio,
            'mar_ratio': mar_ratio,
            'win_rate': win_rate,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'profit_factor': profit_factor,
            'total_trades': len(df_trades),
            'portfolio_history': portfolio_df
        }
    
    def _get_current_price(self, ticker, date, df_trades):
        """Helper to get current price for open position valuation"""
        # Simplified - use entry price as current price (would need market data for accurate valuation)
        relevant_trades = df_trades[df_trades['ticker'] == ticker]
        if not relevant_trades.empty:
            return relevant_trades['entry_price'].iloc[0]
        return 100  # Default fallback
    
    def run_volatility_sizing_comparison(self):
        """Run comparison between fixed sizing and volatility-adjusted sizing"""
        print("Running Volatility-Adjusted Position Sizing Comparison...")
        print("="*65)
        
        # Load market data
        market_data = self.load_market_data()
        if market_data is None:
            print("❌ SPY data not available, cannot run comparison")
            return None
        
        # Test configurations
        configs = [
            {
                'stop_type': 'atr', 
                'atr_multiplier': 5.0, 
                'use_market_filter': True, 
                'use_volatility_sizing': False, 
                'name': '5x ATR + Market Filter (Fixed 10%)'
            },
            {
                'stop_type': 'atr', 
                'atr_multiplier': 5.0, 
                'use_market_filter': True, 
                'use_volatility_sizing': True, 
                'name': '5x ATR + Market Filter (Volatility Sizing)'
            }
        ]
        
        results = {}
        
        for config in configs:
            print(f"\nTesting {config['name']}...")
            
            # Reset trade history
            self.trade_history = []
            
            # Process tickers
            trades = self.process_all_tickers(
                config['stop_type'], 
                config['atr_multiplier'], 
                market_data, 
                config['use_market_filter']
            )
            
            # Calculate performance with appropriate sizing
            performance = self.calculate_portfolio_performance(
                trades, 
                starting_equity=self.starting_capital,
                use_volatility_sizing=config['use_volatility_sizing'],
                market_data=market_data
            )
            
            results[config['name']] = {
                'performance': performance,
                'trades': trades,
                'config': config
            }
            
            print(f"  CAGR: {performance['cagr']:.2%}")
            print(f"  Max Drawdown: {performance['max_drawdown']:.2%}")
            print(f"  Sharpe: {performance['sharpe_ratio']:.2f}")
            print(f"  MAR Ratio: {performance['mar_ratio']:.2f}")
            print(f"  Total Trades: {performance['total_trades']}")
            
            # Check if goal is met
            goal_met = performance['mar_ratio'] > 1.0
            print(f"  MAR Ratio > 1.0: {'✅ YES' if goal_met else '❌ NO'}")
        
        # Generate comparison table
        self.print_volatility_sizing_comparison(results)
        
        # Generate comparison plot
        self.generate_volatility_sizing_plot(results)
        
        return results
    
    def print_volatility_sizing_comparison(self, results):
        """Print volatility sizing comparison table"""
        print("\n" + "="*90)
        print("VOLATILITY-ADJUSTED POSITION SIZING COMPARISON")
        print("="*90)
        
        print(f"{'Configuration':<45} {'CAGR':<10} {'Max DD':<10} {'Sharpe':<8} {'MAR':<8} {'Trades':<8} {'Goal':<8}")
        print("-" * 90)
        
        for name, result in results.items():
            perf = result['performance']
            goal_met = perf['mar_ratio'] > 1.0
            goal_text = '✅ YES' if goal_met else '❌ NO'
            
            print(f"{name:<45} {perf['cagr']:<10.2%} {perf['max_drawdown']:<10.2%} {perf['sharpe_ratio']:<8.2f} "
                  f"{perf['mar_ratio']:<8.2f} {perf['total_trades']:<8} {goal_text:<8}")
        
        print("="*90)
        
        # Analysis
        fixed = results['5x ATR + Market Filter (Fixed 10%)']['performance']
        vol_adj = results['5x ATR + Market Filter (Volatility Sizing)']['performance']
        
        print(f"\nVOLATILITY SIZING IMPACT ANALYSIS:")
        print("-" * 35)
        print(f"CAGR Change: {((vol_adj['cagr'] - fixed['cagr']) / abs(fixed['cagr']) * 100):+.1f}%")
        print(f"Drawdown Change: {((vol_adj['max_drawdown'] - fixed['max_drawdown']) / abs(fixed['max_drawdown']) * 100):+.1f}%")
        print(f"Sharpe Change: {((vol_adj['sharpe_ratio'] - fixed['sharpe_ratio']) / fixed['sharpe_ratio'] * 100):+.1f}%")
        print(f"MAR Ratio Change: {((vol_adj['mar_ratio'] - fixed['mar_ratio']) / abs(fixed['mar_ratio']) * 100):+.1f}%")
        print(f"Trade Count Change: {((vol_adj['total_trades'] - fixed['total_trades']) / fixed['total_trades'] * 100):+.1f}%")
        
        # Recommendation
        goal_met = vol_adj['mar_ratio'] > 1.0
        if goal_met:
            print(f"\n🎯 GOAL ACHIEVED! MAR Ratio > 1.0 with volatility sizing")
            print(f"   Recommendation: Use Volatility-Adjusted Position Sizing")
        else:
            print(f"\n⚠️ Goal not met. MAR Ratio: {vol_adj['mar_ratio']:.2f} (target: > 1.0)")
            if vol_adj['max_drawdown'] <= -0.25:
                print(f"   Consider: Tighten stops further or reduce risk per trade")
            if vol_adj['cagr'] <= 0.20:
                print(f"   Consider: Increase risk per trade or add momentum filter")
    
    def generate_volatility_sizing_plot(self, results):
        """Generate volatility sizing comparison plot"""
        try:
            import matplotlib.pyplot as plt
            import matplotlib.dates as mdates
            
            plt.figure(figsize=(12, 8))
            
            for name, result in results.items():
                perf = result['performance']
                if not perf['portfolio_history'].empty:
                    portfolio_values = perf['portfolio_history']['portfolio_value']
                    # Normalize to starting value
                    normalized = portfolio_values / self.starting_capital
                    
                    plt.plot(perf['portfolio_history'].index, normalized, 
                            label=name, linewidth=2, alpha=0.8)
            
            plt.title('VolatilityHunter: Volatility-Adjusted Position Sizing Comparison', fontsize=16, fontweight='bold')
            plt.xlabel('Date', fontsize=12)
            plt.ylabel('Portfolio Value (Normalized)', fontsize=12)
            plt.legend(loc='upper left')
            plt.grid(True, alpha=0.3)
            
            # Format x-axis
            plt.gca().xaxis.set_major_formatter(mdates.DateFormatter('%Y'))
            plt.gca().xaxis.set_major_locator(mdates.YearLocator())
            
            plt.tight_layout()
            plt.savefig('volatility_sizing_comparison.png', dpi=300, bbox_inches='tight')
            plt.close()
            
            print(f"\nVolatility sizing comparison plot saved to 'volatility_sizing_comparison.png'")
            
        except ImportError:
            print("\nWarning: matplotlib not available for plotting")
        except Exception as e:
            print(f"\nError generating plot: {e}")
    
    def _empty_performance(self):
        """Return empty performance metrics"""
        return {
            'total_return': 0,
            'cagr': 0,
            'max_drawdown': 0,
            'sharpe_ratio': 0,
            'win_rate': 0,
            'profit_factor': 0,
            'total_trades': 0,
            'portfolio_history': pd.DataFrame()
        }
    
    def run_stress_test(self, portfolio_history):
        """Simulate flash crash stress test"""
        if portfolio_history.empty:
            return portfolio_history
        
        stress_history = portfolio_history.copy()
        
        # Find a random date in the last 6 months
        last_date = portfolio_history.index[-1]
        crash_date = last_date - pd.Timedelta(days=np.random.randint(30, 180))
        
        # Find closest date in portfolio history
        if crash_date in portfolio_history.index:
            # Apply 10% crash
            pre_crash_value = stress_history.loc[crash_date, 'portfolio_value']
            stress_history.loc[crash_date:, 'portfolio_value'] *= 0.90
            
            logger.info(f"Flash crash simulated on {crash_date}: -10% from ${pre_crash_value:,.2f}")
        
        return stress_history
    
    def generate_report(self, performance, stress_history=None):
        """Generate performance report"""
        print("\n" + "="*60)
        print("VOLATILITYHUNTER BACKTEST RESULTS")
        print("="*60)
        
        print(f"\nPERFORMANCE METRICS:")
        print(f"  Total Return: {performance['total_return']:.2%}")
        print(f"  CAGR: {performance['cagr']:.2%}")
        print(f"  Max Drawdown: {performance['max_drawdown']:.2%}")
        print(f"  Sharpe Ratio: {performance['sharpe_ratio']:.2f}")
        print(f"  Win Rate: {performance['win_rate']:.2%}")
        print(f"  Profit Factor: {performance['profit_factor']:.2f}")
        print(f"  Total Trades: {performance['total_trades']}")
        
        if stress_history is not None:
            print(f"\nSTRESS TEST RESULTS:")
            original_final = performance['portfolio_history']['portfolio_value'].iloc[-1]
            stress_final = stress_history['portfolio_value'].iloc[-1]
            stress_impact = (stress_final - original_final) / original_final
            
            print(f"  Original Final Value: ${original_final:,.2f}")
            print(f"  Stress Test Final: ${stress_final:,.2f}")
            print(f"  Stress Impact: {stress_impact:.2%}")
        
        print("\n" + "="*60)
    
    def save_results(self, performance, stress_history=None):
        """Save results to files"""
        # Save trade history
        if self.trade_history:
            trades_df = pd.DataFrame(self.trade_history)
            trades_df.to_csv('trade_history.csv', index=False)
            logger.info("Trade history saved to trade_history.csv")
        
        # Save portfolio history
        if not performance['portfolio_history'].empty:
            performance['portfolio_history'].to_csv('portfolio_history.csv')
            logger.info("Portfolio history saved to portfolio_history.csv")
        
        # Save stress test results
        if stress_history is not None:
            stress_history.to_csv('stress_test_history.csv')
            logger.info("Stress test history saved to stress_test_history.csv")

def main():
    """Main execution function"""
    print("VolatilityHunter Backtesting Engine - Volatility-Adjusted Position Sizing")
    print("="*70)
    
    # Initialize backtest engine
    engine = BacktestEngine()
    
    # Run volatility sizing comparison
    results = engine.run_volatility_sizing_comparison()
    
    if results is None:
        print("❌ Volatility sizing comparison failed")
        return
    
    # Generate comparison report
    engine.generate_volatility_sizing_report(results)
    
    # Generate TradingView export for volatility sizing version
    print(f"\nGenerating TradingView export for Volatility Sizing version...")
    if '5x ATR + Market Filter (Volatility Sizing)' in results:
        engine.generate_tradingview_export(
            results['5x ATR + Market Filter (Volatility Sizing)']['trades'], 
            'tradingview_volatility_sized_trades.csv'
        )
    else:
        logger.warning("Volatility sizing results not found")
    
    # Save results for each configuration
    for name, result in results.items():
        print(f"\nSaving results for {name}...")
        
        # Save trade history
        if result['trades']:
            trades_df = pd.DataFrame(result['trades'])
            filename = f"trade_history_{name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct').replace('+', 'plus')}.csv"
            trades_df.to_csv(filename, index=False)
            logger.info(f"Trade history saved to {filename}")
        
        # Save portfolio history
        perf = result['performance']
        if not perf['portfolio_history'].empty:
            portfolio_df = perf['portfolio_history']
            filename = f"portfolio_history_{name.lower().replace(' ', '_').replace('(', '').replace(')', '').replace('%', 'pct').replace('+', 'plus')}.csv"
            portfolio_df.to_csv(filename)
            logger.info(f"Portfolio history saved to {filename}")
    
    print("\n" + "="*70)
    print("Volatility-Adjusted Position Sizing Comparison Complete!")
    print("="*70)
    
    # Summary of findings
    print("\nKEY FINDINGS:")
    print("-" * 20)
    
    if '5x ATR + Market Filter (Fixed 10%)' in results and '5x ATR + Market Filter (Volatility Sizing)' in results:
        fixed = results['5x ATR + Market Filter (Fixed 10%)']['performance']
        vol_adj = results['5x ATR + Market Filter (Volatility Sizing)']['performance']
        
        print(f"Fixed 10% Sizing:")
        print(f"  CAGR: {fixed['cagr']:.2%}")
        print(f"  Max Drawdown: {fixed['max_drawdown']:.2%}")
        print(f"  Sharpe: {fixed['sharpe_ratio']:.2f}")
        print(f"  MAR Ratio: {fixed['mar_ratio']:.2f}")
        print(f"  Total Trades: {fixed['total_trades']}")
        
        print(f"\nVolatility-Adjusted Sizing:")
        print(f"  CAGR: {vol_adj['cagr']:.2%}")
        print(f"  Max Drawdown: {vol_adj['max_drawdown']:.2%}")
        print(f"  Sharpe: {vol_adj['sharpe_ratio']:.2f}")
        print(f"  MAR Ratio: {vol_adj['mar_ratio']:.2f}")
        print(f"  Total Trades: {vol_adj['total_trades']}")
        
        # Check goal achievement
        goal_met = vol_adj['mar_ratio'] > 1.0
        print(f"\n🎯 GOAL STATUS: {'✅ ACHIEVED' if goal_met else '❌ NOT ACHIEVED'}")
        print(f"   Target: MAR Ratio > 1.0")
        print(f"   Actual: MAR Ratio = {vol_adj['mar_ratio']:.2f}")
        
        if goal_met:
            print(f"\n🏆 SUCCESS! Volatility sizing achieves MAR Ratio > 1.0!")
            print(f"   Recommendation: Use Volatility-Adjusted Position Sizing")
        else:
            print(f"\n⚠️ Goal not met. Consider:")
            if vol_adj['mar_ratio'] <= 1.0:
                print(f"   - Adjust risk per trade (currently 1%)")
                print(f"   - Tighten drawdown throttle thresholds")
            if vol_adj['max_drawdown'] <= -0.25:
                print(f"   - Further reduce position sizing during drawdowns")
    
    print(f"\nTradingView export generated for Volatility Sizing configuration")

if __name__ == "__main__":
    main()
