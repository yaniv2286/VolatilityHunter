@echo off
REM VolatilityHunter Neural Environment Testing Protocol
REM Usage: run_neural_venv.bat [fetch|report]

echo ========================================
echo    VolatilityHunter Neural Testing
echo ========================================
echo.

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo [ERROR] Virtual environment not found!
    echo Please run: python -m venv venv
    exit /b 1
)

REM Activate virtual environment
echo [INFO] Activating virtual environment...
call venv\Scripts\activate.bat

REM Parse command argument
set COMMAND=%1
if "%COMMAND%"=="" (
    echo [ERROR] No command specified
    echo Usage: run_neural_venv.bat [fetch^|report]
    exit /b 1
)

if "%COMMAND%"=="fetch" (
    echo [INFO] Running fetch protocol...
    echo [INFO] Fetching market data...
    python main.py update
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Fetch failed with exit code %ERRORLEVEL%
        exit /b %ERRORLEVEL%
    )
    echo [OK] Fetch completed successfully
) else if "%COMMAND%"=="report" (
    echo [INFO] Running report protocol...
    echo [INFO] Generating scan report...
    python main.py scan
    if %ERRORLEVEL% neq 0 (
        echo [ERROR] Report failed with exit code %ERRORLEVEL%
        exit /b %ERRORLEVEL%
    )
    echo [OK] Report completed successfully
) else (
    echo [ERROR] Unknown command: %COMMAND%
    echo Available commands: fetch, report
    exit /b 1
)

echo.
echo [INFO] Protocol completed
exit /b 0
