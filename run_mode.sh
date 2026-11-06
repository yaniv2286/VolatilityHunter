#!/bin/bash
# VolatilityHunter cron helper.
# Accepts a mode argument and runs the appropriate pipeline step.
# Each mode is protected by flock to prevent overlapping runs.

set -e

MODE="$1"
shift || true

if [ -z "$MODE" ]; then
    echo "[RUN_MODE] ERROR: no mode supplied"
    echo "Usage: $0 <fetch|health|trade|report|simulate|backtest> [args...]"
    exit 1
fi

# Cron starts with a minimal environment; source the exported container env.
if [ -f /etc/profile.d/volatilityhunter-env.sh ]; then
    source /etc/profile.d/volatilityhunter-env.sh
fi

cd /app

LOG_DIR="/app/logs"
mkdir -p "$LOG_DIR"

case "$MODE" in
    fetch)
        echo "[RUN_MODE] [$(date)] Running data update..."
        python scripts/update_data.py
        ;;
    health)
        echo "[RUN_MODE] [$(date)] Running health check..."
        python scripts/functional_health_check.py
        ;;
    trade)
        echo "[RUN_MODE] [$(date)] Running VolatilityHunter daily trade pipeline..."
        python scripts/functional_health_check.py
        python scripts/daily_trading_loop.py
        ;;
    report)
        echo "[RUN_MODE] [$(date)] Running live reconciliation..."
        python scripts/live_reconciliation.py
        ;;
    simulate)
        DATE_ARG="${1:-$(date +%F)}"
        echo "[RUN_MODE] [$(date)] Running Monday simulation for $DATE_ARG..."
        python scripts/simulate_monday.py --date "$DATE_ARG"
        ;;
    backtest)
        echo "[RUN_MODE] [$(date)] Running backtest comparison..."
        python scripts/backtest_v8_vs_v8_1.py
        ;;
    *)
        echo "[RUN_MODE] ERROR: unknown mode '$MODE'"
        echo "Supported modes: fetch, health, trade, report, simulate, backtest"
        exit 1
        ;;
esac
