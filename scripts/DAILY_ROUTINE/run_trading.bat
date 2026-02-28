@echo off
:: =============================================================================
:: VOLATILITYHUNTER V10.0 - MASTER PRODUCTION GATEKEEPER
:: Purpose: Pillar I (Health) -> Pillar III (Live Trader)
:: =============================================================================

:: 1. SETUP & ENVIRONMENT
cd /d "D:\GitHub\VolatilityHunter"
:: Kill the HuggingFace Tokenizer Deadlock
set TOKENIZERS_PARALLELISM=false
:: Activate the Environment
call venv\Scripts\activate.bat

:: 2. PILLAR I: FUNCTIONAL HEALTH CHECK
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

exit /b 0