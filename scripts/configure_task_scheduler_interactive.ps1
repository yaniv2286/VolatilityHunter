# VolatilityHunter Task Scheduler Configuration
# =============================================
# Configures the scheduled task to run in interactive session (bypasses Session 0)
# This allows Ghost-Typist GUI automation to work correctly.
#
# USAGE: Run as Administrator
# powershell -ExecutionPolicy Bypass -File scripts/configure_task_scheduler_interactive.ps1

$TaskName = "VolatilityHunter_Daily_Live"
$TaskPath = "\"

Write-Host "=" * 80
Write-Host "TASK SCHEDULER CONFIGURATION - INTERACTIVE SESSION MODE"
Write-Host "=" * 80
Write-Host ""

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

# Get the task
try {
    $task = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -ErrorAction Stop
    Write-Host "[OK] Found task: $TaskName" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Task '$TaskName' not found" -ForegroundColor Red
    Write-Host "Please create the task first using Task Scheduler GUI" -ForegroundColor Yellow
    exit 1
}

# Get current user
$currentUser = [System.Security.Principal.WindowsIdentity]::GetCurrent().Name
Write-Host "[INFO] Current user: $currentUser" -ForegroundColor Cyan

# Configure task settings
Write-Host ""
Write-Host "Configuring task settings..." -ForegroundColor Yellow

# Create new principal (user context)
$principal = New-ScheduledTaskPrincipal -UserId $currentUser -LogonType Interactive -RunLevel Highest

# Update task settings
$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -RunOnlyIfNetworkAvailable `
    -Priority 0 `
    -ExecutionTimeLimit (New-TimeSpan -Hours 2)

# Get existing trigger and action
$trigger = $task.Triggers[0]
$action = $task.Actions[0]

# Register task with new settings
try {
    Register-ScheduledTask `
        -TaskName $TaskName `
        -TaskPath $TaskPath `
        -Action $action `
        -Trigger $trigger `
        -Principal $principal `
        -Settings $settings `
        -Force | Out-Null
    
    Write-Host "[OK] Task configured successfully" -ForegroundColor Green
} catch {
    Write-Host "[ERROR] Failed to configure task: $_" -ForegroundColor Red
    exit 1
}

# Verify configuration
Write-Host ""
Write-Host "Verifying configuration..." -ForegroundColor Yellow

$updatedTask = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath
$taskInfo = $updatedTask | Get-ScheduledTaskInfo

Write-Host ""
Write-Host "=" * 80
Write-Host "TASK CONFIGURATION SUMMARY"
Write-Host "=" * 80
Write-Host "Task Name:        $TaskName"
Write-Host "User:             $($updatedTask.Principal.UserId)"
Write-Host "Logon Type:       $($updatedTask.Principal.LogonType)"
Write-Host "Run Level:        $($updatedTask.Principal.RunLevel)"
Write-Host "Priority:         $($updatedTask.Settings.Priority)"
Write-Host "Last Run:         $($taskInfo.LastRunTime)"
Write-Host "Next Run:         $($taskInfo.NextRunTime)"
Write-Host "Last Result:      $($taskInfo.LastTaskResult)"
Write-Host ""

if ($updatedTask.Principal.LogonType -eq "Interactive") {
    Write-Host "[SUCCESS] Task is now configured for INTERACTIVE SESSION" -ForegroundColor Green
    Write-Host "Ghost-Typist GUI automation will work correctly" -ForegroundColor Green
} else {
    Write-Host "[WARNING] Task logon type is: $($updatedTask.Principal.LogonType)" -ForegroundColor Yellow
    Write-Host "Expected: Interactive" -ForegroundColor Yellow
}

Write-Host ""
Write-Host "=" * 80
Write-Host "CONFIGURATION COMPLETE"
Write-Host "=" * 80
Write-Host ""
Write-Host "IMPORTANT NOTES:" -ForegroundColor Yellow
Write-Host "1. You must be logged in for the task to run" -ForegroundColor White
Write-Host "2. Ghost-Typist requires an active desktop session" -ForegroundColor White
Write-Host "3. Do not lock your computer during scheduled run time" -ForegroundColor White
Write-Host ""
Write-Host "Next scheduled run: $($taskInfo.NextRunTime)" -ForegroundColor Cyan
Write-Host ""
