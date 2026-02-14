import pandas as pd

def explain_cagr_and_drawdown():
    """Explain CAGR and Drawdown with simple examples"""
    
    print('📚 EXPLAINING CAGR AND MAX DRAWDOWN')
    print('=' * 60)
    
    print('\n📈 CAGR (Compound Annual Growth Rate)')
    print('-' * 40)
    print('CAGR answers: "What was my average yearly return?"')
    print('')
    print('Example: Start $100,000 → End $200,000 in 25 years')
    print('CAGR = (200,000/100,000)^(1/25) - 1 = 2.8% per year')
    print('')
    print('This means your money grew by 2.8% each year on average,')
    print('compounding over 25 years to double your investment.')
    
    print('\n📉 Max Drawdown')
    print('-' * 40)
    print('Max Drawdown answers: "What was my biggest loss?"')
    print('')
    print('Example: Portfolio goes $100k → $150k → $80k → $120k')
    print('Peak: $150,000')
    print('Trough: $80,000')
    print('Max Drawdown = (80,000 - 150,000) / 150,000 = -46.7%')
    print('')
    print('This means at your worst point, you were down 46.7%')
    print('from your highest portfolio value.')
    
    print('\n🔍 YOUR VOLATILITYHUNTER ISSUE')
    print('-' * 40)
    
    # Load trades to show the problem
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print('The problem is POSITION SIZING:')
    print(f'• Average shares per trade: {v65_trades["shares"].mean():.0f}')
    print(f'• Maximum shares per trade: {v65_trades["shares"].max():.0f}')
    print(f'• Minimum shares per trade: {v65_trades["shares"].min():.0f}')
    print('')
    print('This creates unrealistic P&L:')
    print(f'• Average P&L per trade: ${v65_trades["profit_loss"].mean():,.0f}')
    print(f'• Largest loss: ${v65_trades["profit_loss"].min():,.0f}')
    print('')
    print('When you calculate CAGR with these massive numbers:')
    print('• Starting: $100,000')
    print(f'• Total P&L: ${v65_trades["profit_loss"].sum():,.0f}')
    print('• Ending: $-58 billion (negative!)')
    print('')
    print('This breaks the CAGR formula and gives crazy results.')
    
    print('\n🎯 REALISTIC METRICS (Fixed Position Sizing)')
    print('-' * 40)
    
    # Calculate with fixed 100 shares per trade
    v65_trades['realistic_pnl'] = v65_trades['profit_loss_pct'] / 100 * v65_trades['entry_price'] * 100
    
    total_realistic_pnl = v65_trades['realistic_pnl'].sum()
    starting_capital = 100000
    ending_capital = starting_capital + total_realistic_pnl
    years = 25.1
    
    realistic_cagr = ((ending_capital / starting_capital) ** (1/years) - 1) * 100
    
    print(f'With 100 shares per trade (more realistic):')
    print(f'• Total P&L: ${total_realistic_pnl:,.0f}')
    print(f'• Starting Capital: ${starting_capital:,}')
    print(f'• Ending Capital: ${ending_capital:,.0f}')
    print(f'• Realistic CAGR: {realistic_cagr:.2f}%')
    
    print('\n📊 WHAT WE KNOW FOR SURE')
    print('-' * 40)
    print('✅ v6.5 captures 90.2% more trades than v6.0')
    print('✅ v6.5 win rate: 45.59% vs v6.0: 32.11% (+42% improvement)')
    print('✅ v6.5 Power Stock win rate: 68.34% (excellent!)')
    print('✅ Power Stock strategy: 67,428 out of 102,483 trades')
    print('')
    print('❓ CAGR & Drawdown: Need position sizing fix to be accurate')
    
    print('\n💡 SOLUTION')
    print('-' * 40)
    print('Fix the position sizing in crucible_engine.py:')
    print('• Current: shares = 1000 / (3 * ATR) (can be huge)')
    print('• Should be: shares = min(max_shares, risk_amount / stop_distance)')
    print('• Or use fixed shares for backtesting (100-1000 shares)')
    print('')
    print('Once position sizing is fixed, CAGR and Drawdown will be realistic.')

if __name__ == "__main__":
    explain_cagr_and_drawdown()
