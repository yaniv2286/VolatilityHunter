from crucible_engine import CrucibleEngine

# Minimal debug to find the exact issue
engine = CrucibleEngine()
ticker = 'se'
df = engine.load_data(ticker)

print('🔍 MINIMAL DEBUG - FIND THE EXACT ISSUE')
print('=' * 60)

# Override the simulate_trading method with minimal debug
original_simulate = engine.simulate_trading

def debug_simulate_trading(df, ticker, version):
    print(f'  Starting debug simulation for {ticker} {version}')
    
    df_indicators = engine.calculate_indicators(df)
    signals = engine.generate_signals(df_indicators, version)
    
    trades = []
    position = None
    close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
    
    for idx, row in enumerate(df_indicators.itertuples()):
        date = getattr(row, 'Index')
        current_price = getattr(row, close_col)
        
        # Entry signal
        if signals.loc[date, 'signal'] == 1 and position is None:
            print(f'    ENTRY at {date.date()}: ${current_price:.2f}')
            position = {
                'ticker': ticker,
                'entry_date': date,
                'entry_price': current_price,
                'shares': 100,
                'entry_cost': current_price * 100,
                'highest_price': current_price,
                'version': version,
                'is_power_stock': False
            }
            continue
        
        # Exit logic
        if position is not None:
            # Update highest price
            if current_price > position['highest_price']:
                position['highest_price'] = current_price
            
            # Check Power Stock
            if version == 'v6.5' and engine.detect_power_stock(df_indicators, df_indicators.index.get_loc(date)):
                position['is_power_stock'] = True
            
            # Check exit conditions
            should_exit = False
            exit_reason = ''
            
            if version == 'v6.0':
                if current_price < getattr(row, 'sma_200'):
                    should_exit = True
                    exit_reason = 'SMA_200_BREAK'
                elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                    should_exit = True
                    exit_reason = 'ATR_STOP'
            else:  # v6.5
                is_power_stock = position.get('is_power_stock', False)
                
                if is_power_stock:
                    if current_price < getattr(row, 'sma_25'):
                        should_exit = True
                        exit_reason = 'POWER_STOCK_SMA_25_BREAK'
                    elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                        should_exit = True
                        exit_reason = 'POWER_STOCK_ATR_STOP'
                else:
                    if current_price < getattr(row, 'sma_200'):
                        should_exit = True
                        exit_reason = 'SMA_200_BREAK'
                    elif current_price < (position['highest_price'] - 3 * getattr(row, 'atr')):
                        should_exit = True
                        exit_reason = 'ATR_STOP'
            
            if should_exit:
                print(f'    EXIT at {date.date()}: ${current_price:.2f} ({exit_reason})')
                
                trade = {
                    'ticker': ticker,
                    'version': version,
                    'entry_date': position['entry_date'],
                    'exit_date': date,
                    'entry_price': position['entry_price'],
                    'exit_price': current_price,
                    'shares': position['shares'],
                    'profit_loss': (current_price - position['entry_price']) * position['shares'],
                    'exit_reason': exit_reason
                }
                
                trades.append(trade)
                position = None
                
                if len(trades) >= 3:  # Stop after 3 trades for debugging
                    break
        
        # Safety break to prevent infinite loop
        if idx > 1000:
            print(f'    Safety break at index {idx}')
            break
    
    print(f'  Debug simulation complete: {len(trades)} trades')
    return trades

# Test both versions
engine.simulate_trading = debug_simulate_trading

print('Testing v6.0:')
v60_trades = engine.simulate_trading(df, ticker, 'v6.0')
print(f'v6.0 result: {len(v60_trades)} trades')

print('\nTesting v6.5:')
v65_trades = engine.simulate_trading(df, ticker, 'v6.5')
print(f'v6.5 result: {len(v65_trades)} trades')

if len(v65_trades) == 0:
    print('\n❌ v6.5 still not working in debug version')
else:
    print('\n🎉 v6.5 working in debug version!')

# Restore original method
engine.simulate_trading = original_simulate
