import pandas as pd
import numpy as np
from src.config import STRATEGY_PARAMS
from src.notifications import log_info, log_error, alert_signal

# Basic sector mapping for major stocks
SECTOR_MAPPING = {
    # Technology
    'AAPL': 'Technology', 'MSFT': 'Technology', 'GOOGL': 'Technology', 'GOOG': 'Technology',
    'META': 'Technology', 'NVDA': 'Technology', 'AMD': 'Technology', 'INTC': 'Technology',
    'CRM': 'Technology', 'ADBE': 'Technology', 'ORCL': 'Technology', 'CSCO': 'Technology',
    'PYPL': 'Technology', 'SQ': 'Technology', 'SHOP': 'Technology', 'SNOW': 'Technology',
    'CRWD': 'Technology', 'ZS': 'Technology', 'OKTA': 'Technology', 'PANW': 'Technology',
    'NET': 'Technology', 'DDOG': 'Technology', 'FTNT': 'Technology', 'CYBR': 'Technology',
    'PLTR': 'Technology', 'RBLX': 'Technology', 'U': 'Technology', 'OPEN': 'Technology',
    'RDFN': 'Technology', 'Z': 'Technology', 'COMP': 'Technology', 'SPOT': 'Technology',
    
    # Healthcare
    'JNJ': 'Healthcare', 'UNH': 'Healthcare', 'PFE': 'Healthcare', 'ABBV': 'Healthcare',
    'LLY': 'Healthcare', 'MRK': 'Healthcare', 'TMO': 'Healthcare', 'ABT': 'Healthcare',
    'DHR': 'Healthcare', 'BMY': 'Healthcare', 'AMGN': 'Healthcare', 'GILD': 'Healthcare',
    'REGN': 'Healthcare', 'VRTX': 'Healthcare', 'BIIB': 'Healthcare', 'MDT': 'Healthcare',
    'ISRG': 'Healthcare', 'SYK': 'Healthcare', 'BSX': 'Healthcare', 'ZTS': 'Healthcare',
    
    # Finance
    'BRK.B': 'Finance', 'JPM': 'Finance', 'V': 'Finance', 'MA': 'Finance', 'BAC': 'Finance',
    'WFC': 'Finance', 'GS': 'Finance', 'MS': 'Finance', 'C': 'Finance', 'AXP': 'Finance',
    'BLK': 'Finance', 'SPGI': 'Finance', 'ICE': 'Finance', 'CME': 'Finance', 'CB': 'Finance',
    'AON': 'Finance', 'AFL': 'Finance', 'MMC': 'Finance', 'AJG': 'Finance', 'TRV': 'Finance',
    'ALL': 'Finance', 'MET': 'Finance', 'PRU': 'Finance', 'LNC': 'Finance', 'HIG': 'Finance',
    
    # Consumer Discretionary
    'AMZN': 'Consumer', 'TSLA': 'Consumer', 'HD': 'Consumer', 'MCD': 'Consumer',
    'NKE': 'Consumer', 'LOW': 'Consumer', 'TJX': 'Consumer', 'TGT': 'Consumer',
    'COST': 'Consumer', 'WMT': 'Consumer', 'BKNG': 'Consumer', 'EXPE': 'Consumer',
    'DIS': 'Consumer', 'CMCSA': 'Consumer', 'NFLX': 'Consumer', 'ROKU': 'Consumer',
    'DECK': 'Consumer', 'LULU': 'Consumer', 'PTON': 'Consumer', 'EL': 'Consumer',
    
    # Energy
    'XOM': 'Energy', 'CVX': 'Energy', 'COP': 'Energy', 'EOG': 'Energy', 'SLB': 'Energy',
    'HAL': 'Energy', 'OXY': 'Energy', 'BP': 'Energy', 'SHEL': 'Energy', 'TOT': 'Energy',
    'ENB': 'Energy', 'KMI': 'Energy', 'WMB': 'Energy', 'ET': 'Energy', 'MPC': 'Energy',
    
    # Industrials
    'BA': 'Industrial', 'CAT': 'Industrial', 'GE': 'Industrial', 'HON': 'Industrial',
    'UPS': 'Industrial', 'RTX': 'Industrial', 'LMT': 'Industrial', 'NOC': 'Industrial',
    'GD': 'Industrial', 'DE': 'Industrial', 'MMM': 'Industrial', '3M': 'Industrial',
    'PH': 'Industrial', 'ITW': 'Industrial', 'ETN': 'Industrial', 'EMR': 'Industrial',
    'CARR': 'Industrial', 'OTIS': 'Industrial', 'GEV': 'Industrial', 'TXT': 'Industrial',
    
    # Materials
    'LIN': 'Materials', 'APD': 'Materials', 'ECL': 'Materials', 'DD': 'Materials',
    'DOW': 'Materials', 'NEM': 'Materials', 'FCX': 'Materials', 'BHP': 'Materials',
    'RIO': 'Materials', 'VALE': 'Materials', 'AA': 'Materials', 'ALB': 'Materials',
    
    # Utilities
    'NEE': 'Utilities', 'DUK': 'Utilities', 'SO': 'Utilities', 'AEP': 'Utilities',
    'XEL': 'Utilities', 'ED': 'Utilities', 'PEG': 'Utilities', 'WEC': 'Utilities',
    'EIX': 'Utilities', 'SRE': 'Utilities', 'CNP': 'Utilities', 'AWK': 'Utilities',
    
    # Real Estate
    'AMT': 'Real Estate', 'PLD': 'Real Estate', 'CCI': 'Real Estate', 'EQIX': 'Real Estate',
    'PSA': 'Real Estate', 'SPG': 'Real Estate', 'VTR': 'Real Estate', 'WELL': 'Real Estate',
    'DLR': 'Real Estate', 'EXR': 'Real Estate', 'AVB': 'Real Estate', 'EQR': 'Real Estate',
    
    # Communication Services
    'VZ': 'Communications', 'T': 'Communications', 'TMUS': 'Communications',
    'CHTR': 'Communications', 'CMCSA': 'Communications', 'DIS': 'Communications',
    'NFLX': 'Communications', 'FOXA': 'Communications', 'WBD': 'Communications',
    'PARA': 'Communications', 'TWC': 'Communications', 'CSCO': 'Communications',
    
    # Default for unknown stocks
}

