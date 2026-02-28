# VolatilityHunter Architecture

**Version**: v10.0 | **Updated**: 2026-02-28 | **Design**: SOLID + Factory + Strategy patterns

---

## High-Level Overview

`
                    VOLATILITYHUNTER v10.0
                    AGENT-BASED ARCHITECTURE

  Windows Task Scheduler (09:45 ET daily)
              |
              v
    run_trading.bat
              |
    +---------------------------+
    | functional_health_check   |  --> Exit Code 0 gate
    +---------------------------+
              |
    +---------------------------+
    | daily_trading_loop.py     |  --> Autonomous scan -> rank -> execute
    +---------------------------+
              |
    Orchestrator (main_agent_system.py)
              |
    +---------+---------+---------+---------+---------+---------+---------+
    |         |         |         |         |         |         |         |
  Data    Strategy  Execution   Sync   Notify  Schedule  Testing
 Agent     Agent     Agent     Agent   Agent    Agent    Agent
`

---

## Agent Specifications

### DataAgent  src/agents/data/agent.py
- Loads Tiingo parquet history (2,147 tickers, 26+ years)
- Appends today Yahoo Finance candle via _load_fresh_data() [R1]
- Caches data in memory (512 MB limit via MemoryManager)
- ChromaDB vector acceleration for pattern lookup
- Smart fallback: Tiingo primary -> Yahoo Finance fallback
- Rate limiter: 50 messages/sec

### StrategyAgent  src/agents/strategy/agent.py
- Runs Sweet Spot v7.2 on fresh data (parquet + today candle) [R1]
- Priority chain: SweetSpotStrategy -> PatternEnhanced -> Basic v7.2
- Signal ranking: 0.6 * annual_return + 0.4 * stoch_score [R9]
- Filters: K in [32,80], price > SMA200, volume surge 1.5x, CAGR >= 15%

### ExecutionAgent  src/agents/execution/agent.py
- IBKR ib_insync interface, fixed threading bug [R3]
- Pre-flight socket probe (5s timeout) before connect
- Direct ib.connect(timeout=15) - no thread+join
- Paper mode fallback when IBKR not reachable
- Ironclad guardrails: 20% position size, max 10 positions

### SyncAgent  src/agents/sync/agent.py
- Reconciles data/portfolio.json vs IBKR live positions
- Runs at start of every daily loop (Step 1)
- Detects and logs discrepancies

### NotificationAgent  src/agents/notification/agent.py
- Gmail SMTP 587 + STARTTLS [R7 verified]
- Daily trade summary email to lugassy.ai@gmail.com
- OrderMonitor unfilled-order alerts [R5]
- Health check status emails

### SchedulerAgent  src/agents/scheduler/agent.py
- Windows Task Scheduler integration
- IBC process watchdog via uto_tws_manager.py [R6]
- 5-minute health loop: detects gateway death, relaunches

### TestingAgent  src/agents/testing/agent.py
- Runs unctional_health_check.py as system gate
- Portfolio sync verification
- Agent status validation

---

## Data Flow

`
Tiingo Parquet (data/*.parquet)
    |
    +-- DataAgent._load_fresh_data(ticker)
    |       |
    |       +-- Append today Yahoo Finance candle (yf.download 5d)
    |       |
    |       v
    |   df: full history + today  (200+ rows minimum)
    |
    v
StrategyAgent._generate_sweet_spot_signals()
    |
    +-- SweetSpotStrategy.analyze_stock_sweet_spot()
    |       |
    |       v
    |   signal: {ticker, signal, confidence, score, reason}
    |
    v
daily_trading_loop.scan_universe()
    |
    +-- Rank by score (60% return + 40% stoch)
    |
    v
daily_trading_loop.execute_entries()
    |
    +-- ExecutionAgent -> IBKR place_market_order()  [live]
    |   OR paper trade  [paper mode]
    |
    v
OrderMonitor.monitor()  [R5]
    |
    +-- Poll openTrades() every 10s
    +-- Alert email at 90s unfilled
    +-- Cancel + portfolio rollback at 180s
    |
    v
NotificationAgent -> Gmail SMTP summary email
`

---

## Key Design Patterns

| Pattern | Application |
|---------|-------------|
| Factory | smart_data_loader_factory.get_data_loader() - Tiingo vs Yahoo |
| Strategy | StrategyAgent.generate_signals() - SweetSpot vs Pattern vs Basic |
| Observer | OrderMonitor polls IBKR trade events |
| Agent/Actor | Each agent processes messages independently via message_bus |
| Circuit Breaker | Drawdown circuit: -10% -> 50% size, -20% -> 25% size |
| Fail-Safe | Paper mode when IBKR unreachable; Yahoo fallback when Tiingo fails |

---

## Configuration

All agent config in config/agents.json. Never hardcode settings.

