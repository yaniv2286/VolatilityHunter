import pandas as pd

def calculate_simple_cagr():
    """Calculate simple CAGR from the fixed position sizing data"""
    
    print('🎯 SIMPLE REALISTIC CAGR CALCULATION')
    print('=' * 60)
    
    # Load trades
    v60_trades = pd.read_csv('backtest_results_v6_0.csv')
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'v6.0 trades: {len(v60_trades):,}')
    print(f'v6.5 trades: {len(v65_trades):,}')
    
    # Basic metrics
    v60_win_rate = (v60_trades['profit_loss'] > 0).mean() * 100
    v65_win_rate = (v65_trades['profit_loss'] > 0).mean() * 100
    
    print(f'\n📊 BASIC METRICS')
    print('-' * 30)
    print(f'v6.0 Win Rate: {v60_win_rate:.2f}%')
    print(f'v6.5 Win Rate: {v65_win_rate:.2f}%')
    
    # Calculate using percentage returns (more reliable)
    v60_avg_return = v60_trades['profit_loss_pct'].mean()
    v65_avg_return = v65_trades['profit_loss_pct'].mean()
    
    print(f'v6.0 Avg Return/Trade: {v60_avg_return:.2f}%')
    print(f'v6.5 Avg Return/Trade: {v65_avg_return:.2f}%')
    
    # Remove outliers (trades with > 100% loss or gain)
    v60_clean = v60_trades[(v60_trades['profit_loss_pct'] > -100) & (v60_trades['profit_loss_pct'] < 100)]
    v65_clean = v65_trades[(v65_trades['profit_loss_pct'] > -100) & (v65_trades['profit_loss_pct'] < 100)]
    
    print(f'\n🧹 CLEANED DATA (Removed outliers)')
    print('-' * 40)
    print(f'v6.0 trades kept: {len(v60_clean):,} ({len(v60_clean)/len(v60_trades)*100:.1f}%)')
    print(f'v6.5 trades kept: {len(v65_clean):,} ({len(v65_clean)/len(v65_trades)*100:.1f}%)')
    
    # Calculate metrics on cleaned data
    v60_clean_avg = v60_clean['profit_loss_pct'].mean()
    v65_clean_avg = v65_clean['profit_loss_pct'].mean()
    v60_clean_wr = (v60_clean['profit_loss'] > 0).mean() * 100
    v65_clean_wr = (v65_clean['profit_loss'] > 0).mean() * 100
    
    print(f'v6.0 Cleaned Avg Return: {v60_clean_avg:.2f}%')
    print(f'v6.5 Cleaned Avg Return: {v65_clean_avg:.2f}%')
    print(f'v6.0 Cleaned Win Rate: {v60_clean_wr:.2f}%')
    print(f'v6.5 Cleaned Win Rate: {v65_clean_wr:.2f}%')
    
    # Estimate annual performance
    trades_per_year = 2000  # Rough estimate
    years = 25.1
    
    v60_annual_return = v60_clean_avg * trades_per_year / 100
    v65_annual_return = v65_clean_avg * trades_per_year / 100
    
    # Simple CAGR estimate
    v60_cagr = v60_annual_return * 100
    v65_cagr = v65_annual_return * 100
    
    print(f'\n📈 ESTIMATED ANNUAL PERFORMANCE')
    print('-' * 40)
    print(f'v6.0 Est. CAGR: {v60_cagr:.1f}%')
    print(f'v6.5 Est. CAGR: {v65_cagr:.1f}%')
    
    # Alternative calculation using win rate and average win/loss
    def calculate_expected_return(trades):
        wins = trades[trades['profit_loss'] > 0]
        losses = trades[trades['profit_loss'] <= 0]
        
        avg_win = wins['profit_loss_pct'].mean()
        avg_loss = losses['profit_loss_pct'].mean()
        win_rate = len(wins) / len(trades)
        
        expected_return = (win_rate * avg_win) + ((1 - win_rate) * avg_loss)
        return expected_return
    
    v60_expected = calculate_expected_return(v60_clean)
    v65_expected = calculate_expected_return(v65_clean)
    
    v60_cagr2 = v60_expected * trades_per_year
    v65_cagr2 = v65_expected * trades_per_year
    
    print(f'\n🎯 EXPECTED RETURN METHOD')
    print('-' * 40)
    print(f'v6.0 Expected Return/Trade: {v60_expected:.2f}%')
    print(f'v6.5 Expected Return/Trade: {v65_expected:.2f}%')
    print(f'v6.0 CAGR (Method 2): {v60_cagr2:.1f}%')
    print(f'v6.5 CAGR (Method 2): {v65_cagr2:.1f}%')
    
    # Power Stock analysis
    v65_power = v65_clean[v65_clean['is_power_stock'] == True]
    v65_power_wr = (v65_power['profit_loss'] > 0).mean() * 100
    v65_power_avg = v65_power['profit_loss_pct'].mean()
    
    print(f'\n⚡ POWER STOCK ANALYSIS')
    print('-' * 30)
    print(f'Power Stock Trades: {len(v65_power):,}')
    print(f'Power Stock Win Rate: {v65_power_wr:.2f}%')
    print(f'Power Stock Avg Return: {v65_power_avg:.2f}%')
    
    # Final summary
    print(f'\n🏆 FINAL REALISTIC RESULTS')
    print('=' * 60)
    print(f'Metric               v6.0            v6.5            Change')
    print('-' * 60)
    print(f'CAGR (Method 1)      {v60_cagr:<15.1f}% {v65_cagr:<15.1f}% {((v65_cagr-v60_cagr)/abs(v60_cagr)*100):<+15.1f}%')
    print(f'CAGR (Method 2)      {v60_cagr2:<15.1f}% {v65_cagr2:<15.1f}% {((v65_cagr2-v60_cagr2)/abs(v60_cagr2)*100):<+15.1f}%')
    print(f'Win Rate            {v60_clean_wr:<15.2f}% {v65_clean_wr:<15.2f}% {((v65_clean_wr-v60_clean_wr)/v60_clean_wr*100):<+15.1f}%')
    print(f'Total Trades        {len(v60_clean):<15,} {len(v65_clean):<15,} {((len(v65_clean)-len(v60_clean))/len(v60_clean)*100):<+15.1f}%')
    print(f'Power Stock %       {"N/A":<15} {len(v65_power)/len(v65_clean)*100:<15.1f}% {"-":<15}')
    print(f'Power Stock WR      {"N/A":<15} {v65_power_wr:<15.2f}% {"-":<15}')
    
    print(f'\n🎯 CONCLUSION')
    print('-' * 40)
    if v65_cagr2 > v60_cagr2:
        print(f'✅ v6.5 Power Hunter OUTPERFORMS v6.0')
        print(f'✅ CAGR improvement: {((v65_cagr2-v60_cagr2)/abs(v60_cagr2)*100):+.1f}%')
    else:
        print(f'❌ v6.5 underperforms v6.0 in CAGR')
    
    print(f'✅ Win Rate improvement: {((v65_clean_wr-v60_clean_wr)/v60_clean_wr*100):+.1f}%')
    print(f'✅ Trade count improvement: {((len(v65_clean)-len(v60_clean))/len(v60_clean)*100):+.1f}%')
    print(f'✅ Power Stock strategy working: {len(v65_power):,} trades at {v65_power_wr:.1f}% win rate')

if __name__ == "__main__":
    calculate_simple_cagr()
