#!/usr/bin/env python3
"""
🔥 REAL POWER STOCK V7.2 BACKTEST - NO MORE MOCKS!
Using the actual Power Stock v7.2 strategy with corrected entry zone (32-80)
"""

import sys
import os
import pandas as pd
import numpy as np
from datetime import datetime
import time
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_loader import get_stock_data
from src.strategy_v7_2 import analyze_stock_v7_2, add_indicators_v7_2, calculate_position_size_v7_2

class RealPowerStockBacktester:
    """Real Power Stock v7.2 backtester with actual strategy"""
    
    def __init__(self, initial_capital=100000):
        self.initial_capital = initial_capital
        self.cash = initial_capital
        self.positions = {}
        
    def run_single_stock_backtest(self, ticker):
        """Run real Power Stock v7.2 backtest on single stock"""
        try:
            # Load real data
            df = get_stock_data(ticker)
            if df is None or len(df) < 252:
                return None
            
            print(f"📊 {ticker}: Loaded {len(df)} days of data")
            
            # Add indicators
            df = add_indicators_v7_2(df)
            
            # Generate signals using REAL Power Stock v7.2 strategy
            signals = []
            positions = []
            
            for i in range(200, len(df)):  # Start after indicators are stable
                current_data = df.iloc[:i+1]  # Data up to current day
                
                # Use REAL Power Stock v7.2 analysis
                signal_result = analyze_stock_v7_2(current_data, ticker)
                
                if signal_result and signal_result.get('signal') == 'BUY':
                    signals.append((df.index[i], 'BUY', signal_result))
                    
                    # Calculate position size using Power Stock rules
                    price = current_data['Close'].iloc[-1]  # Use 'Close' instead of 'adjClose'
                    stop_loss = price * 0.95  # 5% stop loss for backtesting
                    
                    quantity = calculate_position_size_v7_2(
                        self.initial_capital, price, stop_loss
                    )
                    
                    if quantity > 0:
                        positions.append({
                            'date': df.index[i],
                            'ticker': ticker,
                            'action': 'BUY',
                            'quantity': quantity,
                            'price': price,
                            'value': quantity * price,
                            'signal': signal_result
                        })
                
                elif signal_result and signal_result.get('signal') == 'SELL':
                    signals.append((df.index[i], 'SELL', signal_result))
                    
                    # Check if we have position to sell
                    if ticker in self.positions and self.positions[ticker] > 0:
                        price = current_data['Close'].iloc[-1]  # Use 'Close' instead of 'adjClose'
                        quantity = self.positions[ticker]
                        
                        positions.append({
                            'date': df.index[i],
                            'ticker': ticker,
                            'action': 'SELL',
                            'quantity': quantity,
                            'price': price,
                            'value': quantity * price,
                            'signal': signal_result
                        })
            
            # Calculate returns and performance
            if not positions:
                print(f"  📊 {ticker}: No trades executed")
                return {
                    'ticker': ticker,
                    'total_return': 0.0,
                    'cagr': 0.0,
                    'max_drawdown': 0.0,
                    'sharpe_ratio': 0.0,
                    'total_trades': 0,
                    'final_equity': self.initial_capital,
                    'signals': len(signals),
                    'positions': len(positions)
                }
            
            # Calculate equity curve
            equity_curve = []
            running_equity = self.initial_capital
            current_positions = {}
            
            for i in range(200, len(df)):
                date = df.index[i]
                current_price = df['Close'].iloc[i]  # Use 'Close' instead of 'adjClose'
                
                # Update position values
                position_value = 0
                if ticker in self.positions:
                    position_value = self.positions[ticker] * current_price
                
                running_equity = self.cash + position_value
                equity_curve.append(running_equity)
                
                # Process trades for this date
                for pos in positions:
                    if pos['date'] == date:
                        if pos['action'] == 'BUY':
                            cost = pos['value']
                            if self.cash >= cost:
                                self.cash -= cost
                                self.positions[ticker] = self.positions.get(ticker, 0) + pos['quantity']
                        elif pos['action'] == 'SELL':
                            proceeds = pos['value']
                            self.cash += proceeds
                            self.positions[ticker] = 0
            
            # Calculate performance metrics
            if len(equity_curve) > 1:
                equity_series = pd.Series(equity_curve)
                returns = equity_series.pct_change().dropna()
                
                # Total return
                final_equity = equity_curve[-1] if equity_curve else self.initial_capital
                total_return = (final_equity - self.initial_capital) / self.initial_capital
                
                # CAGR (Compound Annual Growth Rate)
                days = len(equity_curve)
                years = days / 252  # Trading days per year
                cagr = (final_equity / self.initial_capital) ** (1/years) - 1 if years > 0 else 0
                
                # Max drawdown
                peak = equity_series.expanding().max()
                drawdown = (equity_series - peak) / peak
                max_drawdown = drawdown.min()
                
                # Sharpe ratio
                sharpe_ratio = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
            else:
                final_equity = self.initial_capital
                total_return = 0
                cagr = 0
                max_drawdown = 0
                sharpe_ratio = 0
            
            print(f"  ✅ {ticker}: {cagr*100:.2f}% CAGR | {max_drawdown*100:.2f}% DD | {len(positions)} trades")
            
            return {
                'ticker': ticker,
                'total_return': total_return,
                'cagr': cagr,
                'max_drawdown': max_drawdown,
                'sharpe_ratio': sharpe_ratio,
                'total_trades': len(positions),
                'final_equity': final_equity,
                'signals': len(signals),
                'positions': len(positions),
                'buy_signals': len([s for s in signals if s[1] == 'BUY']),
                'sell_signals': len([s for s in signals if s[1] == 'SELL'])
            }
            
        except Exception as e:
            print(f"  ❌ {ticker}: Error - {e}")
            return None
    
    def run_universe_backtest(self, tickers):
        """Run backtest on universe of stocks"""
        print("🔥 REAL POWER STOCK V7.2 BACKTEST")
        print("=" * 60)
        print("🎯 Using actual Power Stock v7.2 strategy")
        print("📊 Entry Zone: Stochastic 32-80 (corrected)")
        print("🚀 Real crossover, volume, trend checks")
        print("💰 Real position sizing with 1% risk")
        print("=" * 60)
        
        results = []
        failed_stocks = []
        
        for i, ticker in enumerate(tickers):
            print(f"📈 Processing {ticker} ({i+1}/{len(tickers)})...")
            
            result = self.run_single_stock_backtest(ticker)
            if result:
                results.append(result)
            else:
                failed_stocks.append(ticker)
            
            # Reset portfolio for next stock
            self.cash = self.initial_capital
            self.positions = {}
        
        # Calculate aggregate metrics
        if results:
            avg_cagr = np.mean([r['cagr'] for r in results])
            avg_drawdown = np.mean([r['max_drawdown'] for r in results])
            avg_sharpe = np.mean([r['sharpe_ratio'] for r in results])
            total_trades = sum([r['total_trades'] for r in results])
            avg_return = np.mean([r['total_return'] for r in results])
            
            # Top performers
            top_performers = sorted(results, key=lambda x: x['cagr'], reverse=True)[:10]
            
            print(f"\n🎉 REAL POWER STOCK V7.2 RESULTS!")
            print("=" * 60)
            print(f"📊 Universe Size: {len(tickers)} stocks")
            print(f"✅ Successful: {len(results)} stocks")
            print(f"❌ Failed: {len(failed_stocks)} stocks")
            print(f"📊 Success Rate: {len(results)/len(tickers)*100:.1f}%")
            print(f"\n📈 AGGREGATE PERFORMANCE:")
            print(f"🎯 Average CAGR: {avg_cagr*100:.2f}%")
            print(f"📉 Average Max DD: {avg_drawdown*100:.2f}%")
            print(f"📊 Average Sharpe: {avg_sharpe:.2f}")
            print(f"📊 Average Return: {avg_return*100:.2f}%")
            print(f"📊 Total Trades: {total_trades}")
            
            print(f"\n🏆 TOP 10 PERFORMERS:")
            for i, result in enumerate(top_performers, 1):
                print(f"  {i}. {result['ticker']}: {result['cagr']*100:.2f}% CAGR | {result['total_trades']} trades")
            
            return results
        else:
            print("❌ No successful backtests")
            return []

def main():
    """Run real Power Stock v7.2 backtest"""
    
    # Load focused universe for quality results
    focused_universe = [
        "AAPL", "MSFT", "GOOGL", "AMZN", "TSLA", "NVDA", "META", "NFLX",
        "AMD", "INTC", "JPM", "BAC", "WMT", "HD", "PG", "UNH", "MA", "V",
        "DIS", "CRM", "PYPL", "ADBE", "CSCO", "CMCSA", "PEP", "COST",
        "TMO", "AVGO", "TXN", "ABT", "DHR", "VZ", "NOW", "QCOM", "UPS",
        "IBM", "INTU", "GS", "CAT", "RTX", "LMT", "HON", "UNP", "BA",
        "GE", "MMM", "DE", "JNJ", "PFE", "KO", "MDT", "XOM", "CVX"
    ]
    
    backtester = RealPowerStockBacktester(initial_capital=100000)
    results = backtester.run_universe_backtest(focused_universe)
    
    if results:
        print(f"\n🔥 POWER STOCK V7.2 BACKTEST COMPLETE!")
        print(f"📊 Real strategy with corrected entry zone (32-80)")
        print(f"🚀 Ready for production deployment!")

if __name__ == "__main__":
    main()
