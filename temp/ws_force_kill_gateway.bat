@echo off
echo Killing stuck IB Gateway process...
taskkill /f /im javaw.exe
echo Done.
pause