def get_sector(ticker):
    """Get sector for a ticker, default to 'Unknown'."""
    return SECTOR_MAPPING.get(ticker, 'Unknown')

def check_sector_diversification(portfolio_positions, new_ticker, max_per_sector=3):
    """Check if adding new ticker would exceed sector limit."""
    if new_ticker not in SECTOR_MAPPING:
        return True  # Allow unknown sectors
    
    new_sector = SECTOR_MAPPING[new_ticker]
    
    # Count positions in the same sector
    sector_count = 0
    for ticker in portfolio_positions:
        if ticker in SECTOR_MAPPING and SECTOR_MAPPING[ticker] == new_sector:
            sector_count += 1
    
    return sector_count < max_per_sector

def calculate_sma(df, period):
    return df['Close'].rolling(window=period).mean()

def calculate_stochastic(df, k_period=14, d_period=3, smooth=3):
    low_min = df['Low'].rolling(window=k_period).min()
    high_max = df['High'].rolling(window=k_period).max()
    
    k_raw = 100 * ((df['Close'] - low_min) / (high_max - low_min))
    k_smooth = k_raw.rolling(window=smooth).mean()
    d = k_smooth.rolling(window=d_period).mean()
    
    return k_smooth, d

def calculate_cagr(df, years=2):
    if len(df) < 2:
        return 0.0
    
    try:
        # Use last N years of data instead of full history
        end_date = df.iloc[-1]['date']
        start_date = end_date - pd.Timedelta(days=years * 365.25)
        
        # Filter data to last N years
        recent_df = df[df['date'] >= start_date]
        
        if len(recent_df) < 2:
            # Fall back to full data if not enough recent data
            recent_df = df
        
        start_price = recent_df.iloc[0]['Close']
        end_price = recent_df.iloc[-1]['Close']
        
        actual_days = (recent_df.iloc[-1]['date'] - recent_df.iloc[0]['date']).days
        actual_years = actual_days / 365.25
        
        if actual_years <= 0 or start_price <= 0:
            return 0.0
        
        cagr = (((end_price / start_price) ** (1 / actual_years)) - 1) * 100
        return cagr
    except Exception as e:
        log_error(f"Error calculating CAGR: {e}")
        return 0.0

def add_indicators(df):
    df = df.copy()
    
    df['SMA_200'] = calculate_sma(df, STRATEGY_PARAMS['sma_period'])
    
    k, d = calculate_stochastic(
        df,
        k_period=STRATEGY_PARAMS['stochastic_k_period'],
        d_period=STRATEGY_PARAMS['stochastic_d_period'],
        smooth=STRATEGY_PARAMS['stochastic_smooth']
    )
    df['Stochastic_K'] = k
    df['Stochastic_D'] = d
    
    return df

