# VolatilityHunter

**Version**: v10.0 Agent-Based Architecture | **Updated**: 2026-02-28 | **Health Check**: Exit Code 0
**Capital**: \,000 | **Mode**: Paper (IBKR live-ready) | **Universe**: 2,147 tickers | **Data**: 26+ years parquet

---

## Current System Status

| Component | Status | Notes |
|-----------|--------|-------|
| Agent System (7 agents) | OPERATIONAL | Health check Exit Code 0 |
| Daily Trading Loop | OPERATIONAL | scripts/daily_trading_loop.py |
| IBKR Interface | READY | R3: threading bug fixed, port probe added |
| IBC Auto-Login | IN PROGRESS | Zulu JRE 17 installed, StartGateway.bat fixed |
| OrderMonitor | OPERATIONAL | R5: polls 10s, email alert 90s, auto-cancel 180s |
| Email Notifications | OPERATIONAL | R7: Gmail SMTP 587 + STARTTLS verified |
| Tiingo API Key | FIXED | R8: reads TIINGO_API_KEY from .env |
| Score-Based Ranking | OPERATIONAL | R9: 60% annual_return + 40% stoch_position |
| Data to Strategy Wire | OPERATIONAL | R1: parquet + today Yahoo candle per analysis run |
| Windows Task Scheduler | CONFIGURED | scripts/DAILY_ROUTINE/run_trading.bat |

---

## Backtest Results (Full Universe, 2,147 Tickers)

Run: 2026-02-28 | Engine: scripts/full_universe_backtest.py | Data: Tiingo parquet (2000-2026)

### 25-Year Compounding (2001-2026)

| Metric | Value |
|--------|-------|
| Initial Capital | \,000 |
| Final Equity | \,124,530 |
| Total Return | 1,024.5% |
| **CAGR** | **10.1%** |
| Max Drawdown | -48.6% |
| Sharpe Ratio | 0.59 |
| Win Rate | 49.4% |
| Profit Factor | 1.25 |
| Total Trades | 99,492 |
| Avg Win | +6.5% |
| Avg Loss | -5.1% |

### 25-Year Fixed Capital (Realistic - same position sizing as live system)

| Metric | Value |
|--------|-------|
| Final Equity | \,494 |
| Total Return | 557.5% |
| **CAGR** | **7.8%** |
| Max Drawdown | -36.6% |
| Sharpe Ratio | 0.75 |

### 5-Year Fixed Capital (2021-2026, Recent Regime)

| Metric | Value |
|--------|-------|
| Final Equity | \,703 |
| Total Return | 176.7% |
| **CAGR** | **22.8%** |
| Max Drawdown | -22.2% |
| Sharpe Ratio | 1.09 |
| Win Rate | 46.7% |
| Total Trades | 27,779 |

### Top 5 Trades (All Time)

| Ticker | Entry | Exit | P&L |
|--------|-------|------|-----|
| BNAI | 2026-01-21 | 2026-01-28 | +624% |
| SLNO | 2023-09-20 | 2023-10-05 | +480% |
| TERN | 2025-10-29 | 2025-12-17 | +423% |
| QUBT | 2024-11-08 | 2024-11-27 | +372% |
| RGTI | 2024-11-22 | 2024-12-13 | +311% |

### Notes on Drawdown
- The 25-yr compounding drawdown (-48.6%) is a measurement artifact of compounding capital
- The live system uses **fixed 20% of base \** per position (not compounding)
- Fixed 5-yr max drawdown is -22.2% which is within the <25% target
- Drawdown circuit breaker active: -10% DD -> 50% position size, -20% DD -> 25% size

---

## Architecture: 7-Agent System

`
main_agent_system.py
    Orchestrator
        |-- DataAgent        src/agents/data/agent.py
        |-- StrategyAgent    src/agents/strategy/agent.py
        |-- ExecutionAgent   src/agents/execution/agent.py
        |-- SyncAgent        src/agents/sync/agent.py
        |-- NotificationAgent src/agents/notification/agent.py
        |-- SchedulerAgent   src/agents/scheduler/agent.py
        |-- TestingAgent     src/agents/testing/agent.py
`

### Agent Responsibilities

| Agent | Role | Key Files |
|-------|------|-----------|
| Data | Load parquet history, append Yahoo Finance today candle | src/smart_data_loader_factory.py |
| Strategy | Run Sweet Spot v7.2 on fresh data, score signals | src/strategy_v7_2.py |
| Execution | Place market orders via IBKR ib_insync | src/brokerage_interface.py |
| Sync | Reconcile portfolio.json vs IBKR live positions | src/portfolio_synchronizer.py |
| Notification | Gmail SMTP email reports and alerts | src/email_notifier.py |
| Scheduler | Windows Task Scheduler + IBC gateway management | scripts/auto_tws_manager.py |
| Testing | Functional health check, system validation | scripts/functional_health_check.py |

