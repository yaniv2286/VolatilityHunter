import pandas as pd
import numpy as np

def calculate_realistic_drawdown_clean():
    """Calculate realistic drawdown by removing extreme outliers"""
    
    print('📉 REALISTIC DRAWDOWN CALCULATION')
    print('=' * 60)
    
    # Load trades
    v60_trades = pd.read_csv('backtest_results_v6_0.csv')
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    # Aggressive cleaning - remove extreme outliers
    def clean_trades(trades):
        """Remove extreme outliers from trade data"""
        # Filter out extreme losses/gains
        filtered = trades[
            (trades['profit_loss_pct'] > -50) &  # Max 50% loss per trade
            (trades['profit_loss_pct'] < 50)     # Max 50% gain per trade
        ]
        
        # Also filter out extreme dollar amounts
        filtered = filtered[
            (abs(filtered['profit_loss']) < 100000)  # Max $100k loss/gain per trade
        ]
        
        return filtered
    
    v60_clean = clean_trades(v60_trades)
    v65_clean = clean_trades(v65_trades)
    
    print(f'Original trades - v6.0: {len(v60_trades):,}, v6.5: {len(v65_trades):,}')
    print(f'Cleaned trades - v6.0: {len(v60_clean):,}, v6.5: {len(v65_clean):,}')
    print(f'v6.0 kept: {len(v60_clean)/len(v60_trades)*100:.1f}%')
    print(f'v6.5 kept: {len(v65_clean)/len(v65_trades)*100:.1f}%')
    
    def calculate_drawdown_simple(trades, starting_capital=100000):
        """Simple drawdown calculation"""
        if len(trades) == 0:
            return 0.0, starting_capital
        
        # Sort by date
        trades_sorted = trades.sort_values('entry_date')
        
        # Calculate running equity
        equity = [starting_capital]
        for _, trade in trades_sorted.iterrows():
            new_equity = equity[-1] + trade['profit_loss']
            equity.append(new_equity)
        
        equity_series = pd.Series(equity)
        
        # Calculate drawdown
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        
        return drawdown.min(), equity_series.iloc[-1]
    
    # Calculate drawdown
    v60_dd, v60_final = calculate_drawdown_simple(v60_clean)
    v65_dd, v65_final = calculate_drawdown_simple(v65_clean)
    
    print(f'\n📊 REALISTIC DRAWDOWN RESULTS')
    print('-' * 40)
    print(f'v6.0 Max Drawdown: {v60_dd:.2f}%')
    print(f'v6.5 Max Drawdown: {v65_dd:.2f}%')
    print(f'v6.0 Final Capital: ${v60_final:,.0f}')
    print(f'v6.5 Final Capital: ${v65_final:,.0f}')
    
    # Calculate basic metrics
    v60_wr = (v60_clean['profit_loss'] > 0).mean() * 100
    v65_wr = (v65_clean['profit_loss'] > 0).mean() * 100
    v60_avg_ret = v60_clean['profit_loss_pct'].mean()
    v65_avg_ret = v65_clean['profit_loss_pct'].mean()
    
    print(f'\n📈 CLEANED PERFORMANCE METRICS')
    print('-' * 40)
    print(f'v6.0 Win Rate: {v60_wr:.2f}%')
    print(f'v6.5 Win Rate: {v65_wr:.2f}%')
    print(f'v6.0 Avg Return: {v60_avg_ret:.2f}%')
    print(f'v6.5 Avg Return: {v65_avg_ret:.2f}%')
    
    # Estimate annual returns
    trades_per_year = 2000
    v60_annual = v60_avg_ret * trades_per_year / 100
    v65_annual = v65_avg_ret * trades_per_year / 100
    
    print(f'v6.0 Est. Annual Return: {v60_annual*100:.1f}%')
    print(f'v6.5 Est. Annual Return: {v65_annual*100:.1f}%')
    
    # Power Stock analysis
    v65_power = v65_clean[v65_clean['is_power_stock'] == True]
    v65_power_wr = (v65_power['profit_loss'] > 0).mean() * 100
    
    print(f'\n⚡ POWER STOCK METRICS')
    print('-' * 30)
    print(f'Power Stock Trades: {len(v65_power):,}')
    print(f'Power Stock Win Rate: {v65_power_wr:.2f}%')
    
    # Calculate improvement
    dd_change = ((v65_dd - v60_dd) / abs(v60_dd) * 100) if v60_dd != 0 else 0
    wr_change = ((v65_wr - v60_wr) / v60_wr * 100) if v60_wr != 0 else 0
    
    print(f'\n🏆 FINAL COMPARISON')
    print('=' * 70)
    print(f'Metric               v6.0            v6.5            Change')
    print('-' * 70)
    print(f'Max Drawdown         {v60_dd:<15.2f}% {v65_dd:<15.2f}% {dd_change:<+15.1f}%')
    print(f'Win Rate            {v60_wr:<15.2f}% {v65_wr:<15.2f}% {wr_change:<+15.1f}%')
    print(f'Avg Return/Trade    {v60_avg_ret:<15.2f}% {v65_avg_ret:<15.2f}% {((v65_avg_ret-v60_avg_ret)/abs(v60_avg_ret)*100):<+15.1f}%')
    print(f'Total Trades        {len(v60_clean):<15,} {len(v65_clean):<15,} {((len(v65_clean)-len(v60_clean))/len(v60_clean)*100):<+15.1f}%')
    print(f'Power Stock %       {"N/A":<15} {len(v65_power)/len(v65_clean)*100:<15.1f}% {"-":<15}')
    print(f'Power Stock WR      {"N/A":<15} {v65_power_wr:<15.2f}% {"-":<15}')
    
    print(f'\n🎯 REALISTIC CONCLUSION')
    print('-' * 40)
    if abs(v65_dd) < abs(v60_dd):
        print(f'✅ v6.5 has LOWER drawdown ({abs(v65_dd):.1f}% vs {abs(v60_dd):.1f}%)')
        print(f'✅ More stable strategy')
    else:
        print(f'⚠️  v6.5 has HIGHER drawdown ({abs(v65_dd):.1f}% vs {abs(v60_dd):.1f}%)')
        print(f'⚠️  More volatile but captures more opportunities')
    
    if v65_wr > v60_wr:
        print(f'✅ v6.5 has better win rate ({v65_wr:.1f}% vs {v60_wr:.1f}%)')
    
    print(f'✅ v6.5 captures {((len(v65_clean)-len(v60_clean))/len(v60_clean)*100):+.1f}% more trades')
    print(f'✅ Power Stock strategy: {v65_power_wr:.1f}% win rate on {len(v65_power):,} trades')
    
    # Risk assessment
    print(f'\n⚖️ RISK ASSESSMENT')
    print('-' * 30)
    if abs(v60_dd) < 20:
        print(f'v6.0: LOW RISK ({abs(v60_dd):.1f}% max DD)')
    elif abs(v60_dd) < 50:
        print(f'v6.0: MEDIUM RISK ({abs(v60_dd):.1f}% max DD)')
    else:
        print(f'v6.0: HIGH RISK ({abs(v60_dd):.1f}% max DD)')
    
    if abs(v65_dd) < 20:
        print(f'v6.5: LOW RISK ({abs(v65_dd):.1f}% max DD)')
    elif abs(v65_dd) < 50:
        print(f'v6.5: MEDIUM RISK ({abs(v65_dd):.1f}% max DD)')
    else:
        print(f'v6.5: HIGH RISK ({abs(v65_dd):.1f}% max DD)')

if __name__ == "__main__":
    calculate_realistic_drawdown_clean()
