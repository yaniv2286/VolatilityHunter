from crucible_engine import CrucibleEngine

engine = CrucibleEngine()
df = engine.load_data('se')

print('🔍 COMPARING v6.0 vs v6.5 TRADE BY TRADE')
print('=' * 60)

# Run both simulations
v60_trades = engine.simulate_trading(df, 'se', 'v6.0')
v65_trades = engine.simulate_trading(df, 'se', 'v6.5')

print(f'v6.0 trades: {len(v60_trades)}')
print(f'v6.5 trades: {len(v65_trades)}')

if len(v60_trades) > 0 and len(v65_trades) == 0:
    print('\n🔍 DEEP DIVE: WHY v6.5 FAILS')
    print('-' * 40)
    
    # Let's manually trace what should happen
    df_indicators = engine.calculate_indicators(df)
    signals = engine.generate_signals(df_indicators, 'v6.5')
    
    # Find first entry
    first_entry = signals[signals['signal'] == 1].index[0]
    entry_idx = df_indicators.index.get_loc(first_entry)
    
    print(f'First entry: {first_entry.date()} at index {entry_idx}')
    
    # Now simulate the trading logic manually
    position = None
    close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
    
    for idx in range(entry_idx, min(entry_idx + 200, len(df_indicators))):
        date = df_indicators.index[idx]
        current_row = df_indicators.iloc[idx]
        current_price = current_row[close_col]
        
        # Entry logic
        if signals.loc[date, 'signal'] == 1 and position is None:
            position = {
                'entry_date': date,
                'entry_price': current_price,
                'highest_price': current_price,
                'is_power_stock': False
            }
            print(f'  ENTERED at {date.date()}: ${current_price:.2f}')
            continue
        
        # Power stock detection
        if position is not None and engine.detect_power_stock(df_indicators, idx):
            position['is_power_stock'] = True
        
        # Update highest price
        if position is not None and current_price > position['highest_price']:
            position['highest_price'] = current_price
        
        # Exit logic
        if position is not None:
            is_power_stock = position.get('is_power_stock', False)
            
            if is_power_stock:
                # Power Stock: SMA 25 break OR ATR stop
                exit_sma25 = current_price < current_row['sma_25']
                exit_atr = current_price < (position['highest_price'] - 3 * current_row['atr'])
                should_exit = exit_sma25 or exit_atr
                exit_reason = 'SMA_25' if exit_sma25 else 'ATR_STOP'
            else:
                # Standard: SMA 200 break OR ATR stop
                exit_sma200 = current_price < current_row['sma_200']
                exit_atr = current_price < (position['highest_price'] - 3 * current_row['atr'])
                should_exit = exit_sma200 or exit_atr
                exit_reason = 'SMA_200' if exit_sma200 else 'ATR_STOP'
            
            if should_exit:
                duration = (date - position['entry_date']).days
                pnl = current_price - position['entry_price']
                print(f'  EXITED at {date.date()}: ${current_price:.2f} ({exit_reason}) after {duration} days, P&L: ${pnl:.2f}')
                print(f'    Entry: ${position["entry_price"]:.2f}, Highest: ${position["highest_price"]:.2f}')
                print(f'    Power Stock: {position["is_power_stock"]}')
                print(f'    Current SMA 200: ${current_row["sma_200"]:.2f}')
                print(f'    Current SMA 25: ${current_row["sma_25"]:.2f}')
                print(f'    Current ATR: ${current_row["atr"]:.2f}')
                print(f'    ATR stop level: ${position["highest_price"] - 3 * current_row["atr"]:.2f}')
                break
    
    if position is not None:
        print(f'  POSITION STILL OPEN at end of analysis period')
        print(f'    Entry: ${position["entry_price"]:.2f}')
        print(f'    Highest: ${position["highest_price"]:.2f}')
        print(f'    Current: ${current_price:.2f}')
        print(f'    Power Stock: {position["is_power_stock"]}')

print('\n🎯 FINDING THE REAL ISSUE')
print('=' * 60)
print('The issue might be that v6.5 trades are still open when the')
print('simulation ends, while v6.0 trades have already closed.')
print('')
print('Or there might be a bug in the Power Stock detection logic')
print('that prevents proper exit handling.')

# Let's check the actual v6.0 trades for comparison
if len(v60_trades) > 0:
    print('\n📊 v6.0 ACTUAL TRADES (First 3):')
    print('-' * 40)
    for i, trade in enumerate(v60_trades[:3]):
        print(f'Trade {i+1}:')
        print(f'  Entry: {trade["entry_date"].date()} at ${trade["entry_price"]:.2f}')
        print(f'  Exit: {trade["exit_date"].date()} at ${trade["exit_price"]:.2f}')
        print(f'  Duration: {trade["duration"]} days')
        print(f'  P&L: ${trade["profit_loss"]:.2f}')
        print(f'  Exit Reason: {trade.get("exit_reason", "Unknown")}')
        print()
