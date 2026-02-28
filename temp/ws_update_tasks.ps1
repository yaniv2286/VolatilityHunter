# Update VolatilityHunter_Daily_Live: 17:00 IST, background (not interactive-only)
$taskName = "VolatilityHunter_Daily_Live"
$task = Get-ScheduledTask -TaskName $taskName

# Update trigger to 17:00
$trigger = New-ScheduledTaskTrigger -Daily -At "17:00"

# Principal: run whether logged on or not, highest privilege
$principal = New-ScheduledTaskPrincipal -UserId "DESKTOP-ROOMCOM\Yaniv" -LogonType S4U -RunLevel Highest

# Keep existing action and settings
$action = $task.Actions[0]
$settings = $task.Settings

Set-ScheduledTask -TaskName $taskName -Trigger $trigger -Principal $principal -Action $action -Settings $settings

Write-Host "VolatilityHunter_Daily_Live updated:"
$updated = Get-ScheduledTask -TaskName $taskName
$updated.Triggers | Format-List StartBoundary, Enabled
$updated.Principal | Format-List LogonType, RunLevel
