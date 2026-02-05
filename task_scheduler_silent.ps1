# VolatilityHunter Silent Task Scheduler Script
# Runs completely hidden with no window interaction
# Ideal for automated Task Scheduler execution

param(
    [string]$LogPath = "D:\GitHub\VolatilityHunter"
)

# Silent mode - no console output
$ErrorActionPreference = "Stop"

# Silent logging function (writes to file only)
function Write-SilentLog {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Write to log file only (no console output)
    $logFile = Join-Path $LogPath "task_scheduler_$(Get-Date -Format 'yyyyMMdd').log"
    Add-Content -Path $logFile -Value $logMessage
}

try {
    Write-SilentLog "========================================"
    Write-SilentLog "VolatilityHunter Silent Execution Started"
    Write-SilentLog "========================================"
    
    # Set working directory
    Set-Location $LogPath
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-SilentLog "Python found: $pythonVersion"
    }
    catch {
        Write-SilentLog "ERROR: Python not found" "ERROR"
        throw "Python not available"
    }
    
    # Check virtual environment
    $venvPath = Join-Path $LogPath "venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        & $venvPath
        Write-SilentLog "Virtual environment activated"
    }
    else {
        Write-SilentLog "ERROR: Virtual environment not found" "ERROR"
        throw "Virtual environment missing"
    }
    
    # Check main script
    $mainScript = Join-Path $LogPath "main.py"
    if (Test-Path $mainScript) {
        Write-SilentLog "Main script found"
    }
    else {
        Write-SilentLog "ERROR: main.py not found" "ERROR"
        throw "Main script missing"
    }
    
    # Run main script silently
    Write-SilentLog "Executing VolatilityHunter..."
    
    $startTime = Get-Date
    $outputFile = Join-Path $LogPath "volatility_hunter_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    # Run completely hidden
    $process = Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $LogPath -Wait -PassThru -WindowStyle Hidden -RedirectStandardOutput $outputFile -RedirectStandardError "$outputFile.err"
    $exitCode = $process.ExitCode
    
    $endTime = Get-Date
    $duration = $endTime - $startTime
    
    Write-SilentLog "Execution completed in $($duration.ToString('hh\:mm\:ss')) with exit code $exitCode"
    
    # Cleanup old logs
    try {
        $cutoffDate = (Get-Date).AddDays(-7)
        Get-ChildItem -Path $LogPath -Filter "task_scheduler_*.log" | Where-Object { $_.LastWriteTime -lt $cutoffDate } | Remove-Item -Force
        Get-ChildItem -Path $LogPath -Filter "volatility_hunter_*.log" | Where-Object { $_.LastWriteTime -lt $cutoffDate } | Remove-Item -Force
        Write-SilentLog "Cleaned up old log files"
    }
    catch {
        Write-SilentLog "WARNING: Failed to cleanup old logs"
    }
    
    Write-SilentLog "Silent execution completed successfully"
    
    # Exit silently
    exit 0
    
}
catch {
    Write-SilentLog "ERROR: Silent execution failed: $($_.Exception.Message)"
    Write-SilentLog "Stack Trace: $($_.ScriptStackTrace)"
    
    # Exit with error code
    exit 1
}
