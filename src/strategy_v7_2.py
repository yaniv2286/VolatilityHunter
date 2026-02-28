import pandas as pd
import numpy as np
from src.notifications import log_info, log_error, alert_signal

# VolatilityHunter v7.2 Hybrid Strategy - Sweet Spot Blueprint
# This is our most critical update to align with the Sweet Spot Blueprint

def add_vectorized_guardrails(df):
    """
    V7.3 Vectorized Guardrails - Apply all filters at once using Pandas vectorization
    """
    df = df.copy()
    
    # Vectorized dollar_volume calculation
    close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
    volume_col = 'Volume' if 'Volume' in df.columns else 'volume' if 'volume' in df.columns else 'adjVolume'
    df['dollar_volume'] = df[close_col] * df[volume_col]
    
    # Vectorized liquidity filter
    df['liquidity_pass'] = df['dollar_volume'] >= 1000000  # $1M minimum
    
    # Vectorized price ceiling shield
    df['price_pass'] = df[close_col] <= 500  # $500 maximum
    
    # Vectorized Power Stock criteria (for rolling window calculation)
    df['power_stoch'] = df['stoch_k'] > 80
    df['price_above_all_smas'] = (
        (df[close_col] > df['sma_25']) &
        (df[close_col] > df['sma_50']) &
        (df[close_col] > df['sma_100']) &
        (df[close_col] > df['sma_200'])
    )
    df['high_volume'] = df[volume_col] > (df['volume_sma'] * 1.5)
    
    # Vectorized 2-day Power Confirmation using rolling window
    df['power_criteria'] = df['power_stoch'] & df['price_above_all_smas'] & df['high_volume']
    df['power_confirmation_2day'] = df['power_criteria'].rolling(window=2).sum() == 2
    
    # Vectorized Stochastic Roll-over
    df['stoch_roll_over'] = df['stoch_k'] < df['stoch_d']
    
    return df

def generate_vectorized_signals(df):
    """
    V7.3 Vectorized Signal Generation - No Python loops!
    """
    # Apply vectorized guardrails first
    df = add_vectorized_guardrails(df)
    
    # Vectorized entry conditions
    close_col = 'adjClose' if 'adjClose' in df.columns else 'close'
    entry_conditions = (
        df['liquidity_pass'] &  # Liquidity filter
        df['price_pass'] &  # Price ceiling
        (df[close_col] > df['sma_200']) &  # Trend
        (df['stoch_k'] >= 32) & (df['stoch_k'] <= 80) &  # Entry zone
        df['high_volume'] &  # Volume
        (df['cagr'] > 15.0)  # Growth
    )
    
    # Create signals DataFrame
    signals = pd.DataFrame(index=df.index, columns=['signal'], dtype=int)
    signals['signal'] = 0
    signals.loc[entry_conditions, 'signal'] = 1
    
    return signals, df

def calculate_stochastic_v7_2(df, k_period=10, d_period=3, smooth=3):
    """Calculate Stochastic Oscillator with safety fallbacks"""
    try:
        # Use adjusted columns if available, otherwise regular columns (handle capitalization)
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
        high_col = 'adjHigh' if 'adjHigh' in df.columns else 'High' if 'High' in df.columns else 'high'
        low_col = 'adjLow' if 'adjLow' in df.columns else 'Low' if 'Low' in df.columns else 'low'
        
        low_min = df[low_col].rolling(window=k_period).min()
        high_max = df[high_col].rolling(window=k_period).max()
        
        # Avoid division by zero
        denominator = high_max - low_min
        denominator = denominator.replace(0, np.nan)
        
        k_raw = 100 * ((df[close_col] - low_min) / denominator)
        k_smooth = k_raw.rolling(window=smooth).mean()
        
        # Calculate %D as 3-period SMA of %K (safety fallback)
        if 'Stochastic_D' in df.columns and not df['Stochastic_D'].isna().all():
            d = df['Stochastic_D']
        else:
            d = k_smooth.rolling(window=3).mean()  # Safety fallback: 3-period SMA of %K
        
        return k_smooth, d
    except Exception as e:
        log_error(f"Error calculating stochastic: {e}")
        return pd.Series([50] * len(df)), pd.Series([50] * len(df))

