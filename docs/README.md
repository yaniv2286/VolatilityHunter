# VolatilityHunter

**Version**: v10.2 | **Updated**: 2026-02-28 | **Strategy**: v8.1 | **Health Check**: 10/10 PASS Exit Code 0
**Capital**: $100,000 | **Mode**: Paper (IBKR live-ready) | **Universe**: 2,147 tickers | **Data**: 26+ years parquet

---

## Current System Status

| Component | Status | Notes |
|-----------|--------|-------|
| Strategy Engine (v8.1) | OPERATIONAL | strategy_engine.py — single source of truth |
| Daily Trading Loop | OPERATIONAL | scripts/daily_trading_loop.py |
| IBKR Interface | READY | R3: threading bug fixed, port probe added |
| IBC Auto-Login | OPERATIONAL | IBC 3.23 + Zulu JRE 17 + pyautogui credential injection |
| OrderMonitor | OPERATIONAL | R5: polls 10s, email alert 90s, auto-cancel 180s |
| Email Notifications | OPERATIONAL | R7: Gmail SMTP 587 + STARTTLS verified |
| Tiingo API Key | FIXED | R8: reads TIINGO_API_KEY from .env |
| Score-Based Ranking | OPERATIONAL | R9: 60% annual_return + 40% stoch_position |
| Data to Strategy Wire | OPERATIONAL | R1: parquet + today Yahoo candle per analysis run |
| Windows Task Scheduler | CONFIGURED | scripts/DAILY_ROUTINE/run_trading.bat |

---

## Backtest Results (Full Universe, 2,147 Tickers)

Run: 2026-02-28 | Engine: scripts/backtest_v8_vs_v8_1.py | Data: Tiingo parquet (2000-2026)

### Full Strategy Evolution (26 Years, Compounding)

| Metric | v7.2 | v8 | **v8.1 (production)** |
|--------|------|----|-----------------------|
| **CAGR** | 10.1% | 16.2% | **23.3%** |
| **5yr CAGR** | 23.2% | 28.5% | **45.4%** |
| Max Drawdown | -48.6% | -51.8% | **-28.1%** |
| Sharpe Ratio | 0.59 | 0.76 | **0.73** |
| Avg Win | +6.5% | +15.6% | **+16.7%** |
| Avg Loss | -5.1% | -8.2% | **-4.3%** |
| Profit Factor | 1.25 | 1.51 | **1.48** |
| Total Trades | 99,492 | 37,213 | 41,786 |
| Final $100k | $1.1M | $4.4M | **$19.3M** |

**v8.1 is in production.** v8 and v7.2 preserved in src/ for reference.

### Top 5 Trades (All Time)

| Ticker | Entry | Exit | P&L |
|--------|-------|------|-----|
| BNAI | 2026-01-21 | 2026-01-28 | +624% |
| SLNO | 2023-09-20 | 2023-10-05 | +480% |
| TERN | 2025-10-29 | 2025-12-17 | +423% |
| QUBT | 2024-11-08 | 2024-11-27 | +372% |
| RGTI | 2024-11-22 | 2024-12-13 | +311% |

### Notes on Drawdown
- v8.1 DD of -28.1% is the real portfolio drawdown (regime filter prevents bear market overexposure)
- The live system uses volatility-adjusted position sizing (high-ATR stocks get smaller allocation)
- Drawdown circuit breaker active: -10% DD -> 50% position size, -20% DD -> 25% size
- SPY regime today: **BULL** (SPY=685.99 > SMA200=651.74) — full 10 positions allowed

---

## Architecture: Lean Pipeline

```
Windows Task Scheduler
    └── run_trading.bat
            |
            v
    functional_health_check.py   (10 checks, Exit Code 0 gate)
            |
            v
    daily_trading_loop.py        (autonomous pipeline)
            |
            v
    strategy_engine.py           (SINGLE SOURCE OF TRUTH)
            |
    +-------+--------+--------+
    |       |        |        |
 strategy brokerage email  storage
 _v7_2   _interface notifier  .py
```

### Core Component Responsibilities

