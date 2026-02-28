# Sweet Spot Trading Blueprint

**Source**: Original blueprint rules as defined by the Architect  
**Implementation**: `src/strategy_v7_2.py`, `src/sweet_spot_strategy.py`, `scripts/daily_trading_loop.py`  
**Last verified**: 2026-02-28

---

## Implemented Parameters (live system)

| Parameter | Blueprint Rule | Implemented Value |
|-----------|---------------|-------------------|
| Position size | 20% max per trade | 20% of total equity |
| Hard stop loss | 1-5% trailing | 5% hard stop (`HARD_STOP_PCT = 0.05`) |
| Stochastic settings | K=10, D=3, Smooth=3 | K=14, D=3 (strategy_v7_2) |
| Stochastic sweet spot | 32-80 zone | `STOCH_LOW=32, STOCH_HIGH=80` |
| Volume filter | 30% of 30-day avg in first hour | Volume >= 1.5x 30-day SMA |
| Trend filter | Price above SMA200 | `price > sma_200` |
| CAGR momentum filter | Positive annual momentum | 252-day return >= 15% |
| Liquidity filter | Consistent daily volume | price x volume >= $500,000 |
| Max positions | 5-7 watchlist stocks | 10 simultaneous positions |
| Entry time | After 10:06 AM ET | EOD swing trading (no intraday) |
| Earnings | Never hold through earnings | Not yet automated (manual awareness) |
| Power stocks | Trend-following special rules | SMA25 exit + 3x ATR trailing stop |
| Drawdown circuit | Position reduction in drawdown | -10% DD -> 50% size, -20% -> 25% size |

---

## Signal Ranking Score (R9)

```python
stoch_score = 1.0 - abs(k - 56) / 24   # peaks at K=56, center of 32-80 zone
score       = 0.6 * annual_return + 0.4 * stoch_score
```

Candidates are sorted descending by `score`. Top N fill available position slots.

---

## Original Blueprint Rules

Here is the complete, updated Sweet Spot Trading Blueprint incorporating all the new rules, specific timeframe variations, technical settings, and expanded patterns.
The Updated Sweet Spot Trading Blueprint
1. Core Philosophy & Risk Management
Realistic Expectations: You must accept that you will lose 30% to 40% of the time (roughly 3 out of every 5 trades). The system is built to mitigate those losses while letting your winners run.
The 20% Rule: Never allocate more than 20% of your total account balance into a single stock position, regardless of your total account size.
Stop Losses: Always utilize a 1-5% trailing stop loss to act as an emergency brake.
Stock "Personalities": Do not trade hundreds of random stocks. Narrow your focus to a watchlist of 5 to 7 stocks that consistently hit their average volume. Trade only those so you can learn their unique behaviors.
2. Chart & Indicator Setup (TradingView)
Stochastic (Trend): Set K=10, D=3, and Smooth=3. The Red line is %K and the Yellow line is %D. Set the upper band to 80% and the lower band to 32%.
Volume: Apply a Yellow moving average line to your volume indicator, set to a 30-day average.
Moving Averages: Add four Simple Moving Averages (SMAs): 25-day, 50-day, 100-day, and 200-day. These act as "magnets" and indicate strong levels of support or resistance.
3. The Pre-Trade Checklist
Verify these conditions before executing any trade:
The 10:06 AM Rule: Do not trade before 10:06 AM EST. This allows overnight options, algorithmic trades, and overnight news volatility to settle.
Bid/Ask Spread Limit: To avoid market maker manipulation, the spread must be under 2 cents for stocks under $100. Allow up to 5 cents for $250+ stocks, and an absolute maximum of 20 cents for very expensive stocks (e.g., $300+).
Earnings Dates: Never hold a stock through its earnings report. It is a total "crapshoot" that causes unpredictable spikes and crashes. Always exit the position before the report drops.
The Friday Rule: Remember that Friday is typically "profit taking Friday," which often triggers sell-offs before the weekend.
4. Rules for Entering a Trade
Rule A: Identify the Trend (The "Sweet Spot" FLIPS by Timeframe)
For Swing Trading (1-5 Days) & Long-Term (Weekly): Use a Daily or Weekly chart. The Sweet Spot is the zone between the 32% and 80% lines.
Long Entry: Red and Yellow lines are inside the 32-80 zone, moving upward (Red over Yellow).
Short Entry: Red and Yellow lines drop below the 80% line down into the 32-80 zone (Red under Yellow).
For Day Trading (Intraday): Use a 15-Minute chart. The 32-80 zone in the middle is now "No Man's Land" (avoid trading here). The Day Trading Sweet Spot is above the 80% line for going long, and below the 32% line for going short. Never hold day trades overnight; exit before 4:00 PM EST.
Rule B: Verify the Volume (The "Fuel")
Consistency: Look for consecutive days of increasing volume bars pushing in your desired direction.
The 30% Rule: A strong early signal is seeing 30% of the stock's 30-day average volume within the first hour of the market opening. Avoid trading on "fumes" (days well below the 30-day average).
Rule C: Candlestick Confirmation
Engulfing Candles (Ideal Entry): A thick, full-bodied candle with no wicks that takes out the previous day's high (for longs) or low (for shorts). This proves everyone is pushing in the same direction.
Hammers / Inverse Hammers (Watch): Thick bodies on one end with long wicks on the other. These strongly signal a change in market direction.
Doji Candles (Avoid): Thin candles where the stock opens and closes in nearly the exact same spot. These signal indecision; never enter a trade on a Doji.
Rule D: Pattern Recognition
W Formations (Long): Buy pullbacks that create W patterns with higher lows (creating building support).
M Formations (Short): Look for M patterns with lower highs to initiate a short position.
Ugly Face / Head & Shoulders (Short): These distinct top formations (two eyes/mouth, or two shoulders/head) are massive signals that a stock is about to break down.
The 50% Rule (Short): If a stock suffers a massive drop and rallies back, it will often hit a ceiling right at the 50% mark of its previous drop due to "overhang" selling pressure. Short it here.
5. Rules for Exiting / Taking Profits
Trend Breakdown: Sell when the stochastic trend rolls over (Red crosses below Yellow) or drops out of the designated Sweet Spot.
Taking Profits Off the Table: When your stock hits a major resistance level (like a 50-day or 100-day moving average, or a historical high), you don't have to exit entirely. Sell a portion to secure your profits while leaving your initial cost basis in the trade to see if it breaks out.
Power Stocks (Let it Ride): If a stock breaks above the 80% line but maintains massive volume and stays above all 4 major moving averages, it is a "Power Stock". Do not sell; let it run making all-time highs until the trend firmly breaks down.
Avoid Flag Poles: If a stock shoots straight up for days without any pullbacks or "W" support structures, do not buy the top. It is a "flag pole" that will likely come crashing straight back down.
Use "Tracker Shares" for Reversals: For severely beaten-down "Dog Stocks" lingering at the bottom of a chart, buy a single 1-share position (Tracker Share) to keep it in your brokerage account view. Wait patiently. When it finally creeps back into the Sweet Spot on good volume, buy your full position.


