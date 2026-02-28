@echo off
:: =============================================================================
:: AUTO IB GATEWAY MANAGER - 24/7 Headless (Task Scheduler)
:: Trigger: At logon - runs forever, restarts Gateway if it dies
:: =============================================================================

set LOG=D:\GitHub\VolatilityHunter\logs\auto_tws_manager_boot.log
echo [%DATE% %TIME%] Auto_IBGateway_Manager started >> "%LOG%"

cd /d "D:\GitHub\VolatilityHunter"

python --version >nul 2>&1
if errorlevel 1 (
    echo [%DATE% %TIME%] ERROR: Python not found in PATH >> "%LOG%"
    exit /b 1
)

python scripts\auto_tws_manager.py >> "%LOG%" 2>&1

echo [%DATE% %TIME%] auto_tws_manager.py exited with code %ERRORLEVEL% >> "%LOG%"
exit /b %ERRORLEVEL%
