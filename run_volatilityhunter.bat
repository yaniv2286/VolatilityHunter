@echo off
echo Starting VolatilityHunter Daily Trading...
cd /d "D:\GitHub\VolatilityHunter"
python scheduler_updated.py --daily
echo VolatilityHunter completed.
pause
