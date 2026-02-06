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
    """Calculate Simple Moving Average."""
    return df['Close'].rolling(window=period).mean()

def calculate_multiple_smas(df, periods=[25, 50, 100, 200]):
    """Calculate multiple SMAs for trend analysis."""
    smas = {}
    for period in periods:
        smas[f'SMA_{period}'] = calculate_sma(df, period)
    return smas

def calculate_volume_sma(df, period=30):
    """Calculate Volume Moving Average."""
    return df['Volume'].rolling(window=period).mean()

def check_volume_quality(df, min_days=30):
    """Check if current volume is above 30-day average."""
    if len(df) < min_days:
        return False, "Insufficient volume history"
    
    current_volume = df.iloc[-1]['Volume']
    avg_volume = calculate_volume_sma(df, min_days).iloc[-1]
    
    if pd.isna(avg_volume) or avg_volume == 0:
        return False, "Invalid volume data"
    
    volume_ratio = current_volume / avg_volume
    return volume_ratio >= 1.0, f"Volume ratio: {volume_ratio:.2f}"

def detect_w_formation(df, lookback=20):
    """Detect basic W formation (higher lows)."""
    if len(df) < lookback:
        return False, "Insufficient data for W detection"
    
    recent_data = df.tail(lookback)
    lows = recent_data['Low'].values
    
    # Find the two most recent significant lows
    low_points = []
    for i in range(1, len(lows)-1):
        if lows[i] < lows[i-1] and lows[i] < lows[i+1]:
            low_points.append((i, lows[i]))
    
    if len(low_points) >= 2:
        # Check if the right low is higher than the left low
        left_low = low_points[-2][1]
        right_low = low_points[-1][1]
        return right_low > left_low, f"W pattern: left={left_low:.2f}, right={right_low:.2f}"
    
    return False, "No W pattern detected"

def check_stochastic_crossover(df, days=3):
    """
    Check stochastic crossover and trend direction.
    Returns (bullish_crossover, trend_up, details)
    """
    if len(df) < days + 1:
        return False, False, "Insufficient data for crossover analysis"
    
    recent_data = df.tail(days + 1)
    
    # Get current and previous stochastic values
    curr_k = recent_data.iloc[-1]['Stochastic_K']
    curr_d = recent_data.iloc[-1]['Stochastic_D']
    prev_k = recent_data.iloc[-2]['Stochastic_K']
    prev_d = recent_data.iloc[-2]['Stochastic_D']
    
    # Check for NaN values
    if any(pd.isna([curr_k, curr_d, prev_k, prev_d])):
        return False, False, "Invalid stochastic data"
    
    # Bullish crossover: K was below D, now above D
    bullish_crossover = (prev_k <= prev_d) and (curr_k > curr_d)
    
    # Trend direction: K and D both trending up over period
    k_trend = curr_k > recent_data.iloc[0]['Stochastic_K']
    d_trend = curr_d > recent_data.iloc[0]['Stochastic_D']
    trend_up = k_trend and d_trend
    
    # Position check: K above D (required for BUY)
    k_above_d = curr_k > curr_d
    
    details = f"K={curr_k:.2f}, D={curr_d:.2f}, K>D={k_above_d}, Trend_Up={trend_up}"
    
    return k_above_d, trend_up, details

def detect_engulfing_candle(df):
    """
    Detect engulfing candlestick pattern.
    Returns (is_engulfing, details)
    """
    if len(df) < 2:
        return False, "Insufficient data for candlestick analysis"
    
    # Get last two candles
    prev_candle = df.iloc[-2]
    curr_candle = df.iloc[-1]
    
    # Calculate body sizes and ranges
    prev_body = abs(prev_candle['Close'] - prev_candle['Open'])
    curr_body = abs(curr_candle['Close'] - curr_candle['Open'])
    prev_range = prev_candle['High'] - prev_candle['Low']
    curr_range = curr_candle['High'] - curr_candle['Low']
    
    # Check for engulfing pattern
    # Current candle must completely engulf previous candle's range
    range_engulfed = (curr_candle['High'] >= prev_candle['High'] and 
                     curr_candle['Low'] <= prev_candle['Low'])
    
    # Current body should be larger than previous body
    body_engulfed = curr_body > prev_body
    
    # Check for minimal wicks (body should be most of the range)
    curr_body_ratio = curr_body / curr_range if curr_range > 0 else 0
    minimal_wicks = curr_body_ratio >= 0.7  # Body is 70%+ of range
    
    is_engulfing = range_engulfed and body_engulfed and minimal_wicks
    
    details = (f"Range_Engulfed={range_engulfed}, Body_Engulfed={body_engulfed}, "
              f"Body_Ratio={curr_body_ratio:.2f}, Minimal_Wicks={minimal_wicks}")
    
    return is_engulfing, details

