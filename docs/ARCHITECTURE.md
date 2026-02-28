# VolatilityHunter Architecture

**Version**: v10.2 | **Updated**: 2026-02-28 | **Strategy**: v8.1 (single source of truth: `strategy_engine.py`)

---

## High-Level Overview

```
                    VOLATILITYHUNTER v8.1
                    LEAN PIPELINE ARCHITECTURE

  Windows Task Scheduler (17:06 IST / 10:06 AM ET daily)
              |
              v
    run_trading.bat
              |
    +---------------------------+
    | functional_health_check   |  --> Exit Code 0 gate (10 checks)
    +---------------------------+
              |
    +---------------------------+
    | daily_trading_loop.py     |  --> Autonomous scan -> rank -> execute
    +---------------------------+
              |
    +---------------------------+
    | strategy_engine.py        |  --> SINGLE SOURCE OF TRUTH
    +---------------------------+
              |
    +---------+---------+---------+
    |         |         |         |
  data    brokerage  email    storage
  loader interface notifier    .py
```

---

## Core Component Specifications

### strategy_engine.py  (single source of truth)
- `DEFAULT_VERSION = 'v8.1'` — change here to switch all modes at once
- `PARAMS['v8.1']`: HARD_STOP_PCT=8%, OVERBOUGHT_EXIT=78, TIME_STOP_DAYS=10, REGIME_MAX_POS=3, SECTOR_MAX=3, VOL_SIZE=True
- Functions used by all 4 modes: `check_exits()`, `scan_universe()`, `calc_position_size()`, `can_enter()`, `get_spy_regime()`, `promote_power_stocks()`, `get_params()`
- Signal ranking: 0.6 * annual_return + 0.4 * stoch_score

### daily_trading_loop.py  (live / paper entry point)
- 8-step autonomous pipeline (scan -> rank -> execute -> monitor -> email -> save)
- All strategy logic delegated to `strategy_engine.py` — no hardcoded params here
- IBKR ib_insync interface via `brokerage_interface.py`
- Pre-flight socket probe (5s timeout) before connect; paper mode fallback
- OrderMonitor: poll fills every 10s, email alert at 90s, cancel at 180s

