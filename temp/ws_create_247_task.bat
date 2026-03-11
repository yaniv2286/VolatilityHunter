@echo off
:: =============================================================================
:: CREATE 24/7 AUTO IB GATEWAY MANAGER TASK
:: This creates a proper task that runs every 5 minutes 24/7
:: =============================================================================

echo Creating 24/7 Auto_IBGateway_Manager task...

schtasks /create /tn "Auto_IBGateway_Manager_247" /tr "cmd /c 'D:\GitHub\VolatilityHunter\scripts\DAILY_ROUTINE\run_auto_tws_manager.bat'" /sc minute /mo 5 /ru SYSTEM /f

if %ERRORLEVEL% EQU 0 (
    echo Task created successfully!
    echo Task will run every 5 minutes as SYSTEM user
    echo.
    echo Verifying task...
    schtasks /query /tn "Auto_IBGateway_Manager_247" /fo LIST
) else (
    echo Failed to create task. Try running as Administrator.
)

pause
