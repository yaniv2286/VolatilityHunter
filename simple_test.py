from crucible_engine import CrucibleEngine

# Simple test without multiprocessing
engine = CrucibleEngine()

print('🔍 SIMPLE TEST - NO MULTIPROCESSING')
print('=' * 60)

# Test with SE
ticker = 'se'
df = engine.load_data(ticker)

print(f'Testing {ticker.upper()}...')

# Test v6.0
print('\nTesting v6.0:')
v60_trades = engine.simulate_trading(df, ticker, 'v6.0')
print(f'v6.0 trades: {len(v60_trades)}')

# Test v6.5
print('\nTesting v6.5:')
v65_trades = engine.simulate_trading(df, ticker, 'v6.5')
print(f'v6.5 trades: {len(v65_trades)}')

if len(v65_trades) > 0:
    print(f'\n🎉 SUCCESS! v6.5 is working!')
    total_pnl = sum(t['profit_loss'] for t in v65_trades)
    win_rate = len([t for t in v65_trades if t['profit_loss'] > 0]) / len(v65_trades) * 100
    power_stock_trades = len([t for t in v65_trades if t.get('is_power_stock', False)])
    
    print(f'v6.5 P&L: ${total_pnl:,.2f}')
    print(f'v6.5 Win Rate: {win_rate:.2f}%')
    print(f'v6.5 Power Stock Trades: {power_stock_trades}')
    
    print(f'\n📈 First 3 trades:')
    for i, trade in enumerate(v65_trades[:3]):
        print(f'  {i+1}. {trade["entry_date"].date()} → {trade["exit_date"].date()}')
        print(f'     P&L: ${trade["profit_loss"]:.2f} ({trade["profit_loss_pct"]:.2f}%)')
        print(f'     Reason: {trade["exit_reason"]}')
        print(f'     Power Stock: {trade["is_power_stock"]}')
else:
    print(f'\n❌ v6.5 still not working')
    
    # Let's debug the issue
    print(f'\n🔍 DEBUGGING THE ISSUE')
    print('-' * 40)
    
    # Check if the issue is in the signals
    df_indicators = engine.calculate_indicators(df)
    signals_v60 = engine.generate_signals(df_indicators, 'v6.0')
    signals_v65 = engine.generate_signals(df_indicators, 'v6.5')
    
    print(f'v6.0 signals: {signals_v60["signal"].sum()}')
    print(f'v6.5 signals: {signals_v65["signal"].sum()}')
    print(f'Signals identical: {signals_v60.equals(signals_v65)}')
    
    # Check if the issue is in the simulation
    print(f'\nTesting manual simulation...')
    
    # Manually run the simulation step by step
    trades = []
    position = None
    close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
    
    entry_count = 0
    for row in df_indicators.itertuples():
        date = getattr(row, 'Index')
        current_price = getattr(row, close_col)
        
        # Entry signal
        if signals_v65.loc[date, 'signal'] == 1 and position is None:
            entry_count += 1
            if entry_count <= 3:
                print(f'  Entry #{entry_count}: {date.date()} at ${current_price:.2f}')
            
            # Create position
            position = {
                'ticker': ticker,
                'entry_date': date,
                'entry_price': current_price,
                'shares': 100,
                'entry_cost': current_price * 100,
                'highest_price': current_price,
                'version': 'v6.5',
                'is_power_stock': False
            }
            
            if entry_count >= 3:
                break
    
    print(f'Manual entries found: {entry_count}')
    
    if entry_count > 0:
        print(f'✅ Entry logic works - issue must be in exit logic or trade recording')
    else:
        print(f'❌ Entry logic broken')
