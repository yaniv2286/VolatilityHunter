# 🎯 VolatilityHunter

**Deterministic Quantitative Trading System | v11.6 - Deterministic Automation + Fill-Confirmed Execution**

---

## 📚 Essential Documentation

**IMPORTANT**: Before modifying any trading logic, you MUST read:

- **[🏗️ ARCHITECTURE.md](ARCHITECTURE.md)** - Single Source of Truth for system architecture, execution flow, and technical specifications
- **[📋 ROADMAP.md](ROADMAP.md)** - Future development goals and planned features
- **[� CHANGELOG.md](CHANGELOG.md)** - Historical changes and version history

---

## 🚀 Quick Start

```bash
# 1. Health Check (Critical - Exit Code 0 required)
python scripts/functional_health_check.py

# 2. Verify Windows Task Scheduler
python scripts/verify_scheduler.py

# 3. Run Daily Trading (Production - canonical orchestrator)
python scripts/run_daily_orchestrator.py

# 4. Windows Task Scheduler wrapper
.\scripts\DAILY_ROUTINE\run_trading.bat

# 5. Manual Gateway Launch (component test only)
python scripts/auto_tws_manager.py --one-shot

# 6. Update Data
python scripts/update_data.py

# 7. Backtest Strategy
python scripts/backtest_v8_vs_v8_1.py

# 8. Simulate Trading Day
python scripts/simulate_monday.py

# 9. Monitor Live Logs
Get-Content logs/task_scheduler.log -Wait -Tail 50
```

---

## 📊 System Status

```
✅ Health Check System      : PASS (Exit Code 0, 10 checks)
✅ Daily Orchestrator       : PASS (Gateway -> Data -> Health -> Trading -> Cleanup)
✅ Gateway Automation       : PASS (Ghost-Typist sole login, bounded retries)
✅ Deterministic Guardrails : PASS (11 protection layers active)
✅ ILS to USD Conversion    : PASS (Auto-detect and convert)
✅ Margin Protection        : PASS (Zero margin usage verified)
✅ Market Data Protocol     : PASS (Delayed data, reqMarketDataType(3))
✅ Order Execution          : PASS (Adaptive Limit, SMART routing, fill-confirmed)
✅ Portfolio Sync           : PASS (Live IBKR synchronization)
✅ Daily Trading Routine    : PASS (Monday-Friday via Task Scheduler)
✅ Scheduler Verification   : PASS (`scripts/verify_scheduler.py`, Exit Code 0)
✅ Email Notifications      : PASS (HTML format with log attachments)
✅ Failure Notifications    : PASS (Automatic error alerts)
✅ Data Pipeline            : PASS (Parallel Tiingo API, 15s for 2,136 tickers)
✅ Mode                     : IBKR_PAPER only (no simulation fallback)
```
ALL SYSTEMS OPERATIONAL - Production-hardened with Deterministic Guardrails

SYSTEM HIGHLIGHTS:
  - **Canonical Entry**: `scripts/run_daily_orchestrator.py` writes `data/run_manifest_YYYY-MM-DD.json`
  - **Scheduler**: `VolatilityHunter_Daily_Live` runs Monday-Friday at 17:06; next run verified as Monday 2026-05-04
  - **Gateway Startup**: bounded retry supervisor around `auto_tws_manager.py --one-shot`
  - **Ghost-Typist**: Aggressive field clear, no-maximize, 790x610 natural window
  - **Trading Loop**: ~8 seconds (parallel API fetching)
  - **Email Reports**: Professional HTML format with color-coded P&L tables
  - **Execution**: Adaptive Limit orders only report success after IBKR confirms full fill
  - **Reliability**: Automatic failure notifications with full error details
  - **Data**: Tiingo bulk API (22 parallel requests for 2135 tickers)
  - **Automation**: 100% autonomous daily trading via Windows Task Scheduler
  - **Monitoring**: Live logs via `Get-Content logs/task_scheduler.log -Wait`

---

## 🎯 Latest Achievements (v11.6)