def check_volume_consistency(df, days=5):
    """
    Check volume consistency and increasing trend.
    Returns (consistent, increasing, details)
    """
    if len(df) < days:
        return False, False, "Insufficient volume history"
    
    recent_volume = df.tail(days)['Volume']
    
    # Check for consistent volume (no major drops)
    volume_mean = recent_volume.mean()
    volume_std = recent_volume.std()
    
    # Volume is consistent if within 2 standard deviations
    consistent = all(abs(v - volume_mean) <= 2 * volume_std for v in recent_volume)
    
    # Check if volume is increasing (trend analysis)
    volume_trend = recent_volume.is_monotonic_increasing
    increasing = volume_trend
    
    # Alternative: check if recent volume > average of period
    current_vs_avg = recent_volume.iloc[-1] > recent_volume.mean()
    
    details = f"Consistent={consistent}, Increasing={increasing}, Current_vs_Avg={current_vs_avg}"
    
    return consistent, current_vs_avg, details

def detect_head_and_shoulders(df, lookback=60):
    """
    Detect Head and Shoulders pattern (bearish reversal).
    Returns (is_hns, details)
    """
    if len(df) < lookback:
        return False, "Insufficient data for H&S analysis"
    
    recent_data = df.tail(lookback)
    highs = recent_data['High'].values
    lows = recent_data['Low'].values
    
    # Find peaks (potential shoulders and head)
    peaks = []
    for i in range(1, len(highs)-1):
        if highs[i] > highs[i-1] and highs[i] > highs[i+1]:
            peaks.append((i, highs[i]))
    
    # Need at least 3 peaks for H&S pattern
    if len(peaks) < 3:
        return False, "Insufficient peaks for H&S pattern"
    
    # Check for classic H&S: left shoulder < head > right shoulder
    # with head being the highest peak
    try:
        # Get the three most recent significant peaks
        recent_peaks = peaks[-3:]
        
        left_shoulder_idx, left_shoulder_price = recent_peaks[0]
        head_idx, head_price = recent_peaks[1]
        right_shoulder_idx, right_shoulder_price = recent_peaks[2]
        
        # Head must be higher than both shoulders
        head_highest = head_price > left_shoulder_price and head_price > right_shoulder_price
        
        # Shoulders should be roughly similar height (within 20%)
        shoulder_similarity = abs(left_shoulder_price - right_shoulder_price) / max(left_shoulder_price, right_shoulder_price) < 0.2
        
        # Neckline should be declining (right shoulder lower than left)
        neckline_declining = right_shoulder_price < left_shoulder_price
        
        is_hns = head_highest and shoulder_similarity and neckline_declining
        
        details = (f"Head={head_price:.2f}, L_Shoulder={left_shoulder_price:.2f}, "
                  f"R_Shoulder={right_shoulder_price:.2f}, Head_Highest={head_highest}, "
                  f"Shoulder_Similarity={shoulder_similarity}, Neckline_Declining={neckline_declining}")
        
        return is_hns, details
        
    except Exception:
        return False, "Error analyzing H&S pattern"

def check_power_stock_exception(df):
    """
    Check if stock qualifies as Power Stock (overbought but strong).
    Returns (is_power_stock, details)
    """
    if len(df) < 200:
        return False, "Insufficient data for Power Stock analysis"
    
    latest = df.iloc[-1]
    stoch_k = latest['Stochastic_K']
    
    # Check if overbought (above 80%)
    overbought = stoch_k > 80
    
    if not overbought:
        return False, f"Not overbought (Stochastic K: {stoch_k:.2f})"
    
    # Check if above all major moving averages
    sma_25 = latest.get('SMA_25', 0)
    sma_50 = latest.get('SMA_50', 0)
    sma_100 = latest.get('SMA_100', 0)
    sma_200 = latest.get('SMA_200', 0)
    current_price = latest['Close']
    
    above_all_mas = (current_price > sma_25 and 
                    current_price > sma_50 and 
                    current_price > sma_100 and 
                    current_price > sma_200)
    
    # Check for high volume
    volume_sma = latest.get('Volume_SMA_30', 1)
    current_volume = latest['Volume']
    high_volume = current_volume > volume_sma * 1.5  # 50% above average
    
    is_power_stock = overbought and above_all_mas and high_volume
    
    details = (f"Overbought={overbought}, Above_All_MAs={above_all_mas}, "
              f"High_Volume={high_volume}, Stoch_K={stoch_k:.2f}")
    
    return is_power_stock, details