def analyze_stock(df):
    if df is None or len(df) < STRATEGY_PARAMS['sma_period']:
        return {
            'signal': 'INSUFFICIENT_DATA',
            'reason': 'Not enough data for analysis',
            'indicators': {}
        }
    
    df = add_indicators(df)
    
    latest = df.iloc[-1]
    price = latest['Close']
    sma_200 = latest['SMA_200']
    stoch_k = latest['Stochastic_K']
    
    cagr = calculate_cagr(df)
    
    indicators = {
        'price': float(price),
        'sma_200': float(sma_200) if pd.notna(sma_200) else None,
        'stochastic_k': float(stoch_k) if pd.notna(stoch_k) else None,
        'cagr': float(cagr),
        'date': str(latest['date'])
    }
    
    # Quality score for prioritization: CAGR * (Stochastic_K / 100)
    quality_score = float(cagr) * (float(stoch_k) / 100.0) if pd.notna(stoch_k) else float(cagr)
    
    if pd.isna(sma_200) or pd.isna(stoch_k):
        return {
            'signal': 'INSUFFICIENT_DATA',
            'reason': 'Indicators not yet calculated',
            'indicators': indicators,
            'quality_score': quality_score
        }
    
    if cagr < STRATEGY_PARAMS['min_cagr']:
        return {
            'signal': 'HOLD',
            'reason': f'CAGR ({cagr:.2f}%) below minimum ({STRATEGY_PARAMS["min_cagr"]}%)',
            'indicators': indicators,
            'quality_score': quality_score
        }
    
    price_above_sma = price > sma_200
    in_sweet_spot = (STRATEGY_PARAMS['sweet_spot_lower'] <= stoch_k <= STRATEGY_PARAMS['sweet_spot_upper'])
    
    if price_above_sma and in_sweet_spot:
        return {
            'signal': 'BUY',
            'reason': f'Price above SMA 200 and Stochastic K in sweet spot ({stoch_k:.2f})',
            'indicators': indicators,
            'quality_score': quality_score
        }
    elif not price_above_sma:
        return {
            'signal': 'SELL',
            'reason': f'Price below SMA 200 (trend break)',
            'indicators': indicators,
            'quality_score': quality_score
        }
    else:
        return {
            'signal': 'HOLD',
            'reason': f'Stochastic K ({stoch_k:.2f}) outside sweet spot',
            'indicators': indicators,
            'quality_score': quality_score
        }

def scan_all_stocks(stock_data_dict):
    results = {
        'BUY': [],
        'SELL': [],
        'HOLD': [],
        'ERROR': []
    }
    
    for ticker, df in stock_data_dict.items():
        try:
            analysis = analyze_stock(df)
            signal = analysis['signal']
            
            result = {
                'ticker': ticker,
                'signal': signal,
                'reason': analysis['reason'],
                'indicators': analysis['indicators'],
                'quality_score': analysis.get('quality_score', 0)
            }
            
            if signal in ['BUY', 'SELL', 'HOLD', 'INSUFFICIENT_DATA']:
                if signal == 'INSUFFICIENT_DATA':
                    results['ERROR'].append(result)
                else:
                    results[signal].append(result)
                    
                if signal in ['BUY', 'SELL']:
                    alert_signal(
                        ticker,
                        signal,
                        analysis['indicators'].get('price', 0),
                        analysis['indicators']
                    )
            
        except Exception as e:
            log_error(f"Error analyzing {ticker}: {e}")
            results['ERROR'].append({
                'ticker': ticker,
                'signal': 'ERROR',
                'reason': str(e),
                'indicators': {}
            })
    
    return results

def get_portfolio_summary(scan_results):
    summary = {
        'total_stocks': sum(len(v) for v in scan_results.values()),
        'buy_signals': len(scan_results.get('BUY', [])),
        'sell_signals': len(scan_results.get('SELL', [])),
        'hold_signals': len(scan_results.get('HOLD', [])),
        'errors': len(scan_results.get('ERROR', [])),
        'buy_list': [s['ticker'] for s in scan_results.get('BUY', [])],
        'sell_list': [s['ticker'] for s in scan_results.get('SELL', [])]
    }
    return summary
