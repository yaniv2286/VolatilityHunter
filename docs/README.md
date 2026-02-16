# 🎯 VolatilityHunter

**Deterministic Quantitative Trading System | v7.4 Unified Engine | Pre-Earnings Shield | Forward-Test Suite**

---

## 📋 Project Overview

VolatilityHunter is a **deterministic, rule-based quantitative trading system** built on a **3-Pillar Architecture** designed for systematic wealth generation through technical analysis and risk management. **Successfully validated through 26-year Crucible Engine backtesting with 122,510 trades analyzed.**

### 🏗️ The 3-Pillar Architecture

- **The Guard** (`health_check.py`) - Pre-market system validation and health monitoring
- **The Historian** (`update_universe.py`) - Smart data synchronization with append logic
- **The Hunter** (`main_unified.py`) - Unified trading execution with Environmental Shields

---

## 🚀 Current Version: v7.4 Unified Engine (Phase 4 Complete)

### ✨ Key Features

#### **🔍 5-Gate Entry System with Environmental Shields**
- **Quality Gate**: Historical CAGR > 15%
- **Trend Gate**: Price > SMA 200
- **SweetSpot Gate**: Stochastic %K (10,3,3) in [32-80]
- **Momentum Gate**: Volume > 30-day SMA
- **Blueprint Crossover**: Stochastic %K > %D (Red over Yellow)
- **Environmental Shields**: Pre-Earnings protection, volume/price safety checks

#### **🛡️ Pre-Earnings Shield (Phase 4)**
- **Earnings Safety**: Blocks trades within ±3 days of earnings announcements
- **Volume Spike Detection**: Identifies potential earnings events via volume > 3x normal
- **Universal Protection**: Works across live and simulation modes
- **Reference Date Awareness**: Uses today for live, simulation date for backtest

#### **⚡ Unified Execution Engine**
- **Single Entry Point**: `main_unified.py` handles all execution modes
- **Factory Pattern**: Dependency injection for data loaders and portfolio managers
- **Mode Switching**: Live, simulation, and backtest modes via command line
- **Forward-Test Suite**: Time-shifted simulation with consolidated reporting

#### **🛡️ Power Stock Shield**
- **Detection**: Stochastic > 80 + Price > all SMAs + High volume
- **Enhanced Exits**: SMA 25 break instead of SMA 200 for Power Stocks
- **Vertical Trend Protection**: Prevents premature exits during hyper-momentum
- **Performance**: 69.33% win rate on 5,312 Power Stock trades

---

## 📊 Crucible Engine Validation Results

### **26-Year Backtest Performance (2001-2026)**
- **Total Trades Analyzed**: 122,510 (v7.4) vs 102,483 (v6.5)
- **Trade Capture Improvement**: +19.5% more opportunities with shields
- **Power Stock Trades**: 5,312 (4.3% of all v7.4 trades - higher quality)
- **Power Stock Win Rate**: 69.33%

### **10-Slot Portfolio Real-World Performance**
- **Initial Capital**: $100,000
- **Final Capital**: $219,188
- **CAGR**: 3.12% (realistic with position constraints)
- **Max Drawdown**: -15.23% (Ironclad protection)
- **Win Rate**: 44.80%
- **Executed Trades**: 2,501 (out of 122,510 available)

---

## 📊 Data Pipeline

### **Smart Append Tiingo Integration**
- **Coverage**: 2,147 US stocks with 26+ year historical data
- **Volume**: 8.7+ million rows of clean market data
- **Reliability**: 99.9% uptime with intelligent error handling
- **Storage**: Local Parquet files for optimal performance
- **Integrity**: Append-only logic prevents data destruction

### **Data Specifications**
- **Source**: Tiingo API with EOD pricing
- **Format**: Apache Parquet (columnar storage)
- **History**: 2000-01-03 to present (26+ years)
- **Update**: Smart incremental updates with overlap safety

---

## 🎯 Trading Strategy

### **A+ Wealth Builder Logic with Environmental Shields**
1. **Environmental Shields First**: Pre-Earnings, volume, and price safety checks
2. **Strict Entry Requirements**: All 5 gates must pass + shield approval
3. **Dynamic Position Sizing**: 1% portfolio risk based on 3.0x ATR
4. **ATR-Based Risk Management**: Trailing stops with ratchet logic
5. **Power Stock Enhancement**: Special handling for hyper-momentum stocks

