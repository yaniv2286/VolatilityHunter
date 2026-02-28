# VolatilityHunter - Daily Run Visual Flow

**Version**: v10.2 | **Updated**: 2026-02-28 | **Timezone**: IST (UTC+2)

---

## THE BIG PICTURE

```
  EVERY DAY (Mon-Fri)
  ════════════════════════════════════════════════════════════════════

  [17:00 IST]                [17:30 IST]              [After close]
  Task fires                 Market opens              Email arrives
      |                           |                         |
      v                           v                         v
  HEALTH CHECK  -->  SCAN 2,147 STOCKS  -->  EXECUTE  -->  REPORT
```

---

## PART 1 — INFRASTRUCTURE (Runs 24/7, Always On)

```
  WINDOWS BOOT / LOGON
        |
        v
  ┌─────────────────────────────────────────────┐
  │         Auto_IBGateway_Manager              │
  │         (Task Scheduler, At Logon)          │
  │                                             │
  │  Every 5 minutes, checks:                  │
  │  Is IB Gateway running? ──NO──> Restart it │
  │  Is port 7497 open?    ──NO──> Restart it  │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │         IB Gateway  (port 7497)             │
  │         Auto-login via IBC                  │
  │         Java: Zulu JRE 17                   │
  │         Credentials from .env               │
  └─────────────────────────────────────────────┘
        |
        v
  API READY -- Python can now place real orders
```

---

## PART 2 — DAILY TRADING PIPELINE (17:00 IST)

```
  [17:00 IST] Task Scheduler fires run_trading.bat
        |
        v
  ┌─────────────────────────────────────────────┐
  │  WEEKEND GUARD                              │
  │  Is today Saturday or Sunday?              │
  │  YES --> STOP. Markets closed.             │
  │  NO  --> Continue                          │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  PILLAR I: HEALTH CHECK                     │
  │  scripts/functional_health_check.py         │
  │                                             │
  │  Checks:                                    │
  │    All 7 agents initialize OK?              │
  │    Portfolio synced with IBKR?              │
  │    Data feeds reachable?                    │
  │    Email config working?                    │
  │    IBKR API reachable?                      │
  │                                             │
  │  Result must be Exit Code 0                 │
  │  FAIL --> ABORT. No trading today.          │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 1: SYNC PORTFOLIO                     │
  │  SyncAgent                                  │
  │                                             │
  │  Compares:                                  │
  │    Local  portfolio.json  (what we think)   │
  │    IBKR live positions    (what's real)     │
  │                                             │
  │  Logs any discrepancies, reconciles state   │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 2b: UPDATE TRACKING                   │
  │                                             │
  │  highest_price updated (ATR trailing stop)  │
  │  high_water_mark updated (DD scaling)       │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 3: CHECK EXITS (open positions first) │
  │  ExecutionAgent                             │
  │                                             │
  │  For each of our current positions:         │
  │  --> See EXIT RULES section below           │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 3b: POWER STOCK PROMOTION             │
  │                                             │
  │  K>80 + all SMAs + vol surge x2 days?       │
  │  YES -> upgrade to power stock shield mode  │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 3: SCAN UNIVERSE                      │
  │  DataAgent + StrategyAgent                  │
  │                                             │
  │  2,147 tickers from tickers.txt             │
  │                                             │
  │  Data source:                               │
  │    Primary  --> Tiingo parquet (26yr hist)  │
  │    Fallback --> Yahoo Finance (live candle) │
  │    Today candle appended fresh each run     │
  │                                             │
  │  --> See ENTRY FILTERS section below        │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 4: RANK SIGNALS                       │
  │  StrategyAgent                              │
  │                                             │
  │  Score = 0.6 x annual_return               │
  │        + 0.4 x stoch_score                 │
  │                                             │
  │  stoch_score peaks when K = 56             │
  │  (center of the 32-80 Sweet Spot)           │
  │                                             │
  │  Sort all passing stocks by score DESC      │
  │  Top candidates fill open position slots    │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 4b: REGIME CHECK                      │
  │                                             │
  │  SPY above SMA200? -> BULL (10 slots max)   │
  │  SPY below SMA200? -> BEAR (3 slots max)    │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 5: EXECUTE ENTRIES                    │
  │  ExecutionAgent -> IBKR                     │
  │                                             │
  │  Slots = regime_max - current positions     │
  │  Sector cap: max 3 per sector               │
  │  Order size = 20% equity x vol_scale        │
  │    vol_scale = median_atr / ticker_atr      │
  │    (high-vol stocks sized down, floor 25%)  │
  │                                             │
  │  DRAWDOWN CIRCUIT BREAKER:                  │
  │    Portfolio DD > -10%  -> size x 50%       │
  │    Portfolio DD > -20%  -> size x 25%       │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 6: ORDER MONITOR (R5)                 │
  │  OrderMonitor polls IBKR every 10 seconds   │
  │                                             │
  │   0s  Order placed                         │
  │  90s  Still unfilled? -> Email alert        │
  │ 180s  Still unfilled? -> Auto-cancel        │
  │                        -> Cash refunded     │
  └─────────────────────────────────────────────┘
        |
        v
  ┌─────────────────────────────────────────────┐
  │  STEP 7: EMAIL REPORT                       │
  │  NotificationAgent -> Gmail SMTP            │
  │                                             │
  │  Summary includes:                          │
  │    Positions opened today                   │
  │    Positions closed today                   │
  │    Portfolio value + P&L                    │
  │    Any alerts or errors                     │
  └─────────────────────────────────────────────┘
```

