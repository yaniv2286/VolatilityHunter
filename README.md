# 🎯 VolatilityHunter v5.5 (A+ Wealth Builder)

A locally hosted, autonomous swing-trading bot using Tiingo data. It scans the US market daily, identifies high-volatility setups, and manages a paper portfolio with ATR-based trailing stops.

---

## 🚀 Quick Start

### Daily Automation (Recommended)
**Windows Task Scheduler Setup:**
- **9:00 AM:** `python health_check.py` (System validation)
- **10:00 AM:** `python main.py` (Trading execution)

### Manual Operations
```bash
# Run the Hunter - Main trading execution
python main.py

# Run the Guard - System health validation
python health_check.py

# Force Data Sync - Update all market data
python update_universe.py

# Migrate Portfolio Schema - Update legacy positions
python migrate_portfolio_schema.py

# Create Context Map - Generate project snapshot
python generate_snapshot.py
```

---

## ⚙️ Configuration

### Required Files
1. **`config.json`** - API keys, risk settings, trading parameters
2. **`data/tickers.txt`** - Universe of 2,149 US stocks (auto-generated)
3. **`.env`** - Tiingo API key (get free at https://www.tiingo.com/)

### Key Settings
- **Initial Capital:** $100,000 (paper trading)
- **Max Positions:** 10 concurrent positions
- **Risk Management:** 3.0x ATR trailing stops, volatility-adjusted sizing
- **Entry Rules:** A+ Wealth Builder strict criteria

---

## 📊 Current Status (February 2026)

### Trading Mode
- **Mode:** Paper Trading
- **Portfolio Value:** $100,761.39
- **Active Positions:** 10/10 slots filled
- **Available Cash:** $50,000.00
- **Total Return:** $761.39 (+0.76%)

### Strategy Performance
- **Strategy:** A+ Wealth Builder (Strict Entry + ATR Exits)
- **Indicators:** Stochastic %K (10,3,3), SMA 200, Volume Analysis, CAGR
- **Universe:** 2,149 US stocks (full market coverage)
- **Benchmark:** Tracking performance vs S&P 500

### Recent Activity
- **Market Data:** Fresh through February 10, 2026
- **Last Scan:** 0 BUY signals, 1 SELL signal (MPW)
- **Data Quality:** 99.9% success rate (2,147/2,149 tickers)
- **Execution:** Clean with zero errors

---

## 🎯 A+ Wealth Builder Strategy

### Strict Entry Rules
1. **TREND:** Price (Adj Close) > SMA 200
2. **SWEETSPOT:** Stochastic %K (10,3,3) in [32-80]
3. **MOMENTUM:** Current Volume > 30-Day Volume SMA
4. **QUALITY:** Historical CAGR > 15%

**All rules must pass for BUY signal.**

### Exit Conditions
1. **Trend Break:** Price < SMA 200
2. **Trailing Stop:** Price < 3.0x ATR trailing stop (ratchet - only moves up)

### Risk Management
- **Position Sizing:** Volatility-adjusted (1.5% risk per trade)
- **Stop Loss:** 3.0x ATR trailing stops with ratchet mechanism
- **Portfolio Limits:** Maximum 10 concurrent positions
- **Volume Filters:** Avoids illiquid stocks

### Technical Indicators
- **SMA 200:** Long-term trend direction
- **Stochastic (10,3,3):** Mean reversion signals (K=10 for A+ precision)
- **Volume Analysis:** Momentum confirmation and liquidity checks
- **CAGR:** Historical performance filter (15% minimum)
- **ATR:** Volatility measurement for trailing stops

---

## 🏗️ System Architecture

### Core Components
1. **The Guard** (`health_check.py`) - System validation at 9:00 AM
2. **The Hunter** (`main.py`) - Trading execution at 10:00 AM
3. **The Historian** (`update_universe.py`) - Market data synchronization
4. **The Migrator** (`migrate_portfolio_schema.py`) - Portfolio schema updates

### Data Flow
```
Tiingo API → Parquet Files → A+ Strategy Engine → Trading Signals → Portfolio Management
                                                    ↓
                                          ATR Trailing Stop Engine
```

### Storage
- **Market Data:** Local parquet files (`data/*.parquet`)
- **Portfolio State:** `data/portfolio.json` (ATR-enabled schema)
- **Logs:** Daily execution logs (`logs/VH_YYYY-MM-DD.log`)

---

## 📈 Performance Metrics

### System Performance
- **Startup Time:** <5 seconds
- **Market Scan:** 2,149 stocks in <30 seconds
- **Portfolio Loading:** <1 second with error resilience
- **Memory Usage:** <500MB during full scan

### Reliability
- **Uptime:** 99.9% (with error resilience)
- **Data Loss:** 0 incidents (v5.0 persistence fix)
- **Error Rate:** <0.1% (isolated ticker failures)
- **Recovery:** <30 seconds from backup

---

## 🛡️ Safety Features

### Error Resilience
- **Individual Ticker Isolation:** One bad ticker doesn't crash the system
- **Backup Restoration:** Automatic portfolio backup recovery
- **Graceful Degradation:** Continues operating with partial data
- **Comprehensive Logging:** Full audit trail of all operations

### Risk Management
- **Position Limits:** Maximum 10 concurrent positions
- **ATR Trailing Stops:** Dynamic stops based on volatility
- **Volume Filters:** Avoids illiquid stocks
- **Cash Management:** Maintains minimum cash reserves
- **Ratchet Logic:** Stops only move up, never down

---

## 🔧 Installation & Setup

### Prerequisites
- Python 3.10+
- Tiingo API key (free tier available)
- Windows (optimized) or Unix compatible

### Setup Steps
```bash
# Clone repository
git clone <repository-url>
cd VolatilityHunter

# Create virtual environment
python -m venv venv
venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
echo "TIINGO_API_KEY=your_key_here" > .env

# Initial data sync
python update_universe.py

# Run health check
python health_check.py

# Migrate portfolio schema (if upgrading)
python migrate_portfolio_schema.py
```

---

## 📋 File Structure

```
VolatilityHunter/
├── 📄 Core Files
│   ├── main.py                 # Trading execution
│   ├── health_check.py         # System validation
│   ├── update_universe.py      # Data synchronization
│   ├── migrate_portfolio_schema.py # Portfolio migration
│   └── generate_snapshot.py     # Project documentation
│
├── 📂 src/                    # Business logic
│   ├── tracker.py             # Portfolio management (ATR-enabled)
│   ├── execution.py           # Trading engine
│   ├── strategy.py            # A+ Wealth Builder strategy
│   ├── technical_utils.py     # ATR calculations and utilities
│   └── storage.py             # Data persistence
│
├── 📂 data/                   # Market data (Git ignored)
│   ├── *.parquet            # Individual stock data
│   ├── portfolio.json        # ATR-enabled portfolio state
│   └── portfolio_legacy_backup.json # Legacy backup
│
├── 📂 logs/                   # Daily logs
├── 📂 docs/                   # Documentation
│   ├── README.md              # This file
│   ├── ARCHITECTURE.md        # Technical architecture
│   └── generate_snapshot.py   # Documentation utility
│
└── config.json               # Trading configuration
```

---

## 🎯 Version 5.5 Highlights

### ✅ A+ Wealth Builder Strategy
- **Strict Entry Rules:** 4-rule gatekeeper (Trend, SweetSpot, Momentum, Quality)
- **Stochastic K=10:** Precision-tuned for optimal entry signals
- **Volume Momentum:** Added volume confirmation for entry quality
- **CAGR Quality Filter:** Strict 15% minimum historical performance

### ✅ ATR-Based Exit Engine
- **3.0x ATR Trailing Stops:** Dynamic volatility-based exits
- **Ratchet Logic:** Stops only move up, never down
- **Daily Stop Updates:** Automatic trailing stop adjustments
- **SMA 200 Break Exits:** Trend breakdown protection

### ✅ Portfolio Schema Migration
- **ATR Risk Tracking:** `atr_at_entry`, `stop_price`, `highest_price` fields
- **Legacy Compatibility:** Seamless migration from v5.0 positions
- **Robust Backup:** Automatic legacy backup creation
- **Schema Validation:** Complete field presence verification

### ✅ Enhanced Risk Management
- **Volatility-Adjusted Sizing:** 1.5% risk per trade based on ATR
- **Dynamic Stop Distance:** Adapts to market volatility
- **Position Risk Tracking:** Complete ATR data for each position
- **Exit Engine Integration:** Daily exit condition checks

### ✅ Production Ready
- **Zero Data Loss:** Robust portfolio persistence
- **Comprehensive Error Handling:** Individual ticker isolation
- **Automated Health Checks:** Pre-market system validation
- **Complete Audit Trail:** Full trade and stop update logging

---

## 📞 Support

- **Documentation:** See `docs/ARCHITECTURE.md` for technical details
- **Logs:** Check `logs/VH_YYYY-MM-DD.log` for daily operations
- **Health:** Run `python health_check.py` for system diagnostics
- **Migration:** Run `python migrate_portfolio_schema.py` for schema updates

---

## ⚠️ Disclaimer

**Educational Purpose Only:** This bot is for research and educational purposes. Trading involves substantial risk of loss. Past performance does not guarantee future results. Always conduct your own research and consult with a financial advisor before making investment decisions.

**Paper Trading Only:** Current version operates in paper trading mode only. No real money is at risk.

---

**Built with ❤️ for autonomous algorithmic trading**  
**Version:** 5.5 (A+ Wealth Builder | Stable | Paper Trading | A+ Optimization)