### **Risk Management Framework**
- **Position Limit**: Maximum 10 positions
- **Risk Per Trade**: 1% of portfolio equity
- **Stop Distance**: 3.0x ATR from highest price
- **Sector Diversification**: Maximum 3 positions per sector
- **Ironclad Guardrails**: 20% notional cap, $0.01 micro-stop, $1.00 price floor, 10% volume cap

---

## 🛠️ Installation & Setup

### **Prerequisites**
- Python 3.10+
- Tiingo API key
- 8GB+ RAM recommended

### **Quick Start**
```bash
# Clone repository
git clone https://github.com/your-repo/VolatilityHunter.git
cd VolatilityHunter

# Setup environment
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp .env.example .env
# Edit .env with your Tiingo API key

# Run system health check
python health_check.py

# Start live trading
python main_unified.py --mode live
```

---

## 🎯 How to Run

### **Unified Execution Engine Commands**

#### **Live Trading (Default)**
```bash
# Run live trading with today's date
python main_unified.py --mode live

# Or simply (live is default)
python main_unified.py
```

#### **Simulation Mode**
```bash
# Run simulation for specific date
python main_unified.py --mode sim --date 2026-01-04

# Run full forward-test suite (33 trading days)
python simulation/run_simulation_loop.py
```

#### **Backtest Mode (Future)**
```bash
# Run historical backtest (future integration)
python main_unified.py --mode backtest
```

### **System Operations**
```bash
# System health check
python health_check.py

# Update market data
python update_universe.py

# Run Crucible backtest
python crucible_engine.py

# Generate TradingView import
python prepare_tv_import.py
```

---

## 🧪 Testing & Validation

### **Test Suite**
```bash
# Run comprehensive tests
python lightning_tests.py
python quick_tests.py
python quick_test_runner.py

# Run 26-year backtest
python crucible_engine.py

# Generate TradingView import
python prepare_tv_import.py

# Verify data integrity
python health_check.py
```

### **Validation Checklist**
- ✅ System health checks pass
- ✅ Data pipeline operational (99.9% uptime)
- ✅ Strategy logic verified (122,510 trades analyzed)
- ✅ Environmental shields functional
- ✅ Risk management constraints enforced
- ✅ Backtest results reproducible
- ✅ TradingView integration tested

---

## 📁 Project Structure

```
VolatilityHunter/
├── 📄 Core System
│   ├── main_unified.py           # Unified execution engine (all modes)
│   ├── health_check.py           # System validation
│   ├── update_universe.py        # Data synchronization
│   ├── crucible_engine.py        # Master backtesting
│   ├── prepare_tv_import.py      # TradingView export
│   └── final_audit.py            # Architect audit tools
├── 📂 src/                       # Core business logic
│   ├── shields.py                # Environmental shields (Phase 4)
│   ├── data_loader_factory.py    # Factory pattern for data loaders
│   ├── strategy_v7_2.py          # Hybrid Blueprint logic
│   ├── tracker.py                # Portfolio management
│   ├── execution.py              # Trade execution
│   └── [support modules...]
├── 📂 simulation/                # Forward-Test Suite
│   ├── run_simulation_loop.py    # Consolidated simulation runner
│   ├── simulated_data_loader.py  # Time-shifted data access
│   └── portfolio_sim.json        # Simulation portfolio state
├── 📂 data/                      # Market data (Parquet files)
│   ├── backtest_results_v6_0.csv # v6.0 Crucible results
│   ├── backtest_results_v6_5.csv # v6.5 Crucible results
│   └── tv_final_sync_v6_5.csv    # TradingView import
├── 📂 docs/                      # Documentation
├── 📂 research/                  # Lab notes and analysis
└── 📂 logs/                      # Execution logs
```

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed system architecture and Unified Engine
- **[ROADMAP.md](docs/ROADMAP.md)** - Development roadmap and Phase 4 completion
- **[research/](research/)** - Analysis notes and backtest results

---

## 🤝 Contributing

### **Development Workflow**
1. Fork the repository
2. Create feature branch
3. Implement changes with tests
4. Run full test suite
5. Submit pull request

### **Code Standards**
- Follow PEP 8 guidelines
- Add comprehensive docstrings
- Include unit tests for new features
- Update documentation for API changes

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 📞 Support

For questions, issues, or contributions:
- **Issues**: [GitHub Issues](https://github.com/your-repo/VolatilityHunter/issues)
- **Discussions**: [GitHub Discussions](https://github.com/your-repo/VolatilityHunter/discussions)

---

**VolatilityHunter v7.4 Unified Engine** - Phase 4 Complete | Pre-Earnings Shield | Forward-Test Suite 🎯

*Last Updated: February 2026*
