@echo off
REM VolatilityHunter Launcher Script (Batch)
REM Usage: run.bat [command]
REM Commands: update, update-full, scan, server (default)

echo ========================================
echo    VolatilityHunter Launcher
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    pause
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Check if .env exists
if not exist ".env" (
    echo [WARNING] .env file not found. Please configure your API keys.
    echo.
)

REM Parse command argument
set COMMAND=%1
if "%COMMAND%"=="" set COMMAND=server

echo [INFO] Running command: %COMMAND%
echo.

if "%COMMAND%"=="update" (
    python main.py update
) else if "%COMMAND%"=="update-full" (
    python main.py update-full
) else if "%COMMAND%"=="scan" (
    python main.py scan
) else if "%COMMAND%"=="server" (
    echo [INFO] Starting Flask server at http://localhost:8080
    python main.py
) else (
    echo [ERROR] Unknown command: %COMMAND%
    echo Available commands: update, update-full, scan, server
    pause
    exit /b 1
)

pause
