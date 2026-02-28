# Fix Auto_IBGateway_Manager: remove 72h kill limit, ensure background logon
$taskName = "Auto_IBGateway_Manager"
$task = Get-ScheduledTask -TaskName $taskName

# Settings: disable execution time limit (0 = unlimited)
$settings = New-ScheduledTaskSettingsSet `
    -ExecutionTimeLimit (New-TimeSpan -Seconds 0) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 1) `
    -StartWhenAvailable `
    -DontStopIfGoingOnBatteries `
    -AllowStartIfOnBatteries

# Principal: Interactive/Background, Highest privilege
$principal = New-ScheduledTaskPrincipal -UserId "DESKTOP-ROOMCOM\Yaniv" -LogonType S4U -RunLevel Highest

# Keep existing action and trigger
$action  = $task.Actions[0]
$trigger = $task.Triggers[0]

Set-ScheduledTask -TaskName $taskName -Settings $settings -Principal $principal -Action $action -Trigger $trigger

Write-Host "Auto_IBGateway_Manager updated:"
$updated = Get-ScheduledTask -TaskName $taskName
Write-Host "  ExecutionTimeLimit : $($updated.Settings.ExecutionTimeLimit)"
Write-Host "  LogonType          : $($updated.Principal.LogonType)"
Write-Host "  RunLevel           : $($updated.Principal.RunLevel)"
Write-Host "  RestartCount       : $($updated.Settings.RestartCount)"