def calculate_sma_v7_2(df, period):
    """Calculate SMA with safety checks"""
    try:
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
        return df[close_col].rolling(window=period).mean()
    except Exception as e:
        log_error(f"Error calculating SMA {period}: {e}")
        # Use robust column detection in fallback
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
        if close_col in df.columns:
            return pd.Series([df[close_col].iloc[-1]] * len(df))
        else:
            return pd.Series([0] * len(df))

def calculate_volume_sma_v7_2(df, period=30):
    """Calculate Volume SMA with safety checks"""
    try:
        volume_col = 'Volume' if 'Volume' in df.columns else 'volume' if 'volume' in df.columns else 'adjVolume'
        return df[volume_col].rolling(window=period).mean()
    except Exception as e:
        log_error(f"Error calculating volume SMA: {e}")
        # Use robust column detection in fallback
        volume_col = 'Volume' if 'Volume' in df.columns else 'volume' if 'volume' in df.columns else 'adjVolume'
        if volume_col in df.columns:
            return pd.Series([df[volume_col].mean()] * len(df))
        else:
            return pd.Series([0] * len(df))

def calculate_atr_v7_2(df, period=14):
    """Calculate ATR with safety checks"""
    try:
        close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
        high_col = 'adjHigh' if 'adjHigh' in df.columns else 'High' if 'High' in df.columns else 'high'
        low_col = 'adjLow' if 'adjLow' in df.columns else 'Low' if 'Low' in df.columns else 'low'
        
        high_low = df[high_col] - df[low_col]
        high_close = np.abs(df[high_col] - df[close_col].shift(1))
        low_close = np.abs(df[low_col] - df[close_col].shift(1))
        
        true_range = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return true_range.rolling(window=period, min_periods=1).mean()
    except Exception as e:
        log_error(f"Error calculating ATR: {e}")
        return pd.Series([1.0] * len(df))

def add_indicators_v7_2(df):
    """Add all technical indicators for v7.2 Hybrid Strategy"""
    df = df.copy()
    
    # Calculate Stochastic DNA
    stoch_k, stoch_d = calculate_stochastic_v7_2(df)
    df['stoch_k'] = stoch_k
    df['stoch_d'] = stoch_d
    
    # Calculate SMAs
    df['sma_25'] = calculate_sma_v7_2(df, 25)
    df['sma_50'] = calculate_sma_v7_2(df, 50)
    df['sma_100'] = calculate_sma_v7_2(df, 100)
    df['sma_200'] = calculate_sma_v7_2(df, 200)
    
    # Vectorized volume indicators
    df['volume_sma'] = calculate_volume_sma_v7_2(df, 30)
    df['volume_sma_30'] = df['volume_sma']  # Map for compatibility
    
    # Calculate ATR
    df['atr'] = calculate_atr_v7_2(df, 14)
    
    return df

def check_entry_zone_v7_2(df):
    """
    v7.2 Entry Zone: Stochastic DNA
    Allow BUY signals when stoch_k is between 32 and 80 (sweet spot)
    """
    if len(df) < 10:
        return False, "Insufficient data"
    
    latest = df.iloc[-1]
    stoch_k = latest['stoch_k']
    
    # Entry Zone: 32 to 80 (corrected sweet spot)
    in_entry_zone = 32.0 <= stoch_k <= 80.0
    
    return in_entry_zone, f"Stochastic K: {stoch_k:.2f} (Entry Zone: 32-80)"

def check_crossover_v7_2(df):
    """
    v7.2 Crossover: Red Line (%K) must be above Yellow Line (%D)
    """
    if len(df) < 3:
        return False, "Insufficient data for crossover"
    
    latest = df.iloc[-1]
    stoch_k = latest['stoch_k']
    stoch_d = latest['stoch_d']
    
    # Mandatory filter: %K must be above %D
    k_above_d = stoch_k > stoch_d
    
    return k_above_d, f"K ({stoch_k:.2f}) > D ({stoch_d:.2f}) = {k_above_d}"

