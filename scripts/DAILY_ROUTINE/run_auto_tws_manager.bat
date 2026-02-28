@echo off
echo ============================================================
echo AUTOMATED TWS MANAGER - 24/7 AUTO-PILOT
echo ============================================================
echo Starting: %date% %time%
echo.
echo This will AUTOMATICALLY:
echo 1. Start TWS if not running
echo 2. Wait for TWS to load
echo 3. Auto-detect when API is enabled
echo 4. Start keep-alive service
echo 5. Monitor 24/7 and restart if needed
echo.
echo NO MANUAL INTERVENTION REQUIRED!
echo.

REM Change to VolatilityHunter directory
cd /d "D:\GitHub\VolatilityHunter"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    pause
    exit /b 1
)

REM Start the automated TWS manager
python scripts/auto_tws_manager.py

echo.
echo Auto TWS Manager stopped
pause
