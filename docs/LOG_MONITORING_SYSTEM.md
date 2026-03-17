# VolatilityHunter Log Monitoring System

## Overview
The VolatilityHunter system now includes comprehensive log monitoring and alerting to ensure no silent failures or warnings go unnoticed.

## Components

### 1. Post-Trade Log Monitor (`scripts/monitor_trading_logs.py`)
- **Purpose**: Analyzes trading logs after completion
- **Triggers**: Runs at the end of daily trading batch
- **Detects**:
  - Order execution failures
  - Data download issues
  - General errors and warnings
- **Alerts**: Sends consolidated email if critical issues found

### 2. Real-Time Log Monitor (`scripts/realtime_log_monitor.py`)
- **Purpose**: Monitors logs in real-time during trading
- **Triggers**: File system events on log changes
- **Detects**:
  - Individual order cancellations
  - Data failures as they happen
  - Critical errors during execution
- **Alerts**: Sends immediate alerts with 5-minute cooldown

### 3. Enhanced Batch File (`scripts/DAILY_ROUTINE/run_trading.bat`)
- **Added Step 6**: Log monitoring after trading completes
- **Sequence**:
  1. Start IB Gateway
  2. Health Check
  3. Daily Trading Loop
  4. Stop IB Gateway
  5. **NEW**: Log Monitoring

## Alert Types

### 🚨 Critical Alerts (Immediate)
- **Order Cancellations**: When orders fail to fill after 303 seconds
- **Multiple Data Failures**: 3+ tickers fail to download
- **System Errors**: 5+ general errors in session

### ⚠️ Warning Alerts (Batched)
- **Single Data Failures**: Individual ticker download issues
- **Portfolio Warnings**: Sync issues between paper and live

### 📊 Daily Summary
- **Comprehensive Report**: All issues categorized and counted
- **Trend Analysis**: Day-over-day issue tracking
- **Action Items**: Specific recommendations for each issue type

## Issue Categories Monitored

### 1. Market Data Issues
```
ERROR ['CI']: TypeError("'NoneType' object is not subscriptable")
ERROR $RAPT: possibly delisted; no price data found
```
**Impact**: Strategy calculations may be incomplete
**Action**: Check yfinance API or remove delisted tickers

### 2. Order Execution Issues
```
ERROR ORDER CANCEL: FSLY unfilled after 303s - cancelling
```
**Impact**: No new positions added
**Action**: Check market hours or liquidity

### 3. Portfolio Synchronization
```
WARNING Discarded 9 PAPER positions (IBKR is master)
```
**Impact**: Local paper positions overridden
**Action**: Normal behavior when connecting to live account

### 4. System Errors
```
ERROR Failed to place order: No market data subscription
```
**Impact**: Trading functionality impaired
**Action**: Check IBKR subscriptions

## Alert Cooldowns
- **Order Cancellations**: 5 minutes
- **Data Failures**: 5 minutes
- **General Errors**: 5 minutes
- **Daily Summary**: Once per day

## Email Templates

### Critical Alert Example
```
Subject: 🚨 Order Cancellation Alert - FSLY

Order failed to fill and was cancelled:

Ticker: FSLY
Time: 2026-03-17 13:25:15
Action: Check if market is open or if there are liquidity issues

This is an automated alert from VolatilityHunter.
```

### Daily Summary Example
```
Subject: 🚨 VolatilityHunter CRITICAL Issues Detected - 2026-03-17

VolatilityHunter Trading Log Monitor Report
==================================================
Date: 2026-03-17 13:30:00

🚨 CRITICAL: Order Execution Issues
  - 8 orders failed to fill:
    • FSLY
    • AEHR
    • LIVN
    • VALE
    • BCH
    • HSBC
    • HCSG
    • TSEM

⚠️  Data Fetch Issues
  - 6 tickers failed to download:
    • CI
    • OGN
    • AVB
    • SRPT
    • BW
    • RAPT

📊 Summary
  - Order Issues: 8
  - Data Issues: 6
  - General Errors: 0
  - Warnings: 9
```

## Implementation Details

### Log File Patterns
- **Trading Log**: `logs/trading_YYYY-MM-DD.log`
- **Gateway Log**: `logs/ibc_gateway.log`
- **Monitor Log**: `logs/log_monitor_YYYY-MM-DD.log`

### Error Detection Regex Patterns
```python
# Order cancellations
r"ORDER CANCEL: (\w+) unfilled"

# Data failures
r"\['(\w+)'\]"
r"possibly delisted"

# General errors
r"ERROR.*"
```

### Monitoring Thresholds
- **Order Timeout**: 303 seconds (5 minutes 3 seconds)
- **Data Failure Threshold**: 3 tickers
- **Error Threshold**: 5 errors
- **Warning Threshold**: 10 warnings

## Usage

### Post-Trade Monitoring (Built into batch)
```batch
python scripts\monitor_trading_logs.py
```

### Real-Time Monitoring (Optional)
```bash
# Run in separate terminal during trading
python scripts\realtime_log_monitor.py
```

### Manual Log Check
```bash
# Check specific date
python scripts\monitor_trading_logs.py

# Real-time monitoring
python scripts\realtime_log_monitor.py
```

## Troubleshooting

### Common Issues
1. **No alerts received**
   - Check email configuration in `.env`
   - Verify log files exist in `logs/` directory
   - Check SMTP server settings

2. **Too many alerts**
   - Adjust cooldown periods in scripts
   - Check for recurring issues
   - Verify alert thresholds

3. **Missing issues**
   - Ensure log format matches regex patterns
   - Check log file permissions
   - Verify monitoring script is running

## Future Enhancements

1. **Slack Integration**: Add Slack webhook for instant notifications
2. **Dashboard**: Web interface for real-time monitoring
3. **Auto-Recovery**: Automatic actions for common issues
4. **Performance Metrics**: Track system performance over time
5. **Integration Tests**: Automated testing of monitoring system

## Dependencies
- `watchdog`: Real-time file system monitoring
- `psutil`: Process management (existing)
- `dotenv`: Environment variables (existing)
- Email notifier (existing)

## Configuration
All monitoring settings can be adjusted in the respective scripts:
- Alert cooldowns
- Error thresholds
- Email templates
- Log patterns