def check_power_promotion_v7_2(df, current_position=None):
    """
    v7.3 Power Confirmation System
    Every open trade starts as "Standard"
    Promotion to Power Stock if conditions are met for 2 consecutive days
    """
    if len(df) < 200:
        return False, "Insufficient data for Power Stock analysis"
    
    latest = df.iloc[-1]
    previous = df.iloc[-2]
    
    # V7.3: Check both latest and previous day for Power Stock criteria
    for day_data, day_name in [(latest, "latest"), (previous, "previous")]:
        stoch_k = day_data['stoch_k']
        price = day_data['adjClose'] if 'adjClose' in day_data else day_data['Close'] if 'Close' in day_data else day_data['close']
        
        # Get all SMAs
        sma_25 = day_data['sma_25']
        sma_50 = day_data['sma_50']
        sma_100 = day_data['sma_100']
        sma_200 = day_data['sma_200']
        
        # Volume check
        volume_col = 'Volume' if 'Volume' in day_data else 'volume' if 'volume' in day_data else 'adjVolume'
        current_volume = day_data[volume_col]
        volume_sma = day_data['volume_sma']
        high_volume = current_volume > (volume_sma * 1.5) if volume_sma > 0 else False
        
        # Check if this day meets Power Stock criteria
        day_criteria = (
            stoch_k > 80 and  # Extreme overbought
            price > sma_25 and price > sma_50 and price > sma_100 and price > sma_200 and  # Vertical trend
            high_volume  # High volume momentum
        )
        
        if not day_criteria:
            return False, f"Power Confirmation failed on {day_name} day"
    
    # Both days passed - promote to Power Stock
    latest_stoch_k = latest['stoch_k']
    latest_price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
    volume_col = 'Volume' if 'Volume' in latest else 'volume' if 'volume' in latest else 'adjVolume'
    latest_volume = latest[volume_col]
    latest_volume_sma = latest['volume_sma']
    
    details = (f"V7.3 Power Confirmation: 2 consecutive days of "
              f"Stoch_K>80={latest_stoch_k>80}, "
              f"Above_All_SMAs={latest_price>latest['sma_25'] and latest_price>latest['sma_50'] and latest_price>latest['sma_100'] and latest_price>latest['sma_200']}, "
              f"High_Volume={latest_volume > (latest_volume_sma * 1.5) if latest_volume_sma > 0 else False}")
    
    return True, details

def check_standard_exit_v7_2(df, position):
    """
    V7.3 Blueprint Exit for Standard trades (is_power_stock = False)
    PRIMARY: Exit only on OVERBOUGHT rollover (K>70 AND K crosses below D) - lets winners ride
    SAFETY:  Exit if price < SMA_200 (trend breakdown)
    NOTE:    K<D crossover inside the Sweet Spot zone (32-70) is NOT an exit - it is normal
             oscillation and exiting there was the #1 cause of prematurely cutting winners.
    """
    if len(df) < 2:
        return False, "Insufficient data"

    latest = df.iloc[-1]
    close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
    price = latest[close_col]
    stoch_k = latest['stoch_k']
    stoch_d = latest['stoch_d']
    sma_200 = latest['sma_200']

    # PRIMARY EXIT: Overbought rollover only (K was above 70 and now crosses below D)
    overbought_rollover = (stoch_k < stoch_d) and (stoch_k > 70)

    # SAFETY EXIT: Long-term trend breakdown
    price_below_sma200 = (not pd.isna(sma_200)) and (price < sma_200)

    should_exit = overbought_rollover or price_below_sma200

    exit_reason = []
    if overbought_rollover:
        exit_reason.append(f"Overbought rollover: K({stoch_k:.1f}) < D({stoch_d:.1f}) while K>70")
    if price_below_sma200:
        exit_reason.append(f"Trend breakdown: Price({price:.2f}) < SMA200({sma_200:.2f})")

    return should_exit, " | ".join(exit_reason) if exit_reason else "No exit condition"

def check_power_exit_v7_2(df, position):
    """
    v7.2 Power Exit (is_power_stock = True)
    Shield mode: Exit ONLY if price < sma_25 OR price < 3.0x ATR trailing stop
    """
    if len(df) < 2:
        return False, "Insufficient data"
    
    latest = df.iloc[-1]
    price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
    
    sma_25 = latest['sma_25']
    atr = latest['atr']
    
    # Calculate trailing stop (3.0x ATR below highest price)
    highest_price = position.get('highest_price', price)
    trailing_stop = highest_price - (3.0 * atr)
    
    # Power exit conditions (Shield mode)
    price_below_sma_25 = price < sma_25
    below_trailing_stop = price < trailing_stop
    
    should_exit = price_below_sma_25 or below_trailing_stop
    
    exit_reason = []
    if price_below_sma_25:
        exit_reason.append("Price < SMA_25 (Power Stock exit)")
    if below_trailing_stop:
        exit_reason.append(f"Price < Trailing Stop (${trailing_stop:.2f})")
    
    return should_exit, " | ".join(exit_reason) if exit_reason else "No exit condition"