### ✅ **Deterministic Automation + Fill-Confirmed Execution** (May 1, 2026)
- **Canonical Orchestrator**: Added `scripts/run_daily_orchestrator.py`; Scheduler and manual production runs now use one path.
- **Gateway Retries**: Orchestrator retries Gateway startup up to 3 times with cleanup between attempts.
- **Run Manifest**: Writes `data/run_manifest_YYYY-MM-DD.json` with step exit codes, elapsed seconds, and final status.
- **Ghost-Typist Hardening**: Removed window maximize and disabled PyAutoGUI failsafe to match documented natural-window automation protocol.
- **IBC Login Race Removed**: IBC config no longer generates `[LOGON]`, `IbLoginId`, or `IbPassword`; Ghost-Typist owns credential injection.
- **Fill-Confirmed Orders**: `brokerage_interface.py` waits for IBKR `Filled` status, full quantity, and valid average fill price before returning success.
- **Unsafe Fallback Removed**: No synthetic `$100` buy or `$50` sell fallback prices; order placement aborts if no reliable price source exists.
- **Validation**: Gateway invariant verifier, execution invariant verifier, py_compile, functional health check, and two backtests all returned Exit Code 0 on 2026-05-01.

### ✅ **Scheduler Weekday Enforcement** (May 2, 2026)
- **Task**: `VolatilityHunter_Daily_Live`.
- **Schedule**: Weekly Monday-Friday at 17:06.
- **Proof**: `schtasks` verified `Days: MON, TUE, WED, THU, FRI` and next run `2026-05-04 17:06`.
- **Manual Trigger Test**: Saturday Scheduler run entered batch and exited safely with `US markets closed` before Gateway/trading.
- **Verifier**: `python scripts/verify_scheduler.py` returned Exit Code 0.

### 📊 **Backtest Results** (May 1, 2026)
- **v8.1 vs v8.1.2** (`logs/backtest_v8_1_vs_v8_1_2_20260501_2041.json`):
  - Trades: 41,510 vs 41,510
  - 26yr CAGR: 12.88% vs 12.88%
  - Max Drawdown: -36.68% vs -36.68%
  - Sharpe: 0.62 vs 0.62
  - Profit Factor: 1.51 vs 1.51
  - Result: Trade count preserved; no metric improvement in this run.
- **v8.1 vs v8.1.1** (`logs/backtest_v8_1_vs_v8_1_1_20260501_2041.json`):
  - Trades: 41,510 vs 11,456
  - 26yr CAGR: 13.94% vs 12.76%
  - Max Drawdown: -35.86% vs -31.34%
  - Sharpe: 0.58 vs 0.19
  - Profit Factor: 1.51 vs 13.01
  - Result: Drawdown improved, but trade count and 26yr CAGR degraded. v8.1 remains production default.

## 🎯 Previous Achievements (v11.5)

### ✅ **Gateway Login Resilience** (April 23, 2026)
- **IBC Native Login Disabled**: IBC puts directory path in username field with Gateway 10.37+; removed `[LOGON]` section from config.ini
- **No-Maximize Fix**: Login form is fixed-size (~790x610); maximize broke percentage-based coordinates
- **Aggressive Field Clear**: Triple-click + Home/Shift+End/Delete wipes IBC garbage from Java Swing fields
- **15s IBC Wait**: Ghost-Typist waits for IBC broken login cycle to complete before clearing and retyping (prevents keystroke interleaving)
- **Task Scheduler Fix**: Removed `pause` from bat file that hung forever (exit code 267014)
- **Ghost-Typist Hardening**: Disabled FAILSAFE, safe_click(), port check, retry logic
- **Gateway Startup**: ~60 seconds (15s IBC wait + login + auth)

