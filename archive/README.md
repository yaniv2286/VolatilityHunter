# VolatilityHunter Archive

This folder contains archived files that are no longer actively used in the daily trading pipeline but are kept for historical reference and potential future use.

## 📦 Archived Files

### **� Deployment & Flow Scripts**
- `deploy_production.py` - Production deployment script
- `run_live_trading.py` - Live trading runner
- `run_production_daily_flow.py` - Production daily flow
- `run_production_daily_flow_fixed.py` - Fixed production daily flow

### **�🔍 Verification Scripts (One-time Tools)**
- `verify_universe.py` - Data universe validation tool
- `verify_logic_unity.py` - Logic unity verification
- `verify_pre_sim_health.py` - Pre-simulation health check
- `verify_live_trading.py` - Live trading verification

### **📊 Backtest Scripts (Legacy Versions)**
- `run_26year_backtest.py` - 26-year backtest runner
- `run_comprehensive_26year_backtest.py` - Comprehensive 26-year backtest
- `run_direct_comprehensive_backtest.py` - Direct comprehensive backtest
- `run_fixed_comprehensive_backtest.py` - Fixed comprehensive backtest
- `run_fixed_full_backtest.py` - Fixed full backtest
- `run_full_26year_all_stocks_backtest.py` - Full 26-year all stocks backtest
- `run_optimized_power_stock_backtest.py` - Optimized Power Stock backtest
- `run_production_backtest.py` - Production backtest
- `run_real_power_stock_backtest.py` - Real Power Stock backtest
- `run_timezone_fixed_backtest.py` - Timezone fixed backtest

### **🔧 Analysis Tools**
- `portfolio_aggregator.py` - Portfolio aggregation analysis
- `debug_strategy.py` - Strategy debugging tool
- `investigate_backtest.py` - Backtest investigation tool

## 📋 Archive Status

- **Total Files**: 22
- **Archive Date**: 2026-02-26
- **Reason**: Project cleanup and organization
- **Status**: Preserved for historical reference

## 🔄 Current System

The current VolatilityHunter system uses:
- **Main Backtest**: `scripts/vectorized_backtester.py` (kept in scripts/)
- **Main Trading**: `scripts/run_trading.bat` (fixed and working)
- **Health Check**: `health_check.py` (root)
- **Daily Scripts**: Essential scripts in `/scripts/` folder

## ⚠️ Notes

- These files are not used in the current daily pipeline
- They may contain useful logic for future reference
- Some files may be redundant with current implementations
- Files are preserved to maintain project history

## 📞 Contact

If you need to restore any archived files or have questions about their usage, please refer to the project documentation or contact the development team.