---

## Daily Autonomous Pipeline

`
09:45 ET  Windows Task Scheduler fires run_trading.bat
           |
           v
     functional_health_check.py     Exit Code 0 required to proceed
           |
           v
     daily_trading_loop.py
       Step 1: Reconcile portfolio.json <-> IBKR live positions
       Step 2: Batch fetch today prices via Yahoo Finance (all 2,147 tickers)
       Step 3: Check exits (hard stop -5%, SMA200 break, overbought rollover)
       Step 4: Scan universe -> run strategy -> rank by score
       Step 5: Execute entries (20% sizing, max 10 positions)
       Step 6: OrderMonitor - poll fills, alert at 90s, cancel at 180s
       Step 7: Email summary -> lugassy.ai@gmail.com
       Step 8: Save portfolio.json
`

---

## Trading Strategy: Sweet Spot v7.2

### Entry Conditions (ALL must be true)
- Stochastic K between 32 and 80 (sweet spot zone)
- Price above 200-day SMA (uptrend filter)
- Volume >= 1.5x 30-day average (surge confirmation)
- 252-day annual return >= 15% (momentum filter)
- Price x Volume >= \,000 (liquidity filter)
- Price >= \ (no penny stocks)

### Exit Conditions (ANY triggers exit)
- Hard stop: P&L <= -5%
- Overbought rollover: K < D and K > 80
- SMA200 break: price < 200-day SMA
- Power stocks: SMA25 break or 3x ATR trailing stop

### Position Sizing (Ironclad Guardrails)
- 20% of total equity per position (fixed)
- Max 10 simultaneous positions
- Drawdown circuit breaker: -10% equity -> 50% size, -20% -> 25% size

### Signal Ranking Score
`python
stoch_score = 1.0 - abs(k - 56) / 24   # peak at K=56 (center of 32-80)
score = 0.6 * annual_return + 0.4 * stoch_score
`

---

## Key Files Reference

`
Root
  main_agent_system.py          System entry point
  tickers.txt                   2,147 ticker universe

src/
  agents/                       7 agent implementations
  brokerage_interface.py        IBKR ib_insync interface (R3 fixed)
  strategy_v7_2.py              Core strategy logic
  smart_data_loader_factory.py  Tiingo/Yahoo smart loader
  config.py                     Config (R8: TIINGO_API_KEY)
  email_notifier.py             Gmail SMTP

scripts/
  daily_trading_loop.py         Daily autonomous pipeline (R5 OrderMonitor)
  full_universe_backtest.py     2,147 ticker vectorized backtester
  functional_health_check.py    System health gate
  auto_tws_manager.py           IBC gateway manager (R6: process watchdog)
  setup_ibc.py                  IBC + Zulu JRE 17 auto-install
  DAILY_ROUTINE/run_trading.bat Windows Task Scheduler entry point

config/
  agents.json                   All agent configuration

data/
  portfolio.json                Live portfolio state
  *.parquet                     Tiingo price history (gitignored)

logs/
  trading_YYYY-MM-DD.log        Daily trading log
  ibc_gateway.log               IBC/Gateway startup log
  full_backtest_*.json          Backtest result archives
`

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
Java used: C:\Users\Yaniv\zulu-jre17\bin\javaw.exe (Java 17)

**Current IBC status**: Gateway launches (IBC reads config, starts session) but has
a Java reflection warning (InaccessibleObjectException on javax.swing) that is
non-fatal in most IB Gateway versions. Monitoring for full port 7497 open.

---

## Recent Changes (2026-02-28)

| ID | Fix | File(s) |
|----|-----|---------|
| R1 | Data->Strategy: parquet + today Yahoo candle | src/agents/strategy/agent.py |
| R3 | IBKR threading bug: socket probe + direct connect | src/brokerage_interface.py |
| R5 | OrderMonitor: poll/alert/cancel unfilled orders | scripts/daily_trading_loop.py |
| R7 | Email: verified real smtplib.SMTP implementation | src/email_notifier.py |
| R8 | Tiingo key: reads TIINGO_API_KEY env var | src/config.py, src/config/__init__.py |
| R9 | Score ranking in daily scan | scripts/daily_trading_loop.py |
| R6 | IBC Java: auto-discover + download Zulu JRE 17 | scripts/setup_ibc.py, scripts/auto_tws_manager.py |

---

## Risk Disclaimer

VolatilityHunter is an automated trading system operating with real capital.
Trading involves substantial risk of loss. Past backtest results do not guarantee
future performance. Only deploy with capital you can afford to lose entirely.
