# 🎯 VolatilityHunter

**Deterministic Quantitative Trading System | v11.3 - Gateway Hardened**

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

# 2. Run Daily Trading (Production - includes Gateway auto-start)
.\scripts\DAILY_ROUTINE\run_trading.bat

# 3. Manual Gateway Launch (if needed)
python scripts/auto_tws_manager.py --one-shot

# 4. Update Data
python scripts/update_data.py

# 5. Backtest Strategy
python scripts/backtest_v8_vs_v8_1.py

# 6. Simulate Trading Day
python scripts/simulate_monday.py

# 7. Monitor Live Logs
Get-Content logs/task_scheduler.log -Wait -Tail 50
```

---

## 📊 System Status

```
✅ Health Check System      : PASS (Exit Code 0, 11 checks)
✅ Gateway Automation       : PASS (Ghost-Typist IB API tab + IBC native login, 20s startup)
✅ Deterministic Guardrails : PASS (11 protection layers active)
✅ ILS to USD Conversion    : PASS (Auto-detect and convert)
✅ Margin Protection        : PASS (Zero margin usage verified)
✅ Market Data Protocol     : PASS (Delayed data, reqMarketDataType(3))
✅ Order Execution          : PASS (Market orders, SMART routing)
✅ Portfolio Sync           : PASS (Live IBKR synchronization)
✅ Daily Trading Routine    : PASS (Fully automated via Task Scheduler)
✅ Email Notifications      : PASS (HTML format with log attachments)
✅ Failure Notifications    : PASS (Automatic error alerts)
✅ Data Pipeline            : PASS (Parallel Tiingo API, 15s for 2,136 tickers)
✅ Mode                     : IBKR_PAPER only (no simulation fallback)
```
🎉 ALL SYSTEMS OPERATIONAL! Production-hardened with Deterministic Guardrails!

📊 SYSTEM HIGHLIGHTS:
  - **Gateway Startup**: ~20 seconds via Ghost-Typist (IB API tab click → credentials → submit)
  - **Session 0 Support**: IBC native login for headless Task Scheduler execution
  - **Trading Loop**: ~60 seconds total (4x faster with parallel API fetching)
  - **Email Reports**: Professional HTML format with color-coded P&L tables
  - **Execution**: Market orders filling successfully across multiple exchanges
  - **Reliability**: Automatic failure notifications with full error details
  - **Data**: Tiingo bulk API (3 requests for 2147 tickers)
  - **Automation**: 100% autonomous daily trading via Windows Task Scheduler
  - **Monitoring**: Live logs via `Get-Content logs/task_scheduler.log -Wait`

---

## 🎯 Latest Achievements (v11.3)

### ✅ **Gateway Login Hardening** (April 20, 2026)
- **IB API Tab Fix**: Ghost-Typist now explicitly clicks "IB API" tab before entering credentials
  - Root cause: Gateway defaults to "FIX CTCI" tab which uses different authentication
  - Fix: Click at 75% width, 180px from top (double-click for reliability)
- **Session 0 Detection**: Auto-detects Task Scheduler headless mode via `SESSIONNAME` env var
  - Interactive sessions: Ghost-Typist handles login via GUI automation
  - Task Scheduler (Session 0): IBC native login from `config.ini` credentials
- **Dual Login Strategy**: Ghost-Typist for interactive, IBC native for headless
- **Gateway Startup**: ~20 seconds from launch to API ready on port 7497

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

**Testing Results (April 20, 2026):**
- ✅ Gateway connected in 20 seconds (IB API tab fix verified)
- ✅ 9 positions active, $85,864 total portfolio value
- ✅ Zero margin usage (critical success!)
- ✅ All guardrails verified working in production
- ✅ Email notifications working (HTML format with log attachments)

### ✅ **Gateway Auto-Login** (April 2026)
- **Ghost-Typist Method**: GUI automation with IB API tab selection
- **~20 Second Startup**: Consistent Gateway initialization
- **One-Shot Mode**: `auto_tws_manager.py --one-shot` launches and exits cleanly
- **IBC Integration**: Launches Gateway UI, Ghost-Typist or IBC handles login
- **Zero Manual Intervention**: Fully automated from Task Scheduler trigger

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

**🎉 VolatilityHunter v11.3 is fully operational with IB API tab fix, Session 0 support, and complete automation!**
