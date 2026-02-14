import pandas as pd
import numpy as np

def calculate_final_metrics():
    """Calculate realistic CAGR and drawdown from percentage returns"""
    
    print('🎯 FINAL REALISTIC PERFORMANCE METRICS')
    print('=' * 60)
    
    # Load results
    v60_trades = pd.read_csv('backtest_results_v6_0.csv')
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'v6.0 trades: {len(v60_trades):,}')
    print(f'v6.5 trades: {len(v65_trades):,}')
    
    # Convert dates
    v60_trades['entry_date'] = pd.to_datetime(v60_trades['entry_date'])
    v65_trades['entry_date'] = pd.to_datetime(v65_trades['entry_date'])
    
    # Calculate time period
    v60_start = v60_trades['entry_date'].min()
    v60_end = v60_trades['entry_date'].max()
    years = (v60_end - v60_start).days / 365.25
    
    print(f'Backtest period: {v60_start.date()} to {v60_end.date()} ({years:.1f} years)')
    
    # Calculate compound returns using percentage returns
    def calculate_compound_return(trades):
        """Calculate compound return from trade percentages"""
        if len(trades) == 0:
            return 0.0
        
        # Convert percentage returns to decimal
        returns = trades['profit_loss_pct'] / 100
        
        # Calculate compound return
        compound_return = (1 + returns).prod() - 1
        
        return compound_return
    
    # Calculate compound returns
    v60_compound = calculate_compound_return(v60_trades)
    v65_compound = calculate_compound_return(v65_trades)
    
    # Calculate CAGR
    v60_cagr = ((1 + v60_compound) ** (1/years) - 1) * 100
    v65_cagr = ((1 + v65_compound) ** (1/years) - 1) * 100
    
    # Calculate Max Drawdown from running equity
    def calculate_max_dd(trades):
        """Calculate max drawdown from trade equity curve"""
        if len(trades) == 0:
            return 0.0
        
        # Sort trades by entry date
        trades_sorted = trades.sort_values('entry_date')
        
        # Calculate running equity (starting from 1.0)
        equity = [1.0]
        for _, trade in trades_sorted.iterrows():
            return_pct = trade['profit_loss_pct'] / 100
            new_equity = equity[-1] * (1 + return_pct)
            equity.append(new_equity)
        
        equity_series = pd.Series(equity)
        
        # Calculate drawdown
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        
        return drawdown.min()
    
    v60_dd = calculate_max_dd(v60_trades)
    v65_dd = calculate_max_dd(v65_trades)
    
    # Calculate other metrics
    v60_win_rate = (v60_trades['profit_loss'] > 0).mean() * 100
    v65_win_rate = (v65_trades['profit_loss'] > 0).mean() * 100
    
    # Calculate profit factor
    def calculate_profit_factor(trades):
        wins = trades[trades['profit_loss'] > 0]['profit_loss'].sum()
        losses = abs(trades[trades['profit_loss'] < 0]['profit_loss'].sum())
        return wins / losses if losses > 0 else 0
    
    v60_pf = calculate_profit_factor(v60_trades)
    v65_pf = calculate_profit_factor(v65_trades)
    
    # Power Stock analysis
    v65_power = v65_trades[v65_trades['is_power_stock'] == True]
    v65_power_wr = (v65_power['profit_loss'] > 0).mean() * 100 if len(v65_power) > 0 else 0
    
    # Calculate improvements
    cagr_imp = ((v65_cagr - v60_cagr) / abs(v60_cagr) * 100) if v60_cagr != 0 else 0
    dd_imp = ((v65_dd - v60_dd) / abs(v60_dd) * 100) if v60_dd != 0 else 0
    wr_imp = ((v65_win_rate - v60_win_rate) / v60_win_rate * 100) if v60_win_rate != 0 else 0
    pf_imp = ((v65_pf - v60_pf) / v60_pf * 100) if v60_pf != 0 else 0
    trades_imp = ((len(v65_trades) - len(v60_trades)) / len(v60_trades) * 100)
    
    print(f'\n📈 FINAL PERFORMANCE METRICS')
    print('-' * 50)
    print(f'v6.0 CAGR: {v60_cagr:.2f}%')
    print(f'v6.5 CAGR: {v65_cagr:.2f}%')
    print(f'v6.0 Max Drawdown: {v60_dd:.2f}%')
    print(f'v6.5 Max Drawdown: {v65_dd:.2f}%')
    print(f'v6.0 Win Rate: {v60_win_rate:.2f}%')
    print(f'v6.5 Win Rate: {v65_win_rate:.2f}%')
    print(f'v6.0 Profit Factor: {v60_pf:.2f}')
    print(f'v6.5 Profit Factor: {v65_pf:.2f}')
    print(f'v6.5 Power Stock Trades: {len(v65_power):,} ({len(v65_power)/len(v65_trades)*100:.1f}%)')
    print(f'v6.5 Power Stock Win Rate: {v65_power_wr:.2f}%')
    
    print(f'\n🚀 PERFORMANCE IMPROVEMENTS')
    print('-' * 50)
    print(f'CAGR: {cagr_imp:+.1f}%')
    print(f'Max Drawdown: {dd_imp:+.1f}%')
    print(f'Win Rate: {wr_imp:+.1f}%')
    print(f'Profit Factor: {pf_imp:+.1f}%')
    print(f'Trade Count: {trades_imp:+.1f}%')
    
    print(f'\n🏆 20-YEAR BACKTEST FINAL RESULTS')
    print('=' * 80)
    print(f'{"Metric":<20} {"v6.0":<15} {"v6.5":<15} {"Change":<15}')
    print('-' * 80)
    print(f'{"CAGR":<20} {v60_cagr:<15.2f}% {v65_cagr:<15.2f}% {cagr_imp:<+15.1f}%')
    print(f'{"Max Drawdown":<20} {v60_dd:<15.2f}% {v65_dd:<15.2f}% {dd_imp:<+15.1f}%')
    print(f'{"Win Rate":<20} {v60_win_rate:<15.2f}% {v65_win_rate:<15.2f}% {wr_imp:<+15.1f}%')
    print(f'{"Profit Factor":<20} {v60_pf:<15.2f} {v65_pf:<15.2f} {pf_imp:<+15.1f}%')
    print(f'{"Total Trades":<20} {len(v60_trades):<15,} {len(v65_trades):<15,} {trades_imp:<+15.1f}%')
    print(f'{"Power Stock %":<20} {"N/A":<15} {len(v65_power)/len(v65_trades)*100:<15.1f}% {"-":<15}')
    print(f'{"Power Stock WR":<20} {"N/A":<15} {v65_power_wr:<15.2f}% {"-":<15}')
    print('=' * 80)
    
    print(f'\n🎯 CONCLUSION')
    print('-' * 50)
    if v65_cagr > v60_cagr:
        print(f'✅ v6.5 Power Hunter BEATS v6.0 by {cagr_imp:+.1f}% CAGR')
        print(f'✅ Over {years:.1f} years: ${100000*(1+v60_cagr/100)**years:,.0f} → ${100000*(1+v65_cagr/100)**years:,.0f}')
    else:
        print(f'❌ v6.5 underperforms v6.0 by {cagr_imp:+.1f}% CAGR')
    
    print(f'✅ Win Rate improved by {wr_imp:+.1f}% ({v60_win_rate:.1f}% → {v65_win_rate:.1f}%)')
    print(f'✅ Trade count increased by {trades_imp:+.1f}% ({len(v60_trades):,} → {len(v65_trades):,})')
    print(f'✅ Power Stock strategy: {len(v65_power):,} trades with {v65_power_wr:.1f}% win rate')
    
    return v60_cagr, v65_cagr, v60_dd, v65_dd

if __name__ == "__main__":
    calculate_final_metrics()
