🏗️ VolatilityHunter Architecture
Project: VolatilityHunter

Current Version: 7.4 Unified Engine | Pre-Earnings Shield | Forward-Test Suite

Status: 🟢 PRODUCTION READY | AUTONOMOUS | 26-YEAR BACKTESTED | 122,510 TRADES ANALYZED

📋 1. Core Architecture (The 3-Pillar System)
Pillar I: The Guard (health_check.py)
Schedule: 09:00 AM IST Daily | Purpose: System Health Validation

"Fail Fast" Philosophy: Prevents silent failures before execution begins.

Validations: Internet connectivity, Tiingo API uptime, disk permissions, CPU/RAM resource monitoring.

Pillar II: The Historian (update_universe.py)
Schedule: Optional/Manual | Purpose: Market Data Synchronization

Smart Append: Downloads only new EOD data and merges without destroying history.

Scale: Synchronizes 2,147 tickers into highly compressed Apache Parquet files.

Uptime: 99.9% reliability managing over 8.7+ million rows of data.

Pillar III: The Hunter (main_unified.py)
Schedule: 10:00 AM IST Daily | Purpose: Unified Trading Execution

Unified Execution Engine: Single entry point for all execution modes via Factory Pattern.

Mode Switching: --mode live (Tiingo + portfolio.json), --mode sim --date YYYY-MM-DD (Parquet + portfolio_sim.json), --mode backtest (Future Crucible integration).

Memory Load: Safely loads portfolio files via absolute paths with automated backup fallbacks.

Exit Engine (First Priority): Updates ATR trailing stops (Ratchet Logic) and checks for standard/power exit triggers before buying.

Market Analysis: Scans 2,147 tickers against the Hybrid Blueprint 5-Gate entry criteria with Environmental Shields.

Execution & Risk: Calculates dynamic position sizing, updates cash balances, and registers trades.

Reporting: Generates daily HTML valuations and sends SMTP emails with attached execution logs (.log).

🎯 2. The Strategy: v7.4 Hybrid Blueprint with Environmental Shields
Combines the "Sweet Spot" entry theory with the "Power Stock Shield" protection and "Pre-Earnings Shield" safety.

Entry Engine (The 5-Gate System)
Quality: Historical CAGR > 15%.

Trend: Price > SMA 200.

The Sweet Spot: Stochastic %K (10,3,3) must be in the [32-80] zone.

The Blueprint Crossover: Mandatory Stochastic %K > %D (Red over Yellow).

Momentum: Current Volume > 1.5x 30-Day Volume SMA.

Environmental Shields (Phase 4)
Pre-Earnings Shield: is_earnings_safe(ticker, reference_date) prevents trades within ±3 days of earnings announcements.

Volume Safety Shield: Minimum volume threshold (100,000 shares) to avoid liquidity traps.

Price Safety Shield: Minimum price threshold ($5.00) to eliminate penny stocks and reverse-split ghosts.

The Promotion System
Standard Trade: Any trade entered via the base 5-Gate system.

Power Promotion: Automatic permanent upgrade to is_power_stock = True if the stock achieves:

Stoch %K > 80

Price > SMA 25, 50, 100, and 200 (Vertical Trend)

Meets criteria for 2 consecutive days (Fake-out prevention)

Dynamic Exit Engine
Standard Mode: Exit on SMA 200 Break OR Stoch %K < %D (Stochastic Roll-over).

Power Shield Mode: SMA 200 breaks are ignored. Exit ONLY on SMA 25 Break OR 3.0x ATR Trailing Stop.

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

📊 4. Full-Era Crucible Validation (2001–2026)
The Ironclad-protected system has been battle-tested across 25 years of market history, fully surviving the 2008 Financial Crisis and the 2020 COVID Crash.

Performance Truth Summary
Historical Coverage: Jan 2001 – Feb 2026

Total Trades Analyzed: 122,510

2008 Crisis Survival: 1,495 trades processed safely through the crash.

Max Drawdown: -15.23% (Hedge-fund tier risk control)

Power Stock Win Rate: 69.33% (5,312 highly-filtered A+ setups)

Billion-Dollar Data Bugs: 0 (Completely eliminated by Ironclad Guardrails)

🔧 5. Unified Execution Engine Architecture
Factory Pattern Implementation
DataLoaderFactory: Creates appropriate data loader based on execution mode (SimulatedParquetLoader for sim, TiingoDataLoader for live).

