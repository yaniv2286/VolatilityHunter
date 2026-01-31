# PowerShell script to automatically create Windows Task Scheduler task
# Run as Administrator

$TaskName = "VolatilityHunter Daily Scan"
$Description = "Automated stock scanner with email alerts"
$PythonPath = "$PSScriptRoot\venv\Scripts\python.exe"
$ScriptPath = "$PSScriptRoot\scheduler.py"
$WorkingDir = $PSScriptRoot

Write-Host "="*60
Write-Host "VolatilityHunter - Task Scheduler Setup"
Write-Host "="*60

# Check if running as Administrator
$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
if (-not $isAdmin) {
    Write-Host "ERROR: This script must be run as Administrator!" -ForegroundColor Red
    Write-Host "Right-click PowerShell and select 'Run as Administrator'" -ForegroundColor Yellow
    exit 1
}

Write-Host "`nConfiguration:" -ForegroundColor Cyan
Write-Host "  Task Name: $TaskName"
Write-Host "  Python: $PythonPath"
Write-Host "  Script: $ScriptPath"
Write-Host "  Working Directory: $WorkingDir"
Write-Host "  Schedule: Daily at 9:00 AM"

# Check if Python exists
if (-not (Test-Path $PythonPath)) {
    Write-Host "`nERROR: Python not found at $PythonPath" -ForegroundColor Red
    Write-Host "Please run this script from the VolatilityHunter directory" -ForegroundColor Yellow
    exit 1
}

# Check if scheduler.py exists
if (-not (Test-Path $ScriptPath)) {
    Write-Host "`nERROR: scheduler.py not found at $ScriptPath" -ForegroundColor Red
    exit 1
}

Write-Host "`nCreating scheduled task..." -ForegroundColor Green

# Create the action
$Action = New-ScheduledTaskAction -Execute $PythonPath -Argument $ScriptPath -WorkingDirectory $WorkingDir

# Create the trigger (daily at 9:00 AM)
$Trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM

# Create settings
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -WakeToRun `
    -StartWhenAvailable `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1)

# Create the principal (run with highest privileges)
$Principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -RunLevel Highest

# Register the task
try {
    # Remove existing task if it exists
    $existingTask = Get-ScheduledTask -TaskName $TaskName -ErrorAction SilentlyContinue
    if ($existingTask) {
        Write-Host "Removing existing task..." -ForegroundColor Yellow
        Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false
    }
    
    Register-ScheduledTask `
        -TaskName $TaskName `
        -Description $Description `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Principal $Principal | Out-Null
    
    Write-Host ""
    Write-Host "Task created successfully!" -ForegroundColor Green
    
    # Display task info
    $task = Get-ScheduledTask -TaskName $TaskName
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "  State: $($task.State)"
    Write-Host "  Next Run: $(Get-ScheduledTaskInfo -TaskName $TaskName | Select-Object -ExpandProperty NextRunTime)"
    
    Write-Host ""
    Write-Host "Power Settings Recommendations:" -ForegroundColor Yellow
    Write-Host "  1. Disable sleep: Win+X -> Power Options -> Never"
    Write-Host "  2. Enable wake timers: Power Options -> Advanced -> Allow wake timers"
    Write-Host "  3. Keep PC plugged in during scan times (9:00 AM)"
    
    Write-Host ""
    Write-Host "To test the task now, run:" -ForegroundColor Cyan
    Write-Host "  Start-ScheduledTask -TaskName '$TaskName'"
    
    Write-Host ""
    Write-Host "To view task in Task Scheduler:" -ForegroundColor Cyan
    Write-Host "  taskschd.msc"
    
    Write-Host ""
    Write-Host ("="*60)
    Write-Host "Setup Complete! Your scanner will run daily at 9:00 AM" -ForegroundColor Green
    Write-Host ("="*60)
    
} catch {
    Write-Host ""
    Write-Host "ERROR: Failed to create task" -ForegroundColor Red
    Write-Host $_.Exception.Message -ForegroundColor Red
    exit 1
}
