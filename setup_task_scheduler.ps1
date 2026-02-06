# VolatilityHunter Task Scheduler Setup Script
# Run this script as Administrator to create/update the Windows Task Scheduler job

# Task Configuration
$taskName = "VolatilityHunter Daily Trading"
$description = "VolatilityHunter automated trading system - Daily execution at 12:30 AM"
$scriptPath = "D:\GitHub\VolatilityHunter\scheduler_updated.py"
$workingDirectory = "D:\GitHub\VolatilityHunter"
$pythonPath = "python"
$arguments = "--daily"

# Environment Variables
$envVars = @{
    "VH_MODE" = "production"
    "VH_EMAIL_ENABLED" = "true"
    "VH_EMAIL_RECIPIENT" = "lugassy.ai@gmail.com"
}

Write-Host "Setting up VolatilityHunter Task Scheduler..." -ForegroundColor Green
Write-Host "Task Name: $taskName" -ForegroundColor Yellow
Write-Host "Script: $scriptPath" -ForegroundColor Yellow
Write-Host "Schedule: Daily at 12:30 AM" -ForegroundColor Yellow

# Remove existing task if it exists
try {
    Get-ScheduledTask -TaskName $taskName -ErrorAction Stop | Out-Null
    Write-Host "Removing existing task..." -ForegroundColor Yellow
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
} catch {
    Write-Host "No existing task found (this is normal)" -ForegroundColor Green
}

# Create the action
$action = New-ScheduledTaskAction -Execute $pythonPath -Argument "$scriptPath $arguments" -WorkingDirectory $workingDirectory

# Create the trigger (daily at 12:30 AM)
$trigger = New-ScheduledTaskTrigger -Daily -At 12:30AM

# Create settings
$settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -DontStopOnIdleEnd -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries -WakeToRun

# Register the task
try {
    Register-ScheduledTask -TaskName $taskName -Action $action -Trigger $trigger -Settings $settings -Description $description -RunLevel Highest -Force
    
    Write-Host "Task created successfully!" -ForegroundColor Green
    
    # Set environment variables
    $task = Get-ScheduledTask -TaskName $taskName
    foreach ($var in $envVars.GetEnumerator()) {
        $task.Actions[0].Arguments += " /setenv $($var.Key)=$($var.Value)"
    }
    Set-ScheduledTask -TaskName $task -InputObject $task
    
    Write-Host "Environment variables set:" -ForegroundColor Yellow
    foreach ($var in $envVars.GetEnumerator()) {
        Write-Host "  $($var.Key)=$($var.Value)" -ForegroundColor Cyan
    }
    
} catch {
    Write-Host "Error creating task: $_" -ForegroundColor Red
    exit 1
}

# Display task information
Write-Host "`nTask Scheduler Configuration:" -ForegroundColor Green
Write-Host "=============================" -ForegroundColor Green
Get-ScheduledTask -TaskName $taskName | Select-Object TaskName, State, Description | Format-Table -AutoSize

Write-Host "`nNext run time:" -ForegroundColor Yellow
(Get-ScheduledTask -TaskName $taskName).Triggers | Select-Object StartBoundary, DaysInterval, Enabled

Write-Host "`nSetup complete! The task will run daily at 12:30 AM." -ForegroundColor Green
Write-Host "To test immediately, run: python scheduler_updated.py --daily" -ForegroundColor Cyan