Based on the provided sources, the rules for entering and exiting trades rely on a strict checklist combining time of day, volume, trend indicators (specifically the "Sweet Spot"), and candlestick patterns.
Pre-Trade Checklist
Before executing any trade, you must verify the following conditions to ensure safety and prevent market manipulation:
Time of Day: Do not trade before 10:06 AM EST. This allows overnight trades, options, and algorithm trades to settle, reducing volatility,,.
Bid/Ask Spread: Check the difference between the bid and ask price. It should be under 2 cents (or up to 5 cents for stocks priced over $250) to ensure you are not "the sucker in the room" overpaying due to manipulation,,.
Earnings Check: Verify the earnings date. Never hold a trade through an earnings report because it is a "total crapshoot." Exit the position before the report is released,,.
Friday Rule: Be aware that Friday is typically "profit taking Friday," which may affect price action.
--------------------------------------------------------------------------------
Rules for Entering a Trade
1. The "Sweet Spot" (Trend)
The primary filter for entry is the trend, identified using Stochastics (Red %K and Yellow %D lines) on a daily or weekly chart,.
The Zone: The Sweet Spot is the area between the 32% and 80% lines on the stochastic indicator,,. This is where you have the highest probability of making money.
Going Long (Buying): Enter when the Red and Yellow lines are inside the Sweet Spot and trending upward, with the Red line above the Yellow line,,.
Going Short (Betting against): Enter when the Red and Yellow lines drop below the 80% line and move down into the Sweet Spot, with the Red line below the Yellow line,,.
2. Volume (Fuel)
Volume is the "gasoline" that drives the stock; never trade without it,.
Consistency: Look for consistent or increasing volume bars (green for buys, red for sells). You want to see "people rowing in the same direction",.
Average Volume: The volume bars should ideally be above the 30-day average volume (indicated by a yellow line on the volume chart),,. Avoid trading on days with low volume ("fumes").
3. Candlestick Confirmation
Engulfing Candle: The ideal entry signal is an engulfing candlestick. This is a thick-bodied candle with no wicks that completely "engulfs" (is larger than) the previous day's candle range,.
No Wicks: Avoid candles with long wicks, as they indicate indecision. A full-bodied candle shows that buyers (or sellers) pushed in one direction all day,.
4. Pattern Recognition
W Formations (Long): Look for stocks creating "W" patterns with higher lows (the right side of the W is higher than the left). This indicates building momentum,.
Ugly Face / Head & Shoulders (Short): Look for an "Ugly Face" (two eyes and a mouth pattern) or "Head and Shoulders," which indicate a change in direction and are strong signals to go short,,.
50% Rule (Short): If a stock falls significantly, rallies back up, but fails to break above 50% of its drop, it often hits "overhang" resistance. This is a rule to enter a short position,,.
--------------------------------------------------------------------------------
Rules for Exiting a Trade
1. Trend Breakdown
Long Exit: Sell when the Red and Yellow stochastic lines drop below the 80% line and move out of the Sweet Spot. Alternatively, sell when the stochastic "rolls over" (the Red line crosses below the Yellow line).
Power Stock Exception: If a stock becomes "overbought" (goes above the 80% line/Sweet Spot) but maintains high volume and stays above all four moving averages (25, 50, 100, 200), it is a Power Stock. Do not sell yet; let it run until the trend breaks back down into the Sweet Spot,,.
2. Resistance and Support Levels
Moving Averages: Use the 25, 50, 100, and 200-day moving averages as profit targets. If a stock hits a major moving average (like the 100-day) and volume or trend begins to falter, take profits,,.
Historical Lines: Draw horizontal lines at previous peaks or consolidation areas. Exit or take partial profits when the stock price hits these historical resistance levels,.
3. Stop Losses
Safety Guards: Always have a stop loss in place to mitigate risk. A typical trailing stop is 1-5%.
Risk Management: Never put more than 20% of your total account balance into a single position.
4. Emotional Discipline
Snapbacks: Do not exit just because a stock price pulls back slightly (creating a W formation) if the trend and volume are still intact. You need pullbacks to create support levels,.
Step Away: If you have consecutive losing trades or feel emotional, step away from the market. Do not "chase" losses,.