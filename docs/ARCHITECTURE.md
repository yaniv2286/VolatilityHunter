# VolatilityHunter Architecture - Single Source of Truth

**Version**: Production v11.1 | **Updated**: 2026-04-10 | **Strategy**: v8.1 (Lean Pipeline)

---

## 🎯 Executive Summary

VolatilityHunter is a **deterministic quantitative trading fund** ($100k) using a **Lean Pipeline Architecture** with **100% autonomy**. The system executes one complete trading cycle per market day via Windows Task Scheduler, using **Tiingo Professional API** (parallel fetching) for data and **IBKR Paper Trading** for execution.

**🔒 CURRENT STATUS**: Fully operational - Gateway auto-login via Ghost-Typist (8-10s), parallel API fetching (15s for 2,136 tickers), HTML email reports, automatic failure notifications. Trading loop completes in ~60 seconds.

### Core Philosophy
- **No Silent Failures**: Every error is logged, reported, and visible in Command Center
- **Single Source of Truth**: All strategy logic in `strategy_engine.py`
- **Professional Data Tier**: Tiingo bulk API for 2,147 ticker universe
- **Dead Man's Switch**: Window never closes silently, always awaits Architect review

---

## 🏗️ Production Architecture

```
                    VOLATILITYHUNTER v8.1
                    LEAN PIPELINE ARCHITECTURE

  Windows Task Scheduler (17:06 IST / 10:06 AM ET daily)
              |
              v
    run_trading.bat (Command Center with Dead Man's Switch)
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

## 🔧 Core Component Specifications

### strategy_engine.py (Single Source of Truth)
- **DEFAULT_VERSION = 'v8.1'** — change here to switch all modes at once
- **PARAMS['v8.1']**: 
  - `HARD_STOP_PCT = 8%` — Maximum loss tolerance
  - `OVERBOUGHT_EXIT = 78` — Stochastic exit threshold
  - `TIME_STOP_DAYS = 10` — Maximum holding period
  - `REGIME_MAX_POS = 3` — Positions in drawdown regime
  - `SECTOR_MAX = 3` — Maximum per sector
  - `VOL_SIZE = True` — Volatility-adjusted sizing
- **Signal Ranking**: `0.6 * annual_return + 0.4 * stoch_score`

### daily_trading_loop.py (Live/Paper Entry Point)
- **8-step autonomous pipeline**: scan → rank → execute → monitor → email → save
- **Tiingo Bulk API Integration**: 3 requests for 2,147 tickers (1000 per request)
- **IBKR Interface**: Port 7497 with paper mode fallback
- **OrderMonitor**: Poll fills every 10s, alert at 90s, cancel at 180s

### functional_health_check.py (Gate)
- **10 Critical Checks**: strategy_engine, strategy_v7_2, brokerage_interface, email_notifier, .env keys, portfolio.json, tickers.txt, SPY.parquet, data/*.parquet universe, IBKR port 7497
- **Exit Code 0 Required**: Any failure aborts trading
- **No Silent Failures**: All errors visible in Command Center

### auto_tws_manager.py (Gateway Launcher)
- **One-shot mode**: `--one-shot` flag launches Gateway and exits after API ready
- **Ghost-Typist Login**: `ibc_login_helper.py` handles credential injection via GUI automation
- **IBC Integration**: Launches Gateway via IBC, disables IBC native login to avoid conflicts
- **Paper Mode Enforced**: Both `jts.ini` and `C:\IBC\config.ini`
- **API Ready Check**: Waits up to 300s for port 7497 to become available

### brokerage_interface.py
- **Port 7497 Standard**: Active connection to IBKR TWS/Gateway
- **Paper Mode Fallback**: Automatic switching when port unreachable
- **Ironclad Guardrails**: 20% max position size, max 10 positions

### smart_data_loader_factory.py (Professional Data Tier)
- **Tiingo Exclusive**: Professional API with bulk metadata endpoint
- **Optimized Fetching**: 1000 tickers per request, 3 requests total
- **Error Handling**: Comprehensive retry logic with rate limit protection

---

## 📊 Data Flow & Execution

```
Tiingo Professional API (Bulk Metadata)
    |
    +-- smart_data_loader_factory.update_all_stocks()
    |       |-- 1000 tickers per request
    |       |-- 3 total requests for 2,147 tickers
    |       |-- Latest close + volume data
    |       v
    |   data/*.parquet (26yr history + today's candle)
    |
    v
strategy_engine.scan_universe()
    |
    +-- add_indicators_v7_2() [strategy_v7_2.py]
    +-- Apply PARAMS[DEFAULT_VERSION] filters
    |   (stoch 32-80, SMA200, vol 1.5x, CAGR 15%, momentum 5%)
    +-- Score calculation: 0.6 * annual_return + 0.4 * stoch_score
    v
    Ranked candidate list
    |
    v
strategy_engine.can_enter() + calc_position_size()
    |
    +-- Regime check: get_spy_regime() [data/SPY.parquet]
    +-- Sector cap: max 3 per sector
    +-- Vol-adjusted size: base * (median_atr / ticker_atr)
    v
brokerage_interface.place_market_order() [Port 7497]
    |
    v
OrderMonitor: poll 10s → alert 90s → cancel 180s
    |
    v
email_notifier → Gmail SMTP summary
    |
    v
data/portfolio.json (state saved)
```

---

## 🚀 Command Center Execution Flow

### Batch Execution Sequence (run_trading.bat)

```batch
:: 1. Weekday Validation
if %dayofweek%==6 goto WEEKEND_SKIP
if %dayofweek%==0 goto WEEKEND_SKIP

:: 2. Environment Setup
cd /d "D:\GitHub\VolatilityHunter"
call venv\Scripts\activate.bat

:: 3. Gateway Startup (One-Shot Mode)
python scripts\auto_tws_manager.py --one-shot
if %ERRORLEVEL% NEQ 0 (
    python scripts\send_gateway_failure_email.py
    goto :FAILED
)

:: 4. Health Check Gate
python scripts\functional_health_check.py
if %ERRORLEVEL% NEQ 0 goto :FAILED

:: 5. Trading Loop Execution
python scripts\daily_trading_loop.py
if %ERRORLEVEL% NEQ 0 goto :FAILED

:: 6. Gateway Shutdown
python scripts\stop_gateway.py

:: 7. Cleanup
taskkill /F /IM java.exe /T >nul 2>&1
taskkill /F /IM javaw.exe /T >nul 2>&1

:: 8. Success
goto :END

:FAILED
echo [VH] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo [VH] !!           MISSION FAILED               !!
echo [VH] !!       CRITICAL ERROR - SYSTEMS       !!
echo [VH] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!

:END
echo [VH] COMMAND CENTER - Dead Man's Switch Active
echo [VH] Window will remain open for Architect review
pause
exit /b %ERRORLEVEL%
```

### No Silent Failures Protocol

1. **Log Redirection**: Task Scheduler redirects all output to `logs/task_scheduler.log`
2. **Error Redirection**: Every `ERRORLEVEL` check redirects to `:FAILED`
3. **Big Block Errors**: Failed section displays ERRORLEVEL and details
4. **Permanent Pause**: `:END` section always triggers, success or failure
5. **Window Persistence**: Command Center never closes silently
6. **Live Monitoring**: Use `Get-Content logs/task_scheduler.log -Wait -Tail 50` to view real-time output

---

## 🔌 Port 7497 Infrastructure

### Global Port Configuration
- **.env**: `IBKR_PORT=7497` (Global production constant)
- **brokerage_interface.py**: `self.port = config.get('IBKR_PORT', 7497)`
- **auto_tws_manager.py**: `TWS_PORT = 7497` and `LocalServerPort=7497`
- **functional_health_check.py**: Port 7497 reachability check
- **run_trading.bat**: PowerShell ping loop checks port 7497

### IBKR Connection Flow
```
Port 7497 (TWS Paper)
    |
    v
IBKR Interface (ib_insync)
    |
    v
Paper Trading Mode (if port unreachable)
    |
    v
Order Execution
```

---

## 📡 Tiingo Professional Data Integration

### Bulk API Optimization
```python
# Before: 2,136 individual ticker requests
# After: 3 bulk requests (1000 tickers each)

url = "https://api.tiingo.com/tiingo/daily/prices"
params = {
    'tickers': ','.join(chunk),  # 1000 tickers per request
    'startDate': (datetime.now() - timedelta(days=2)).strftime('%Y-%m-%d'),
    'endDate': datetime.now().strftime('%Y-%m-%d'),
    'columns': 'close,volume',
    'format': 'json',
    'resampleFreq': 'daily'
}
headers = {'Authorization': f'Bearer {TIINGO_API_KEY}'}
```

### Data Loader Factory
```python
def get_data_loader():
    """Professional data loader - Tiingo exclusive."""
    log_info("Production: Using Tiingo Professional API")
    return TiingoLoader()
```

---

## 🛡️ Safety & Risk Management

### No Margin/Leverage Policy
```python
# ENFORCED: Only trade with available cash
available_cash = portfolio.get('cash', 0)
if shares <= 0 or cost > available_cash or cost > alloc:
    return 0, 0.0
```

### Position Sizing Rules
- **Maximum 20%** per position
- **Maximum 10** simultaneous positions
- **Sector cap**: 3 positions per sector
- **Volatility-adjusted sizing** enabled

### Drawdown Circuit
- **-10% DD**: 50% position size
- **-20% DD**: 25% position size
- **Hard stop**: 8% maximum loss

---

## 📁 File Structure (Production)

```
VolatilityHunter/
├── 📄 ARCHITECTURE.md              # This file - Single Source of Truth
├── 📄 ROADMAP.md                   # Future development goals
├── 📄 CHANGELOG.md                 # Historical changes
├── 📄 README.md                    # Brief introduction
├── 📄 .env                         # API keys + IBKR_PORT=7497
├── 📄 tickers.txt                  # 2,147 ticker universe
│
├── 📁 src/                         # Active pipeline only
│   ├── strategy_engine.py         # *** SINGLE SOURCE OF TRUTH ***
│   ├── strategy_v7_2.py           # Indicators (shared by all versions)
│   ├── brokerage_interface.py     # IBKR port 7497 interface
│   ├── email_notifier.py          # Gmail SMTP
│   ├── smart_data_loader_factory.py # Tiingo Professional API
│   └── storage.py                  # Parquet read/write
│
├── 📁 scripts/
│   ├── daily_trading_loop.py       # Main autonomous pipeline
│   ├── functional_health_check.py  # Health gate (Exit Code 0)
│   ├── auto_tws_manager.py         # IBC watchdog (24/7)
│   ├── ibc_login_helper.py         # Ghost-Typist login recovery
│   └── DAILY_ROUTINE/
│       └── run_trading.bat         # Command Center with Dead Man's Switch
│
├── 📁 config/
│   └── agents.json                 # System configuration
│
├── 📁 data/
│   ├── portfolio.json              # Live state (gitignored)
│   ├── SPY.parquet                 # Regime filter data
│   └── *.parquet                   # Tiingo 26yr history (gitignored)
│
├── 📁 logs/                        # Daily execution logs
└── 📁 archive/                     # Historical code (not used)
```

---

## 🧪 Testing & Validation

### Mandatory Health Check
```bash
python scripts/functional_health_check.py
# Must exit with code 0
```

### 10 Critical Checks
1. **strategy_engine** — imports + DEFAULT_VERSION + PARAMS integrity
2. **strategy_v7_2** — add_indicators_v7_2() smoke test
3. **brokerage_interface** — importable check
4. **email_notifier** — importable check
5. **.env** — TIINGO_API_KEY + IBKR_PORT present
6. **portfolio.json** — valid JSON, cash + positions keys
7. **tickers.txt** — 100+ tickers loaded
8. **data/SPY.parquet** — readable (regime filter)
9. **data/*.parquet** — 500+ ticker files present
10. **IBKR port 7497** — reachable (WARN only if not)

### Simulation Mode
```bash
python scripts/simulate_monday.py
# Full pipeline dry-run on historical date
```

---

## 🔄 Daily Operations

### Automated Execution (17:06 IST)
1. **Windows Task Scheduler** triggers `run_trading.bat`
2. **Command Center** opens (output redirected to `logs/task_scheduler.log`)
3. **Gateway Startup** launches via `auto_tws_manager.py --one-shot`
   - IBC launches Gateway UI
   - Ghost-Typist injects credentials (focus → clear → type → submit)
   - Waits for port 7497 API ready (8-10 seconds typical)
4. **Health Check** validates all systems (Exit Code 0 required)
5. **Trading Loop** executes full autonomous cycle
6. **Gateway Shutdown** via `stop_gateway.py`
7. **Cleanup** terminates Java processes
8. **Dead Man's Switch** pauses for Architect review

### Manual Operations
- **Data Refresh**: `python scripts/update_data.py`
- **Backtesting**: `python scripts/backtest_v8_vs_v8_1.py`
- **IBKR Manual**: `python scripts/auto_tws_manager.py`

---

## 📞 Support & Troubleshooting

### Critical Error Response
1. **Command Center** shows big block error display
2. **ERRORLEVEL** indicates failure point
3. **Logs** contain detailed traceback
4. **Window remains open** for Architect review
5. **No silent failures** - all issues visible

### Common Issues
- **Port 7497 unreachable**: Check IBKR Gateway status
- **Tiingo API failures**: Verify TIINGO_API_KEY in .env
- **Health check failures**: Run individual checks manually
- **Order execution issues**: Resolved with delayed data protocol (reqMarketDataType(3))

### 🚀 Execution System (NEW)
- **Market Data**: Delayed data permission (reqMarketDataType(3))
- **Order Type**: Market orders for immediate paper trading fills
- **Routing**: SMART routing with contract qualification
- **Exchanges**: Multi-exchange execution (NASDAQ, NYSE, ARCA, BYX, LTSE)
- **Timeout**: 5-minute cancellation for unfilled orders
- **Monitoring**: Real-time order status tracking

---

## 🎯 Production Readiness Checklist

### ✅ Daily Operations
- [ ] Windows Task Scheduler enabled (17:06 IST)
- [ ] IBKR Gateway running on port 7497
- [ ] Tiingo API key valid and funded
- [ ] Gmail SMTP credentials working
- [ ] Command Center visible and responsive

### ✅ System Health
- [ ] functional_health_check.py exits 0
- [ ] All 10 critical checks passing
- [ ] Portfolio state synchronized
- [ ] Data files up-to-date
- [ ] Logs rotating properly

### ✅ Risk Management
- [ ] No margin/leverage usage
- [ ] Position sizing limits enforced
- [ ] Drawdown circuit functional
- [ ] Order monitoring active
- [ ] Email alerts working

---

**This ARCHITECTURE.md serves as the Single Source of Truth for the VolatilityHunter production system. All technical decisions, port configurations, and execution flows are documented here. No other documentation should contain active technical specifications.**

*Last Updated: 2026-04-10 - Ghost-Typist Gateway Auto-Login Implemented*
