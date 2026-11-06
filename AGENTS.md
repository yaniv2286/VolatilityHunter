# VolatilityHunter Deployment Notes

## Project Memory and Current Priority

Read `docs/PROJECT_MEMORY.md` at the start of each session. It records the user's
objectives, paper-only constraints, invalidated backtest conclusions, data audit,
and exact next work. Keep its checkpoint current when work progresses.
The immediate priority is a validated backtest and frozen historical dataset,
before further strategy optimization. Deployment notes below describe available
infrastructure, not authorization to deploy or trade real money.

## Containerised Execution

This project can run 24/7 on a VPS via Docker.

- Image build: `docker compose -p volatilityhunter build`
- Start scheduled trading loop: `docker compose -p volatilityhunter up -d`
- View logs: `docker compose -p volatilityhunter logs -f`
- One-off simulation:
  ```bash
  docker compose -p volatilityhunter run --rm volatilityhunter \
    python scripts/simulate_monday.py --date 2026-09-02
  ```
- One-off backtest comparison:
  ```bash
  docker compose -p volatilityhunter run --rm volatilityhunter \
    python scripts/backtest_v8_vs_v8_1.py
  ```

## Deployment

Run the standalone Windows deploy script from the repo root:

```powershell
.\deploy_volatilityhunter.bat C:\Users\Yaniv\.ssh\id_ed25519
```

It validates Python syntax, packages the repo, uploads it to the VPS, extracts it
to `/root/volatilityhunter`, seeds `data/raw` if needed, and restarts the container.

## IB Gateway / TWS Note

The container does **not** run the IB Gateway GUI. The Gateway must be started
outside the container (on the VPS host or in a separate container) and reachable
at `IBKR_HOST`/`IBKR_PORT` (default `host.docker.internal:7497`).

## Cron Schedule

Cron runs inside the container in `America/New_York` time:

- `09:00 ET` - `update_data.py` (EOD refresh)
- `09:35 ET` - `functional_health_check.py` then `daily_trading_loop.py`
- `16:35 ET` - `live_reconciliation.py`

## Telegram Alerting

Set `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID` in `.env` and on the VPS.
Email notifications (`src/email_notifier.py`) automatically mirror daily reports
and error alerts to Telegram.

## State Persistence

All mutable state is kept in host-mounted directories under the compose working
folder (e.g. `/root/volatilityhunter`):

- `./data`   - portfolio.json, SPY.parquet, per-ticker EOD parquets, sector_map.json
- `./logs`   - execution, health, gateway and cron logs
- `./reports` - backtest outputs and reconciliation reports

## Required Environment Variables

Copy `.env.example` to `.env` and fill in real values before starting the
container. Critical variables: `TIINGO_API_KEY`, `EMAIL_SENDER`/`EMAIL_PASSWORD`,
`EMAIL_RECIPIENTS`, `TELEGRAM_BOT_TOKEN`/`TELEGRAM_CHAT_ID`, `IBKR_HOST`/`IBKR_PORT`.
