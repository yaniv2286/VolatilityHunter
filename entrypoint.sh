#!/bin/bash
# VolatilityHunter container entrypoint
# Default: start the 24/7 cron-driven trading loop.
# Override: pass any command (e.g. python scripts/daily_trading_loop.py) and it
# will be executed directly.

set -e

# Apply the configured timezone so cron runs in US/Eastern.
if [ -n "$TZ" ]; then
    ln -sf "/usr/share/zoneinfo/$TZ" /etc/localtime
    echo "$TZ" > /etc/timezone
fi

# Runtime directories (bind-mounted in production).
mkdir -p /app/data /app/logs /app/reports

# Export container environment so cron jobs inherit secrets and config.
mkdir -p /etc/profile.d
> /etc/profile.d/volatilityhunter-env.sh
printenv | while IFS= read -r line; do
    [ -z "$line" ] && continue
    printf 'export %q\n' "$line" >> /etc/profile.d/volatilityhunter-env.sh
done
chmod 0644 /etc/profile.d/volatilityhunter-env.sh

# If a command was supplied, run it directly (one-off backtest, simulation, etc.)
if [ "$#" -gt 0 ]; then
    echo "[ENTRYPOINT] Override mode: executing supplied command: $*"
    exec "$@"
fi

# Default: validate configuration before touching the broker or cron.
echo "[ENTRYPOINT] Running startup validator..."
python /app/scripts/startup_validator.py

echo "[ENTRYPOINT] Probing IBKR/TWS connectivity (non-blocking)..."
python /app/scripts/ibkr_startup_check.py || true

echo "[ENTRYPOINT] Starting VolatilityHunter 24/7 scheduled trading loop..."
echo "[ENTRYPOINT] Cron schedule:"
cat /etc/cron.d/volatilityhunter
cron -f