---

## ENTRY FILTERS — All Must Pass

```
  STOCK CANDIDATE
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 1: LIQUIDITY                                             │
  │  Price x Daily Volume >= $500,000                                │
  │  (enough real money trading this stock)                          │
  │  FAIL --> SKIP                                                   │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 2: TREND (The Big Picture)                               │
  │  Price ABOVE the 200-day SMA                                     │
  │  (only trade stocks in a long-term uptrend)                      │
  │  FAIL --> SKIP                                                   │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 3: MOMENTUM (Annual Return)                              │
  │  1-year return >= 15%                                            │
  │  (only trade stocks that are already winning)                    │
  │  FAIL --> SKIP                                                   │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 3b: 20-DAY MOMENTUM ACCELERATION                         │
  │  20-day return >= 5%                                             │
  │  (only enter stocks that are accelerating NOW)                   │
  │  FAIL --> SKIP                                                   │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 4: SWEET SPOT (Stochastic K=14,D=3)                      │
  │  K line must be inside 32 - 80 zone                              │
  │  K line trending UP (Red over Yellow)                            │
  │                                                                  │
  │  ZONE VISUAL:                                                    │
  │                                                                  │
  │  100% ─────────────────────── overbought (too hot, skip)        │
  │   80% ═══════════════════════ UPPER BOUND                       │
  │                                                                  │
  │         SWEET SPOT ZONE  <── BUY HERE                           │
  │              K trending up, Red above Yellow                     │
  │                                                                  │
  │   32% ═══════════════════════ LOWER BOUND                       │
  │    0% ─────────────────────── oversold (too cold, skip)         │
  │                                                                  │
  │  FAIL --> SKIP                                                   │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 5: VOLUME SURGE                                          │
  │  Today's volume >= 1.5x the 30-day average                       │
  │  (need fuel to move - avoid trading on fumes)                    │
  │  FAIL --> SKIP                                                   │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 6: POSITION LIMIT (REGIME-AWARE)                         │
  │  BULL regime: fewer than 10 positions?                           │
  │  BEAR regime: fewer than 3 positions?                            │
  │  FAIL --> NO SLOT AVAILABLE, SKIP                                │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  ┌──────────────────────────────────────────────────────────────────┐
  │  FILTER 7: SECTOR CAP                                            │
  │  Already holding 3+ stocks in this sector?                       │
  │  FAIL --> SKIP (avoid sector concentration)                      │
  └──────────────────────────────────────────────────────────────────┘
        |
        v
  SIGNAL CONFIRMED --> Scored and ranked
```

---

## EXIT RULES — 4 Ways a Position Closes

