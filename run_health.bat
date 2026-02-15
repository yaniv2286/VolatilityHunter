@echo off
cd /d "D:\GitHub\VolatilityHunter"
call venv\Scripts\activate.bat
python health_check.py
pause