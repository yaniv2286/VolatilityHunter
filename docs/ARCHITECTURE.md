🏗️ VolatilityHunter Architecture
Project: VolatilityHunter

Current Version: 9.0 IBKR Integration | Portfolio Synchronization | Live Trading System | Production Hedge Fund Platform

Status: 🟢 PRODUCTION READY | FULLY INTEGRATED WITH IBKR | TWS PORTFOLIO SYNCHRONIZED | LIVE TRADING OPERATIONAL

System Health: ✅ 8/8 HEALTH CHECKS PASSING (Feb 23, 2026)
- ✅ Internet Connectivity: Connected (IP: 46.116.184.75)
- ✅ Tiingo API: Valid (AAPL: $271.01)
- ✅ IBKR Connectivity: Fully operational with trade testing (Port 7497)
- ✅ Disk Permissions: Read/Write OK
- ✅ Config Validity: LIVE mode, TIINGO source
- ✅ Python Environment: 3.10.9
- ✅ Market Hours: Validated (17:30-23:00 IST SweetSpot window)
- ✅ Email Notifications: Operational with full portfolio reporting

🚀 NEW: Complete IBKR Integration (Phase 12 Complete)
- ✅ IBKR Interface: Full connection and order execution through TWS
- ✅ Live Executor: Real-time trade execution with IBKR integration
- ✅ Portfolio Synchronizer: Automatic sync between local portfolio and TWS
- ✅ Trade Testing: Health check includes buy/sell order verification
- ✅ TWS Integration: Portfolio visible and updated in TWS GUI
- ✅ Order Tracking: Real-time order status and execution monitoring
- ✅ Account Sync: Cash and position synchronization between systems
- ✅ Production Ready: Complete live trading pipeline with IBKR

🎯 KEY ACHIEVEMENT: Email Portfolio === TWS Portfolio
- ✅ Daily email reports show exact portfolio status
- ✅ TWS GUI displays identical portfolio in real-time
- ✅ Automatic synchronization after every trade execution
- ✅ Complete portfolio verification and reconciliation
- ✅ Full logging of all IBKR operations and sync actions

� 1. Core Architecture (The 3-Pillar System)
Pillar I: The Guard (health_check.py + run_trading.bat)
Schedule: 17:30 IST Daily (10:30 AM EST) | Purpose: System Health Validation & Production Gatekeeper

"Fail Fast" Philosophy: Prevents silent failures before execution begins.

Validations: Internet connectivity, Tiingo API uptime, disk permissions, CPU/RAM resource monitoring, IBKR connectivity (7497/7496), SweetSpot window validation (17:30-23:00 IST).

Gatekeeper Workflow: Health Check → IBKR Port Validation → Market Hours Window → Auto-Launch Live Trader.

Pillar II: The Historian (update_universe.py)
Schedule: Optional/Manual | Purpose: Market Data Synchronization

Smart Append: Downloads only new EOD data and merges without destroying history.

Scale: Synchronizes 2,000+ tickers into highly compressed Apache Parquet files.

Uptime: 99.9% reliability managing over 8.7+ million rows of data.

Pillar III: The Hunter (main_unified.py + scripts/portfolio_aggregator.py + Sweet Spot Strategy)
Schedule: 17:30 IST Daily (10:30 AM EST) | Purpose: Unified Trading Execution

Total Market Crucible: Single $100k portfolio dynamically allocated across 2,000+ ticker universe.


Portfolio Aggregator: Eliminates cash drag with 89.7% capital utilization and Ironclad Guardrails.

Power Stock State Machine: Real-time promotion tracking with dual-exit architecture.

Memory Load: Safely loads portfolio files via absolute paths with automated backup fallbacks.

Exit Engine (First Priority): Updates ATR trailing stops (Ratchet Logic) and checks for standard/power exit triggers before buying.

Market Analysis: Scans 2,000+ tickers against the Hybrid Blueprint 5-Gate entry criteria with Environmental Shields.

Execution & Risk: Calculates dynamic position sizing, updates cash balances, and registers trades.

Reporting: Generates Master Tearsheet with Power Stock performance metrics and exports to tv_export_full.csv.

Note: Execution delayed by 60 minutes to avoid Opening Range volatility and ensure Stochastic signal stabilization (SweetSpot window).

🎯 2. The Strategy: v8.0 Power Stock Dual-Exit Architecture + Sweet Spot Blueprint Integration
Revolutionary advancement beyond the Hybrid Blueprint with state machine-based promotion tracking, dual-exit logic, and comprehensive pattern recognition.

