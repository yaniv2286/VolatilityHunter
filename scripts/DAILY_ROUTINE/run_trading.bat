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

:: 2. PILLAR I: FUNCTIONAL HEALTH CHECK (V10.0)
echo [V10.0] Starting Functional Health Check with Real Trading Verification...
echo [V10.0] This will test: Portfolio Sync, Real Trading (1 share), Performance Isolation
echo.
python simplified_health_check.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] Functional Health Check Failed.
    echo System is not ready for trading.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo [V10.0] Functional Health Check PASSED! All systems are GO for trading.
echo.

:: 3. PILLAR III: DAILY TRADING WORKFLOW (V10.0)
echo.
echo [V10.0] Starting Daily Trading Workflow with Agent System...
echo [V10.0] Agents: Data -> Strategy -> Execution -> Sync -> Notification -> Testing
echo.
python src\deploy_agent_system.py --mode live --workflow daily_trading
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo [CRITICAL ERROR] Daily Trading Workflow Failed.
    echo Check logs for detailed error information.
    echo.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [V10.0] Daily Trading Workflow COMPLETED SUCCESSFULLY!
echo [V10.0] Check your email for the daily summary report.
echo.

:: 4. CLEANUP & VALIDATION
echo [V10.0] Performing system cleanup...
python sync_with_tws_screenshot.py
if %ERRORLEVEL% NEQ 0 (
    echo [WARNING] Portfolio sync cleanup had issues, but trading completed.
)

echo.
echo [V10.0] ============================================================================
echo [V10.0] VOLATILITYHUNTER V10.0 DAILY TRADING COMPLETE
echo [V10.0] ============================================================================
echo [V10.0] - Functional Health Check: PASS
echo [V10.0] - Agent System: OPERATIONAL  
echo [V10.0] - Daily Trading: COMPLETED
echo [V10.0] - Email Summary: SENT
echo [V10.0] ============================================================================

exit