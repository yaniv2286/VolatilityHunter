import pandas as pd
import numpy as np
from datetime import datetime

def final_audit():
    """Final audit script for VolatilityHunter v6.5 Power Hunter"""
    
    print('🏛️ ARCHITECT FINAL AUDIT - VOLATILITYHUNTER v6.5')
    print('=' * 80)
    
    # Load the data
    print('📊 Loading backtest results...')
    trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'Total trades: {len(trades):,}')
    
    # Convert dates
    trades['entry_date'] = pd.to_datetime(trades['entry_date'])
    trades['exit_date'] = pd.to_datetime(trades['exit_date'])
    
    # 1. TRADINGVIEW IMPORT - TOP 100 PROFITABLE TRADES
    print('\n🎯 1. TRADINGVIEW IMPORT - TOP 100 MOST PROFITABLE TRADES')
    print('-' * 60)
    
    # Get top 100 most profitable trades
    top_trades = trades.nlargest(100, 'profit_loss')
    
    # Prepare TradingView format
    tradingview_data = []
    for _, trade in top_trades.iterrows():
        # Format ticker for TradingView (add exchange prefix)
        ticker = trade['ticker'].upper()
        
        # Simple exchange mapping (most are NASDAQ)
        if len(ticker) <= 4 and ticker.isalpha():
            symbol = f'NASDAQ:{ticker}'
        else:
            symbol = f'NYSE:{ticker}'
        
        tradingview_data.append({
            'Symbol': symbol,
            'Side': 'buy',
            'Qty': int(trade['shares']),
            'Fill Price': round(trade['entry_price'], 2),
            'Closing Time': trade['entry_date'].strftime('%Y-%m-%d')
        })
    
    # Save TradingView file
    tradingview_df = pd.DataFrame(tradingview_data)
    tradingview_df.to_csv('tradingview_upload.csv', index=False)
    
    print(f'✅ Created tradingview_upload.csv with {len(tradingview_df)} top trades')
    print(f'✅ Total P&L of top 100 trades: ${top_trades["profit_loss"].sum():,.0f}')
    print(f'✅ Average P&L per top trade: ${top_trades["profit_loss"].mean():,.0f}')
    
    # 2. 10-SLOT PORTFOLIO REALITY
    print('\n💼 2. 10-SLOT PORTFOLIO REALITY - $100K ACCOUNT')
    print('-' * 60)
    
    # Sort trades by entry date
    sorted_trades = trades.sort_values('entry_date')
    
    # Simulate 10-slot portfolio
    initial_capital = 100000
    current_capital = initial_capital
    max_positions = 10
    open_positions = []
    executed_trades = []
    equity_curve = [initial_capital]
    equity_dates = [sorted_trades['entry_date'].min()]
    
    print(f'Simulating {len(sorted_trades):,} trades with {max_positions} max positions...')
    
    for idx, (_, trade) in enumerate(sorted_trades.iterrows()):
        # Check if we have open slots
        if len(open_positions) < max_positions:
            # Calculate trade cost (shares * entry_price)
            trade_cost = trade['shares'] * trade['entry_price']
            
            if current_capital >= trade_cost:
                # Add to positions
                position = {
                    'trade': trade,
                    'entry_date': trade['entry_date'],
                    'entry_cost': trade_cost,
                    'shares': trade['shares']
                }
                open_positions.append(position)
                current_capital -= trade_cost
                executed_trades.append(trade)
                
                # Update equity
                total_equity = current_capital + sum(pos['trade']['profit_loss'] for pos in open_positions)
                equity_curve.append(total_equity)
                equity_dates.append(trade['entry_date'])
        
        # Check for exits
        positions_to_remove = []
        for i, pos in enumerate(open_positions):
            if pos['trade']['exit_date'] <= trade['entry_date']:
                # Close position
                exit_value = pos['trade']['shares'] * pos['trade']['exit_price']
                current_capital += exit_value
                positions_to_remove.append(i)
                
                # Update equity
                total_equity = current_capital + sum(open_positions[j]['trade']['profit_loss'] for j in range(len(open_positions)) if j not in positions_to_remove)
                equity_curve.append(total_equity)
                equity_dates.append(pos['trade']['exit_date'])
        
        # Remove closed positions
        for i in reversed(positions_to_remove):
            del open_positions[i]
        
        # Progress update
        if (idx + 1) % 10000 == 0:
            print(f'  Processed {idx+1:,}/{len(sorted_trades):,} trades, {len(executed_trades)} executed, {len(open_positions)} open')
    
    print(f'✅ Simulation complete!')
    print(f'✅ Executed trades: {len(executed_trades):,} out of {len(sorted_trades):,} ({len(executed_trades)/len(sorted_trades)*100:.1f}%)')
    print(f'✅ Final capital: ${current_capital:,.0f}')
    
    # Calculate performance metrics
    equity_series = pd.Series(equity_curve, index=equity_dates)
    
    # CAGR calculation
    if len(equity_series) > 1:
        start_value = equity_series.iloc[0]
        end_value = equity_series.iloc[-1]
        total_days = (equity_series.index[-1] - equity_series.index[0]).days
        years = total_days / 365.25
        
        if years > 0 and start_value > 0:
            cagr = ((end_value / start_value) ** (1/years) - 1) * 100
        else:
            cagr = 0
    else:
        cagr = 0
    
    # Max Drawdown calculation
    running_max = equity_series.expanding().max()
    drawdown = (equity_series - running_max) / running_max * 100
    max_drawdown = drawdown.min()
    
    # Additional metrics
    total_return = (current_capital - initial_capital) / initial_capital * 100
    win_rate = (pd.DataFrame(executed_trades)['profit_loss'] > 0).mean() * 100
    
    print(f'\n📈 10-SLOT PORTFOLIO METRICS')
    print('=' * 60)
    print(f'Initial Capital: ${initial_capital:,}')
    print(f'Final Capital: ${current_capital:,}')
    print(f'Total Return: {total_return:.2f}%')
    print(f'CAGR: {cagr:.2f}%')
    print(f'Max Drawdown: {max_drawdown:.2f}%')
    print(f'Win Rate: {win_rate:.2f}%')
    print(f'Executed Trades: {len(executed_trades):,}')
    print(f'Trades Discarded: {len(sorted_trades) - len(executed_trades):,}')
    
    # 3. THE WINNER'S CIRCLE
    print('\n🏆 3. THE WINNER\'S CIRCLE - SINGLE BEST TRADE')
    print('-' * 60)
    
    # Find the most profitable trade
    winner = trades.loc[trades['profit_loss'].idxmax()]
    
    print(f'🥇 MOST PROFITABLE TRADE (26-YEAR HISTORY):')
    print(f'   Ticker: {winner["ticker"].upper()}')
    print(f'   Entry Date: {winner["entry_date"].date()}')
    print(f'   Entry Price: ${winner["entry_price"]:.2f}')
    print(f'   Exit Date: {winner["exit_date"].date()}')
    print(f'   Exit Price: ${winner["exit_price"]:.2f}')
    print(f'   Shares: {int(winner["shares"]):,}')
    print(f'   P&L: ${winner["profit_loss"]:,.0f}')
    print(f'   P&L %: {winner["profit_loss_pct"]:.2f}%')
    print(f'   Duration: {winner["duration"]} days')
    print(f'   Exit Reason: {winner["exit_reason"]}')
    print(f'   Power Stock: {winner["is_power_stock"]}')
    
    # Additional winner analysis
    print(f'\n🎯 WINNER\'S CIRCLE ANALYSIS:')
    print('-' * 40)
    
    # Top 5 trades
    top_5 = trades.nlargest(5, 'profit_loss')
    print(f'Top 5 trades total P&L: ${top_5["profit_loss"].sum():,.0f}')
    
    # Power Stock winners
    power_winners = trades[trades['is_power_stock'] == True].nlargest(3, 'profit_loss')
    if len(power_winners) > 0:
        print(f'Best Power Stock trade: ${power_winners["profit_loss"].iloc[0]:,.0f}')
    
    # Exit reason analysis
    exit_analysis = trades.groupby('exit_reason')['profit_loss'].agg(['count', 'mean', 'sum']).sort_values('mean', ascending=False)
    print(f'\n📊 EXIT REASON PERFORMANCE:')
    print(exit_analysis.round(2))
    
    # Final summary
    print(f'\n🎯 ARCHITECT FINAL SUMMARY')
    print('=' * 80)
    print(f'📁 Files Created:')
    print(f'   • tradingview_upload.csv - Top 100 trades for chart verification')
    print(f'   • backtest_results_v6_5.csv - Full dataset ({len(trades):,} trades)')
    print('')
    print(f'💼 10-Slot Portfolio Performance:')
    print(f'   • CAGR: {cagr:.2f}%')
    print(f'   • Max Drawdown: {max_drawdown:.2f}%')
    print(f'   • Win Rate: {win_rate:.2f}%')
    print(f'   • Capital: ${initial_capital:,} → ${current_capital:,}')
    print('')
    print(f'🏆 Best Trade:')
    print(f'   • {winner["ticker"].upper()}: ${winner["profit_loss"]:,.0f} ({winner["profit_loss_pct"]:.2f}%)')
    print(f'   • Exit: {winner["exit_reason"]}')
    print('')
    print(f'✅ VolatilityHunter v6.5 Power Hunter - AUDIT COMPLETE')

if __name__ == "__main__":
    final_audit()
