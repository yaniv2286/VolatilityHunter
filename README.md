# 🎯 VolatilityHunter

**Deterministic Quantitative Trading System | v6.5 A+ Wealth Builder**

---

## 📋 Project Overview

VolatilityHunter is a **deterministic, rule-based quantitative trading system** built on a **3-Pillar Architecture** designed for systematic wealth generation through technical analysis and risk management.

### 🏗️ The 3-Pillar Architecture

- **The Guard** (`health_check.py`) - Pre-market system validation and health monitoring
- **The Historian** (`update_universe.py`) - Smart data synchronization with append logic
- **The Hunter** (`main.py`) - Autonomous trading execution with A+ Wealth Builder strategy

---

## 🚀 Current Version: v6.5 A+ Wealth Builder

### ✨ Key Features

#### **🔍 4-Gate Entry System**
- **Quality Gate**: Historical CAGR > 15%
- **Trend Gate**: Price > SMA 200
- **SweetSpot Gate**: Stochastic %K (10,3,3) in [32-80]
- **Momentum Gate**: Volume > 30-day SMA
- **Phase 1**: Visual Pattern Recognition (W-Pattern/Engulfing)

#### **🛡️ Power Stock Shield**
- **Detection**: Stochastic > 80 + Price > all SMAs + High volume
- **Enhanced Exits**: SMA 25 break instead of SMA 200 for Power Stocks
- **Vertical Trend Protection**: Prevents premature exits during hyper-momentum

#### **⚡ 26-Year Crucible Engine**
- **`crucible_engine.py`**: Master backtesting framework
- **v6.0 vs v6.5 Comparison**: Direct performance analysis
- **Multiprocessing**: `ProcessPoolExecutor` with memory management
- **252-Day Bouncer**: Minimum data requirement enforcement

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

### **A+ Wealth Builder Logic**
1. **Strict Entry Requirements**: All 4 gates must pass + visual pattern
2. **Dynamic Position Sizing**: 1% portfolio risk based on 3.0x ATR
3. **ATR-Based Risk Management**: Trailing stops with ratchet logic
4. **Power Stock Enhancement**: Special handling for hyper-momentum stocks

### **Risk Management Framework**
- **Position Limit**: Maximum 10 positions
- **Risk Per Trade**: 1% of portfolio equity
- **Stop Distance**: 3.0x ATR from highest price
- **Sector Diversification**: Maximum 3 positions per sector

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

# Start paper trading
python main.py
```

---

## 📈 Performance

### **Backtested Results (26-Year Analysis)**
- **Strategy**: A+ Wealth Builder v6.5 with Power Stock Shield
- **Timeframe**: 2000-01-03 to 2026-02-12
- **Universe**: 2,147 US stocks
- **Engine**: Crucible Engine with multiprocessing

### **Key Metrics**
- **Entry Success Rate**: Strict 4-gate system with pattern confirmation
- **Power Stock Performance**: Enhanced returns during vertical trends
- **Risk-Adjusted Returns**: ATR-based position sizing and stops
- **Drawdown Control**: Dynamic trailing stops with ratchet logic

---

## 🔧 Configuration

### **Core Settings (`config.json`)**
```json
{
    "DATA_SOURCE": "TIINGO",
    "TRADING_MODE": "PAPER",
    "RISK_TOLERANCE": "MEDIUM",
    "MAX_POSITIONS": 10,
    "POSITION_SIZE_PERCENT": 0.01
}
```

### **Strategy Parameters**
- **Stochastic Settings**: K=10, D=3, Smooth=3
- **SMA Periods**: 25, 50, 100, 200
- **ATR Period**: 14 days
- **Volume SMA**: 30 days

---

## 📁 Project Structure

```
VolatilityHunter/
├── 📄 Core System
│   ├── main.py                    # Autonomous trading execution
│   ├── health_check.py            # System validation
│   ├── update_universe.py         # Data synchronization
│   └── crucible_engine.py          # Master backtesting
├── 📂 src/                        # Core business logic
│   ├── strategy.py                # A+ Wealth Builder logic
│   ├── tracker.py                 # Portfolio management
│   ├── execution.py               # Trade execution
│   └── [support modules...]
├── 📂 data/                       # Market data (Parquet files)
├── 📂 docs/                       # Documentation
├── 📂 research/                   # Lab notes and analysis
└── 📂 logs/                       # Execution logs
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

# Verify data integrity
python health_check.py
```

### **Validation Checklist**
- ✅ System health checks pass
- ✅ Data pipeline operational (99.9% uptime)
- ✅ Strategy logic verified
- ✅ Risk management constraints enforced
- ✅ Backtest results reproducible

---

## 📚 Documentation

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - Detailed system architecture
- **[ROADMAP.md](docs/ROADMAP.md)** - Development roadmap and future plans
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

**VolatilityHunter v6.5** - Deterministic Wealth Generation Through Technical Excellence 🎯