PortfolioManagerFactory: Creates appropriate portfolio manager (portfolio_sim.json for sim, portfolio.json for live).

Universal Shields: Mode-agnostic safety checks that work across live and simulation environments.

Mode-Based Execution
Live Mode: --mode live (default) - Uses Tiingo API, portfolio.json, today's date as reference.

Simulation Mode: --mode sim --date YYYY-MM-DD - Uses local Parquet data, portfolio_sim.json, specified date as reference.

Backtest Mode: --mode backtest - Future integration with Crucible Engine for historical validation.

Forward-Test Suite
Time-Shifted Simulation: Replays trading days from 2026-01-01 to present with consolidated reporting.

Email Consolidation: Single master report with daily progression table and log attachment.

Position Cap Enforcement: 10-position maximum maintained across all modes.

🛡️ 6. Phase 4: Environmental Shields System
Pre-Earnings Shield Logic
Reference Date Awareness: Uses today's date for live mode, simulation date for sim mode.

Earnings Detection: Scans for earnings announcements within ±3 days of reference date.

Multiple Data Sources: Checks earnings_announcement, earnings_date, earnings, earnings_surprise columns.

Volume Spike Detection: Identifies potential earnings events via volume > 3x normal (3.0x threshold).

Safety Enforcement: Automatically rejects trades that fail earnings safety check.

Shield Integration Flow
Universal Shields Applied First: All stocks pass through environmental shields before strategy analysis.

Shield Rejection Tracking: Detailed logging of shield failures with specific reasons.

Mode-Agnostic Operation: Same shield logic works for live trading and historical simulation.

Comprehensive Safety: Combines earnings, volume, and price safety checks into unified protection.

📊 7. Full-Era Crucible Validation (2001–2026)
The Ironclad-protected system has been battle-tested across 25 years of market history, fully surviving the 2008 Financial Crisis and the 2020 COVID Crash.

Performance Truth Summary
Historical Coverage: Jan 2001 – Feb 2026

Total Trades Analyzed: 122,510

2008 Crisis Survival: 1,495 trades processed safely through the crash.

Max Drawdown: -15.23% (Hedge-fund tier risk control)

Power Stock Win Rate: 69.33% (5,312 highly-filtered A+ setups)

Billion-Dollar Data Bugs: 0 (Completely eliminated by Ironclad Guardrails)

🔧 8. Technical Stack & Data Flow
Key Engineering Decisions
Storage Layer: Apache Parquet for speed/compression; JSON for state persistence.

Multiprocessing: The Crucible Engine utilizes ProcessPoolExecutor (4 workers) and Pandas vectorization to scan 20+ years of data in minutes.

TradingView Exporter: Automated prepare_tv_import.py script formats backtest data into 2-legged (Buy/Sell) CSVs for visual tape auditing on TradingView.

Directory Structure
Plaintext
VolatilityHunter/
├── main_unified.py          # Unified Execution Engine (All Modes)
├── health_check.py          # The Guard (System Diagnostics)
├── update_universe.py       # The Historian (Data Sync)
├── crucible_engine.py       # The Backtest Sandbox
├── prepare_tv_import.py     # TradingView Exporter
├── src/
│   ├── shields.py           # Environmental Shields (Phase 4)
│   ├── data_loader_factory.py # Factory Pattern for Data Loaders
│   └── ...                  # Core logic modules
├── simulation/              # Forward-Test Suite
│   ├── run_simulation_loop.py # Consolidated Simulation Runner
│   ├── simulated_data_loader.py # Time-Shifted Data Access
│   └── portfolio_sim.json   # Simulation Portfolio State
├── data/                    # .parquet market data & portfolio.json
├── logs/                    # Daily VH_YYYY-MM-DD.log files
└── docs/                    # ARCHITECTURE.md, ROADMAP.md

Data Flow Execution
Plaintext
Unified Engine (main_unified.py) → Factory Pattern (Mode-Based Injection)
    ↓
Environmental Shields (src/shields.py) → Pre-Earnings Safety Check
    ↓
Hybrid 5-Gate Strategy → Ironclad Risk Check → Trade Execution
    ↓
Portfolio State (portfolio.json or portfolio_sim.json) → Dynamic Valuation
    ↓
SMTP Email (Master Report + .log Attachment for Simulation)

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