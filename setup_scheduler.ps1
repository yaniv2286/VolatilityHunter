# VolatilityHunter Task Scheduler Setup Script
# Creates and configures Windows Task Scheduler for daily execution

param(
    [string]$TaskName = "VolatilityHunter Daily",
    [string]$RunTime = "09:00",
    [switch]$Remove,
    [switch]$Test,
    [switch]$Silent
)

# Error handling
$ErrorActionPreference = "Stop"

function Write-Log {
    param([string]$Message, [string]$Level = "INFO")
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] [$Level] $Message"
}

try {
    Write-Log "========================================"
    Write-Log "VolatilityHunter Task Scheduler Setup"
    Write-Log "========================================"
    
    # Choose script based on Silent parameter
    if ($Silent) {
        $scriptPath = "D:\GitHub\VolatilityHunter\task_scheduler_silent.ps1"
        Write-Log "Using silent execution script"
    } else {
        $scriptPath = "D:\GitHub\VolatilityHunter\task_scheduler_run.ps1"
        Write-Log "Using standard execution script"
    }
    
    # Check if script exists
    if (-not (Test-Path $scriptPath)) {
        Write-Log "ERROR: Script not found at $scriptPath" "ERROR"
        throw "Setup script missing"
    }
    
    # Remove existing task if it exists
    try {
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
        Write-Log "Removed existing task"
    }
    catch {
        Write-Log "No existing task to remove"
    }
    
    # Create task action - Run hidden without window
    if ($Silent) {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
        Write-Log "Task configured for silent execution"
    } else {
        $action = New-ScheduledTaskAction -Execute "powershell.exe" -Argument "-WindowStyle Hidden -ExecutionPolicy Bypass -File `"$scriptPath`""
        Write-Log "Task configured for standard execution with auto-close"
    }
    
    # Create trigger (daily at specified time)
    $trigger = New-ScheduledTaskTrigger -Daily -At $RunTime
    
    # Set task settings
    $settings = New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -StartWhenAvailable -RunOnlyIfNetworkAvailable -WakeToRun
    
    # Set principal (run with highest privileges)
    $principal = New-ScheduledTaskPrincipal -UserId "NT AUTHORITY\SYSTEM" -LogonType ServiceAccount -RunLevel Highest
    
    # Register the task
    Write-Log "Creating scheduled task..."
    Write-Log "Task Name: $TaskName"
    Write-Log "Run Time: $RunTime (daily)"
    Write-Log "Script: $scriptPath"
    Write-Log "Working Directory: $workingDir"
    
    Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "VolatilityHunter Daily Automated Trading System"
    
    Write-Log "Task created successfully"
    
    # Verify task
    $task = Get-ScheduledTask -TaskName $TaskName
    if ($task) {
        Write-Log "Task verification:"
        Write-Log "  - Name: $($task.TaskName)"
        Write-Log "  - Status: $($task.State)"
        Write-Log "  - Next Run: $($task.Triggers.StartBoundary)"
        Write-Log "  - Enabled: $($task.Enabled)"
    }
    
    if ($Test) {
        Write-Log "Running test execution..."
        Start-ScheduledTask -TaskName $TaskName
        
        # Wait a bit and check status
        Start-Sleep -Seconds 5
        $taskInfo = Get-ScheduledTaskInfo -TaskName $TaskName
        Write-Log "Test execution status: $($taskInfo.LastTaskResult)"
        
        if ($taskInfo.LastTaskResult -eq 0) {
            Write-Log "Test execution successful"
        } else {
            Write-Log "Test execution failed with code: $($taskInfo.LastTaskResult)" "WARNING"
        }
    }
    
    Write-Log "========================================"
    Write-Log "Task Scheduler setup completed"
    Write-Log "========================================"
    Write-Log "Task will run daily at $RunTime"
    Write-Log "To run manually: Start-ScheduledTask -TaskName '$TaskName'"
    Write-Log "To remove: Unregister-ScheduledTask -TaskName '$TaskName'"
    Write-Log "To view: Get-ScheduledTask -TaskName '$TaskName'"
    Write-Log "========================================"
    
}
catch {
    Write-Log "ERROR: Failed to setup task scheduler: $($_.Exception.Message)" "ERROR"
    Write-Log "Stack Trace: $($_.ScriptStackTrace)" "ERROR"
    exit 1
}
