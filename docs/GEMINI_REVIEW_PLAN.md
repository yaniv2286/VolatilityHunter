# VolatilityHunter Improvement Plan - Gemini Review Request

## Executive Summary

I'm working on improving a quantitative trading system called VolatilityHunter. The current system (v8.1) has 5.8% CAGR with -22% max drawdown. I want to get Gemini's feedback on our improvement plan before implementing.

**Current System Overview:**
- **Strategy:** Momentum + mean reversion hybrid on US equities
- **Universe:** 2,135 tickers, 10 positions max, 20% sizing
- **Entry:** Stochastic sweet spot (32-80), volume surge, momentum filter
- **Exit:** ATR stops, hard stops, overbought rollover, SMA200 breaks
- **Risk:** Regime filter, sector caps, volatility-adjusted sizing

**Problem:** Performance underperforms buy-and-hold SPY with higher risk.

---

## Full Audit Findings

### Critical Issues Identified

1. **Fake Sector Diversification** (HIGH RISK)
   - Current: First-letter bucketing (AAPL=Tech, NVDA=Financials)
   - Impact: Sector cap of 3 provides zero actual diversification
   - Evidence: AAPL and AMD both "Technology" but NVDA is "Financials"

2. **Stale Parquet Data** (PERFORMANCE ISSUE)
   - Current: Parquet files not updated daily, indicators compute on old data
   - Problem: `load_ticker_with_latest()` tries Yahoo Finance but `yf` not imported
   - Impact: Entry/exit signals based on stale indicators

3. **No Trailing Stop for Standard Positions** (PERFORMANCE ISSUE)
   - Current: Only Power Stocks get trailing stops (3× ATR)
   - Problem: Standard positions give back massive gains on reversals
   - Example: Stock rallies +30% then drops to +5% → no exit triggered

4. **Scale-Imbalanced Scoring** (SELECTION ISSUE)
   - Current: `score = 0.6 × annual_return + 0.4 × stoch_score`
   - Problem: Annual return unbounded (0.15 to 5.0+), stochastic bounded (0-1)
   - Impact: High-return stocks dominate ranking, stochastic becomes decorative

5. **Single-Day Volume Surge** (NOISE ISSUE)
   - Current: Volume ≥ 1.5× SMA30 on single latest bar triggers entry
   - Problem: One-off events (earnings, news) trigger false entries
   - Need: Confirmation without killing trade frequency

6. **Calendar vs Trading Days Bug** (CONSISTENCY ISSUE)
   - Current: Time stop uses `(today - entry_dt).days` (calendar days)
   - Backtest uses bar index (trading days)
   - Impact: Different behavior between live and backtest

---

## Initial Failed Attempt (v8.2)

I implemented all improvements together in v8.2:
- Trailing stop for standard positions
- Multi-day volume confirmation (2 consecutive days)
- Trading days for time stop
- Real GICS sectors (placeholder)
- Normalized scoring
- Fresh parquet data (placeholder)

**Result:** CATASTROPHIC FAILURE
- Trade count: 41,786 → 8,892 (-78% reduction)
- CAGR: 23.33% → 10.40% (-12.93%)
- Max DD: -28.13% → -40.06% (worse)

**Root Cause:** Multi-day volume filter was too restrictive. By requiring 2 consecutive days of volume surge, we eliminated most momentum opportunities. The original single-day surge, while noisy, captures real moves.

---

## Revised Incremental Approach

### Phase 1: Trailing Stop Only (v8.1.1) - TESTING NOW

**Change:** Add 2× ATR trailing stop for standard positions
```python
# Only triggers after stock moves above entry
if not is_power and atr > 0 and highest > entry:
    trailing_stop_price = highest - 2.0 * atr
    if price < trailing_stop_price:
        exit('Trailing stop')
```

**Expected Impact:**
- CAGR: +1 to +3%
- Max DD: -2 to -4%
- Trade count: Same as v8.1 (preserves frequency)

**Status:** Currently backtesting, results pending

---

## Proposed Solutions (Need Gemini Feedback)

### Solution A: Volume + Price Confirmation Filter

**Problem:** Single-day volume surge catches false entries
**Proposed Fix:** Require volume surge AND price movement up

```python
volume_surge = volume >= 1.5 * volume_sma_30
price_up = close > close.shift(1)  # Price moved up today
volume_with_price = volume_surge & price_up
```

**Why This Works:**
- Volume surge with price up = institutional buying
- Volume surge with price down = earnings miss/news (filtered out)
- Preserves single-day entry frequency

**Alternative:** Volume surge + above-average range
```python
range_today = (high - low) / close
range_avg = ((high - low) / close).rolling(20).mean()
volume_with_range = volume_surge & (range_today > range_avg * 1.2)
```

**Questions for Gemini:**
1. Which approach is better for momentum strategies?
2. Will this significantly reduce trade count?
3. Are there better volume confirmation methods?

---

