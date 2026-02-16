@echo off
cd /d "D:\GitHub\VolatilityHunter"
call venv\Scripts\activate.bat
python main.py --mode live
pause