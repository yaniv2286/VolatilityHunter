# VolatilityHunter Daily Routine

Last Updated: 2026-02-28

---

## Files

| File | Purpose |
|------|----------|
| `run_trading.bat` | Daily trading entry point. Weekend guard (skip Sat/Sun), functional health check, then trading loop. |
| `run_auto_tws_manager.bat` | Launches `auto_tws_manager.py` at system logon. Headless, no blocking pause. |

---

## Task Scheduler

| Task | Trigger | Action |
|------|---------|--------|
| `Auto_IBGateway_Manager` | At logon (continuous) | `run_auto_tws_manager.bat` |
| `VolatilityHunter_Daily_Live` | Daily 17:06 IST (blueprint: no trades before 10:06 AM ET) | `run_trading.bat` |

---

## Daily Timeline (IST)

```
All day   Auto_IBGateway_Manager runs: IBC keeps port 7497 alive
16:30     US market opens (NYSE/NASDAQ = 9:30 AM ET)
17:06     VolatilityHunter_Daily_Live fires run_trading.bat
          - Weekend guard: skip Sat/Sun
          - functional_health_check.py (exit 0 gate)
          - daily_trading_loop.py -> scan -> rank -> execute
~18:30    Email report sent
```

---

## Entry Point Flow

```
Windows Task Scheduler
    run_trading.bat
        functional_health_check.py  (exit 0 gate)
        daily_trading_loop.py
            main_agent_system.py (7 agents)

    run_auto_tws_manager.bat
        auto_tws_manager.py
            ibc_login_helper.py   (spawned after IBC starts)
            tws_keep_alive.py     (spawned after API opens)
```

---

## IBC / Gateway

- IB Gateway 10.37 launched via IBC 3.23.0 + Zulu 17.0.16 JRE (i4j bundled, includes JavaFX)
- `auto_tws_manager.py` strips `jts.ini` SSO tokens before each launch, forces `tradingMode=p`
- `ibc_login_helper.py` injects credentials via pyautogui after Gateway window appears
- Paper trading mode enforced: `jts.ini` tradingMode=p + `config.ini` TradingMode=paper
- API port 7497 checked every 5 min; 5-min grace period if closed (user may be browsing portal)
- Weekends: Gateway process kept alive, API port check skipped (markets closed)
- 2FA: disabled via IBKR portal SLS Opt Out for unattended login
