# Time-Shifted Forward Test Simulation

This folder contains the complete Time-Shifted Forward Test system for VolatilityHunter, completely isolated from the main codebase.

## 📁 Files Structure

```
simulation/
├── README.md                    # This documentation
├── simulate_ytd.py              # Single-day simulation script
├── run_simulation_loop.py      # Full replay loop script
└── portfolio_sim.json          # Simulated portfolio state
```

## 🚀 Usage

### Single Day Simulation
```bash
python simulation/simulate_ytd.py --date 2026-01-04
```

### Full Replay Loop (2026-01-01 to Today)
```bash
python simulation/run_simulation_loop.py
```

## 🛡️ Architectural Guarantees

- **✅ Complete Isolation:** No files in root directory
- **✅ Live Portfolio Safe:** `data/portfolio.json` never touched
- **✅ Core Logic Untouched:** Zero modifications to `main.py`
- **✅ Lookahead Bias Prevention:** Strict data truncation
- **✅ Same Strategy Logic:** Uses exact same `strategy_v7_2` classes

## 📊 Features

- **Data Guillotine:** SimulatedParquetLoader truncates data to target_date
- **Shadow Execution:** Parallel trading simulation with `portfolio_sim.json`
- **ASCII Output:** Task Scheduler compatible (no Unicode)
- **Progress Tracking:** Real-time simulation progress
- **Final Summary:** Complete performance reporting

## 🔧 Technical Details

- **Data Source:** Local parquet files only (no API calls)
- **Portfolio File:** `simulation/portfolio_sim.json`
- **Strategy:** v7.2 Hybrid Blueprint (same as live system)
- **Risk Management:** Same Ironclad Guardrails as live system
- **Execution:** PaperExecutor with simulation mode

## 📈 Output

Simulation results are saved in `simulation/portfolio_sim.json` with:
- Complete trade history
- Portfolio valuation
- Cash and positions tracking
- Performance metrics

## 🎯 Purpose

This simulation system allows you to:
- Test strategy performance on recent data
- Validate strategy changes before live deployment
- Analyze drawdowns and win rates
- Compare different parameter configurations
- Maintain perfect isolation from live trading

---

**Architect's Constraint Met:** All simulation components perfectly isolated in `simulation/` folder.