### functional_health_check.py  (gate)
- 10 checks: strategy_engine, strategy_v7_2, brokerage_interface, email_notifier,
  .env keys, portfolio.json, tickers.txt, SPY.parquet, data/*.parquet universe, IBKR port 7497
- Critical failures (FAIL) → exit code 1, trading aborted
- Non-critical issues (WARN) → logged, trading continues

### auto_tws_manager.py  (IBC watchdog, runs 24/7)
- 5-minute health loop: checks port 7497, restarts gateway if down on weekdays
- Launches IBC via Zulu JRE 17 + `ibc_login_helper.py` (pyautogui credential injection)
- Paper mode enforced in both `jts.ini` and `C:\IBC\config.ini`

### brokerage_interface.py
- IBKR ib_insync wrapper; socket probe + direct `ib.connect(timeout=15)`
- Paper mode fallback when port 7497 unreachable
- Ironclad guardrails: 20% max position size, max 10 positions

### email_notifier.py
- Gmail SMTP 587 + STARTTLS
- Daily trade summary + OrderMonitor alerts + health check status

### smart_data_loader_factory.py
- Tiingo primary → Yahoo Finance fallback
- Returns DataFrame with 26+ years of OHLCV + today's candle appended

---

## Data Flow

```
data/*.parquet  (Tiingo 26yr history, 2,147 tickers)
    |
    +-- load_ticker_with_latest(ticker)         [daily_trading_loop.py]
    |       |
    |       +-- smart_data_loader_factory       Tiingo parquet + today yfinance candle
    |       v
    |   df: full history + today (200+ rows minimum)
    |
    v
strategy_engine.scan_universe()                 [delegated from daily_trading_loop]
    |
    +-- add_indicators_v7_2(df)                 [strategy_v7_2.py]
    +-- apply PARAMS[DEFAULT_VERSION] filters
    |   (stoch 32-80, SMA200, vol 1.5x, CAGR 15%, momentum 5%)
    +-- score = 0.6 * annual_return + 0.4 * stoch_score
    v
    ranked candidate list
    |
    v
strategy_engine.can_enter() + calc_position_size()
    |
    +-- regime check: get_spy_regime()          data/SPY.parquet
    +-- sector cap: max 3 per sector
    +-- vol-adjusted size: base * (median_atr / ticker_atr)
    v
brokerage_interface.place_market_order()        [live] OR paper log [paper]
    |
    v
OrderMonitor: poll 10s -> alert 90s -> cancel 180s
    |
    v
email_notifier -> Gmail SMTP summary
    |
    v
data/portfolio.json  (saved)
```

---

## File Structure

```
VolatilityHunter/
  tickers.txt                     2,149 ticker universe

  src/                            ACTIVE PIPELINE FILES ONLY
    strategy_engine.py            *** SINGLE SOURCE OF TRUTH — change params here ***
    strategy_v7_2.py              Indicators shared by all versions
    strategy_v8.py                v8 backtest engine (reference)
    strategy_v8_1.py              v8.1 backtest engine (reference)
    brokerage_interface.py        IBKR ib_insync wrapper
    email_notifier.py             Gmail SMTP
    smart_data_loader_factory.py  Tiingo/Yahoo smart loader
    storage.py                    Parquet read/write
    config.py                     API key constants

  scripts/
    daily_trading_loop.py         Autonomous daily pipeline v8.1
    simulate_monday.py            Full pipeline dry-run on historical date
    functional_health_check.py    Health gate (10 checks, Exit Code 0 required)
    auto_tws_manager.py           IBC gateway watchdog (24/7)
    ibc_login_helper.py           pyautogui credential injector
    setup_ibc.py                  IBC + Zulu JRE 17 one-time installer
    full_universe_backtest.py     v7.2 standalone backtest
    backtest_v7_vs_v8.py          v7.2 vs v8 comparison
    backtest_v8_vs_v8_1.py        v8 vs v8.1 DD-reduction proof
    fetch_deep_history.py         Download 26yr Tiingo history
    update_data.py                Incremental daily data refresh
    DAILY_ROUTINE/
      run_trading.bat             Task Scheduler entry point (17:06 IST)
      run_auto_tws_manager.bat    Task Scheduler entry point (at logon)

  config/
    agents.json                   Configuration (timeouts, retries, v8.1 params)

  data/
    portfolio.json                Live/paper state — daily_trading_loop.py (gitignored)
    portfolio_sim.json            Simulation snapshot — simulate_monday.py (gitignored)
    portfolio_backtest.json       Backtest scratch state (gitignored)
    SPY.parquet                   SPY history for regime filter (gitignored)
    *.parquet                     Tiingo price history (gitignored)

  logs/
    trading_YYYY-MM-DD.log        Daily loop output
    functional_health_check.log   Health check log
    ibc_gateway.log               IBC startup log
    backtest_v7_vs_v8_*.json      v7 vs v8 comparison results
    backtest_v8_vs_v8_1_*.json    v8 vs v8.1 DD-reduction results

  archive/src_orphans/            Archived 2026-02-28 (not used by active pipeline)
    main_agent_system.py          Former orchestrator entry point
    agents_src/                   7-agent layer (DataAgent, StrategyAgent, etc.)
    [+ 35 other archived files]

  docs/
    README.md                     System overview + backtest results
    ARCHITECTURE.md               This file
    BLUEPRINT.md                  Original Sweet Spot trading rules
    DAILY_FLOW.md                 Step-by-step daily pipeline visual
```

---

## Health Check Protocol

Mandatory before any trading session:

```bash
python scripts/functional_health_check.py
# Must exit with code 0
```

Checks run (10 total):
1. `strategy_engine` — imports + DEFAULT_VERSION + all v8.1 PARAMS present
2. `strategy_v7_2` — `add_indicators_v7_2()` executes without error
3. `brokerage_interface` — `get_brokerage_interface()` importable
4. `email_notifier` — `EmailNotifier` importable
5. `.env` — `TIINGO_API_KEY` set
6. `portfolio.json` — readable, valid JSON, `cash` + `positions` keys present
7. `tickers.txt` — at least 100 tickers loaded
8. `data/SPY.parquet` — exists and readable (regime filter)
9. `data/*.parquet` — at least 500 ticker parquets present
10. `IBKR port 7497` — reachable (WARN only if not, trading continues in paper mode)

**Exit Code 0 = all green. Exit Code 1 = critical failure, abort trading.**

---

## Testing

```bash
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
```

---

## Pipeline File Map (All Active Files)

Every file that participates in the live/paper/simulation/backtest pipeline.

```python
ENTRY POINTS (Task Scheduler)
══════════════════════════════════════════════════════════════════════
scripts/DAILY_ROUTINE/run_trading.bat          Task Scheduler trigger (17:06 IST)
scripts/DAILY_ROUTINE/run_auto_tws_manager.bat Task Scheduler trigger (at logon)

INFRASTRUCTURE (runs 24/7)
══════════════════════════════════════════════════════════════════════
scripts/auto_tws_manager.py        IBC gateway watchdog, 5-min health loop
    └── scripts/tws_keep_alive.py      Called by auto_tws_manager to keep port alive
    └── scripts/ibc_login_helper.py    pyautogui credential injector for IBC

DAILY TRADING PIPELINE (17:06 IST each trading day)
══════════════════════════════════════════════════════════════════════
scripts/functional_health_check.py     GATE: must exit 0 before trading starts
    └── src/strategy_engine.py         DEFAULT_VERSION + PARAMS integrity
    └── src/strategy_v7_2.py           add_indicators_v7_2() smoke test
    └── src/brokerage_interface.py     importable check
    └── src/email_notifier.py          importable check
    └── .env                           TIINGO_API_KEY present
    └── data/portfolio.json            valid JSON, cash+positions keys
    └── tickers.txt                    100+ tickers
    └── data/SPY.parquet               readable
    └── data/*.parquet                 500+ files
    └── port 7497                      IBKR reachable (WARN only)

scripts/daily_trading_loop.py          MAIN: full autonomous trading cycle
    │
    ├── [Step 1] IBKR reconciliation
    │   └── src/brokerage_interface.py         IBKR ib_insync wrapper
    │
    ├── [Step 2] Price fetch
    │   └── (yfinance direct — no wrapper)
    │
    ├── [Step 2b] Tracking update
    │   └── src/strategy_engine.py             update_highest_prices()
    │   └── src/strategy_engine.py             update_high_water_mark()
    │
    ├── [Step 3] Exit check
    │   └── src/strategy_engine.py             check_exits()  ← reads PARAMS[DEFAULT_VERSION]
    │       └── src/strategy_v7_2.py           add_indicators_v7_2()
    │
    ├── [Step 3b] Power stock promotion
    │   └── src/strategy_engine.py             promote_power_stocks()
    │
    ├── [Step 4] Universe scan
    │   └── src/strategy_engine.py             scan_universe()  ← reads PARAMS[DEFAULT_VERSION]
    │       └── src/strategy_v7_2.py           add_indicators_v7_2()
    │       └── data/*.parquet                 26yr Tiingo history (2,147 tickers)
    │
    ├── [Step 4b] Regime check
    │   └── src/strategy_engine.py             get_spy_regime()
    │       └── data/SPY.parquet               SPY 26yr history
    │
    ├── [Step 5] Execute entries
    │   └── src/strategy_engine.py             can_enter() + calc_position_size()
    │   └── src/brokerage_interface.py         place_market_order()
    │
    ├── [Step 6] Order monitor
    │   └── src/brokerage_interface.py         poll openTrades()
    │
    ├── [Step 7] Email summary
    │   └── src/email_notifier.py              Gmail SMTP
    │
    └── [Step 8] Save state
        └── data/portfolio.json                live portfolio state

STRATEGY LOGIC (single source of truth)
══════════════════════════════════════════════════════════════════════
src/strategy_engine.py        *** CHANGE PARAMS HERE — all modes use this ***
    └── src/strategy_v7_2.py  add_indicators_v7_2() — indicators shared by all versions

SIMULATION MODE
══════════════════════════════════════════════════════════════════════
scripts/simulate_monday.py
    └── src/strategy_engine.py    (same functions as live — full parity)
    └── src/strategy_v7_2.py
    └── data/*.parquet

BACKTEST MODE
══════════════════════════════════════════════════════════════════════
scripts/backtest_v8_vs_v8_1.py       v8 vs v8.1 comparison (production proof)
    └── src/strategy_v8.py           v8 backtest engine
    └── src/strategy_v8_1.py         v8.1 backtest engine
    └── src/strategy_v7_2.py         indicators
    └── data/*.parquet

scripts/backtest_v7_vs_v8.py         v7.2 vs v8 comparison (reference)
    └── src/strategy_v8.py
    └── src/strategy_v7_2.py

scripts/full_universe_backtest.py    v7.2 standalone backtest (reference)
    └── src/strategy_v7_2.py

DATA MAINTENANCE (run manually as needed)
══════════════════════════════════════════════════════════════════════
scripts/fetch_deep_history.py    Download full 26yr Tiingo history for all tickers
    └── src/smart_data_loader_factory.py   Tiingo/Yahoo loader
    └── data/*.parquet                     Output

scripts/update_data.py           Incremental daily data refresh
    └── src/smart_data_loader_factory.py
    └── data/*.parquet

CONFIGURATION
══════════════════════════════════════════════════════════════════════
config/agents.json               Agent configuration (timeouts, retries, etc.)
tickers.txt                      2,147 ticker universe
.env                             API keys + EMAIL_RECIPIENTS (TIINGO_API_KEY, Gmail, IBKR)
                                 NOTE: EMAIL_RECIPIENTS must be in .env — config.json does not exist
data/portfolio.json              Live/paper state — daily_trading_loop.py (gitignored)
data/portfolio_sim.json          Simulation snapshot — simulate_monday.py (gitignored)
data/portfolio_backtest.json     Backtest scratch state (gitignored)
data/SPY.parquet                 SPY regime data (gitignored)
```

---

## File Audit: Archived 2026-02-28

All files not used by the active pipeline were moved to `archive/src_orphans/` on 2026-02-28.
Backtests confirmed identical numbers before and after cleanup. Health check 10/10 PASS.

| Archived Group | Contents |
|----------------|----------|
| `archive/src_orphans/main_agent_system.py` | Former 7-agent orchestrator entry point |
| `archive/src_orphans/agents_src/` | All 7 agent implementations |
| `archive/src_orphans/src/` | config_manager, shields, strategy_factory, sweet_spot_strategy, technical_utils, system_monitor, log_sanitizer, yfinance_loader, orchestrator, portfolio_synchronizer, brain_watcher |
| `archive/src_orphans/messaging/` | Message bus (not used by active pipeline) |
| `archive/src_orphans/workflows/` | Workflow manager |
| `archive/src_orphans/patterns/` | Candlestick/chart pattern library |
| `archive/src_orphans/factories/` | Agent factory |
| `archive/src_orphans/interfaces/` | Abstract agent interfaces |
| `archive/src_orphans/utils/` | Concurrency/memory managers |
| `archive/src_orphans/config/` | Config dataclasses |
| `archive/dev/` | Code intelligence tools (index_codebase.py, query_brain.py) |

> All archived files are available for recovery. Nothing was permanently deleted.