| Component | Role | File |
|-----------|------|------|
| Strategy Engine | All params + logic for all 4 modes | `src/strategy_engine.py` |
| Daily Loop | 8-step autonomous pipeline | `scripts/daily_trading_loop.py` |
| Health Check | 10-check gate before trading | `scripts/functional_health_check.py` |
| IBC Watchdog | Gateway 24/7 monitor + auto-restart | `scripts/auto_tws_manager.py` |
| Brokerage | IBKR ib_insync, paper fallback | `src/brokerage_interface.py` |
| Notifier | Gmail SMTP trade summaries + alerts | `src/email_notifier.py` |
| Data Loader | Tiingo parquet + Yahoo Finance today | `src/smart_data_loader_factory.py` |

---

## Daily Autonomous Pipeline

```
17:06 IST  Windows Task Scheduler fires run_trading.bat
           |
           v
     functional_health_check.py     Exit Code 0 required to proceed
           |
           v
     daily_trading_loop.py
       Step 1:  Reconcile portfolio.json <-> IBKR live positions
       Step 2:  Batch fetch today prices via Yahoo Finance (all 2,147 tickers)
       Step 2b: Update highest_price + high-water mark for all open positions
       Step 3:  Check exits (hard stop -8%, time stop 10d, SMA200 break, K>78)
       Step 3b: Power stock promotion check (K>80 + all SMAs + vol surge x2 days)
       Step 4:  Scan universe -> 20-day momentum filter -> rank by score
       Step 4b: Check SPY regime (BULL=10 slots / BEAR=3 slots)
       Step 5:  Execute entries (vol-adjusted sizing, sector cap 3, max 10/3 positions)
       Step 6:  OrderMonitor - poll fills, alert at 90s, cancel at 180s
       Step 7:  Email summary -> lugassy.ai@gmail.com
       Step 8:  Save portfolio.json
```

---

## Trading Strategy: Sweet Spot v8.1 (Production)

### Entry Conditions (ALL must be true)
- Stochastic K between 32 and 80 (sweet spot zone)
- Price above 200-day SMA (uptrend filter)
- Volume >= 1.5x 30-day average (surge confirmation)
- 252-day annual return >= 15% (quality filter)
- 20-day return >= 5% (momentum acceleration filter)
- Price x Volume >= $500,000 (liquidity filter)
- Price >= $5 (no penny stocks)
- SPY regime: BULL -> max 10 positions | BEAR -> max 3 positions
- Sector cap: max 3 positions per sector simultaneously

### Exit Conditions (ANY triggers exit)
- Hard stop: P&L <= -8%
- Time stop: P&L < 0 after 10 trading days (avg exit at -2.2% vs -8%)
- Overbought rollover: K < D and K > 78
- SMA200 break: price < 200-day SMA
- Power stocks: SMA25 break or 3x ATR trailing stop from highest_price

### Position Sizing (Ironclad Guardrails)
- Base: 20% of total equity per position
- Volatility-adjusted: size = base * (median_atr / ticker_atr) — high-vol stocks sized down
- Max 10 simultaneous positions (3 in bear regime)
- Drawdown circuit breaker: -10% equity -> 50% size, -20% -> 25% size

### Power Stock Promotion
- Promoted when K > 80 + above all SMAs + volume surge for 2 consecutive days
- Standard exit rules replaced with shield mode (SMA25 + ATR trailing stop)
- Checked daily as Step 3b in the trading loop

### Signal Ranking Score
`python
stoch_score = 1.0 - abs(k - 56) / 24   # peak at K=56 (center of 32-80)
score = 0.6 * annual_return + 0.4 * stoch_score
`

---

## Key Files Reference

