# VolatilityHunter Architecture

**Version**: v10.2 | **Updated**: 2026-02-28 | **Design**: SOLID + Factory + Strategy patterns

---

## High-Level Overview

`
                    VOLATILITYHUNTER v10.0
                    AGENT-BASED ARCHITECTURE

  Windows Task Scheduler (17:06 IST / 10:06 AM ET daily)
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
- Runs Sweet Spot v8.1 on fresh data (parquet + today candle) [R1]
- Priority chain: SweetSpotStrategy -> PatternEnhanced -> Basic v8.1
- Signal ranking: 0.6 * annual_return + 0.4 * stoch_score [R9]
- Filters: K in [32,80], price > SMA200, volume surge 1.5x, CAGR >= 15%, 20-day momentum >= 5%
- Regime filter: SPY < SMA200 -> max 3 positions (bear guard)
- Sector cap: max 3 positions per sector simultaneously

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
    +-- _ensure_clean_jts_ini()
    |     strip SSO tokens, force tradingMode=p, set Username in [Logon]
    |
    +-- check: is port 7497 open?
    |
    +-- NO (weekday) -> start_gateway_via_ibc()
    |           |
    |           +-- find_java() -> i4j bundled Zulu 17.0.16 JRE (has JavaFX)
    |           +-- build classpath: IBC.jar + ibgateway/jars/*.jar
    |           +-- Popen: javaw -cp ... IbcGateway config.ini gateway_dir paper
    |           +-- spawn ibc_login_helper.py (pyautogui fills credentials)
    |
    +-- NO (weekend) -> log "API not required", skip restart
    |
    +-- closed < 5 min -> grace period (user may be browsing IBKR portal)
    |
    +-- YES -> is_api_ready() -> start_keep_alive()
`

IBC Config: C:\IBC\config.ini
- IbDir uses forward slashes, LF line endings (avoids Windows backslash parse bug)
- Credentials NOT in config.ini (IBC 3.23 misidentifies field index in GW 10.37 UI)
- Credentials injected by ibc_login_helper.py via pyautogui after window appears
- TradingMode=paper + jts.ini tradingMode=p (paper mode enforced in both places)
- IbAutoClosedown=no (gateway runs 24/7)
- AcceptIncomingConnectionAction=accept (auto-accepts API connections)
- 2FA disabled via IBKR SLS Opt Out for fully unattended login

---

## Risk Management Layer

`
Position Level:
  - Hard stop loss: -8% P&L -> immediate market sell
  - Time stop: P&L < 0 after 10 trading days -> exit (avg -2.2% vs -8%)
  - Power stock exit: SMA25 break or 3x ATR trailing stop from highest_price
  - Standard exit: Stoch K>78 rollover OR SMA200 break

Portfolio Level:
  - Max 10 positions (bull regime) / 3 positions (bear regime: SPY < SMA200)
  - Sector cap: max 3 positions per sector simultaneously
  - Volatility-adjusted sizing: base_size * (median_atr / ticker_atr), floor 25%
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
    strategy_v7_2.py              Core Sweet Spot logic + indicators (reference)
    strategy_v8.py                v8 backtest engine (reference)
    strategy_v8_1.py              v8.1 production backtest engine
    strategy_engine.py            Single source of truth (all 4 modes use this)
    sweet_spot_strategy.py        Enhanced strategy wrapper
    smart_data_loader_factory.py  Tiingo/Yahoo smart loader
    config.py                     Constants (R8: TIINGO_API_KEY)
    email_notifier.py             SMTP email (R7: verified)
    portfolio_synchronizer.py     IBKR reconciliation
    storage.py                    Parquet read/write

  scripts/
    daily_trading_loop.py         Autonomous daily pipeline v8.1 [R5,R9,R12]
    full_universe_backtest.py     v7.2 full universe backtest (2,147 tickers)
    backtest_v7_vs_v8.py          Side-by-side v7 vs v8 comparison backtest
    backtest_v8_vs_v8_1.py        v8 vs v8.1 DD-reduction proof backtest
    simulate_monday.py            Full pipeline dry-run on historical date
    functional_health_check.py    Health gate (Exit Code 0 required)
    auto_tws_manager.py           IBC watchdog [R6]
    ibc_login_helper.py           pyautogui credential injector
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
    backtest_v7_vs_v8_*.json      v7 vs v8 comparison results
    backtest_v8_vs_v8_1_*.json    v8 vs v8.1 DD-reduction results

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

# Backtest full universe v7.2 (takes ~2 min)
python scripts/full_universe_backtest.py

# Compare v7.2 vs v8 side-by-side (takes ~2 min)
python scripts/backtest_v7_vs_v8.py

# Compare v8 vs v8.1 DD-reduction (takes ~3 min)
python scripts/backtest_v8_vs_v8_1.py

# Simulate a historical trading day end-to-end
python scripts/simulate_monday.py

# Validate specific fix
python scripts/verify_X.py  # per Rule 4.1
`
