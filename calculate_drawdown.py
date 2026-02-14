import pandas as pd
import numpy as np

def calculate_realistic_drawdown():
    """Calculate realistic Max Drawdown from the fixed position sizing data"""
    
    print('📉 CALCULATING REALISTIC MAX DRAWDOWN')
    print('=' * 60)
    
    # Load trades
    v60_trades = pd.read_csv('backtest_results_v6_0.csv')
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'v6.0 trades: {len(v60_trades):,}')
    print(f'v65_trades: {len(v65_trades):,}')
    
    # Clean data (remove outliers)
    v60_clean = v60_trades[(v60_trades['profit_loss_pct'] > -100) & (v60_trades['profit_loss_pct'] < 100)]
    v65_clean = v65_trades[(v65_trades['profit_loss_pct'] > -100) & (v65_trades['profit_loss_pct'] < 100)]
    
    print(f'v6.0 clean trades: {len(v60_clean):,}')
    print(f'v6.5 clean trades: {len(v65_clean):,}')
    
    def calculate_max_drawdown_from_trades(trades, starting_capital=100000):
        """Calculate max drawdown from trade sequence"""
        
        if len(trades) == 0:
            return 0.0, starting_capital
        
        # Sort by entry date
        trades_sorted = trades.sort_values('entry_date')
        
        # Calculate equity curve
        equity = [starting_capital]
        
        for _, trade in trades_sorted.iterrows():
            # Calculate P&L for this trade (1000 shares fixed)
            trade_pnl = trade['profit_loss']  # Already calculated with 1000 shares
            new_equity = equity[-1] + trade_pnl
            equity.append(new_equity)
        
        equity_series = pd.Series(equity)
        
        # Calculate drawdown
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        
        max_drawdown = drawdown.min()
        final_equity = equity_series.iloc[-1]
        
        return max_drawdown, final_equity
    
    # Calculate drawdown for both versions
    v60_dd, v60_final = calculate_max_drawdown_from_trades(v60_clean)
    v65_dd, v65_final = calculate_max_drawdown_from_trades(v65_clean)
    
    print(f'\n📊 DRAWDOWN ANALYSIS')
    print('-' * 40)
    print(f'v6.0 Max Drawdown: {v60_dd:.2f}%')
    print(f'v6.5 Max Drawdown: {v65_dd:.2f}%')
    print(f'v6.0 Final Capital: ${v60_final:,.0f}')
    print(f'v6.5 Final Capital: ${v65_final:,.0f}')
    
    # Calculate improvement
    dd_improvement = ((v65_dd - v60_dd) / abs(v60_dd) * 100) if v60_dd != 0 else 0
    
    print(f'\n🚀 DRAWDOWN COMPARISON')
    print('-' * 40)
    print(f'Drawdown Change: {dd_improvement:+.1f}%')
    
    if v65_dd > v60_dd:
        print(f'v6.5 has {abs(dd_improvement):.1f}% HIGHER drawdown (more volatile)')
    else:
        print(f'v6.5 has {abs(dd_improvement):.1f}% LOWER drawdown (more stable)')
    
    # Calculate additional metrics
    def calculate_drawdown_metrics(equity_series):
        """Calculate detailed drawdown metrics"""
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        
        # Count drawdown periods
        in_drawdown = drawdown < 0
        drawdown_periods = []
        
        current_dd_start = None
        for i, is_dd in enumerate(in_drawdown):
            if is_dd and current_dd_start is None:
                current_dd_start = i
            elif not is_dd and current_dd_start is not None:
                drawdown_periods.append((current_dd_start, i))
                current_dd_start = None
        
        # Handle case where we end in drawdown
        if current_dd_start is not None:
            drawdown_periods.append((current_dd_start, len(equity_series) - 1))
        
        # Calculate average drawdown
        negative_drawdowns = drawdown[drawdown < 0]
        avg_drawdown = negative_drawdowns.mean() if len(negative_drawdowns) > 0 else 0
        
        # Calculate max drawdown duration
        max_duration = 0
        for start, end in drawdown_periods:
            duration = end - start
            max_duration = max(max_duration, duration)
        
        return {
            'max_dd': drawdown.min(),
            'avg_dd': avg_drawdown,
            'dd_periods': len(drawdown_periods),
            'max_duration': max_duration
        }
    
    # Calculate detailed metrics
    v60_equity = [100000]
    for _, trade in v60_clean.sort_values('entry_date').iterrows():
        v60_equity.append(v60_equity[-1] + trade['profit_loss'])
    
    v65_equity = [100000]
    for _, trade in v65_clean.sort_values('entry_date').iterrows():
        v65_equity.append(v65_equity[-1] + trade['profit_loss'])
    
    v60_dd_metrics = calculate_drawdown_metrics(pd.Series(v60_equity))
    v65_dd_metrics = calculate_drawdown_metrics(pd.Series(v65_equity))
    
    print(f'\n📈 DETAILED DRAWDOWN METRICS')
    print('-' * 50)
    print(f'v6.0 Max DD: {v60_dd_metrics["max_dd"]:.2f}%')
    print(f'v6.0 Avg DD: {v60_dd_metrics["avg_dd"]:.2f}%')
    print(f'v6.0 DD Periods: {v60_dd_metrics["dd_periods"]}')
    print(f'v6.0 Max DD Duration: {v60_dd_metrics["max_duration"]} trades')
    print('')
    print(f'v6.5 Max DD: {v65_dd_metrics["max_dd"]:.2f}%')
    print(f'v6.5 Avg DD: {v65_dd_metrics["avg_dd"]:.2f}%')
    print(f'v6.5 DD Periods: {v65_dd_metrics["dd_periods"]}')
    print(f'v6.5 Max DD Duration: {v65_dd_metrics["max_duration"]} trades')
    
    # Risk-adjusted return (Sortino ratio approximation)
    def calculate_sortino_metrics(returns):
        """Calculate Sortino-like metrics"""
        negative_returns = returns[returns < 0]
        downside_deviation = negative_returns.std() if len(negative_returns) > 0 else 0
        mean_return = returns.mean()
        
        if downside_deviation > 0:
            sortino = mean_return / downside_deviation
        else:
            sortino = float('inf') if mean_return > 0 else 0
        
        return sortino
    
    v60_returns = v60_clean['profit_loss_pct'] / 100
    v65_returns = v65_clean['profit_loss_pct'] / 100
    
    v60_sortino = calculate_sortino_metrics(v60_returns)
    v65_sortino = calculate_sortino_metrics(v65_returns)
    
    print(f'\n⚖️ RISK-ADJUSTED METRICS')
    print('-' * 30)
    print(f'v6.0 Sortino-like: {v60_sortino:.2f}')
    print(f'v6.5 Sortino-like: {v65_sortino:.2f}')
    
    print(f'\n🏆 FINAL DRAWDOWN RESULTS')
    print('=' * 60)
    print(f'Metric               v6.0            v6.5            Change')
    print('-' * 60)
    print(f'Max Drawdown         {v60_dd:<15.2f}% {v65_dd:<15.2f}% {dd_improvement:<+15.1f}%')
    print(f'Avg Drawdown         {v60_dd_metrics["avg_dd"]:<15.2f}% {v65_dd_metrics["avg_dd"]:<15.2f}% {((v65_dd_metrics["avg_dd"]-v60_dd_metrics["avg_dd"])/abs(v60_dd_metrics["avg_dd"])*100):<+15.1f}%')
    print(f'DD Periods           {v60_dd_metrics["dd_periods"]:<15} {v65_dd_metrics["dd_periods"]:<15} {((v65_dd_metrics["dd_periods"]-v60_dd_metrics["dd_periods"])/v60_dd_metrics["dd_periods"]*100):<+15.1f}%')
    print(f'Max DD Duration      {v60_dd_metrics["max_duration"]:<15} {v65_dd_metrics["max_duration"]:<15} {((v65_dd_metrics["max_duration"]-v60_dd_metrics["max_duration"])/v60_dd_metrics["max_duration"]*100):<+15.1f}%')
    print(f'Sortino Ratio        {v60_sortino:<15.2f} {v65_sortino:<15.2f} {((v65_sortino-v60_sortino)/abs(v60_sortino)*100):<+15.1f}%')
    
    print(f'\n🎯 DRAWDOWN CONCLUSION')
    print('-' * 40)
    if abs(v65_dd) < abs(v60_dd):
        print(f'✅ v6.5 has LOWER drawdown ({abs(v65_dd):.1f}% vs {abs(v60_dd):.1f}%)')
        print(f'✅ More stable strategy')
    else:
        print(f'⚠️  v6.5 has HIGHER drawdown ({abs(v65_dd):.1f}% vs {abs(v60_dd):.1f}%)')
        print(f'⚠️  More volatile but captures more opportunities')
    
    return v60_dd, v65_dd

if __name__ == "__main__":
    calculate_realistic_drawdown()
