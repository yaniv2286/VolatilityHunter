$taskName = "VolatilityHunter_Daily_Live"
$task = Get-ScheduledTask -TaskName $taskName
$trigger = New-ScheduledTaskTrigger -Daily -At "17:06"
$principal = New-ScheduledTaskPrincipal -UserId "DESKTOP-ROOMCOM\Yaniv" -LogonType S4U -RunLevel Highest
Set-ScheduledTask -TaskName $taskName -Trigger $trigger -Principal $principal -Action $task.Actions[0] -Settings $task.Settings
Write-Host "Done - new trigger:"
(Get-ScheduledTask -TaskName $taskName).Triggers | Select-Object StartBoundary
