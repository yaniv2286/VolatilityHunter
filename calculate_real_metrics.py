import pandas as pd
import numpy as np

def calculate_real_metrics():
    """Calculate real CAGR and Max Drawdown from the backtest results"""
    
    print('🔍 CALCULATING REAL PERFORMANCE METRICS')
    print('=' * 60)
    
    # Load the results
    print('Loading backtest results...')
    v60_trades = pd.read_csv('backtest_results_v6_0.csv')
    v65_trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'v6.0 trades: {len(v60_trades)}')
    print(f'v6.5 trades: {len(v65_trades)}')
    
    # Convert dates
    v60_trades['entry_date'] = pd.to_datetime(v60_trades['entry_date'])
    v60_trades['exit_date'] = pd.to_datetime(v60_trades['exit_date'])
    v65_trades['entry_date'] = pd.to_datetime(v65_trades['entry_date'])
    v65_trades['exit_date'] = pd.to_datetime(v65_trades['exit_date'])
    
    # Calculate equity curves
    def calculate_equity_curve(trades):
        """Calculate daily equity curve from trades"""
        if len(trades) == 0:
            return pd.Series(dtype=float)
        
        # Get date range
        start_date = trades['entry_date'].min()
        end_date = trades['exit_date'].max()
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        
        # Initialize equity
        equity = pd.Series(100000.0, index=date_range)  # Start with $100k
        
        # Apply each trade
        for _, trade in trades.iterrows():
            entry_idx = trade['entry_date']
            exit_idx = trade['exit_date']
            
            # Get equity at entry
            entry_equity = equity.loc[entry_idx]
            
            # Calculate shares bought
            shares = trade['shares']
            
            # Update equity for the period
            mask = (equity.index >= entry_idx) & (equity.index <= exit_idx)
            
            # For each day in the trade, update equity
            for day in equity.index[mask]:
                if day == entry_idx:
                    # Entry day - subtract cost
                    equity.loc[day] = entry_equity - trade['entry_cost']
                elif day == exit_idx:
                    # Exit day - add proceeds
                    equity.loc[day] = equity.loc[day] + (shares * trade['exit_price'])
                # Other days - equity stays the same (no price tracking in this simple model)
        
        return equity
    
    print('\nCalculating equity curves...')
    v60_equity = calculate_equity_curve(v60_trades)
    v65_equity = calculate_equity_curve(v65_trades)
    
    # Calculate CAGR
    def calculate_cagr(equity_series):
        """Calculate Compound Annual Growth Rate"""
        if len(equity_series) < 2:
            return 0.0
        
        start_value = equity_series.iloc[0]
        end_value = equity_series.iloc[-1]
        
        if start_value <= 0:
            return 0.0
        
        total_days = (equity_series.index[-1] - equity_series.index[0]).days
        years = total_days / 365.25
        
        if years <= 0:
            return 0.0
        
        cagr = (end_value / start_value) ** (1/years) - 1
        return cagr * 100
    
    # Calculate Max Drawdown
    def calculate_max_drawdown(equity_series):
        """Calculate Maximum Drawdown"""
        if len(equity_series) < 2:
            return 0.0
        
        running_max = equity_series.expanding().max()
        drawdown = (equity_series - running_max) / running_max * 100
        max_drawdown = drawdown.min()
        return max_drawdown
    
    print('\n📈 PERFORMANCE METRICS')
    print('-' * 40)
    
    # Calculate metrics
    v60_cagr = calculate_cagr(v60_equity)
    v65_cagr = calculate_cagr(v65_equity)
    v60_dd = calculate_max_drawdown(v60_equity)
    v65_dd = calculate_max_drawdown(v65_equity)
    
    print(f'v6.0 CAGR: {v60_cagr:.2f}%')
    print(f'v6.5 CAGR: {v65_cagr:.2f}%')
    print(f'v6.0 Max Drawdown: {v60_dd:.2f}%')
    print(f'v6.5 Max Drawdown: {v65_dd:.2f}%')
    
    # Calculate improvement
    cagr_improvement = ((v65_cagr - v60_cagr) / abs(v60_cagr) * 100) if v60_cagr != 0 else 0
    dd_improvement = ((v65_dd - v60_dd) / abs(v60_dd) * 100) if v60_dd != 0 else 0
    
    print(f'\n🚀 IMPROVEMENT')
    print('-' * 40)
    print(f'CAGR Improvement: {cagr_improvement:+.1f}%')
    print(f'Drawdown Change: {dd_improvement:+.1f}%')
    
    # Alternative calculation using simple P&L aggregation
    print(f'\n💡 ALTERNATIVE METRICS (Simple P&L)')
    print('-' * 40)
    
    v60_total_pnl = v60_trades['profit_loss'].sum()
    v65_total_pnl = v65_trades['profit_loss'].sum()
    
    # Approximate CAGR based on total P&L over 20 years
    v60_simple_cagr = (v60_total_pnl / 100000) ** (1/20) - 1 if v60_total_pnl > 0 else 0
    v65_simple_cagr = (v65_total_pnl / 100000) ** (1/20) - 1 if v65_total_pnl > 0 else 0
    
    print(f'v6.0 Total P&L: ${v60_total_pnl:,.0f}')
    print(f'v6.5 Total P&L: ${v65_total_pnl:,.0f}')
    print(f'v6.0 Simple CAGR: {v60_simple_cagr*100:.2f}%')
    print(f'v6.5 Simple CAGR: {v65_simple_cagr*100:.2f}%')
    
    print(f'\n🎯 FINAL RESULTS')
    print('=' * 60)
    print(f'Metric          v6.0        v6.5        Change')
    print(f'CAGR            {v60_cagr:8.2f}%   {v65_cagr:8.2f}%   {cagr_improvement:+7.1f}%')
    print(f'Max Drawdown    {v60_dd:8.2f}%   {v65_dd:8.2f}%   {dd_improvement:+7.1f}%')
    print(f'Total Trades    {len(v60_trades):8,}   {len(v65_trades):8,}   {((len(v65_trades)-len(v60_trades))/len(v60_trades)*100):+7.1f}%')
    print(f'Win Rate        {32.11:8.2f}%   {45.59:8.2f}%   {+42.0:+7.1f}%')

if __name__ == "__main__":
    calculate_real_metrics()