```
Root
  tickers.txt                   2,149 ticker universe

src/                            ACTIVE PIPELINE FILES ONLY
  strategy_engine.py            *** Single source of truth — change params here ***
  strategy_v7_2.py              Indicators (shared by all versions)
  strategy_v8.py                v8 backtest engine (reference)
  strategy_v8_1.py              v8.1 backtest engine (reference)
  brokerage_interface.py        IBKR ib_insync wrapper
  email_notifier.py             Gmail SMTP
  smart_data_loader_factory.py  Tiingo/Yahoo smart loader
  storage.py                    Parquet read/write
  config.py                     API key constants

scripts/
  daily_trading_loop.py         Daily autonomous pipeline v8.1
  simulate_monday.py            Full pipeline dry-run on historical date
  functional_health_check.py    System health gate (10 checks)
  auto_tws_manager.py           IBC gateway watchdog (24/7)
  ibc_login_helper.py           pyautogui credential injector
  setup_ibc.py                  IBC + Zulu JRE 17 one-time installer
  backtest_v7_vs_v8.py          v7 vs v8 comparison
  backtest_v8_vs_v8_1.py        v8 vs v8.1 DD-reduction proof
  full_universe_backtest.py     v7.2 standalone backtest
  DAILY_ROUTINE/run_trading.bat Task Scheduler entry point (17:06 IST)

config/
  agents.json                   Configuration (timeouts, retries, v8.1 params)

data/
  portfolio.json                Live portfolio state (gitignored)
  SPY.parquet                   SPY regime history (gitignored)
  *.parquet                     Tiingo price history (gitignored)

logs/
  trading_YYYY-MM-DD.log        Daily trading log
  functional_health_check.log   Health gate log
  ibc_gateway.log               IBC startup log
  backtest_*.json               Backtest result archives

archive/src_orphans/            Archived 2026-02-28 (not used by active pipeline)
  main_agent_system.py          Former orchestrator
  agents_src/                   7-agent layer
  [+ 35 other archived files]
```

---

## Environment Variables (.env)

`
EMAIL_SENDER=lugassy.ai@gmail.com
EMAIL_PASSWORD=<gmail app password>
TIINGO_API_KEY=<tiingo key>       # Note: TIINGO_API_KEY not TIINGO_KEY
IBKR_USER_NAME=yanivl228
IBKR_PASSWORD=<ibkr password>
`

---

## IBC Auto-Login Setup

IB Gateway headless auto-login via IBC (Interactive Brokers Controller):

`ash
# One-time setup (downloads Zulu JRE 17 if needed, configures IBC)
python scripts/setup_ibc.py

# Start gateway (run before daily_trading_loop.py)
C:\IBC\StartGateway.bat

# Or use the full manager (monitors + auto-restarts)
python scripts/auto_tws_manager.py
`

IBC config: C:\IBC\config.ini
Gateway log: logs/ibc_gateway.log
Java used: i4j bundled Zulu 17.0.16 JRE (includes JavaFX)

**Current IBC status**: OPERATIONAL. Gateway launches unattended via IBC 3.23 + Zulu 17.
Credentials injected by ibc_login_helper.py via pyautogui. Paper mode enforced in both
jts.ini (tradingMode=p) and config.ini (TradingMode=paper). Port 7497 monitored every 5 min.

---

## Recent Changes (2026-02-28)

| ID | Fix | File(s) |
|----|-----|---------|
| R1 | Data->Strategy: parquet + today Yahoo candle | src/smart_data_loader_factory.py |
| R3 | IBKR threading bug: socket probe + direct connect | src/brokerage_interface.py |
| R5 | OrderMonitor: poll/alert/cancel unfilled orders | scripts/daily_trading_loop.py |
| R6 | IBC: Zulu JRE 17 + pyautogui credential injection | scripts/auto_tws_manager.py, scripts/ibc_login_helper.py |
| R7 | Email: verified real smtplib.SMTP implementation | src/email_notifier.py |
| R8 | Tiingo key: reads TIINGO_API_KEY env var | src/config.py |
| R9 | Score ranking in daily scan | scripts/daily_trading_loop.py |
| R10 | Strategy v8: hard stop -8%, exit K>78, 20d momentum | src/strategy_v8.py, src/strategy_engine.py |
| R11 | Pipeline parity: power promotion (Step 3b), highest_price tracking, drawdown scaling | scripts/daily_trading_loop.py, scripts/simulate_monday.py |
| R12 | Strategy v8.1: regime filter, sector cap, time stop, vol sizing (+7% CAGR, -24% DD) | src/strategy_v8_1.py, scripts/daily_trading_loop.py |

---

## Risk Disclaimer

VolatilityHunter is an automated trading system operating with real capital.
Trading involves substantial risk of loss. Past backtest results do not guarantee
future performance. Only deploy with capital you can afford to lose entirely.
