import pandas as pd
import numpy as np
from crucible_engine import CrucibleEngine

# Deep dive into exit logic differences
engine = CrucibleEngine()

# Use SE as our test case (has good v6.0 performance)
ticker = 'se'

print(f'🔍 DEEP DIVE: EXIT LOGIC ANALYSIS FOR {ticker.upper()}')
print('=' * 70)

df = engine.load_data(ticker)
df_indicators = engine.calculate_indicators(df)

# Get v6.0 trades for comparison
v60_trades = engine.simulate_trading(df, ticker, 'v6.0')

print(f'v6.0 completed {len(v60_trades)} trades')
print(f'v6.0 total P&L: ${sum(t["profit_loss"] for t in v60_trades):,.2f}')

# Now let's manually trace what happens in v6.5
print(f'\n📊 MANUAL TRACE OF v6.5 LOGIC')
print('-' * 50)

# Get entry signals
signals = engine.generate_signals(df_indicators, 'v6.5')
entry_dates = signals[signals['signal'] == 1].index

print(f'Found {len(entry_dates)} entry signals')

# Trace first few entries
for i, entry_date in enumerate(entry_dates[:3]):
    print(f'\n--- Entry #{i+1} on {entry_date.date()} ---')
    
    # Find the entry row
    entry_idx = df_indicators.index.get_loc(entry_date)
    entry_row = df_indicators.iloc[entry_idx]
    
    close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
    entry_price = entry_row[close_col]
    
    print(f'Entry price: ${entry_price:.2f}')
    print(f'SMA 200: ${entry_row["sma_200"]:.2f}')
    print(f'SMA 25: ${entry_row["sma_25"]:.2f}')
    print(f'ATR: ${entry_row["atr"]:.2f}')
    
    # Check if this becomes a power stock
    became_power_stock = False
    power_stock_date = None
    
    # Look forward from entry
    for future_idx in range(entry_idx + 1, len(df_indicators)):
        if engine.detect_power_stock(df_indicators, future_idx):
            became_power_stock = True
            power_stock_date = df_indicators.index[future_idx]
            break
    
    print(f'Became Power Stock: {became_power_stock}')
    if became_power_stock:
        print(f'Power Stock date: {power_stock_date.date()}')
    
    # Now trace exit logic day by day
    position_active = True
    exit_reason = 'Unknown'
    exit_date = None
    highest_price = entry_price
    
    for future_idx in range(entry_idx + 1, len(df_indicators)):
        current_date = df_indicators.index[future_idx]
        current_row = df_indicators.iloc[future_idx]
        current_price = current_row[close_col]
        
        # Update highest price
        if current_price > highest_price:
            highest_price = current_price
        
        # Check if it's a power stock now
        is_current_power_stock = engine.detect_power_stock(df_indicators, future_idx)
        
        # v6.5 exit logic
        should_exit = False
        
        if is_current_power_stock:
            # Power Stock: SMA 25 break OR ATR stop
            if current_price < current_row['sma_25']:
                should_exit = True
                exit_reason = 'POWER_STOCK_SMA_25_BREAK'
            elif current_price < (highest_price - 3 * current_row['atr']):
                should_exit = True
                exit_reason = 'POWER_STOCK_ATR_STOP'
        else:
            # Standard: SMA 200 break OR ATR stop
            if current_price < current_row['sma_200']:
                should_exit = True
                exit_reason = 'SMA_200_BREAK'
            elif current_price < (highest_price - 3 * current_row['atr']):
                should_exit = True
                exit_reason = 'ATR_STOP'
        
        if should_exit:
            exit_date = current_date
            exit_price = current_price
            break
    
    if exit_date:
        print(f'Exit on: {exit_date.date()} at ${current_price:.2f}')
        print(f'Exit reason: {exit_reason}')
        print(f'Duration: {(exit_date - entry_date).days} days')
        
        # Compare with v6.0
        v60_trade = None
        for trade in v60_trades:
            if trade['entry_date'] == entry_date:
                v60_trade = trade
                break
        
        if v60_trade:
            print(f'v6.0 exited on: {v60_trade["exit_date"].date()} at ${v60_trade["exit_price"]:.2f}')
            print(f'v6.0 exit reason: {v60_trade.get("exit_reason", "Unknown")}')
            print(f'v6.0 P&L: ${v60_trade["profit_loss"]:.2f}')
    else:
        print(f'No exit found - position runs to end of data')

print(f'\n🎯 POWER STOCK DETECTION ANALYSIS')
print('-' * 50)

# Let's see what makes a power stock
power_stock_days = 0
total_days = len(df_indicators)

for idx in range(len(df_indicators)):
    if engine.detect_power_stock(df_indicators, idx):
        power_stock_days += 1

print(f'Power Stock days: {power_stock_days} ({power_stock_days/total_days*100:.1f}%)')

# Show some examples of power stock conditions
print(f'\nSample Power Stock conditions:')
power_stock_indices = []
for idx in range(len(df_indicators)):
    if engine.detect_power_stock(df_indicators, idx):
        power_stock_indices.append(idx)
        if len(power_stock_indices) >= 3:
            break

for i, idx in enumerate(power_stock_indices):
    row = df_indicators.iloc[idx]
    date = df_indicators.index[idx]
    close_col = 'adjClose' if 'adjClose' in df_indicators.columns else 'close'
    
    print(f'  {i+1}. {date.date()}:')
    print(f'     Price: ${row[close_col]:.2f}')
    print(f'     Stoch K: {row["stoch_k"]:.1f}')
    print(f'     SMA 25: ${row["sma_25"]:.2f}')
    print(f'     SMA 50: ${row["sma_50"]:.2f}')
    print(f'     SMA 100: ${row["sma_100"]:.2f}')
    print(f'     SMA 200: ${row["sma_200"]:.2f}')
    print(f'     Volume SMA: {row["volume_sma_30"]:,.0f}')
    print(f'     Current Volume: {row["volume"]:,.0f}')

print(f'\n✅ ANALYSIS COMPLETE')