Entry Engine (The Enhanced 6-Gate System)
Gate 1: Quality: Historical CAGR > 15%.

Gate 2: Trend: Price > SMA 200.

Gate 3: The Sweet Spot: Stochastic %K (10,3,3) must be in the [32-80] zone.

Gate 4: The Blueprint Crossover: Mandatory Stochastic %K > %D (Red over Yellow).

Gate 5: Momentum: Current Volume > 1.5x 30-Day Volume SMA.

Gate 6: Pattern Confirmation: Candlestick + Chart pattern validation (NEW).

Environmental Shields (Phase 4)
Pre-Earnings Shield: is_earnings_safe(ticker, reference_date) prevents trades within ±3 days of earnings announcements.

Volume Safety Shield: Minimum volume threshold (100,000 shares) to avoid liquidity traps.

Price Safety Shield: Minimum price threshold ($5.00) to eliminate penny stocks and reverse-split ghosts.

Market Microstructure Filters (NEW - Sweet Spot Blueprint)
Time Filters: 10:06 AM Rule (preference scoring) + Friday Rule (profit-taking awareness).

Spread Monitor: Real-time IBKR bid/ask spread limits (< 2c under $100, < 5c $250+, < 20c $300+).

Pattern Recognition System (NEW)
Candlestick Patterns: Engulfing (strong reversal), Hammer (potential reversal), Doji (avoid - indecision).

Chart Patterns: W Formations (bullish pullbacks), M Formations (bearish tops), Head & Shoulders (major bearish), 50% Rule (resistance levels).

Pattern Scoring: Weighted pattern strength calculation integrated with entry decisions.

The Power Stock State Machine (v8.0 Revolution)
Standard Entry: All trades enter as Standard Trades (is_power_stock = False).

Daily Promotion Check: Every day, the system checks if held positions meet Power Stock promotion criteria.

Power Promotion Criteria:
- Stoch %K > 80
- Price > SMA 25, 50, 100, and 200 (Vertical Trend)
- Meets criteria for 2 consecutive days (Fake-out prevention)

State Persistence: Once promoted, is_power_stock = True permanently via positions dictionary tracking.

Dual-Exit Architecture (Revolutionary Breakthrough)
Standard Trade Exit: SMA 200 Break OR Stochastic %K < %D (Stochastic Roll-over).

Power Stock Exit: SMA 25 Break OR 3.0x ATR Trailing Stop (Power Shield conditions).

Enhanced Exit Logic (NEW): Pattern-based early exit signals for bearish patterns.

State Machine Logic: Exit conditions determined by CURRENT Power Stock status, not entry status.

🛡️ 3. Risk Management: The Ironclad Guardrails
Absolute mathematical boundaries designed to prevent catastrophic losses, split-adjustment data ghosts, and liquidity traps.

Position Sizing Engine
Base Risk: 1% of total portfolio equity risked per trade based on a 3.0x ATR stop distance.

Ratchet Stops: Trailing stops only move UP, never down.

The 4 Ironclad Constraints (Zero-Exception Rules)
The 20% Notional Cap: Never exceeds 20% of portfolio equity in a single position (e.g., Max $20k per trade on a $100k account).

Micro-Stop Filter: Rejects trades if stop-loss distance is < $0.01 (prevents infinite-share data bugs).

Absolute Price Floor: Rejects any stock priced < $1.00 (eliminates penny stocks and reverse-split ghosts).

Volume Cap: Total shares purchased cannot exceed 10% of the stock's 30-day average daily volume.

Portfolio Constraints (v8.0)
Maximum Positions: 10 concurrent positions enforced throughout 26-year timeline.

Capital Utilization: 89.7% average utilization (vs 99% dead cash in isolated accounts).

Risk Per Trade: Strict 1% portfolio equity risk per trade.

📊 4. Total Market Crucible Validation (2000–2026)
The Ironclad-protected system has been battle-tested across 26 years of market history with 2,000+ ticker universe, fully surviving the Dot-Com bust, 2008 Financial Crisis, 2020 COVID Crash, and 2022 inflation bleed.

Performance Truth Summary
Historical Coverage: Jan 2000 – Feb 2026 (26-year total market validation)

Total Trades Executed: 3,004 (Portfolio Aggregator)

Power Stock Trades: 1,841 (61.3% of all trades)

Power Stock Win Rate: 62.19% (vs 46.24% overall)

Total Return: 2,112.63% ($100k → $2.21M)

CAGR: 12.62% (26-year performance)

Max Drawdown: -50.90% (Survived all major crises)

Capital Utilization: 89.7% (Near-optimal deployment)

