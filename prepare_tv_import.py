import pandas as pd
import numpy as np
from datetime import datetime

def prepare_tv_import():
    """Prepare TradingView portfolio import file from VolatilityHunter v6.5 results"""
    
    print('🎯 PREPARING TRADINGVIEW PORTFOLIO IMPORT - CLEAN VERSION')
    print('=' * 70)
    
    # Load the data
    print('📊 Loading backtest results...')
    trades = pd.read_csv('backtest_results_v6_5.csv')
    
    print(f'✅ Loaded {len(trades):,} total trades')
    
    # 1. STRICT SAFETY FILTERS
    print('\n🛡️ APPLYING STRICT SAFETY FILTERS...')
    print('-' * 50)
    
    # Filter conditions
    original_count = len(trades)
    
    # PRICE CEILING: Remove trades with entry_price > $500 (reverse split ghosts)
    price_ceiling_filter = trades['entry_price'] <= 500
    trades = trades[price_ceiling_filter]
    removed_ceiling = original_count - len(trades)
    print(f'• PRICE CEILING: Removed {removed_ceiling:,} trades with entry_price > $500')
    
    # PENNY STOCK FLOOR: Remove trades with entry_price < $1.00
    current_count = len(trades)
    price_floor_filter = trades['entry_price'] >= 1.00
    trades = trades[price_floor_filter]
    removed_floor = current_count - len(trades)
    print(f'• PENNY STOCK FLOOR: Removed {removed_floor:,} trades with entry_price < $1.00')
    
    # Remove trades with 0 or NaN shares
    shares_filter = (trades['shares'] > 0) & (~trades['shares'].isna())
    trades = trades[shares_filter]
    print(f'• SHARES FILTER: Removed trades with 0/NaN shares')
    
    # Remove NaN values in critical columns
    trades = trades.dropna(subset=['ticker', 'entry_price', 'shares', 'entry_date'])
    print(f'• CRITICAL VALUES: Removed trades with NaN values')
    
    print(f'✅ Remaining trades after cleaning: {len(trades):,}')
    print(f'✅ Clean rate: {len(trades)/original_count*100:.1f}%')
    
    # 2. SELECT TOP 500 VALID TRADES (ORDERED BY DATE)
    print('\n📅 SELECTING TOP 500 VALID TRADES BY DATE...')
    print('-' * 55)
    
    # Sort by entry_date to get chronological history
    trades_sorted = trades.sort_values('entry_date')
    
    # Take first 500 trades (chronological)
    top_trades = trades_sorted.head(500)
    
    print(f'✅ Selected {len(top_trades):,} trades')
    print(f'• Date range: {top_trades["entry_date"].min()} to {top_trades["entry_date"].max()}')
    print(f'• Average profit: {top_trades["profit_loss_pct"].mean():.2f}%')
    print(f'• Win rate: {(top_trades["profit_loss"] > 0).mean() * 100:.1f}%')
    
    # 3. DYNAMIC EXCHANGE MAPPING
    print('\n📋 DYNAMIC EXCHANGE MAPPING...')
    print('-' * 35)
    
    # Specific exchange lists for accurate TradingView mapping
    nasdaq_tickers = [
        'AAPL', 'TSLA', 'MSFT', 'GOOGL', 'NVDA', 'AMZN', 'NFLX', 'META', 'ADBE', 'CRM', 
        'PYPL', 'INTC', 'CSCO', 'CMCSA', 'PEP', 'COST', 'AVGO', 'TXN', 'QCOM', 'TMUS', 
        'SBUX', 'AMD', 'INTU', 'MU', 'AMAT', 'CSX', 'FISV', 'GILD', 'BKNG', 'ADP', 
        'KLAC', 'MDLZ', 'ISRG', 'REGN', 'EBAY', 'ATVI', 'ILMN', 'LRCX', 'KHC', 'MELI', 
        'ZS', 'SNOW', 'DOCU', 'CRWD', 'ZM', 'OKTA', 'SQ', 'SHOP', 'ROKU', 'JD', 'BIDU', 
        'PDD', 'NTES', 'BABA', 'NIO', 'XPEV', 'LI', 'TME', 'BILI', 'IQ', 'WISH', 'SPCE'
    ]
    
    amex_tickers = [
        'FCEL', 'ABEO', 'MARA', 'RIOT', 'SNDL', 'AMC', 'GME', 'BB', 'NOK', 'PLTR', 
        'RGTI', 'QXO', 'APLD', 'SPR', 'SOS', 'TKAT', 'TOP', 'CAN', 'MVIS', 'SPRB', 
        'HEAR', 'VERU', 'VXRT', 'INO', 'GNUS', 'SAVA', 'AVCT', 'CLOV', 'WISH', 'SKLZ'
    ]
    
    def map_symbol(ticker):
        """Map ticker to TradingView symbol format with dynamic exchange mapping"""
        ticker_upper = ticker.upper()
        
        if ticker_upper in nasdaq_tickers:
            return f'NASDAQ:{ticker_upper}'
        elif ticker_upper in amex_tickers:
            return f'AMEX:{ticker_upper}'
        else:
            return f'NYSE:{ticker_upper}'  # Default to NYSE for unknown tickers
    
    # Format dates
    def format_date(date_str):
        """Format date to YYYY-MM-DD"""
        try:
            # Handle different date formats
            if '+' in date_str:  # ISO format with timezone
                date_str = date_str.split('+')[0].split('T')[0]
            elif 'T' in date_str:  # ISO format without timezone
                date_str = date_str.split('T')[0]
            elif ' ' in date_str:  # Space separated
                date_str = date_str.split(' ')[0]
            
            # Validate date format
            parsed_date = pd.to_datetime(date_str)
            return parsed_date.strftime('%Y-%m-%d')
        except:
            return date_str.split(' ')[0]  # Fallback
    
    # Create TradingView format
    tv_data = []
    
    for _, trade in top_trades.iterrows():
        tv_trade = {
            'Symbol': map_symbol(trade['ticker']),
            'Side': 'buy',
            'Qty': int(trade['shares']),
            'Fill Price': round(trade['entry_price'], 2),
            'Commission': 0,
            'Closing Time': format_date(trade['entry_date'])
        }
        tv_data.append(tv_trade)
    
    # Create DataFrame with exact TradingView column order
    tv_df = pd.DataFrame(tv_data, columns=['Symbol', 'Side', 'Qty', 'Fill Price', 'Commission', 'Closing Time'])
    
    # 4. SAVE TO FILE
    print('\n💾 SAVING TRADINGVIEW FILE...')
    print('-' * 30)
    
    output_file = 'tv_final_sync_v6_5.csv'
    tv_df.to_csv(output_file, index=False)
    
    print(f'✅ Saved to: {output_file}')
    print(f'✅ File size: {tv_df.memory_usage(deep=True).sum() / 1024:.1f} KB')
    
    # 5. VERIFICATION
    print('\n🔍 VERIFICATION SUMMARY')
    print('=' * 70)
    
    print(f'📊 PROCESSING SUMMARY:')
    print(f'• Original trades: {original_count:,}')
    print(f'• After price ceiling ($500): {original_count - removed_ceiling:,}')
    print(f'• After price floor ($1.00): {len(trades):,}')
    print(f'• Exported to TV: {len(tv_df):,}')
    print(f'• Export rate: {len(tv_df)/original_count*100:.2f}%')
    
    print(f'\n📈 TRADE STATISTICS:')
    print(f'• Avg shares per trade: {tv_df["Qty"].mean():.0f}')
    print(f'• Avg fill price: ${tv_df["Fill Price"].mean():.2f}')
    print(f'• Price range: ${tv_df["Fill Price"].min():.2f} - ${tv_df["Fill Price"].max():.2f}')
    print(f'• Total shares traded: {tv_df["Qty"].sum():,}')
    
    print(f'\n🎯 EXCHANGE DISTRIBUTION:')
    exchange_counts = tv_df['Symbol'].apply(lambda x: x.split(':')[0]).value_counts()
    for exchange, count in exchange_counts.items():
        print(f'• {exchange}: {count} trades ({count/len(tv_df)*100:.1f}%)')
    
    print(f'\n📅 DATE FORMAT VERIFICATION:')
    first_row_date = tv_df['Closing Time'].iloc[0]
    print(f'• First row date: {first_row_date}')
    format_check = "✅ YYYY-MM-DD" if len(first_row_date) == 10 and first_row_date.count('-') == 2 else "❌ Invalid format"
    print(f'• Format check: {format_check}')
    
    print(f'\n🏆 TOP 5 TRADES (for manual verification):')
    top_5_sample = top_trades.head(5)
    for i, (_, trade) in enumerate(top_5_sample.iterrows(), 1):
        print(f'{i}. {trade["ticker"].upper()}: ${trade["entry_price"]:.2f} → {trade["profit_loss_pct"]:.2f}%')
    
    print(f'\n🎯 TRADINGVIEW IMPORT READY!')
    print('=' * 70)
    print(f'📁 File: {output_file}')
    print(f'📊 Trades: {len(tv_df)}')
    print(f'💰 Total P&L of exported trades: ${top_trades["profit_loss"].sum():,.0f}')
    print(f'📈 Avg profit per exported trade: {top_trades["profit_loss_pct"].mean():.2f}%')
    print(f'🛡️ Safety filters: Price ceiling $500, Floor $1.00')
    print(f'✅ Ready for TradingView Portfolio import!')
    
    # Sample of the file content
    print(f'\n📋 SAMPLE FILE CONTENT (First 3 rows):')
    print('-' * 50)
    print(tv_df.head(3).to_string(index=False))

if __name__ == "__main__":
    prepare_tv_import()