### ✅ **Portfolio Sync & Email Hardening** (April 21, 2026)
- **IBKR Sync Fix**: Positions preserve `entry_date`, `entry_price`, `stop_loss_price` during sync
- **Purchase Date Column**: Email report includes Purchase Date alongside Days Held
- **Always-Spawn Ghost-Typist**: Removed unreliable `SESSIONNAME` check
- **RAPT Ticker Removed**: Delisted after GSK acquisition (March 2026)
- **Windows Auto-Login**: `netplwiz` auto-login + no-sleep for 24/7 operation

### ✅ **Deterministic Guardrails** (April 15, 2026)
- **Nuclear Clear Protocol**: Window center click before credential entry
- **JTS Configuration Guard**: Auto-enforce API=IB mode and LastUser settings
- **Port 7497 Enforcement**: Hardcoded port with 180s timeout and exit code 1
- **ILS to USD Conversion**: Auto-detect currency and convert (250k ILS → $67.5k USD)
- **Margin Abort Check**: Exit if IBKR cash > $150k (prevents inflated balance bugs)
- **Triple-Lock Cash Guard**: Uses min(IBKR cash, portfolio cash, $100k ceiling)
- **Anti-Shorting Logic**: Validates position before sell orders (prevents accidental shorts)
- **UTF-8 Force**: Environment variables for Task Scheduler compatibility
- **Portfolio Sanity Check**: Cash range validation (0-$150k) in health check

**Testing Results (April 23, 2026):**
- Gateway connected in 60 seconds (15s IBC wait + Ghost-Typist login)
- Daily loop: 8.0s, 10 positions, $85,259 total equity
- Health check: 10 PASS, 0 FAIL, Exit Code 0
- Email sent successfully (HTML format with Purchase Date column)
- Task Scheduler: next run today 17:06, pause bug fixed

### ✅ **Gateway Auto-Login** (April 2026)
- **Ghost-Typist Method**: GUI automation with IB API tab selection (always spawned)
- **~25 Second Startup**: Consistent Gateway initialization
- **One-Shot Mode**: `auto_tws_manager.py --one-shot` launches and exits cleanly
- **IBC Integration**: Launches Gateway via IBC classpath method
- **Zero Manual Intervention**: Fully automated from Task Scheduler trigger
- **Windows Auto-Login**: `netplwiz` configured for unattended operation

### ✅ **Production System Stabilization**
- **Lean Pipeline Architecture**: Single source of truth in `strategy_engine.py`
- **Task Scheduler Integration**: Daily execution at 17:06 IST with log redirection
- **Port 7497 Standardization**: Global infrastructure alignment
- **Tiingo Professional API**: 3 bulk requests for 2147 tickers
- **Dead Man's Switch**: Command Center with Architect review

### ✅ **Order Execution System**
- **Market Data Protocol**: reqMarketDataType(3) for delayed data
- **SMART Routing**: Multi-exchange execution for optimal fills
- **Market Orders**: Immediate execution in paper trading
- **Real-time Monitoring**: Order status tracking and alerts

### ✅ **Complete Automation**
- **Windows Task Scheduler**: Triggers daily at 17:06 IST
- **Automated Workflow**: Gateway start → Health check → Trading → Gateway stop
- **Email Notifications**: Success/failure reports via Gmail SMTP
- **Log Management**: All output redirected to `logs/task_scheduler.log`

---

## 🏗️ Architecture Overview

### **Lean Pipeline Architecture**
- **strategy_engine.py**: Single source of truth for all strategy logic
- **daily_trading_loop.py**: Main autonomous pipeline (8 steps)
- **functional_health_check.py**: 10 critical checks (Exit Code 0 gate)
- **auto_tws_manager.py**: Gateway launcher with Ghost-Typist integration
- **brokerage_interface.py**: IBKR API wrapper (port 7497)
- **smart_data_loader_factory.py**: Tiingo Professional API integration

### **Execution Flow**
1. **Task Scheduler** triggers `run_trading.bat` at 17:06 IST
2. **Gateway Startup** via `auto_tws_manager.py --one-shot`
3. **Health Check** validates all systems (10 checks)
4. **Trading Loop** executes autonomous scan → rank → execute
5. **Gateway Shutdown** via `stop_gateway.py`
6. **Dead Man's Switch** pauses for Architect review