Crisis Survival: Successfully navigated Dot-Com bust, 2008 Financial Crisis, COVID crash, 2022 inflation bleed

Billion-Dollar Data Bugs: 0 (Completely eliminated by Ironclad Guardrails)

🔧 5. Portfolio Aggregator Architecture (v8.0 Revolution)
Total Market Engine
Single Portfolio: $100k dynamically allocated across 2,000+ ticker universe

Cash Drag Elimination: 89.7% capital utilization vs 99% dead cash in isolated accounts

Power Stock State Machine: Real-time promotion tracking with positions dictionary persistence

Dual-Exit Logic: Dynamic exit conditions based on CURRENT Power Stock status

Ironclad Guardrails: 1% risk model, 3.0x ATR stops, 20% notional cap, max 10 positions

Chronological Loop: Day-by-day simulation across 26-year timeline with proper state synchronization

State Machine Implementation
Daily Promotion Check: Monitors power_promotion_trigger for held positions

State Persistence: positions[ticker]['is_power_stock'] tracks current Power Stock status

Exit Logic: Uses tracked state (not dataframe state) for dual-exit decisions

Promotion Tracking: 100% accuracy - 1,841 promoted trades properly tracked

Performance Tracking: Complete trade history with Power Stock metrics in tv_export_full.csv

🛡️ 6. Ironclad Risk Management System
Mathematical Boundaries
Position Sizing: 1% portfolio equity risk per trade based on 3.0x ATR stop distance

Micro-Stop Filter: Rejects trades with stop distance < $0.01

Notional Cap: Maximum 20% portfolio equity per position

Volume Constraints: 10% average daily volume cap per position

Portfolio Constraints
Maximum Positions: 10 concurrent positions enforced throughout 26-year timeline

Risk Per Trade: Strict 1% portfolio equity risk per trade

Capital Efficiency: 89.7% average utilization with controlled risk

Crisis Management: Survived all major market crashes with controlled drawdowns

📊 7. Total Market Crucible Validation (2000–2026)
The Ironclad-protected system has been battle-tested across 26 years of market history with 2,000+ ticker universe, fully surviving the Dot-Com bust, 2008 Financial Crisis, 2020 COVID Crash, and 2022 inflation bleed.

Performance Truth Summary
Historical Coverage: Jan 2000 – Feb 2026 (26-year total market validation)

Total Trades Executed: 3,004

Power Stock Trades: 1,841 (61.3% of all trades)

Power Stock Win Rate: 62.19%

Total Return: 2,112.63% ($100k → $2.21M)

CAGR: 12.62%

Max Drawdown: -50.90%

Capital Utilization: 89.7%

Crisis Survival: Successfully navigated all major market crashes

🔧 8. Technical Stack & Data Flow
Key Engineering Decisions
Storage Layer: Apache Parquet for speed/compression; JSON for state persistence; CSV for trade exports.

Multiprocessing: Portfolio Aggregator utilizes vectorized signal generation and chronological processing for efficient 2,000+ ticker analysis.

TradingView Exporter: Automated tv_export_full.csv export formats trade data with Power Stock tracking for visual tape auditing.

Directory Structure
VolatilityHunter/
 Core System
 main_unified.py           # Unified execution engine with strategy selection
 health_check.py           # System validation
 update_universe.py        # Data synchronization
 run_trading.bat           # Task Scheduler integration
 src/                       # Core business logic
 strategy_v7_2.py          # Hybrid Blueprint strategy (v7.2)
 sweet_spot_strategy.py    # Sweet Spot Enhanced strategy
 strategy_factory.py       # Strategy factory for v7.2  Sweet Spot switching
 patterns/                 # Pattern Recognition Module
 candlestick_patterns.py # Candlestick pattern detection
 chart_patterns.py     # Chart pattern detection
 pattern_utils.py      # Pattern utilities & scoring
 market_microstructure/    # Market Microstructure Module
 time_filters.py       # Time-based trading filters
 spread_monitor.py     # IBKR spread monitoring
 execution.py              # Trade execution
 data_loader.py            # Data management
 tracker.py                # Portfolio management
 system_monitor.py        # System resource monitoring
 log_sanitizer.py          # Log sanitization & API redaction
 [support modules...]
 scripts/                   # Automation & validation
 portfolio_aggregator.py   # Total Market Crucible engine
 tws_keep_alive.py         # TWS Keep-Alive service
 [validation scripts...]
 Validation Scripts         # Sweet Spot validation suite
 test_sweet_spot_integration.py # Integration tests (5/5 PASS)
 validate_sweet_spot_config.py # Configuration validation (6/6 PASS)
 test_sweet_spot_performance.py # Performance tests (EXCELLENT)
 data/                      # Market data & portfolio state
 [2,000+ ticker files]     # Total Market universe
 portfolio.json           # Live portfolio state
 docs/                      # Documentation
 README.md                  # This file
 ARCHITECTURE.md           # System architecture
 ROADMAP.md                # Development roadmap
 logs/                      # Daily VH_YYYY-MM-DD.log files
 .vh_knowledge_base/          # VH-BRAIN Vector Database
 docs/                        # ARCHITECTURE.md, ROADMAP.md

