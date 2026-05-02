# Better Solutions for VolatilityHunter Issues

**Date:** 2026-04-24  
**Context:** v8.2 backtest failed (-78% trade reduction). Need more nuanced approaches.

---

## What We Learned from v8.2 Failure

The multi-day volume filter was **too restrictive**. 2 consecutive days of 1.5× volume surge eliminated 78% of trades. This tells us:
- The original single-day surge, while noisy, captures real opportunities
- We need **smarter filters, not stricter filters**
- Test improvements **one at a time**, not all together

---

## Revised Solutions (More Nuanced)

### 1. Trailing Stop for Standard Positions ✅ TESTING NOW

**Original Problem:** Standard positions give back massive gains on reversals.

**v8.1.1 Solution:** 2× ATR trailing stop from highest price (only after stock moves above entry).

**Why This Should Work:**
- Protects winners without hurting entry frequency
- Only triggers after profit, reduces premature exits
- Conservative 2× ATR (not 3×) balances protection vs. flexibility

**Expected Impact:** +1 to +3% CAGR, -2 to -4% DD

---

### 2. Volume Filter Improvement (Instead of Multi-Day)

**Original Problem:** Single-day volume surge catches one-off events.

**Better Solution:** **Volume Surge + Price Confirmation**

```python
# Instead of: volume >= 1.5 × SMA30 for 2 days
# Use: volume surge AND price moves up on the surge day

volume_surge = volume >= vsma * 1.5
price_up = close > close.shift(1)  # Price moved up today
volume_with_price = volume_surge & price_up
```