Key environment variables (.env):
`
TIINGO_API_KEY   # Tiingo historical data (reads TIINGO_API_KEY first, then TIINGO_KEY) [R8]
EMAIL_SENDER     # Gmail sender address
EMAIL_PASSWORD   # Gmail app password
IBKR_USER_NAME   # IB Gateway credentials for IBC auto-login
IBKR_PASSWORD    # IB Gateway password
`

---

## IBKR / IBC Integration

`
auto_tws_manager.py (runs continuously, 5-min health loop)
    |
    +-- check: is port 7497 open?
    |
    +-- NO -> start_gateway_via_ibc()
    |           |
    |           +-- find_java() -> Zulu JRE 17 (C:\Users\Yaniv\zulu-jre17)
    |           +-- build classpath: IBC.jar + ibgateway/jars/*.jar
    |           +-- Popen: javaw -cp ... IbcGateway config.ini gateway_dir live
    |           |
    |           +-- FALLBACK: C:\IBC\StartGateway.bat
    |
    +-- YES -> is_api_ready() -> start_keep_alive()
`

IBC Config: C:\IBC\config.ini
- Credentials from .env (auto-written by setup_ibc.py)
- TradingMode passed as 3rd CLI arg (not in config.ini) [IBC 3.18+ requirement]
- IbAutoClosedown=no (gateway runs 24/7)
- AcceptIncomingConnectionAction=accept (auto-accepts API connections)

---

## Risk Management Layer

`
Position Level:
  - Hard stop loss: -5% P&L -> immediate market sell
  - Power stock exit: SMA25 break or 3x ATR trailing stop
  - Standard exit: Stoch overbought rollover OR SMA200 break

Portfolio Level:
  - Max 10 simultaneous positions
  - Max 20% equity per position
  - Drawdown circuit: equity DD > -10% -> scale to 50% size
  - Drawdown circuit: equity DD > -20% -> scale to 25% size

Order Level (R5 OrderMonitor):
  - Poll IBKR openTrades() every 10 seconds
  - Email alert if unfilled after 90 seconds
  - Auto-cancel + portfolio cash refund after 180 seconds
`

---

## File Structure

`
VolatilityHunter/
  main_agent_system.py            Orchestrator entry point
  tickers.txt                     2,147 ticker universe

  src/
    agents/
      data/agent.py               DataAgent
      strategy/agent.py           StrategyAgent + _load_fresh_data() [R1]
      execution/agent.py          ExecutionAgent
      sync/agent.py               SyncAgent
      notification/agent.py       NotificationAgent
      scheduler/agent.py          SchedulerAgent
      testing/agent.py            TestingAgent
    brokerage_interface.py        IBKRInterface (R3: threading fix)
    strategy_v7_2.py              Core Sweet Spot logic
    sweet_spot_strategy.py        Enhanced strategy wrapper
    smart_data_loader_factory.py  Tiingo/Yahoo smart loader
    config.py                     Constants (R8: TIINGO_API_KEY)
    email_notifier.py             SMTP email (R7: verified)
    portfolio_synchronizer.py     IBKR reconciliation
    storage.py                    Parquet read/write

  scripts/
    daily_trading_loop.py         Autonomous daily pipeline [R5,R9]
    full_universe_backtest.py     2,147 ticker vectorized backtest
    functional_health_check.py    Health gate (Exit Code 0 required)
    auto_tws_manager.py           IBC watchdog [R6]
    setup_ibc.py                  IBC + Zulu JRE 17 installer
    DAILY_ROUTINE/
      run_trading.bat             Task Scheduler entry point

  config/
    agents.json                   Agent configuration
    agent_config.py               Config dataclasses

  data/
    portfolio.json                Live portfolio state (gitignored)
    *.parquet                     Tiingo history (gitignored)

  logs/
    trading_YYYY-MM-DD.log        Daily loop output
    ibc_gateway.log               IBC startup log
    full_backtest_*.json          Backtest result archives

  docs/
    README.md                     This system overview
    ARCHITECTURE.md               This file - architecture details
    BLUEPRINT.md                  Sweet Spot trading rules
`

---

## Health Check Protocol

Mandatory before any trading session:

`ash
python scripts/functional_health_check.py
# Must exit with code 0
`

Checks run:
1. All 7 agents initialize without error
2. Portfolio sync verification (local vs IBKR)
3. Data agent connectivity
4. Strategy agent signal generation
5. Notification agent email config
6. Execution agent IBKR reachability (falls back to paper OK)

**Exit Code 0 = all green. Any other code = abort trading.**

---

## Testing

`ash
# Full system health gate
python scripts/functional_health_check.py

# Backtest full universe (takes ~10-30 min)
python scripts/full_universe_backtest.py

# Validate specific fix
python scripts/verify_X.py  # per Rule 4.1
`
