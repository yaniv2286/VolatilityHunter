# VolatilityHunter Health Check Script
# Quick diagnostic tool to check task status and recent logs

$TaskName = "VolatilityHunter_Daily_Live"
$LogFile = "D:\GitHub\VolatilityHunter\logs\task_scheduler.log"

Write-Host "============================================================" -ForegroundColor Cyan
Write-Host "VOLATILITYHUNTER HEALTH CHECK" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan

# Get task information
try {
    $Task = Get-ScheduledTask -TaskName $TaskName -ErrorAction Stop
    $TaskInfo = Get-ScheduledTaskInfo -TaskName $TaskName -ErrorAction Stop
    
    Write-Host "`n[TASK STATUS]" -ForegroundColor Yellow
    Write-Host ("  Task Name        : {0}" -f $Task.TaskName)
    Write-Host ("  State            : {0}" -f $Task.State)
    Write-Host ("  Logon Type       : {0}" -f $Task.Principal.LogonType)
    Write-Host ("  Run Level        : {0}" -f $Task.Principal.RunLevel)
    Write-Host ("  Hidden           : {0}" -f $Task.Settings.Hidden)
    Write-Host ("  Wake To Run      : {0}" -f $Task.Settings.WakeToRun)
    Write-Host ("  Restart Count    : {0}" -f $Task.Settings.RestartCount)
    
    Write-Host "`n[LAST RUN INFO]" -ForegroundColor Yellow
    Write-Host ("  Last Run Time    : {0}" -f $TaskInfo.LastRunTime)
    Write-Host ("  Last Task Result : {0} (0x{1:X})" -f $TaskInfo.LastTaskResult, $TaskInfo.LastTaskResult)
    Write-Host ("  Next Run Time    : {0}" -f $TaskInfo.NextRunTime)
    
    # Decode common result codes
    $ResultMessage = switch ($TaskInfo.LastTaskResult) {
        0 { "SUCCESS - Task completed successfully" }
        1 { "ERROR - Incorrect function called or unknown function called" }
        2 { "ERROR - File not found" }
        10 { "ERROR - Environment is incorrect" }
        267009 { "RUNNING - Task is currently running" }
        267011 { "MISSED - Task has not yet run" }
        -2147024891 { "ERROR - Access denied" }
        -2147024894 { "ERROR - File not found" }
        default { "See Task Scheduler for details" }
    }
    Write-Host ("  Result Meaning   : {0}" -f $ResultMessage) -ForegroundColor $(if ($TaskInfo.LastTaskResult -eq 0) { "Green" } else { "Red" })
    
} catch {
    Write-Host "[ERROR] Could not retrieve task information: $_" -ForegroundColor Red
    exit 1
}

# Check if log file exists and show last 20 lines
Write-Host "`n[TASK SCHEDULER LOG - Last 20 Lines]" -ForegroundColor Yellow
if (Test-Path $LogFile) {
    $LogSize = (Get-Item $LogFile).Length / 1KB
    Write-Host ("  Log File Size    : {0:N2} KB" -f $LogSize)
    Write-Host ("  Log File Path    : {0}" -f $LogFile)
    Write-Host "`n  --- Log Content ---" -ForegroundColor Gray
    Get-Content $LogFile -Tail 20 | ForEach-Object {
        Write-Host "  $_" -ForegroundColor Gray
    }
} else {
    Write-Host "  Log file not found: $LogFile" -ForegroundColor Red
    Write-Host "  (Task may not have run yet, or logging is not configured)" -ForegroundColor Yellow
}

# Check Gateway process status
Write-Host "`n[GATEWAY PROCESS STATUS]" -ForegroundColor Yellow
$GatewayProcess = Get-Process -Name "ibgateway" -ErrorAction SilentlyContinue
if ($GatewayProcess) {
    Write-Host ("  Gateway Running  : YES (PID: {0})" -f $GatewayProcess.Id) -ForegroundColor Green
    Write-Host ("  Start Time       : {0}" -f $GatewayProcess.StartTime)
    Write-Host ("  CPU Time         : {0}" -f $GatewayProcess.CPU)
    Write-Host ("  Memory (MB)      : {0:N2}" -f ($GatewayProcess.WorkingSet64 / 1MB))
} else {
    Write-Host "  Gateway Running  : NO" -ForegroundColor Red
}

# Check API port 7497
Write-Host "`n[API PORT CHECK]" -ForegroundColor Yellow
$PortTest = Test-NetConnection -ComputerName localhost -Port 7497 -InformationLevel Quiet -WarningAction SilentlyContinue
if ($PortTest) {
    Write-Host "  Port 7497        : OPEN (API Ready)" -ForegroundColor Green
} else {
    Write-Host "  Port 7497        : CLOSED (API Not Ready)" -ForegroundColor Red
}

Write-Host "`n============================================================" -ForegroundColor Cyan
Write-Host "HEALTH CHECK COMPLETE" -ForegroundColor Cyan
Write-Host "============================================================" -ForegroundColor Cyan
