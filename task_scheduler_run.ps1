# VolatilityHunter Task Scheduler PowerShell Script
# For reliable daily automated execution with enhanced logging
# Auto-closes after completion for Task Scheduler

param(
    [switch]$Test,
    [switch]$Force,
    [string]$LogPath = "D:\GitHub\VolatilityHunter"
)

# Auto-close configuration - Window will close after 5 seconds on success, immediately on error
$AutoCloseDelay = 5

# Error handling
$ErrorActionPreference = "Stop"

# Logging function
function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    $logMessage = "[$timestamp] [$Level] $Message"
    
    # Write to console
    Write-Host $logMessage
    
    # Write to log file
    $logFile = Join-Path $LogPath "task_scheduler_$(Get-Date -Format 'yyyyMMdd').log"
    Add-Content -Path $logFile -Value $logMessage
}

try {
    Write-Log "========================================"
    Write-Log "VolatilityHunter Task Scheduler Started"
    Write-Log "========================================"
    Write-Log "Parameters: Test=$Test, Force=$Force"
    Write-Log "Working Directory: $LogPath"
    
    # Set working directory
    Set-Location $LogPath
    Write-Log "Changed to directory: $(Get-Location)"
    
    # Check Python
    try {
        $pythonVersion = python --version 2>&1
        Write-Log "Python found: $pythonVersion"
    }
    catch {
        Write-Log "ERROR: Python not found in PATH" "ERROR"
        throw "Python not available"
    }
    
    # Check virtual environment
    $venvPath = Join-Path $LogPath "venv\Scripts\Activate.ps1"
    if (Test-Path $venvPath) {
        Write-Log "Activating virtual environment..."
        & $venvPath
        Write-Log "Virtual environment activated"
    }
    else {
        Write-Log "ERROR: Virtual environment not found at $venvPath" "ERROR"
        throw "Virtual environment missing"
    }
    
    # Verify activation
    $pythonPath = python -c "import sys; print(sys.executable)" 2>&1
    if ($pythonPath -like "*venv*") {
        Write-Log "Virtual environment verified: $pythonPath"
    }
    else {
        Write-Log "ERROR: Virtual environment activation failed" "ERROR"
        throw "Virtual environment not properly activated"
    }
    
    # Check if main.py exists
    $mainScript = Join-Path $LogPath "main.py"
    if (Test-Path $mainScript) {
        Write-Log "Main script found: $mainScript"
    }
    else {
        Write-Log "ERROR: main.py not found at $mainScript" "ERROR"
        throw "Main script missing"
    }
    
    # Run main script
    Write-Log "========================================"
    Write-Log "Executing VolatilityHunter main script..."
    Write-Log "========================================"
    
    $startTime = Get-Date
    $outputFile = Join-Path $LogPath "volatility_hunter_$(Get-Date -Format 'yyyyMMdd_HHmmss').log"
    
    try {
        # Run main script and capture output
        $process = Start-Process -FilePath "python" -ArgumentList "main.py" -WorkingDirectory $LogPath -Wait -PassThru -RedirectStandardOutput $outputFile -RedirectStandardError "$outputFile.err"
        $exitCode = $process.ExitCode
        
        $endTime = Get-Date
        $duration = $endTime - $startTime
        
        Write-Log "========================================"
        Write-Log "Execution Results"
        Write-Log "========================================"
        Write-Log "Start Time: $($startTime.ToString('yyyy-MM-dd HH:mm:ss'))"
        Write-Log "End Time: $($endTime.ToString('yyyy-MM-dd HH:mm:ss'))"
        Write-Log "Duration: $($duration.ToString('hh\:mm\:ss'))"
        Write-Log "Exit Code: $exitCode"
        
        if ($exitCode -eq 0) {
            Write-Log "SUCCESS: VolatilityHunter completed successfully"
        }
        else {
            Write-Log "ERROR: VolatilityHunter failed with exit code $exitCode" "ERROR"
            
            # Show last 20 lines of output
            if (Test-Path $outputFile) {
                Write-Log "Last 20 lines of output:"
                $lastLines = Get-Content $outputFile -Tail 20
                foreach ($line in $lastLines) {
                    Write-Log "  $line"
                }
            }
            
            # Show error file if exists
            $errorFile = "$outputFile.err"
            if (Test-Path $errorFile) {
                Write-Log "Error output:"
                $errorLines = Get-Content $errorFile
                foreach ($line in $errorLines) {
                    Write-Log "  ERROR: $line" "ERROR"
                }
            }
            
            throw "Script execution failed"
        }
    }
    catch {
        Write-Log "ERROR: Failed to execute main script: $($_.Exception.Message)" "ERROR"
        throw
    }
    
    # Cleanup old logs (keep last 7 days)
    try {
        $cutoffDate = (Get-Date).AddDays(-7)
        Get-ChildItem -Path $LogPath -Filter "task_scheduler_*.log" | Where-Object { $_.LastWriteTime -lt $cutoffDate } | Remove-Item -Force
        Get-ChildItem -Path $LogPath -Filter "volatility_hunter_*.log" | Where-Object { $_.LastWriteTime -lt $cutoffDate } | Remove-Item -Force
        Write-Log "Cleaned up old log files"
    }
    catch {
        Write-Log "WARNING: Failed to cleanup old logs: $($_.Exception.Message)" "WARNING"
    }
    
    Write-Log "========================================"
    Write-Log "Task Scheduler execution completed successfully"
    Write-Log "========================================"
    
    # Auto-close window after success (unless in Test mode)
    if (-not $Test) {
        Write-Log "Window will auto-close in $AutoCloseDelay seconds..."
        Start-Sleep -Seconds $AutoCloseDelay
    }
    
    # Exit with success
    exit 0
    
}
catch {
    Write-Log "========================================"
    Write-Log "Task Scheduler execution FAILED"
    Write-Log "========================================"
    Write-Log "ERROR: $($_.Exception.Message)" "ERROR"
    Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
    Write-Log "========================================"
    
    # Auto-close window immediately on error (unless in Test mode)
    if (-not $Test) {
        Write-Log "Window will auto-close immediately due to error..."
        Start-Sleep -Seconds 2  # Brief pause to read error
    }
    
    # Exit with failure
    exit 1
}