```
  OPEN POSITION
        |
        +──────────────────────────────────────────────────────────────+
        |                                                              |
        v                                                              v
  ┌─────────────────────┐                                   ┌─────────────────────┐
  │  EXIT 1: HARD STOP  │                                   │  Is this a          │
  │                     │                                   │  POWER STOCK?       │
  │  Price drops 8%     │                                   │  (see below)        │
  │  from entry price   │                                   └──────────┬──────────┘
  │                     │                                              |
  │  Immediate market   │                               YES ──────────+──────── NO
  │  sell. No debate.   │                                |                        |
  └─────────────────────┘                                v                        v
                                               POWER STOCK EXITS          STANDARD EXITS
                                               (see section below)
                                                                   ┌──────────────────────┐
                                                                   │  EXIT 1b: TIME STOP │
                                                                   │                     │
                                                                   │  Still losing after │
                                                                   │  10 trading days?   │
                                                                   │  Exit at avg -2.2%  │
                                                                   │  (not -8% hard stop)│
                                                                   └──────────────────────┘

                                                                   ┌──────────────────────┐
                                                                   │  EXIT 2: STOCH BREAK │
                                                                   │                      │
                                                                   │  K < D AND K > 78    │
                                                                   │  (overbought rollover│
                                                                   │  lets winners run    │
                                                                   │  longer than K>70)   │
                                                                   │                      │
                                                                   │  Trend is broken.    │
                                                                   │  Sell.               │
                                                                   └──────────────────────┘

                                                                   ┌──────────────────────┐
                                                                   │  EXIT 3: SMA200 BREAK│
                                                                   │                      │
                                                                   │  Price drops BELOW   │
                                                                   │  the 200-day SMA     │
                                                                   │                      │
                                                                   │  Long-term trend     │
                                                                   │  is now broken.      │
                                                                   │  Sell.               │
                                                                   └──────────────────────┘
```

---

## POWER STOCK — Special Rules

```
  WHAT IS A POWER STOCK?
  ════════════════════════════════════════════════════════════════════

  A normal stock enters the Sweet Spot (32-80) and we buy.
  A Power Stock breaks ABOVE the 80% line and keeps going.

  100% ─────────────────── K breaks above 80 ──> POWER STOCK!
   80% ════════════════════════════════════════════════════════
                                              <── Normal zone
   32% ════════════════════════════════════════════════════════
    0% ─────────────────────────────────────────────────────────

  CONDITIONS TO QUALIFY AS POWER STOCK:
    1. Stochastic K is ABOVE the 80% line
    2. Massive volume (well above 30-day average)
    3. Price is ABOVE all 4 SMAs (25, 50, 100, 200)
    4. Making new highs

  ────────────────────────────────────────────────────────────────────

  POWER STOCK RULES:
    DO NOT SELL just because K is "overbought" above 80%
    DO NOT SELL on normal pullbacks (W formations = healthy)
    LET IT RUN until the trend firmly breaks down

  ────────────────────────────────────────────────────────────────────

  POWER STOCK EXIT TRIGGERS (either one fires):

  ┌──────────────────────────────────────────────────────────────────┐
  │  POWER EXIT 1: SMA25 BREAK                                       │
  │                                                                  │
  │  Price closes BELOW the 25-day SMA                               │
  │  The short-term trend has ended.                                 │
  │  SELL.                                                           │
  └──────────────────────────────────────────────────────────────────┘

  ┌──────────────────────────────────────────────────────────────────┐
  │  POWER EXIT 2: 3x ATR TRAILING STOP                              │
  │                                                                  │
  │  Trail at 3 x ATR (Average True Range) below highest close       │
  │  ATR measures recent daily price swings                          │
  │                                                                  │
  │  Example: Stock at $100, ATR=$2                                  │
  │    Stop = $100 - (3 x $2) = $94                                 │
  │    If stock goes to $110 -> stop rises to $104                   │
  │    If price hits the stop -> SELL                                │
  └──────────────────────────────────────────────────────────────────┘

  ────────────────────────────────────────────────────────────────────

  POWER STOCK vs NORMAL STOCK COMPARISON:

  Normal Stock:
    Buy: K enters 32-80 zone going up
    Sell: K exits 32-80 zone OR stoch rolls over
    Stop: -5% hard stop

  Power Stock:
    Buy: same entry (caught it in the Sweet Spot before breakout)
    Sell: SMA25 break OR 3x ATR trailing stop
    Stop: -5% hard stop (still applies)
    Key: IGNORE the "overbought" signal above 80%

  ────────────────────────────────────────────────────────────────────

  THINGS TO AVOID:

  FLAG POLE TRAP:
    Stock shoots straight up for many days with no pullback
    DO NOT buy at the top of a flag pole
    It will likely come straight back down
    Wait for a W formation to form before entering

  DOJI CANDLES:
    Thin candle, open = close (indecision day)
    Never enter on a Doji

  EARNINGS DATES:
    Never hold through an earnings report
    Exit BEFORE the earnings date
    (not yet automated - manual awareness required)

  FRIDAY RULE:
    Friday = profit-taking day
    Be extra cautious entering new positions on Fridays
```

