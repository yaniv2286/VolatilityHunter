import pandas as pd
import numpy as np
from src.config import STRATEGY_PARAMS
from src.notifications import log_info, log_error, alert_signal

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
        start_price = df.iloc[0]['Close']
        end_price = df.iloc[-1]['Close']
        
        actual_days = (df.iloc[-1]['date'] - df.iloc[0]['date']).days
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