def is_friday_trading():
    """Check if today is Friday (for Friday Rule awareness)."""
    from datetime import datetime
    return datetime.now().weekday() == 4  # Friday is 4 (0=Monday)

def check_earnings_safety(ticker, days_ahead=5):
    """
    Check if ticker has earnings in the next N days.
    For now, returns True (safe) - can be enhanced with earnings API later.
    """
    # TODO: Implement earnings date check using API like:
    # - Yahoo Finance earnings calendar
    # - Alpha Vantage earnings endpoint
    # - Financial Modeling Prep
    
    # For now, assume all stocks are safe (no earnings data available)
    return True, "No earnings data available - assuming safe"

# List of high-risk stocks that frequently have volatile earnings
EARNINGS_SENSITIVE_STOCKS = {
    'TSLA', 'NVDA', 'AMD', 'NFLX', 'AMZN', 'META', 'GOOGL', 'MSFT',
    'AAPL', 'CRM', 'PYPL', 'SQ', 'SHOP', 'ROKU', 'SNAP', 'TWTR'
}

def is_earnings_sensitive(ticker):
    """Check if stock is known for earnings volatility."""
    return ticker in EARNINGS_SENSITIVE_STOCKS

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
        # Drop rows with invalid dates
        df_clean = df.dropna(subset=['date'])
        if len(df_clean) < 2:
            return 0.0
        
        # Try to use last N years of data, but fall back to what's available
        end_date = df_clean.iloc[-1]['date']
        target_start_date = end_date - pd.Timedelta(days=years * 365.25)
        
        # Filter data to last N years
        recent_df = df_clean[df_clean['date'] >= target_start_date]
        
        if len(recent_df) < 2:
            # Fall back to full data if not enough recent data
            recent_df = df_clean
        
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
    
    # Add multiple SMAs for trend analysis
    smas = calculate_multiple_smas(df, [25, 50, 100, 200])
    for name, sma in smas.items():
        df[name] = sma
    
    # Add volume analysis
    df['Volume_SMA_30'] = calculate_volume_sma(df, 30)
    
    k, d = calculate_stochastic(
        df,
        k_period=STRATEGY_PARAMS['stochastic_k_period'],
        d_period=STRATEGY_PARAMS['stochastic_d_period'],
        smooth=STRATEGY_PARAMS['stochastic_smooth']
    )
    df['Stochastic_K'] = k
    df['Stochastic_D'] = d
    
    return df

