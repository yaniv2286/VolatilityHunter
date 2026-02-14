import pandas as pd
import numpy as np

def calculate_simple_metrics():
    """Calculate simple CAGR and Max Drawdown from trade P&L"""
    
    print('🎯 CALCULATING FINAL PERFORMANCE METRICS')
    print('=' * 60)
    
    # Load the results
    v60_trades = pd.read_csv('backtest_results_v6_0.csv')
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'v6.0 trades: {len(v60_trades):,}')
    print(f'v6.5 trades: {len(v65_trades):,}')
    
    # Convert dates
    v60_trades['entry_date'] = pd.to_datetime(v60_trades['entry_date'])
    v65_trades['entry_date'] = pd.to_datetime(v65_trades['entry_date'])
    
    # Calculate total P&L
    v60_total_pnl = v60_trades['profit_loss'].sum()
    v65_total_pnl = v65_trades['profit_loss'].sum()
    
    # Calculate time period
    v60_start = v60_trades['entry_date'].min()
    v60_end = v60_trades['entry_date'].max()
    v65_start = v65_trades['entry_date'].min()
    v65_end = v65_trades['entry_date'].max()
    
    v60_years = (v60_end - v60_start).days / 365.25
    v65_years = (v65_end - v65_start).days / 365.25
    
    print(f'\n📊 TRADE ANALYSIS')
    print('-' * 40)
    print(f'v6.0 Period: {v60_start.date()} to {v60_end.date()} ({v60_years:.1f} years)')
    print(f'v6.5 Period: {v65_start.date()} to {v65_end.date()} ({v65_years:.1f} years)')
    print(f'v6.0 Total P&L: ${v60_total_pnl:,.0f}')
    print(f'v6.5 Total P&L: ${v65_total_pnl:,.0f}')
    
    # Calculate simple CAGR (assuming $100k starting capital)
    starting_capital = 100000
    
    v60_final_capital = starting_capital + v60_total_pnl
    v65_final_capital = starting_capital + v65_total_pnl
    
    v60_cagr = ((v60_final_capital / starting_capital) ** (1/v60_years) - 1) * 100
    v65_cagr = ((v65_final_capital / starting_capital) ** (1/v65_years) - 1) * 100
    
    # Calculate Max Drawdown from cumulative P&L
    def calculate_max_dd_from_trades(trades):
        """Calculate max drawdown from cumulative P&L"""
        if len(trades) == 0:
            return 0.0
        
        # Sort by exit date
        trades_sorted = trades.sort_values('exit_date')
        
        # Calculate cumulative P&L
        cumulative_pnl = trades_sorted['profit_loss'].cumsum()
        
        # Calculate running max
        running_max = cumulative_pnl.expanding().max()
        
        # Calculate drawdown
        drawdown = (cumulative_pnl - running_max) / running_max * 100
        
        return drawdown.min()
    
    v60_dd = calculate_max_dd_from_trades(v60_trades)
    v65_dd = calculate_max_dd_from_trades(v65_trades)
    
    # Calculate other metrics
    v60_win_rate = (v60_trades['profit_loss'] > 0).mean() * 100
    v65_win_rate = (v65_trades['profit_loss'] > 0).mean() * 100
    
    v60_profit_factor = abs(v60_trades[v60_trades['profit_loss'] > 0]['profit_loss'].sum() / 
                           v60_trades[v60_trades['profit_loss'] < 0]['profit_loss'].sum()) if v60_trades[v60_trades['profit_loss'] < 0]['profit_loss'].sum() != 0 else 0
    v65_profit_factor = abs(v65_trades[v65_trades['profit_loss'] > 0]['profit_loss'].sum() / 
                           v65_trades[v65_trades['profit_loss'] < 0]['profit_loss'].sum()) if v65_trades[v65_trades['profit_loss'] < 0]['profit_loss'].sum() != 0 else 0
    
    # Power Stock analysis for v6.5
    v65_power_trades = v65_trades[v65_trades['is_power_stock'] == True]
    v65_power_win_rate = (v65_power_trades['profit_loss'] > 0).mean() * 100 if len(v65_power_trades) > 0 else 0
    
    print(f'\n📈 PERFORMANCE METRICS')
    print('-' * 40)
    print(f'v6.0 CAGR: {v60_cagr:.2f}%')
    print(f'v6.5 CAGR: {v65_cagr:.2f}%')
    print(f'v6.0 Max Drawdown: {v60_dd:.2f}%')
    print(f'v6.5 Max Drawdown: {v65_dd:.2f}%')
    print(f'v6.0 Win Rate: {v60_win_rate:.2f}%')
    print(f'v6.5 Win Rate: {v65_win_rate:.2f}%')
    print(f'v6.0 Profit Factor: {v60_profit_factor:.2f}')
    print(f'v6.5 Profit Factor: {v65_profit_factor:.2f}')
    print(f'v6.5 Power Stock Trades: {len(v65_power_trades):,} ({len(v65_power_trades)/len(v65_trades)*100:.1f}% of total)')
    print(f'v6.5 Power Stock Win Rate: {v65_power_win_rate:.2f}%')
    
    # Calculate improvements
    cagr_improvement = ((v65_cagr - v60_cagr) / abs(v60_cagr) * 100) if v60_cagr != 0 else 0
    dd_improvement = ((v65_dd - v60_dd) / abs(v60_dd) * 100) if v60_dd != 0 else 0
    wr_improvement = ((v65_win_rate - v60_win_rate) / v60_win_rate * 100) if v60_win_rate != 0 else 0
    pf_improvement = ((v65_profit_factor - v60_profit_factor) / v60_profit_factor * 100) if v60_profit_factor != 0 else 0
    trades_improvement = ((len(v65_trades) - len(v60_trades)) / len(v60_trades) * 100)
    
    print(f'\n🚀 IMPROVEMENT ANALYSIS')
    print('-' * 40)
    print(f'CAGR Improvement: {cagr_improvement:+.1f}%')
    print(f'Drawdown Change: {dd_improvement:+.1f}%')
    print(f'Win Rate Improvement: {wr_improvement:+.1f}%')
    print(f'Profit Factor Improvement: {pf_improvement:+.1f}%')
    print(f'Trade Count Improvement: {trades_improvement:+.1f}%')
    
    print(f'\n🏆 FINAL 20-YEAR BACKTEST RESULTS')
    print('=' * 80)
    print(f'{"Metric":<20} {"v6.0":<15} {"v6.5":<15} {"Change":<15}')
    print('-' * 80)
    print(f'{"CAGR":<20} {v60_cagr:<15.2f}% {v65_cagr:<15.2f}% {cagr_improvement:<+15.1f}%')
    print(f'{"Max Drawdown":<20} {v60_dd:<15.2f}% {v65_dd:<15.2f}% {dd_improvement:<+15.1f}%')
    print(f'{"Win Rate":<20} {v60_win_rate:<15.2f}% {v65_win_rate:<15.2f}% {wr_improvement:<+15.1f}%')
    print(f'{"Profit Factor":<20} {v60_profit_factor:<15.2f} {v65_profit_factor:<15.2f} {pf_improvement:<+15.1f}%')
    print(f'{"Total Trades":<20} {len(v60_trades):<15,} {len(v65_trades):<15,} {trades_improvement:<+15.1f}%')
    print(f'{"Power Stock %":<20} {"N/A":<15} {len(v65_power_trades)/len(v65_trades)*100:<15.1f}% {"-":<15}')
    print(f'{"Power Stock WR":<20} {"N/A":<15} {v65_power_win_rate:<15.2f}% {"-":<15}')
    print('=' * 80)
    
    print(f'\n🎯 CONCLUSION')
    print('-' * 40)
    if v65_cagr > v60_cagr:
        print(f'✅ v6.5 Power Hunter OUTPERFORMS v6.0 by {cagr_improvement:+.1f}% CAGR')
    else:
        print(f'❌ v6.5 underperforms v6.0 by {cagr_improvement:+.1f}% CAGR')
    
    if v65_win_rate > v60_win_rate:
        print(f'✅ v6.5 Win Rate is {wr_improvement:+.1f}% higher')
    
    if len(v65_trades) > len(v60_trades):
        print(f'✅ v6.5 captures {trades_improvement:+.1f}% more trading opportunities')
    
    if len(v65_power_trades) > 0:
        print(f'✅ Power Stock strategy: {len(v65_power_trades):,} trades with {v65_power_win_rate:.1f}% win rate')

if __name__ == "__main__":
    calculate_simple_metrics()
