@echo off
:: =============================================================================
:: VOLATILITYHUNTER V11.0 - SURGICAL STRIKE EDITION
:: Trigger: Daily 17:06 IST (15:06 UTC) Mon-Fri  
:: Purpose: Port Realignment + Unbreakable Batch Flow
:: =============================================================================

:: Display banner in console (even when redirected to log)
echo.
echo ========================================================================
echo    VOLATILITYHUNTER V11.0 - SURGICAL STRIKE EDITION
echo    Starting Daily Trading Routine at %DATE% %TIME%
echo ========================================================================
echo.

:: 1. TIME & DAY CHECK
echo [VH] Current Time: %DATE% %TIME%
for /f "tokens=1 delims= " %%D in ('powershell -NoProfile -Command "(Get-Date).DayOfWeek"') do set DOW=%%D
if /i "%DOW%"=="Saturday" (
    echo [VH] %DATE% is Saturday - US markets closed. Exiting.
    exit /b 0
)
if /i "%DOW%"=="Sunday" (
    echo [VH] %DATE% is Sunday - US markets closed. Exiting.
    exit /b 0
)
echo [VH] Weekday confirmed - proceeding with ignition sequence.

:: 2. SETUP & ENVIRONMENT
cd /d "D:\GitHub\VolatilityHunter"

:: UTF-8 FORCE: Prevent UnicodeEncodeErrors in Task Scheduler
chcp 65001 >nul 2>&1
set PYTHONIOENCODING=utf-8

set TOKENIZERS_PARALLELISM=false
call venv\Scripts\activate.bat

:: PILLAR 0: START IB GATEWAY WITH AUTO_TWS_MANAGER (Ghost-Typist Method)
echo [VH] Starting IB Gateway (auto_tws_manager.py --one-shot)...
python scripts\auto_tws_manager.py --one-shot
if %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] IB Gateway failed to start
    echo [VH] Sending failure notification email...
    python scripts\send_gateway_failure_email.py
    echo [VH] Trading SKIPPED - check email for details
    goto :FAILED
)
echo [VH] IB Gateway API ready - proceeding to data update
echo.

:: 4. DATA PIPELINE UPDATE
echo [VH] Data Pipeline: Fetching fresh market data...
python scripts\update_data.py
if %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] Data update failed - stale data detected
    echo [VH] Trading SKIPPED - check data logs
    goto :FAILED
)
echo [VH] Data update completed successfully
echo.

:CONTINUE_EXECUTION

:: 5. THE GATE - Health Check
echo [VH] The Gate: Running functional health check...
python scripts\functional_health_check.py
if %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] Health Check Failed - aborting execution
    goto :FAILED
)
echo [VH] Health Check PASSED - systems GO

:: 6. TRADING LOOP EXECUTION
echo [VH] Trading Loop: Executing main trading logic...
python scripts\daily_trading_loop.py
if %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] Trading Loop Failed - aborting execution
    goto :FAILED
)
echo [VH] Trading Loop completed successfully

:: PILLAR 4: STOP IB GATEWAY (CLEANUP)
echo [VH] Stopping IB Gateway...
python scripts\stop_gateway.py
echo [VH] Gateway stopped - daily routine complete.

:: 7. CLEANUP - Kill Gateway and Watchdog
echo [VH] Cleanup: Terminating IB Gateway and Watchdog processes...
taskkill /F /FI "WINDOWTITLE eq VH_Watchdog*" /T >nul 2>&1
taskkill /F /IM java.exe /T >nul 2>&1
taskkill /F /IM javaw.exe /T >nul 2>&1
echo [VH] Gateway cleanup complete

:: 8. MISSION COMPLETE
echo [VH] =============================================================================
echo [VH] SURGICAL STRIKE COMPLETE - All systems nominal
echo [VH] =============================================================================
goto :END

:FAILED
echo [VH] =============================================================================
echo [VH] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo [VH] !!                       MISSION FAILED                              !!
echo [VH] !!           CRITICAL ERROR - SYSTEMS NOT NOMINAL                     !!
echo [VH] !!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!!
echo [VH] =============================================================================
echo [VH] ERRORLEVEL: %ERRORLEVEL%
echo [VH] Check the logs above for failure details
echo [VH] =============================================================================
goto :END

:END
echo [VH] =============================================================================
echo [VH] Daily routine finished at %DATE% %TIME%
echo [VH] =============================================================================
exit /b %ERRORLEVEL%
