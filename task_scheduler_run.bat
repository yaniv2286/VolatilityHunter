@echo off
REM VolatilityHunter Task Scheduler Batch File
REM For reliable daily automated execution

setlocal enabledelayedexpansion

echo ========================================
echo VolatilityHunter Task Scheduler Execution
echo ========================================
echo Time: %date% %time%
echo ========================================

REM Set working directory
cd /d "D:\GitHub\VolatilityHunter"

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python not found in PATH
    echo Please ensure Python is installed and in PATH
    exit /b 1
)

REM Check if virtual environment exists
if not exist "venv\Scripts\activate.bat" (
    echo ERROR: Virtual environment not found
    echo Please run setup script first
    exit /b 1
)

REM Activate virtual environment
echo Activating virtual environment...
call "venv\Scripts\activate.bat"

REM Check activation
python -c "import sys; print('Python path:', sys.executable)" 2>&1 | findstr "venv" >nul
if errorlevel 1 (
    echo ERROR: Failed to activate virtual environment
    exit /b 1
)

REM Run main script
echo.
echo Running VolatilityHunter main script...
echo ========================================

REM Run with error handling
python main.py > task_scheduler_output.log 2>&1
set exit_code=%errorlevel%

REM Check results
echo.
echo ========================================
echo Execution Results
echo ========================================
echo Exit Code: %exit_code%
echo Time: %date% %time%

if %exit_code% equ 0 (
    echo SUCCESS: VolatilityHunter completed successfully
) else (
    echo ERROR: VolatilityHunter failed with exit code %exit_code%
    echo Check task_scheduler_output.log for details
)

REM Show last 10 lines of output if error occurred
if %exit_code% neq 0 (
    echo.
    echo Last 10 lines of output:
    echo ----------------------------------------
    powershell "Get-Content task_scheduler_output.log -Tail 10"
)

REM Cleanup old logs (keep last 7 days)
forfiles /p "D:\GitHub\VolatilityHunter" /m "task_scheduler_*.log" /d -7 /c "cmd /c del @path" 2>nul

echo ========================================
echo Task Scheduler execution completed
echo ========================================

REM Auto-close window after 3 seconds on success
if %exit_code% equ 0 (
    echo Window will close automatically...
    timeout /t 3 /nobreak >nul
) else (
    echo Window will close after 10 seconds due to error...
    timeout /t 10 /nobreak >nul
)

REM Exit with same code as main script
exit /b %exit_code%
