# VolatilityHunter production container
# Runs the autonomous daily trading pipeline on a Linux VPS.
# The IB Gateway/TWS GUI must run OUTSIDE this container and be reachable at
# IBKR_HOST:IBKR_PORT (default host.docker.internal:7497).
FROM python:3.10-slim

ENV TZ=America/New_York
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Install system dependencies: cron for scheduling, tzdata for market-relative
# times, and build tools for psutil / numpy wheels.
RUN apt-get update && apt-get install -y --no-install-recommends \
    cron \
    tzdata \
    gcc \
    g++ \
    build-essential \
    libgomp1 \
    libsqlite3-0 \
    git \
    util-linux \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies first for layer caching.
COPY requirements-docker.txt .
RUN pip install --no-cache-dir -r requirements-docker.txt

# Copy source, scripts, config, and the ticker universe.
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY config/ ./config/
COPY tickers.txt ./
COPY TWSibgateway/ ./TWSibgateway/

# Create runtime directories (will be bind-mounted in production, but this keeps
# the image self-contained for one-off commands).
RUN mkdir -p /app/data /app/logs /app/reports

# Cron schedule and helper scripts.
COPY crontab /etc/cron.d/volatilityhunter
COPY entrypoint.sh /app/entrypoint.sh
COPY run_mode.sh /app/run_mode.sh
RUN chmod 0644 /etc/cron.d/volatilityhunter && \
    chmod +x /app/entrypoint.sh /app/run_mode.sh

# Make sure any CRLF line endings from Windows are normalized.
RUN sed -i 's/\r$//' /app/entrypoint.sh /app/run_mode.sh /etc/cron.d/volatilityhunter

ENTRYPOINT ["/app/entrypoint.sh"]
CMD []