def analyze_stock_v7_2(df, ticker=None):
    """
    VolatilityHunter v7.2 Hybrid Strategy Analysis
    Implements the Sweet Spot Blueprint
    """
    _hold = lambda reason, indicators={}: {
        'signal': 'HOLD', 'reason': reason, 'indicators': indicators,
        'score': 0.0, 'should_enter': False, 'confidence': 0.0, 'is_power_stock': False
    }

    if df is None or len(df) < 252:
        return _hold('Insufficient data (need 252+ days)')

    # Add all indicators
    df = add_indicators_v7_2(df)

    latest = df.iloc[-1]
    close_col = 'adjClose' if 'adjClose' in df.columns else 'Close' if 'Close' in df.columns else 'close'
    volume_col = 'Volume' if 'Volume' in df.columns else 'volume' if 'volume' in df.columns else 'adjVolume'
    price = latest[close_col]
    volume = latest[volume_col]

    # Safety: Check for missing indicators
    if pd.isna(latest['stoch_k']) or pd.isna(latest['stoch_d']):
        return _hold('Stochastic indicators not available')

    stoch_k = latest['stoch_k']
    stoch_d = latest['stoch_d']
    sma_25  = latest['sma_25']
    sma_50  = latest['sma_50']
    sma_100 = latest['sma_100']
    sma_200 = latest['sma_200']
    volume_sma = latest['volume_sma']
    atr = latest['atr']

    # --- GUARD 1: Liquidity ($500K minimum) ---
    dollar_volume = price * volume
    if dollar_volume < 500000:
        return _hold(
            f'Liquidity: ${dollar_volume:,.0f} < $500K minimum',
            {'price': price, 'dollar_volume': dollar_volume}
        )

    # --- GUARD 2: Stochastic Sweet Spot zone (32-80) ---
    if not (32.0 <= stoch_k <= 80.0):
        return _hold(
            f'Stoch_K ({stoch_k:.2f}) outside Sweet Spot zone [32-80]',
            {'stoch_k': stoch_k, 'stoch_d': stoch_d, 'price': price}
        )

    # --- GUARD 3: Price above SMA_200 (long-term trend) ---
    if pd.isna(sma_200) or price <= sma_200:
        return _hold(
            f'Price ({price:.2f}) not above SMA_200 ({sma_200:.2f})',
            {'price': price, 'sma_200': sma_200, 'stoch_k': stoch_k}
        )

    # --- GUARD 4: Volume surge >= 1.5x 30-day SMA (fuel check) ---
    if pd.isna(volume_sma) or volume_sma <= 0 or volume < volume_sma * 1.5:
        return _hold(
            f'Volume ({volume:,.0f}) < 1.5x SMA ({volume_sma:,.0f}) - trading on fumes',
            {'price': price, 'stoch_k': stoch_k, 'volume': volume, 'volume_sma': volume_sma}
        )

    # --- GUARD 5: CAGR quality filter (only trade stocks with 15%+ annual growth) ---
    # Use 252-day price return as a proxy for 1-year CAGR
    if len(df) >= 252:
        price_252d_ago = df[close_col].iloc[-252]
        annual_return = (price / price_252d_ago) - 1 if price_252d_ago > 0 else 0
    else:
        annual_return = 0

    if annual_return < 0.15:
        return _hold(
            f'CAGR filter: 1yr return ({annual_return:.1%}) < 15% minimum quality threshold',
            {'price': price, 'stoch_k': stoch_k, 'annual_return': annual_return}
        )

    # --- ALL CONDITIONS PASSED: BUY SIGNAL ---
    indicators = {
        'stoch_k': stoch_k,
        'stoch_d': stoch_d,
        'price': price,
        'sma_25': sma_25,
        'sma_50': sma_50,
        'sma_100': sma_100,
        'sma_200': sma_200,
        'volume': volume,
        'volume_sma': volume_sma,
        'annual_return': annual_return,
        'atr': atr
    }

    reason = (
        f'BUY | Stoch_K={stoch_k:.1f} in [32-80] | Price ({price:.2f}) > SMA200 ({sma_200:.2f}) '
        f'| Vol {volume:,.0f} > 1.5x SMA {volume_sma:,.0f} | 1yr return {annual_return:.1%}'
    )

    # Score: normalized composite of signal quality (0.0-1.0)
    stoch_score = 1.0 - abs(stoch_k - 56) / 24  # best at midpoint of 32-80
    vol_ratio = min(volume / (volume_sma * 1.5), 2.0) / 2.0
    cagr_score = min(annual_return / 0.40, 1.0)  # normalized up to 40% CAGR
    score = round((stoch_score * 0.3 + vol_ratio * 0.35 + cagr_score * 0.35), 4)

    return {
        'signal': 'BUY',
        'reason': reason,
        'indicators': indicators,
        'is_power_stock': False,
        'score': score,
        'should_enter': True,
        'confidence': score
    }

