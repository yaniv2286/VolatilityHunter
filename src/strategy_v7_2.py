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
    Allow BUY signals when stoch_k is between 32 and 100
    """
    if len(df) < 10:
        return False, "Insufficient data"
    
    latest = df.iloc[-1]
    stoch_k = latest['stoch_k']
    
    # Entry Zone: 32 to 100 (expanded from 32-80)
    in_entry_zone = 32.0 <= stoch_k <= 100.0
    
    return in_entry_zone, f"Stochastic K: {stoch_k:.2f} (Entry Zone: 32-100)"

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
    MANDATORY: Exit if stoch_k < stoch_d (Red crosses below Yellow) - Stochastic Roll-over
    Optional: Exit if price < sma_200 (additional safety)
    """
    if len(df) < 2:
        return False, "Insufficient data"
    
    latest = df.iloc[-1]
    price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
    stoch_k = latest['stoch_k']
    stoch_d = latest['stoch_d']
    
    sma_200 = latest['sma_200']
    
    # V7.3 BLUEPRINT EXIT: Stochastic Roll-over (MANDATORY)
    k_below_d = stoch_k < stoch_d
    
    # Additional safety: SMA 200 break
    price_below_sma = price < sma_200
    
    # V7.3: Stochastic Roll-over is the primary exit for Standard trades
    should_exit = k_below_d or price_below_sma
    
    exit_reason = []
    if k_below_d:
        exit_reason.append("Blueprint Exit: Stoch_K < Stoch_D (Roll-over)")
    if price_below_sma:
        exit_reason.append("Safety: Price < SMA_200")
    
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
    if df is None or len(df) < 252:
        return {
            'signal': 'HOLD',
            'reason': 'Insufficient data (need 252+ days)',
            'indicators': {}
        }
    
    # Add all indicators
    df = add_indicators_v7_2(df)
    
    latest = df.iloc[-1]
    price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
    
    # Safety: Check for missing indicators
    if pd.isna(latest['stoch_k']) or pd.isna(latest['stoch_d']):
        return {
            'signal': 'HOLD',
            'reason': 'Stochastic indicators not available',
            'indicators': {}
        }
    
    # V7.3 DYNAMIC GUARDRAILS: Liquidity Filter
    price = latest['adjClose'] if 'adjClose' in latest else latest['Close'] if 'Close' in latest else latest['close']
    volume_col = 'Volume' if 'Volume' in latest else 'volume' if 'volume' in latest else 'adjVolume'
    volume = latest[volume_col]
    dollar_volume = price * volume
    
    if dollar_volume < 1000000:  # $1M minimum daily dollar volume
        return {
            'signal': 'HOLD',
            'reason': f'Liquidity Filter: ${dollar_volume:,.0f} < $1M minimum',
            'indicators': {
                'price': price,
                'volume': volume,
                'dollar_volume': dollar_volume
            }
        }
    
    # V7.3 DYNAMIC GUARDRAILS: Price Ceiling Shield
    if price > 500:
        return {
            'signal': 'HOLD',
            'reason': f'Price Ceiling Shield: ${price:.2f} > $500 maximum (split-adjustment ghost)',
            'indicators': {
                'price': price
            }
        }
    
    # v7.2 ENTRY LOGIC
    
    # 1. Entry Zone Check
    in_entry_zone, entry_zone_reason = check_entry_zone_v7_2(df)
    if not in_entry_zone:
        return {
            'signal': 'HOLD',
            'reason': f'Entry Zone Failed: {entry_zone_reason}',
            'indicators': {
                'stoch_k': latest['stoch_k'],
                'stoch_d': latest['stoch_d'],
                'price': price
            }
        }
    
    # 2. Crossover Check
    k_above_d, crossover_reason = check_crossover_v7_2(df)
    if not k_above_d:
        return {
            'signal': 'HOLD',
            'reason': f'Crossover Failed: {crossover_reason}',
            'indicators': {
                'stoch_k': latest['stoch_k'],
                'stoch_d': latest['stoch_d'],
                'price': price
            }
        }
    
    # 3. Trend Check (price above SMA_200)
    sma_200 = latest['sma_200']
    if pd.isna(sma_200) or price <= sma_200:
        return {
            'signal': 'HOLD',
            'reason': f'Trend Failed: Price (${price:.2f}) <= SMA_200 (${sma_200:.2f})',
            'indicators': {
                'stoch_k': latest['stoch_k'],
                'stoch_d': latest['stoch_d'],
                'price': price,
                'sma_200': sma_200
            }
        }
    
    # 4. Volume Check
    volume_col = 'Volume' if 'Volume' in latest else 'volume' if 'volume' in latest else 'adjVolume'
    current_volume = latest[volume_col]
    volume_sma = latest['volume_sma']
    if pd.isna(volume_sma) or volume_sma <= 0 or current_volume <= volume_sma:
        return {
            'signal': 'HOLD',
            'reason': f'Volume Failed: Current ({current_volume:,.0f}) <= SMA ({volume_sma:,.0f})',
            'indicators': {
                'stoch_k': latest['stoch_k'],
                'stoch_d': latest['stoch_d'],
                'price': price,
                'current_volume': current_volume,
                'volume_sma': volume_sma
            }
        }
    
    # ALL ENTRY CONDITIONS PASSED - GENERATE BUY SIGNAL
    indicators = {
        'stoch_k': latest['stoch_k'],
        'stoch_d': latest['stoch_d'],
        'price': price,
        'sma_200': sma_200,
        'current_volume': current_volume,
        'volume_sma': volume_sma,
        'sma_25': latest['sma_25'],
        'sma_50': latest['sma_50'],
        'sma_100': latest['sma_100'],
        'atr': latest['atr']
    }
    
    reason_parts = [
        'v7.2 HYBRID STRATEGY: BUY SIGNAL',
        f'Entry Zone: Stoch_K ({latest["stoch_k"]:.2f}) in [32-100]',
        f'Crossover: Stoch_K ({latest["stoch_k"]:.2f}) > Stoch_D ({latest["stoch_d"]:.2f})',
        f'Trend: Price (${price:.2f}) > SMA_200 (${sma_200:.2f})',
        f'Volume: Current ({current_volume:,.0f}) > SMA ({volume_sma:,.0f})'
    ]
    
    return {
        'signal': 'BUY',
        'reason': ' | '.join(reason_parts),
        'indicators': indicators,
        'is_power_stock': False  # All trades start as Standard
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
