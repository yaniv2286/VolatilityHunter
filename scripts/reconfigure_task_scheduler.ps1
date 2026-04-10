# VolatilityHunter Task Scheduler Reconfiguration Script
# Configures task for production-grade background service with GUI access

$TaskName = "VolatilityHunter_Daily_Live"
$TaskPath = "\"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VOLATILITYHUNTER TASK SCHEDULER RECONFIGURATION" -ForegroundColor Cyan
Write-Host "Production-Grade Background Service with GUI Access" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Get current task
$Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
Write-Host "[OK] Found task: $TaskName" -ForegroundColor Green

# Create new action with cmd.exe and logging redirection
$ActionParams = @{
    Execute = "cmd.exe"
    Argument = '/c "D:\GitHub\VolatilityHunter\scripts\DAILY_ROUTINE\run_trading.bat >> D:\GitHub\VolatilityHunter\logs\task_scheduler.log 2>&1"'
    WorkingDirectory = "D:\GitHub\VolatilityHunter"
}
$Action = New-ScheduledTaskAction @ActionParams
Write-Host "[OK] Created new action with logging redirection" -ForegroundColor Green

# Create principal for "Run only when user is logged on" with highest privileges
$PrincipalParams = @{
    UserId = $env:USERNAME
    LogonType = "Interactive"  # Run only when user is logged on (allows GUI access)
    RunLevel = "Highest"       # Run with highest privileges
}
$Principal = New-ScheduledTaskPrincipal @PrincipalParams
Write-Host "[OK] Created principal: Interactive mode with Highest privileges" -ForegroundColor Green

# Get existing settings and modify them
$Settings = $Task.Settings
$Settings.Hidden = $false  # MUST be false for Ghost-Typist to work with GUI automation
$Settings.AllowDemandStart = $true
$Settings.AllowHardTerminate = $true
$Settings.Compatibility = "Win8"
$Settings.DisallowStartIfOnBatteries = $false
$Settings.StopIfGoingOnBatteries = $false
$Settings.WakeToRun = $true
$Settings.RestartCount = 3
$Settings.RestartInterval = "PT5M"  # 5 minutes in ISO 8601 duration format
$Settings.ExecutionTimeLimit = "PT4H"  # 4 hours
$Settings.StartWhenAvailable = $true
$Settings.MultipleInstances = 2  # 2 = IgnoreNew
Write-Host "[OK] Created settings: Hidden=True, WakeToRun=True, RestartOnFailure=3x5min" -ForegroundColor Green

# Get existing trigger (preserve the schedule)
$Trigger = $Task.Triggers[0]
Write-Host "[OK] Preserved existing trigger schedule" -ForegroundColor Green

# Register the updated task (this replaces the existing task)
$RegisterParams = @{
    TaskName = $TaskName
    TaskPath = $TaskPath
    Action = $Action
    Principal = $Principal
    Settings = $Settings
    Trigger = $Trigger
    Force = $true
}
Register-ScheduledTask @RegisterParams | Out-Null
Write-Host "[OK] Task reconfigured successfully" -ForegroundColor Green

# Verify the new configuration
Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "VERIFICATION" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

$UpdatedTask = Get-ScheduledTask -TaskName $TaskName
$Config = @{
    "Task Name" = $UpdatedTask.TaskName
    "State" = $UpdatedTask.State
    "Logon Type" = $UpdatedTask.Principal.LogonType
    "Run Level" = $UpdatedTask.Principal.RunLevel
    "Hidden" = $UpdatedTask.Settings.Hidden
    "Wake To Run" = $UpdatedTask.Settings.WakeToRun
    "Restart Count" = $UpdatedTask.Settings.RestartCount
    "Restart Interval" = $UpdatedTask.Settings.RestartInterval
    "Action" = $UpdatedTask.Actions.Execute + " " + $UpdatedTask.Actions.Arguments
}

$Config.GetEnumerator() | Sort-Object Name | ForEach-Object {
    Write-Host ("{0,-20}: {1}" -f $_.Key, $_.Value) -ForegroundColor Yellow
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "RECONFIGURATION COMPLETE" -ForegroundColor Green
Write-Host "The task will now run in the background with GUI access" -ForegroundColor Green
Write-Host "All output will be logged to: logs\task_scheduler.log" -ForegroundColor Green
Write-Host "============================================================" -ForegroundColor Cyan
