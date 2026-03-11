@echo off
:: =============================================================================
:: CREATE 24/7 IB GATEWAY MONITOR TASK
:: This creates a proper task that runs every 5 minutes 24/7
:: =============================================================================

echo Creating 24/7 IB Gateway Monitor task...

:: Delete old tasks
schtasks /delete /tn "Auto_IBGateway_Manager" /f >nul 2>&1
schtasks /delete /tn "IBGateway_Monitor_247" /f >nul 2>&1

:: Create the new 24/7 task
schtasks /create /tn "IBGateway_Monitor_247" /tr "cmd /c 'D:\GitHub\VolatilityHunter\scripts\DAILY_ROUTINE\run_auto_tws_manager.bat'" /sc minute /mo 5 /ru SYSTEM /f

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ✅ SUCCESS: 24/7 IB Gateway Monitor task created!
    echo.
    echo Task Details:
    echo - Name: IBGateway_Monitor_247
    echo - Schedule: Every 5 minutes (24/7)
    echo - User: SYSTEM (background service)
    echo.
    echo Verifying task...
    schtasks /query /tn "IBGateway_Monitor_247" /fo LIST
    echo.
    echo Task will start monitoring within 5 minutes.
    echo IB Gateway will be automatically started and maintained 24/7.
    echo.
    echo Starting task manually to test...
    schtasks /run /tn "IBGateway_Monitor_247"
) else (
    echo.
    echo ❌ FAILED: Could not create task.
    echo.
    echo Try running this as Administrator:
    echo 1. Right-click on Command Prompt
    echo 2. "Run as administrator"
    echo 3. Run this batch file again
)

pause