def analyze_stock(df, ticker=None):
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
    
    # CRITICAL: Complete Professional Trading Checklist Analysis
    volume_ok, volume_reason = check_volume_quality(df)
    volume_consistent, volume_increasing, volume_consistency_reason = check_volume_consistency(df)
    w_pattern, w_reason = detect_w_formation(df)
    engulfing_candle, engulfing_reason = detect_engulfing_candle(df)
    k_above_d, stochastic_trend_up, stochastic_reason = check_stochastic_crossover(df)
    earnings_safe, earnings_reason = check_earnings_safety(ticker) if ticker else (True, "No ticker provided")
    
    # Additional pattern analysis
    head_and_shoulders, hns_reason = detect_head_and_shoulders(df)
    is_power_stock, power_stock_reason = check_power_stock_exception(df)
    is_friday = is_friday_trading()
    
    # Add comprehensive indicators
    indicators.update({
        'sma_25': float(latest['SMA_25']) if pd.notna(latest['SMA_25']) else None,
        'sma_50': float(latest['SMA_50']) if pd.notna(latest['SMA_50']) else None,
        'sma_100': float(latest['SMA_100']) if pd.notna(latest['SMA_100']) else None,
        'volume_ratio': float(latest['Volume'] / latest['Volume_SMA_30']) if pd.notna(latest['Volume_SMA_30']) and latest['Volume_SMA_30'] > 0 else None,
        'w_pattern': w_pattern,
        'volume_ok': volume_ok,
        'volume_consistent': volume_consistent,
        'volume_increasing': volume_increasing,
        'engulfing_candle': engulfing_candle,
        'k_above_d': k_above_d,
        'stochastic_trend_up': stochastic_trend_up,
        'head_and_shoulders': head_and_shoulders,
        'is_power_stock': is_power_stock,
        'is_friday': is_friday
    })
    
    price_above_sma = price > sma_200
    in_sweet_spot = (STRATEGY_PARAMS['sweet_spot_lower'] <= stoch_k <= STRATEGY_PARAMS['sweet_spot_upper'])
    
    # PROFESSIONAL CHECKLIST: All critical elements must pass
    checklist_pass = True
    failure_reasons = []
    
    # 1. Trend: Price above SMA 200
    if not price_above_sma:
        checklist_pass = False
        failure_reasons.append("Price below SMA 200")
    
    # 2. Sweet Spot: Stochastic K in 32-80% range
    if not in_sweet_spot:
        checklist_pass = False
        failure_reasons.append(f"Stochastic K ({stoch_k:.2f}) outside sweet spot")
    
    # 3. Stochastic Crossover: K above D (RED > YELLOW)
    if not k_above_d:
        checklist_pass = False
        failure_reasons.append(f"Stochastic K not above D ({stochastic_reason})")
    
    # 4. Trend Direction: Stochastics trending upward
    if not stochastic_trend_up:
        checklist_pass = False
        failure_reasons.append(f"Stochastics not trending up ({stochastic_reason})")
    
    # 5. Volume Confirmation: Above 30-day average
    if not volume_ok:
        checklist_pass = False
        failure_reasons.append(f"Volume insufficient ({volume_reason})")
    
    # 6. Volume Consistency: Consistent or increasing
    if not volume_consistent:
        checklist_pass = False
        failure_reasons.append(f"Volume inconsistent ({volume_consistency_reason})")
    
    # 7. Candlestick Confirmation: Engulfing pattern preferred
    # Note: Not a hard requirement, but enhances signal quality
    
    # 8. Earnings Safety: No upcoming earnings
    if not earnings_safe:
        checklist_pass = False
        failure_reasons.append(f"Earnings risk ({earnings_reason})")
    
    # Final decision based on checklist
    if checklist_pass:
        reason_parts = [
            f'PROFESSIONAL CHECKLIST PASS',
            f'Price > SMA 200 (${sma_200:.2f})',
            f'Stochastic K ({stoch_k:.2f}) in sweet spot with K>D and uptrend',
            f'Volume confirmed ({volume_reason}) and consistent ({volume_consistency_reason})',
            f'Earnings safe ({earnings_reason})'
        ]
        
        # Add bonus confirmations
        if engulfing_candle:
            reason_parts.append(f'BONUS: Engulfing candle ({engulfing_reason})')
        if w_pattern:
            reason_parts.append(f'BONUS: W pattern ({w_reason})')
        if volume_increasing:
            reason_parts.append('BONUS: Volume increasing')
        
        return {
            'signal': 'BUY',
            'reason': ' | '.join(reason_parts),
            'indicators': indicators,
            'quality_score': quality_score * 1.5  # Bonus for passing full checklist
        }
    else:
        # Check for SELL signals
        sell_reasons = []
        
        # 1. Trend Break: Price below SMA 200
        if not price_above_sma:
            sell_reasons.append(f'Price below SMA 200 (trend break)')
        
        # 2. Head & Shoulders Pattern (bearish reversal)
        if head_and_shoulders:
            sell_reasons.append(f'Head & Shoulders pattern detected ({hns_reason})')
        
        # 3. Stochastic Breakdown (below sweet spot)
        if stoch_k < STRATEGY_PARAMS['sweet_spot_lower']:
            sell_reasons.append(f'Stochastic breakdown (K: {stoch_k:.2f} below 32%)')
        
        # If any SELL conditions met, return SELL signal
        if sell_reasons:
            return {
                'signal': 'SELL',
                'reason': ' | '.join(sell_reasons),
                'indicators': indicators,
                'quality_score': quality_score
            }
        
        # Check for Power Stock exception (hold overbought strong stocks)
        if is_power_stock:
            return {
                'signal': 'HOLD',
                'reason': f'POWER STOCK EXCEPTION - Hold overbought strong stock ({power_stock_reason})',
                'indicators': indicators,
                'quality_score': quality_score * 1.2  # Bonus for power stock
            }
        
        # Friday Rule awareness
        if is_friday:
            return {
                'signal': 'HOLD',
                'reason': f'FRIDAY RULE - Profit taking day | CHECKLIST FAIL: {" | ".join(failure_reasons)}',
                'indicators': indicators,
                'quality_score': quality_score
            }
        
        # Default HOLD for failed checklist
        return {
            'signal': 'HOLD',
            'reason': f'CHECKLIST FAIL: {" | ".join(failure_reasons)}',
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
            analysis = analyze_stock(df, ticker)
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