---

## 📈 Strategy Performance

**Strategy v8.1** (Current Production)
- **Signal Ranking**: 0.6 × annual_return + 0.4 × stoch_score
- **Entry Filters**: Stochastic 32-80, SMA200, Vol 1.5×, CAGR 15%, Momentum 5%
- **Exit Rules**: Hard stop 8%, Overbought 78, Time stop 10 days
- **Position Sizing**: Volatility-adjusted, max 20% per position
- **Risk Management**: Drawdown circuit (-10% DD → 50% size, -20% DD → 25% size)

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                  VolatilityHunter v11.0                     │
│                 Lean Pipeline Architecture                  │
├─────────────────────────────────────────────────────────────┤
│  Task Scheduler (17:06 IST)                                │
│       ↓                                                      │
│  auto_tws_manager.py --one-shot (Gateway + Ghost-Typist)   │
│       ↓                                                      │
│  functional_health_check.py (10 checks)                    │
│       ↓                                                      │
│  daily_trading_loop.py (scan → rank → execute)            │
│       ↓                                                      │
│  stop_gateway.py (cleanup)                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🎯 Key Features

- **🚀 Full Automation**: 100% autonomous daily trading via Task Scheduler
- **� Ghost-Typist Login**: Reliable Gateway auto-login (8-10s startup)
- **📊 Tiingo Professional**: Bulk API for 2147 tickers (3 requests)
- **🛡️ Safety Systems**: No margin/leverage, position limits, drawdown circuit
- **🧪 Health Check Gate**: 10 critical checks, Exit Code 0 required
- **� Email Notifications**: Success/failure reports via Gmail SMTP
- **� Live Monitoring**: Real-time log viewing via PowerShell

---

## 📁 Project Structure

```
VolatilityHunter/
├── 📚 docs/                    # Documentation
│   ├── ARCHITECTURE.md        # Single source of truth (MUST READ)
│   ├── ROADMAP.md            # Future development goals
│   └── CHANGELOG.md          # Version history
├── 🤖 src/                    # Core pipeline
│   ├── strategy_engine.py    # *** SINGLE SOURCE OF TRUTH ***
│   ├── strategy_v7_2.py      # Indicators (shared by all versions)
│   ├── brokerage_interface.py # IBKR port 7497 interface
│   ├── email_notifier.py     # Gmail SMTP
│   ├── smart_data_loader_factory.py # Tiingo Professional API
│   └── storage.py            # Parquet read/write
├── 🧪 scripts/               # Execution scripts
│   ├── daily_trading_loop.py # Main autonomous pipeline
│   ├── functional_health_check.py # Health gate (Exit Code 0)
│   ├── auto_tws_manager.py   # Gateway launcher + Ghost-Typist
│   ├── ibc_login_helper.py   # Ghost-Typist credential injection
│   ├── stop_gateway.py       # Gateway shutdown
│   ├── DAILY_ROUTINE/
│   │   └── run_trading.bat   # Command Center with Dead Man's Switch
│   └── [other scripts]       # Utilities and backtesting
├── ⚙️ config/                # Configuration files
├── 📊 data/                  # Market data (gitignored)
│   ├── portfolio.json        # Live state
│   ├── SPY.parquet          # Regime filter data
│   └── *.parquet            # 26yr history per ticker
├── � logs/                  # Execution logs
│   └── task_scheduler.log   # Daily routine output
├── 📚 requirements.txt       # Dependencies
├── 📋 tickers.txt           # 2147 ticker universe
└── 📚 .env                  # API keys (gitignored)
```

---

## 📞 Support

For detailed information about the mathematical rules and system architecture, please see the **[docs/](docs/)** folder.

**⚠️ IMPORTANT**: Always read `docs/ARCHITECTURE.md` before modifying any trading logic!

---

**🎉 VolatilityHunter v11.4 is fully operational with IB API tab fix, portfolio sync hardening, and unattended automation!**