---

## RISK MANAGEMENT SUMMARY

```
  POSITION LEVEL
  ──────────────────────────────────────────────
  Base size per trade   20% of total equity
  Vol-adjusted size     base x (median_atr / ticker_atr), floor 25%
  Hard stop loss        -8% from entry
  Time stop             exit if losing after 10 trading days
  Max open positions    10 (bull) / 3 (bear: SPY < SMA200)
  Sector cap            max 3 positions per sector

  PORTFOLIO LEVEL
  ──────────────────────────────────────────────
  Drawdown -10%    Reduce all new positions to 50% size
  Drawdown -20%    Reduce all new positions to 25% size

  ORDER LEVEL
  ──────────────────────────────────────────────
  90 seconds unfilled    Email alert sent
  180 seconds unfilled   Auto-cancel + cash refunded

  WIN/LOSS REALITY (v8.1 backtest, 26 years)
  ──────────────────────────────────────────────
  Win rate               ~28% (momentum filter is selective)
  Avg win                +16.7%  (let winners run to K>78)
  Avg loss               -4.3%   (time stop cuts early)
  Profit factor          1.48
  System is built to     let winners run far, cut losers fast
```

---

## 7-AGENT SYSTEM — Who Does What

```
  ┌─────────────────┬──────────────────────────────────────────────────┐
  │  Agent          │  Job                                             │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  DataAgent      │  Loads 26yr Tiingo history + today's candle      │
  │                 │  2,147 tickers, parquet files, Yahoo fallback    │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  StrategyAgent  │  Runs Sweet Spot filters on every ticker         │
  │                 │  Scores and ranks all signals                    │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  ExecutionAgent │  Places orders via IBKR API                      │
  │                 │  Paper mode fallback if IBKR unreachable         │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  SyncAgent      │  Reconciles local portfolio vs IBKR live state   │
  │                 │  Runs at start of every session                  │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  NotifyAgent    │  Sends daily email summary (Gmail SMTP)          │
  │                 │  Alerts for unfilled orders                      │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  SchedulerAgent │  Watches IB Gateway 24/7, restarts if it dies    │
  │                 │  5-minute health loop                            │
  ├─────────────────┼──────────────────────────────────────────────────┤
  │  TestingAgent   │  Runs health check before every trading session  │
  │                 │  Exit Code 0 = green light. Anything else = stop │
  └─────────────────┴──────────────────────────────────────────────────┘
```

---

## DAILY TIMELINE (IST)

```
  ALL DAY     Auto_IBGateway_Manager watches port 7497, restarts if dead
  16:30       US Market opens (NYSE/NASDAQ) - 9:30 AM ET
  17:06       Task Scheduler fires run_trading.bat  [Blueprint: 10:06 AM ET rule]
  17:06       Weekend guard check (skip Sat/Sun)
  17:07       Health check runs (all 7 agents, portfolio sync)
  17:10       Sync portfolio with IBKR live state
  17:11       Check exits on all open positions
  17:15       Scan 2,147 tickers (data load + strategy filters)
  17:25       Rank signals by score
  17:28       Execute entries (market orders via IBKR)
  17:30       Orders fill at live market price (30+ min post-open, settled)
  ~18:00      Order monitor confirms all fills (or cancels unfilled)
  ~18:30      Email report sent to lugassy.ai@gmail.com
```

---

## BACKTEST RESULTS (26 years, 2,147 tickers)

```
  Strategy    CAGR    5yr CAGR  Max DD    Sharpe  Avg Win  Avg Loss
  ─────────────────────────────────────────────────────────────────
  v7.2        10.1%   23.2%    -48.6%    0.59    +6.5%    -5.1%
  v8          16.2%   28.5%    -51.8%    0.76    +15.6%   -8.2%
  v8.1        23.3%   45.4%    -28.1%    0.73    +16.7%   -4.3%  <-- PRODUCTION

  $100,000 compounded over 26 years:
  v7.2 -> $1.1M  |  v8 -> $4.4M  |  v8.1 -> $19.3M
```