Data Flow Execution
Unified Engine (main_unified.py) → Strategy Factory (v7.2 vs Sweet Spot Selection)
    ↓
Environmental Shields (src/shields.py) → Pre-Earnings Safety Check
    ↓
Enhanced 6-Gate Strategy (v7.2 + Sweet Spot Patterns) → Market Microstructure Filters
    ↓
Ironclad Risk Check → IBKR Spread Validation → Pattern Confirmation
    ↓
Trade Execution → Portfolio State Update → Email Reporting
    ↓
Portfolio State (portfolio.json or portfolio_sim.json) → Dynamic Valuation
    ↓
SMTP Email (Master Report + Sweet Spot Analytics + .log Attachment)

Resilience & API Handling
Production-Grade Error Prevention & Data Source Compatibility

1. "Slow Drip" Tiingo API Batching Fix
Problem: Tiingo API returns 404 Client Error when too many tickers are batched in a single URL request due to URL length limits.

Solution: Individual ticker processing with intelligent rate limiting.
- BATCH_SIZE = 1 (processes one ticker at a time)
- 100ms delay between requests (time.sleep(0.1))
- Graceful 404 handling with WARNING logs for delisted tickers
- Continues processing remaining tickers even if some fail

Result: Eliminates URL length crashes, provides granular error tracking, maintains full 2,149 ticker universe coverage.

2. Robust Column Detection System
Problem: Different data sources use varying column naming conventions (adjClose vs Close vs close), causing KeyError crashes when accessing price/volume data.

Solution: Dynamic column detection with fallback hierarchy.
- Price Columns: 'adjClose' > 'Close' > 'close' (prioritized check)
- Volume Columns: 'Volume' > 'volume' > 'adjVolume'
- Applied across all strategy calculations, exit conditions, and portfolio valuation
- Centralized in strategy_v7_2.py with consistent error handling

Result: System automatically adapts to any data source format, prevents case-sensitivity crashes, ensures reliable operation across Tiingo, YFinance, or local parquet data.

🧠 9. VH-BRAIN Automated Watchdog (NEW)
Intelligent Vector Database Synchronization System

Purpose: Eliminates local RAG memory gap by automatically maintaining perfect sync between codebase changes and vector database.

Technology Stack: Python watchdog library hooks into OS file events for real-time monitoring.

Monitoring Scope: src/, scripts/, simulation/, and main_unified.py for .py and .md file modifications.

Debounce Logic: 2-second delay prevents multiple triggers from single save operations.

Indexing Action: Dynamic calls to scripts/index_codebase.py for only the modified file, updating specific vector chunks.

Error Protocol: "No Silent Failures" - logs [ERROR] VH-BRAIN failed to index {file_path} on database lock or update failures.

Integration: Must run in background terminal during development for perfect VH-BRAIN synchronization.

📊 10. 20-Year Vectorized Backtest Infrastructure (NEW)
Institutional-Grade Backtesting with Pure Pandas Vectorization

Data Acquisition: scripts/fetch_deep_history.py pulls 20 years (2004-01-01 to Present) from Tiingo for S&P 500 universe.

Storage: {ticker}_20yr.parquet files separate from current optimized data to avoid conflicts.

Vectorized Engine: scripts/vectorized_backtester.py uses pure Pandas operations (no loops) with corrected equity curve math:

Correct P&L Calculation:
```python
df['daily_return'] = df['adjClose'].pct_change()
df['strategy_return'] = df['position'].shift(1) * df['daily_return']  
df['equity'] = initial_capital * (1 + df['strategy_return'].fillna(0)).cumprod()
```

Position Management: .where() and .ffill() prevents buying same stock multiple times without SELL reset.

Performance Metrics: CAGR, Max Drawdown, Win Rate, Profit Factor vs SPY benchmark.

TradingView Export: Industry-standard CSV format (Symbol, Date, Side, Qty, Price) for visual tape auditing.

Runtime Target: Under 5 minutes for full 20-year analysis across 500 tickers.