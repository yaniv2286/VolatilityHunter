@echo off
:: =============================================================================
:: VOLATILITYHUNTER V10.0 - MASTER PRODUCTION GATEKEEPER
:: Trigger: Daily 17:06 IST (15:06 UTC) Mon-Fri  [Blueprint: no trades before 10:06 AM ET]
:: Purpose: Pillar I (Health) -> Pillar III (Live Trader)
:: =============================================================================

:: 1. WEEKEND GUARD - skip Sat/Sun (US markets closed)
for /f "tokens=1 delims= " %%D in ('powershell -NoProfile -Command "(Get-Date).DayOfWeek"') do set DOW=%%D
if /i "%DOW%"=="Saturday" (
    echo [VH] %DATE% is Saturday - US markets closed. Skipping.
    exit /b 0
)
if /i "%DOW%"=="Sunday" (
    echo [VH] %DATE% is Sunday - US markets closed. Skipping.
    exit /b 0
)

:: 2. SETUP & ENVIRONMENT
cd /d "D:\GitHub\VolatilityHunter"
:: Kill the HuggingFace Tokenizer Deadlock
set TOKENIZERS_PARALLELISM=false
:: Activate the Environment
call venv\Scripts\activate.bat

:: 3. PILLAR 0: START IB GATEWAY WITH RETRIES
echo [VH] Starting IB Gateway (IBC method, 120s timeout, 3 retries)...
python scripts\start_gateway_with_retry.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] IB Gateway failed after 3 retries
    echo [VH] Sending failure notification email...
    python scripts\send_gateway_failure_email.py
    echo [VH] Trading SKIPPED - check email for details
    echo.
    exit /b %ERRORLEVEL%
)
echo [VH] IB Gateway API ready - proceeding to health check
echo.

:: 4. PILLAR I: FUNCTIONAL HEALTH CHECK
echo [VH] Starting Functional Health Check...
python scripts\functional_health_check.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] Functional Health Check Failed - aborting trading.
    echo.
    exit /b %ERRORLEVEL%
)
echo [VH] Health Check PASSED - systems GO.
echo.

:: 3. DAILY TRADING LOOP (scan -> rank -> execute -> email)
echo [VH] Starting Daily Trading Loop...
echo [VH] Scan 2147 tickers, check exits, open entries, send email summary
echo.
python scripts\daily_trading_loop.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] Daily Trading Loop Failed - check logs\trading_%DATE%.log
    echo.
    exit /b %ERRORLEVEL%
)

echo.
echo [VH] Daily Trading Loop COMPLETED SUCCESSFULLY.
echo [VH] Check email for summary report.
echo.

:: 5. PILLAR IV: STOP IB GATEWAY (CLEANUP)
echo [VH] Stopping IB Gateway...
python scripts\stop_gateway.py
echo [VH] Gateway stopped - daily routine complete.
echo.

:: 6. PILLAR V: LOG MONITORING (QUALITY CONTROL)
echo [VH] Monitoring logs for critical issues...
python scripts\monitor_trading_logs.py
echo [VH] Log monitoring complete.
echo.

exit /b 0