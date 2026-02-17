@echo off
:: =============================================================================
:: VOLATILITYHUNTER V8.0 - MASTER PRODUCTION GATEKEEPER
:: Purpose: Pillar I (Health) -> Pillar III (Live Trader)
:: =============================================================================

:: 1. SETUP & ENVIRONMENT
cd /d "D:\GitHub\VolatilityHunter"
:: Kill the HuggingFace Tokenizer Deadlock
set TOKENIZERS_PARALLELISM=false
:: Activate the Environment
call venv\Scripts\activate.bat

:: 2. PILLAR I: THE GUARD (Health Check)
echo [V8] Starting Pillar I: Health Check...
python health_check.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] Health Check Failed. 
    echo Possible causes: No Internet, IBKR Gateway Closed, or Tiingo API Down.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

:: 3. PILLAR III: THE HUNTER (Live Trading)
echo.
echo [V8] Health is GREEN. Launching Live Trader...
echo [IST] 16:30 Launch Sequence Initialized.
echo.
:: Launch in a separate window so we can monitor the [HEARTBEAT]
start "VH-TRADER-V8-LIVE" cmd /k "python main_unified.py --mode live"

exit