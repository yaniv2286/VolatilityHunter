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

:: CANONICAL ORCHESTRATOR: Gateway -> Data -> Health -> Trading -> Cleanup
echo [VH] Running canonical daily orchestrator...
python scripts\run_daily_orchestrator.py
if %ERRORLEVEL% NEQ 0 (
    echo [CRITICAL ERROR] Daily orchestrator failed - aborting execution
    goto :FAILED
)
echo [VH] Daily orchestrator completed successfully

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