### Solution B: Real GICS Sector Mapping

**Problem:** First-letter bucketing provides zero diversification
**Proposed Options:**

**Option 1: Static Mapping (Quick Win)**
```python
def get_sector_improved(ticker):
    tech_patterns = ['AAPL', 'MSFT', 'GOOGL', 'NVDA', 'AMD', 'INTC', 'CSCO']
    finance_patterns = ['JPM', 'BAC', 'WFC', 'GS', 'MS', 'C', 'AXP']
    # Map known tickers, fallback to first-letter
```

**Option 2: Tiingo Metadata API (Best Long-term)**
```python
def get_sector_tiingo(ticker):
    metadata = tiingo.get_metadata(ticker)
    return metadata.get('sector', 'Unknown')
```

**Questions for Gemini:**
1. Which approach is more maintainable?
2. Should I use official GICS classifications?
3. How to handle sector mapping for ETFs/ADRs?

---

### Solution C: Fresh Parquet Data Pipeline

**Problem:** Indicators compute on stale data
**Proposed Solution:** Daily batch updates

```python
def update_all_parquets_daily():
    all_tickers = load_ticker_universe()
    latest_prices = fetch_latest_prices_tiingo(all_tickers)
    
    for ticker, price in latest_prices.items():
        parquet_path = DATA_DIR / f"{ticker.lower()}.parquet"
        df = pd.read_parquet(parquet_path)
        
        # Append today's data if newer than last date
        if today > df.index[-1]:
            new_row = {
                'date': today,
                'close': price,
                'high': price,  # Simplified
                'low': price,
                'open': price,
                'volume': np.nan
            }
            df = pd.concat([df, pd.DataFrame([new_row]).set_index('date')])
            df.to_parquet(parquet_path)
```

**Questions for Gemini:**
1. Is this approach robust for production?
2. How to handle missing data (volume, high/low)?
3. Should I use intraday data for better accuracy?

---

### Solution D: Normalized Scoring Function

**Problem:** Scale imbalance favors high-return stocks
**Proposed Options:**

**Option 1: Capped Returns (Simple)**
```python
annual_capped = min(annual_return, 2.0)  # Cap at 200%
score = 0.6 * annual_capped + 0.4 * stoch_score
```

**Option 2: Percentile Ranking**
```python
annual_pct = pd.Series(annual_returns).rank(pct=True).values
score = 0.6 * annual_pct + 0.4 * stoch_score
```

**Option 3: Z-Score Normalization**
```python
annual_z = (annual_returns - np.mean(annual_returns)) / np.std(annual_returns)
annual_norm = (annual_z - annual_z.min()) / (annual_z.max() - annual_z.min())
score = 0.6 * annual_norm + 0.4 * stoch_score
```

**Questions for Gemini:**
1. Which method preserves strategy character best?
2. Will capping returns hurt outlier detection?
3. Is percentile ranking more stable over time?

---

## Expected Combined Impact

**Conservative Estimates:**
- Trailing stop: +1-3% CAGR, -2-4% DD
- Volume+price: +0.5-1% CAGR, -1-2% DD
- Real sectors: 0% CAGR, -2-4% DD (risk reduction)
- Fresh data: +1-3% CAGR, -1-3% DD
- Normalized score: +0.5-1.5% CAGR, 0% DD

**Total Expected:** +3 to +8% CAGR, -6 to -13% DD

**Target Performance:** 9-14% CAGR with -9 to -16% DD

---

## Key Questions for Gemini

### Strategic Questions
1. Is the incremental approach (one change at a time) optimal?
2. Should I prioritize exits over entries for momentum strategies?
3. Is 78% trade reduction always bad, or can higher quality trades compensate?

### Technical Questions
1. Which volume confirmation method works best for momentum?
2. What's the best approach for real sector mapping?
3. How to handle missing data in daily parquet updates?

### Risk Management
1. Are trailing stops too tight for momentum stocks?
2. Should sector caps be based on real GICS or custom buckets?
3. How to validate that improvements work in live trading?

### Implementation
1. Should I implement all solutions or focus on highest-impact ones?
2. How to test these changes without affecting live trading?
3. What metrics should I track to measure improvement?

---

## Current Status

**Completed:**
- Full algorithm audit completed
- v8.2 implemented (failed due to over-filtering)
- v8.1.1 created (trailing stop only)
- Better solutions documented

**In Progress:**
- Backtesting v8.1 vs v8.1.1 (trailing stop impact)
- Waiting for results (~15 minutes remaining)

**Next Steps:**
- Analyze trailing stop results
- If successful: Deploy v8.1.1
- Continue with incremental improvements based on Gemini feedback

---

## Request for Gemini

Please review this improvement plan and provide:
1. Feedback on the proposed solutions
2. Suggestions for better approaches
3. Priority ranking of improvements
4. Any potential issues or risks I missed
5. Alternative methods for volume confirmation and sector mapping

Thank you for your help!