**Why This Works:**
- Volume surge with price up confirms institutional buying
- Volume surge with price down (earnings miss) gets filtered out
- Still allows single-day entries (doesn't kill trade count)

**Alternative:** **Volume Surge + Above Average Range**

```python
range_today = (high - low) / close
range_avg = ((high - low) / close).rolling(20).mean()
volume_with_range = volume_surge & (range_today > range_avg * 1.2)
```

---

### 3. Real GICS Sector Mapping (Critical Risk Fix)

**Original Problem:** First-letter bucketing is meaningless.

**Solution Options:**

**Option A: Tiingo Metadata Integration**
```python
# Tiingo provides sector info in their metadata API
def get_sector_tiingo(ticker):
    metadata = tiingo.get_metadata(ticker)
    return metadata.get('sector', 'Unknown')
```

**Option B: Static GICS Mapping CSV**
```python
# Download GICS classification from S&P or use existing mapping
gics_df = pd.read_csv('data/gics_mapping.csv')  # ticker, sector columns
def get_sector_gics(ticker):
    return gics_df.loc[gics_df['ticker'] == ticker, 'sector'].iloc[0]
```

**Option C: Simple Industry Buckets (Better than first-letter)**
```python
# Use known ticker patterns
def get_sector_improved(ticker):
    tech_patterns = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMD', 'INTC', 'CSCO']
    finance_patterns = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP']
    # ... etc
    if ticker in tech_patterns:
        return 'Technology'
    elif ticker in finance_patterns:
        return 'Financials'
    # Fallback to first-letter for unknown
    return get_sector_first_letter(ticker)
```

**Recommendation:** Start with Option C (quick win), then Option A (best long-term).

---

### 4. Fresh Parquet Data Pipeline

**Original Problem:** Indicators compute on stale data.

**Solution: Incremental Parquet Updates**

```python
# In smart_data_loader_factory.py
def update_parquet_with_latest(ticker, latest_price):
    parquet_path = DATA_DIR / f"{ticker.lower()}.parquet"
    df = pd.read_parquet(parquet_path)
    
    # Get last date in parquet
    last_date = df.index[-1]
    today = pd.Timestamp.now().normalize()
    
    # If today > last_date, append today's data
    if today > last_date:
        new_row = pd.DataFrame({
            'date': [today],
            'close': [latest_price],
            # Fill other columns with NaN or estimates
            'volume': [np.nan],
            'high': [latest_price],  # Assume close=high=low for simplicity
            'low': [latest_price],
            'open': [latest_price],
        })
        df = pd.concat([df, new_row], ignore_index=True)
        df = df.set_index('date')
        df.to_parquet(parquet_path)
        return True
    return False
```

**Better Solution:** **Batch Update All Parquets Daily**

```python
def update_all_parquets_daily():
    """Run this once per day after market close"""
    all_tickers = load_ticker_universe()
    latest_prices = fetch_latest_prices_tiingo(all_tickers)
    
    for ticker, price in latest_prices.items():
        update_parquet_with_latest(ticker, price)
    
    logger.info(f"Updated {len(latest_prices)} parquet files")
```

**Integration:** Add to `daily_trading_loop.py` after price fetch.

---

### 5. Normalized Scoring Function

**Original Problem:** Scale imbalance favors high-return stocks.

**Solution A: Percentile Ranking**
```python
def calculate_score_normalized(annual_returns, stoch_scores):
    # Convert to percentiles (0-1 scale)
    annual_pct = pd.Series(annual_returns).rank(pct=True).values
    stoch_pct = stoch_scores  # Already 0-1
    
    # Weighted combination
    return 0.6 * annual_pct + 0.4 * stoch_pct
```

**Solution B: Capped Returns**
```python
def calculate_score_capped(annual_returns, stoch_scores):
    # Cap annual returns at 200% to prevent domination
    annual_capped = np.minimum(annual_returns, 2.0)
    return 0.6 * annual_capped + 0.4 * stoch_scores
```

**Solution C: Z-Score Normalization**
```python
def calculate_score_zscore(annual_returns, stoch_scores):
    # Convert to z-scores, then to 0-1
    annual_z = (annual_returns - np.mean(annual_returns)) / np.std(annual_returns)
    annual_norm = (annual_z - annual_z.min()) / (annual_z.max() - annual_z.min())
    
    return 0.6 * annual_norm + 0.4 * stoch_scores
```

**Recommendation:** Start with Solution B (capped returns) - simplest and most intuitive.

---

## Implementation Priority (Revised)

### Phase 1: Test Trailing Stop Only (v8.1.1)
- **Status:** Currently running backtest
- **Expected:** +1-3% CAGR, -2-4% DD
- **If successful:** Deploy immediately

### Phase 2: Volume + Price Confirmation
- **Replace:** Multi-day volume requirement
- **Expected:** Similar trade count to v8.1, better quality entries
- **Implementation:** Modify `scan_universe()` in `strategy_engine.py`

### Phase 3: Real Sector Mapping
- **Start:** Option C (improved buckets)
- **Long-term:** Option A (Tiingo metadata)
- **Impact:** Risk reduction, not performance

### Phase 4: Fresh Parquet Data
- **Implementation:** Daily batch update
- **Impact:** Fresh indicators, better signals
- **Risk:** Data pipeline complexity

### Phase 5: Normalized Scoring
- **Start:** Capped returns (simple)
- **Impact:** Better candidate selection
- **Risk:** May change strategy character

---

## Key Insights

### What the v8.2 Failure Taught Us

1. **Entry frequency matters more than entry quality** (for this strategy)
2. **The original filters, while noisy, capture real momentum**
3. **Incremental testing is essential** - don't bundle changes
4. **78% trade reduction = strategy death**, regardless of individual trade quality

### The Right Approach

1. **Preserve trade count** - don't let filters eliminate opportunities
2. **Improve exits first** - trailing stops have clear upside without affecting entries
3. **Refine entries gradually** - small tweaks, not overhauls
4. **Measure everything** - backtest each change in isolation

### Expected Final Impact (Conservative)

| Improvement | CAGR Impact | DD Impact | Confidence |
|-------------|-------------|-----------|------------|
| Trailing stop | +1 to +3% | -2 to -4% | High |
| Volume+price | +0.5 to +1% | -1 to -2% | Medium |
| Real sectors | 0% | -2 to -4% | High (risk) |
| Fresh data | +1 to +3% | -1 to -3% | Medium |
| Normalized score | +0.5 to +1.5% | 0% | Medium |

**Total Expected:** +3 to +8% CAGR, -6 to -13% DD

This would take v8.1 from 5.8% CAGR / -22% DD to **9-14% CAGR / -9 to -16% DD** - a meaningful improvement while preserving the strategy's core character.

---

## Next Steps

1. ✅ **Wait for v8.1.1 results** (trailing stop only)
2. If successful: **Deploy v8.1.1** immediately
3. **Implement volume+price filter** as v8.1.2
4. **Test real sector mapping** (Option C first)
5. **Fix parquet data pipeline** (highest remaining opportunity)

The key is: **one change at a time, measure everything, preserve trade frequency.**
