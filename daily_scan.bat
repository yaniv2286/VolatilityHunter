@echo off
cd /d "D:\GitHub\VolatilityHunter"

echo STARTING VISIBLE SCAN...
echo --------------------------------

:: Activate VENV
call venv\Scripts\activate.bat

:: Run Script ON SCREEN (No hiding in logs)
python -u volatilityhunter.py --mode trading

echo --------------------------------
echo SCAN FINISHED.
echo --------------------------------
pause