def check_exit_conditions_v7_2(df, position):
    """
    v7.2 Dynamic Exit Logic
    Standard vs Power Stock exit rules
    """
    if position is None:
        return False, "No position to check"
    
    is_power_stock = position.get('is_power_stock', False)
    
    # Update highest price for trailing stop
    latest = df.iloc[-1]
    current_price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
    
    if current_price > position.get('highest_price', current_price):
        position['highest_price'] = current_price
    
    # Check for Power Promotion
    if not is_power_stock:
        should_promote, promotion_reason = check_power_promotion_v7_2(df, position)
        if should_promote:
            position['is_power_stock'] = True
            log_info(f"[POWER PROMOTION] {position.get('ticker', 'Unknown')} promoted to Power Stock: {promotion_reason}")
    
    # Apply appropriate exit logic
    if position.get('is_power_stock', False):
        should_exit, exit_reason = check_power_exit_v7_2(df, position)
    else:
        should_exit, exit_reason = check_standard_exit_v7_2(df, position)
    
    return should_exit, exit_reason

def calculate_position_size_v7_2(current_equity, entry_price, stop_loss_price, avg_volume_30d=None):
    """
    V7.3 Ironclad Math Guardrails - Absolute Position Sizing with Blueprint 20% Cap
    
    MANDATORY LIMITS:
    1. Blueprint 20% Cap: Never exceed 20% of portfolio equity in single position
    2. Micro-Stop Filter: Reject if stop distance < $0.01 (data corruption)
    3. Absolute Price Floor: Reject if entry_price < $1.00
    4. 'Too Big' Filter: Cap shares at 10% of 30-day average volume
    """
    # IRONCLAD GUARDRAIL: Absolute Price Floor
    if entry_price < 1.00:
        return 0  # Reject penny stocks and corrupted data
    
    # IRONCLAD GUARDRAIL: Micro-Stop Filter
    stop_distance = entry_price - stop_loss_price
    if stop_distance < 0.01:
        return 0  # Data corruption detected - stop loss too close to entry
    
    # IRONCLAD GUARDRAIL: Invalid setup
    if entry_price <= stop_loss_price or stop_distance <= 0:
        return 0  # Invalid parameters, skip trade
    
    # Standard 1% risk calculation
    risk_amount = current_equity * 0.01  # 1% risk per trade
    shares_by_risk = risk_amount / stop_distance
    
    # IRONCLAD GUARDRAIL: Blueprint 20% Cap (Notional Limit)
    max_position_value = current_equity * 0.20  # 20% of portfolio equity MAX
    shares_by_notional = max_position_value / entry_price
    
    # Apply the more conservative limit
    shares = min(shares_by_risk, shares_by_notional)
    
    # IRONCLAD GUARDRAIL: 'Too Big' Filter (Liquidity Constraint)
    if avg_volume_30d is not None and avg_volume_30d > 0:
        max_shares_by_volume = avg_volume_30d * 0.10  # Max 10% of daily volume
        shares = min(shares, max_shares_by_volume)
    
    # Apply absolute limits (safety net)
    shares = max(1, min(int(shares), 10000))  # Min 1, max 10,000 shares
    
    # Final validation: Check position value against 20% cap
    final_position_value = shares * entry_price
    if final_position_value > max_position_value:
        # Force cap if somehow exceeded
        shares = int(max_position_value / entry_price)
        shares = max(1, shares)  # Ensure at least 1 share
    
    return shares

# Export the main functions
__all__ = [
    'analyze_stock_v7_2',
    'check_exit_conditions_v7_2',
    'calculate_position_size_v7_2',
    'add_indicators_v7_2',
    'check_power_promotion_v7_2'
]
