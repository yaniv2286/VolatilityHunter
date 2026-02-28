# VolatilityHunter Scripts

Last Updated: 2026-02-28

---

## DAILY_ROUTINE/

| File | Purpose | Task Scheduler |
|------|---------|----------------|
| `run_trading.bat` | Daily trading entry point. Weekend guard, health check, trading loop. | `VolatilityHunter_Daily_Live` — daily 17:06 IST |
| `run_auto_tws_manager.bat` | Launches `auto_tws_manager.py` on boot. Headless, no pause. | `Auto_IBGateway_Manager` — at logon |

---

## IBC / Gateway

| File | Purpose |
|------|----------|
| `auto_tws_manager.py` | 24/7 IB Gateway manager. Launches IBC with correct i4j JRE, cleans jts.ini SSO tokens, sets paper mode, 5-min grace period for user browsing, weekend-aware. |
| `ibc_login_helper.py` | pyautogui credential injector. Runs after Gateway window appears — clears username field, types credentials from .env, submits login. |
| `tws_keep_alive.py` | Sends EClient heartbeat every 55s to prevent IB Gateway auto-disconnect. |
| `setup_ibc.py` | One-time IBC installer. Downloads IBC 3.23.0, writes StartGateway.bat. |

---

## Data

| File | Purpose |
|------|----------|
| `update_data.py` | Refresh Tiingo parquet files for all tickers. |
| `fetch_deep_history.py` | Download full 26-year history for a ticker list. |

---

## Analysis / Backtest

| File | Purpose |
|------|----------|
| `full_universe_backtest.py` | Run Sweet Spot v7.2 over full 2,147-ticker universe (~2 min). |
| `backtest_v7_vs_v8.py` | Side-by-side comparison: v7.2 vs v8 on all 2,147 tickers. Result: v8 +6.1% CAGR (10.1% -> 16.2%). |
| `simulate_monday.py` | Full pipeline dry-run on a historical date — portfolio load, exit check, power promotion, scan, entries. |

---

## System

| File | Purpose |
|------|----------|
| `functional_health_check.py` | Full system health gate — all 7 agents, portfolio sync, IBKR connectivity. Exit 0 = green light. |
| `daily_trading_loop.py` | Main trading session loop — called by `run_trading.bat`. |
| `brain_watcher.py` | ChromaDB vector sync watchdog — auto-updates VH-BRAIN on .py/.md changes. |

---

## Script Dependency Tree

```
run_trading.bat
    functional_health_check.py
    daily_trading_loop.py
        main_agent_system.py (7 agents)

run_auto_tws_manager.bat
    auto_tws_manager.py
        ibc_login_helper.py  (spawned after IBC starts)
        tws_keep_alive.py    (spawned after API opens)
```
