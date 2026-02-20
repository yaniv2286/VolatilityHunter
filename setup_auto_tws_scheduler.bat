@echo off
echo ============================================================
echo SETUP AUTO TWS MANAGER - TASK SCHEDULER
echo ============================================================
echo.
echo This will create a Windows Task Scheduler entry
echo to auto-start the TWS Manager at system boot.
echo.
echo REQUIREMENTS:
echo - Run as Administrator
echo - TWS must be installed
echo.
echo Press any key to continue...
pause >nul

REM Create the scheduled task
schtasks /create /tn "Auto_TWS_Manager" /tr "cmd /c \"D:\GitHub\VolatilityHunter\run_auto_tws_manager.bat\"" /sc onlogon /rl highest /f /it

if errorlevel 1 (
    echo.
    echo ❌ FAILED: Access denied - Run as Administrator!
    echo.
    echo MANUAL SETUP:
    echo 1. Press Win+R, type taskschd.msc
    echo 2. Right-click Task Scheduler Library ^> Create Task
    echo 3. Name: Auto_TWS_Manager
    echo 4. Trigger: At logon
    echo 5. Action: Start program = cmd
    echo 6. Arguments: /c "D:\GitHub\VolatilityHunter\run_auto_tws_manager.bat"
    echo 7. Start in: D:\GitHub\VolatilityHunter
    echo 8. Run with highest privileges
    echo.
) else (
    echo.
    echo ✅ SUCCESS: Auto TWS Manager scheduled!
    echo.
    echo The TWS Manager will now:
    echo - Auto-start at Windows boot
    echo - Run 24/7 in background
    echo - Auto-manage TWS completely
    echo - Never require manual intervention
    echo.
    echo To test: Right-click task in Task Scheduler ^> Run
)

pause
