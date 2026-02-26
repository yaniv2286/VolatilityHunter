# VolatilityHunter Scripts Directory

## 📁 Essential Scripts Overview

This directory contains essential automation scripts for the VolatilityHunter trading system. Only scripts actively used by the system are kept here.

---

## 🎯 Core Trading Scripts

### **🚀 Main Entry Points (DAILY_ROUTINE/)**
- **`DAILY_ROUTINE/run_trading.bat`** - Daily trading system launcher
  - **Purpose**: Primary entry point for daily trading
  - **Used by**: Scheduler Agent (`Auto_Trading_System` task)
  - **Schedule**: Daily at 17:30 IST (10:00 EST)

- **`DAILY_ROUTINE/run_auto_tws_manager.bat`** - 24/7 TWS automation
  - **Purpose**: TWS automation and monitoring
  - **Used by**: Scheduler Agent (`Auto_TWS_Manager` task)
  - **Schedule**: Runs on system startup (24/7)

### **🤖 TWS Automation**
- **`auto_tws_manager.py`** - TWS automation manager
  - **Purpose**: 24/7 TWS automation and monitoring
  - **Used by**: `run_auto_tws_manager.bat`
  - **Function**: Start TWS, monitor connection, restart if needed

- **`tws_keep_alive.py`** - TWS connection maintenance
  - **Purpose**: Prevents TWS auto-logout
  - **Used by**: `auto_tws_manager.py`
  - **Function**: Maintains TWS connection alive

---

## 📊 Data Management Scripts

### **📈 Data Operations**
- **`update_data.py`** - Market data updates
  - **Purpose**: Daily market data updates
  - **Used by**: Manual data refresh operations
  - **Function**: Updates market data using Tiingo API

- **`check_data_dates.py`** - Data date validation
  - **Purpose**: Validate data currency
  - **Used by**: `update_data.py`
  - **Function**: Check if data is up-to-date

- **`fill_data_gaps.py`** - Data gap filling
  - **Purpose**: Fill missing data gaps
  - **Used by**: Data maintenance operations
  - **Function**: Fill gaps in historical data

- **`fetch_deep_history.py`** - Historical data acquisition
  - **Purpose**: Fetch 20 years of historical data
  - **Used by**: Backtesting and deep analysis
  - **Function**: Download long-term historical data

---

## 🧠 System Intelligence

### **🧠 VH-BRAIN System**
- **`brain_watcher.py`** - VH-BRAIN automated watchdog
  - **Purpose**: Vector database synchronization
  - **Used by**: Continuous code monitoring
  - **Function**: Auto-sync codebase changes to vector database

---

## 🧪 Testing Framework

### **📊 Backtesting**
- **`vectorized_backtester.py`** - Institutional backtesting engine
  - **Purpose**: Vectorized backtesting framework
  - **Used by**: Testing Agent
  - **Function**: High-performance backtesting with 20-year data

---

## 🔄 System Integration

### **📋 Scheduler Integration**
```
Scheduler Agent monitors 2 tasks:
├── Auto_TWS_Manager → scripts/run_auto_tws_manager.bat
└── Auto_Trading_System → scripts/run_trading.bat
```

### **🔗 Script Dependencies**
```
run_trading.bat
└── health_check.py (root)

run_auto_tws_manager.bat
└── auto_tws_manager.py
    └── tws_keep_alive.py

update_data.py
└── check_data_dates.py
```

---

## 🚨 Important Notes

### **✅ Essential Scripts Only**
- All scripts in this directory are actively used
- No redundant or unused files
- Clean, minimal, production-ready

### **🔧 System Dependencies**
- Scripts are interconnected and depend on each other
- Modifying one script may affect others
- Always test system after changes

### **📊 Usage Patterns**
- **Daily**: `run_trading.bat` (trading), `auto_tws_manager.py` (TWS)
- **Weekly**: `update_data.py` (data maintenance)
- **As Needed**: `fetch_deep_history.py` (historical data)
- **Continuous**: `brain_watcher.py` (code monitoring)
- **Testing**: `vectorized_backtester.py` (backtesting)

---

## 📞 Script Descriptions

### **Trading Scripts**
- **Main Entry**: `run_trading.bat` - Start trading system
- **TWS Management**: `auto_tws_manager.py` - 24/7 TWS automation
- **Connection**: `tws_keep_alive.py` - Maintain TWS connection

### **Data Scripts**
- **Updates**: `update_data.py` - Daily data refresh
- **Validation**: `check_data_dates.py` - Check data currency
- **Maintenance**: `fill_data_gaps.py` - Fix data gaps
- **History**: `fetch_deep_history.py` - Long-term data

### **System Scripts**
- **Intelligence**: `brain_watcher.py` - Code monitoring
- **Testing**: `vectorized_backtester.py` - Backtesting engine

---

## 🎯 Quick Reference

| Script | Purpose | Frequency | Dependencies |
|--------|---------|-----------|--------------|
| `run_trading.bat` | Main trading | Daily | `health_check.py` |
| `auto_tws_manager.py` | TWS automation | 24/7 | `tws_keep_alive.py` |
| `update_data.py` | Data updates | Weekly | `check_data_dates.py` |
| `brain_watcher.py` | Code monitoring | Continuous | Vector DB |
| `vectorized_backtester.py` | Backtesting | As needed | Historical data |

---

**📋 Last Updated: 2026-02-26**
**🎯 Purpose: Essential automation scripts for VolatilityHunter trading system**
