import pandas as pd
import os

def show_trade_files():
    """Show the trade files and their structure"""
    
    print('📁 TRADE FILES LOCATION')
    print('=' * 60)
    
    # Check if files exist
    v60_file = 'backtest_results_v6_0.csv'
    v65_file = 'backtest_results_v6_5.csv'
    
    print(f'Current directory: {os.getcwd()}')
    print(f'\nFiles:')
    print(f'  v6.0: {v60_file} - {"✅ EXISTS" if os.path.exists(v60_file) else "❌ MISSING"}')
    print(f'  v6.5: {v65_file} - {"✅ EXISTS" if os.path.exists(v65_file) else "❌ MISSING"}')
    
    if os.path.exists(v60_file) and os.path.exists(v65_file):
        # Load and show structure
        v60_trades = pd.read_csv(v60_file)
        v65_trades = pd.read_csv(v65_file)
        
        print(f'\n📊 FILE STRUCTURE')
        print('-' * 40)
        print(f'Columns: {list(v60_trades.columns)}')
        print(f'v6.0 file size: {os.path.getsize(v60_file):,} bytes')
        print(f'v6.5 file size: {os.path.getsize(v65_file):,} bytes')
        
        print(f'\n🔍 SAMPLE TRADES (v6.5)')
        print('-' * 40)
        print(v65_trades.head(3).to_string(index=False))
        
        print(f'\n📈 TRADE SUMMARY')
        print('-' * 40)
        print(f'v6.0 trades: {len(v60_trades):,}')
        print(f'v6.5 trades: {len(v65_trades):,}')
        print(f'v6.5 Power Stock trades: {v65_trades["is_power_stock"].sum():,}')
        
        # Show file paths
        print(f'\n🎯 FULL FILE PATHS:')
        print('-' * 40)
        print(f'v6.0: {os.path.abspath(v60_file)}')
        print(f'v6.5: {os.path.abspath(v65_file)}')
        
        # Create JSON version if needed
        print(f'\n💾 CREATING JSON VERSIONS...')
        v60_json = v60_file.replace('.csv', '.json')
        v65_json = v65_file.replace('.csv', '.json')
        
        v60_trades.to_json(v60_json, orient='records', date_format='iso')
        v65_trades.to_json(v65_json, orient='records', date_format='iso')
        
        print(f'✅ Created: {v60_json}')
        print(f'✅ Created: {v65_json}')
        print(f'v6.0 JSON size: {os.path.getsize(v60_json):,} bytes')
        print(f'v6.5 JSON size: {os.path.getsize(v65_json):,} bytes')
        
    else:
        print(f'\n❌ Files not found. Running backtest to create them...')
        print('Run: python crucible_engine.py')

if __name__ == "__main__":
    show_trade_files()
