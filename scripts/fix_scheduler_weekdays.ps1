#Requires -RunAsAdministrator
<#
Fix VolatilityHunter_Daily_Live to run Monday-Friday at 17:06 with wake enabled.
Run from an elevated PowerShell:
  powershell -ExecutionPolicy Bypass -File scripts\fix_scheduler_weekdays.ps1
#>

$ErrorActionPreference = 'Stop'
$TaskName = 'VolatilityHunter_Daily_Live'
$TaskPath = '\'
$Root = 'D:\GitHub\VolatilityHunter'
$Batch = 'D:\GitHub\VolatilityHunter\scripts\DAILY_ROUTINE\run_trading.bat'
$Log = 'D:\GitHub\VolatilityHunter\logs\task_scheduler.log'

$task = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath
$action = New-ScheduledTaskAction -Execute 'cmd.exe' -Argument "/c `"$Batch >> $Log 2>&1`"" -WorkingDirectory $Root
$trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At 17:06
$settings = New-ScheduledTaskSettingsSet -WakeToRun -StartWhenAvailable -MultipleInstances IgnoreNew -ExecutionTimeLimit (New-TimeSpan -Hours 4) -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 5) -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries
$principal = New-ScheduledTaskPrincipal -UserId $task.Principal.UserId -RunLevel Highest -LogonType Interactive

Set-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath -Action $action -Trigger $trigger -Settings $settings -Principal $principal | Out-Null

$updated = Get-ScheduledTask -TaskName $TaskName -TaskPath $TaskPath
$info = Get-ScheduledTaskInfo -TaskName $TaskName -TaskPath $TaskPath
Write-Output '=== UPDATED TASK ==='
[PSCustomObject]@{
    TaskName = $updated.TaskName
    State = $updated.State
    LastRunTime = $info.LastRunTime
    LastTaskResult = $info.LastTaskResult
    NextRunTime = $info.NextRunTime
    TriggerClass = $updated.Triggers[0].CimClass.CimClassName
    DaysOfWeek = $updated.Triggers[0].DaysOfWeek
    WakeToRun = $updated.Settings.WakeToRun
    StartWhenAvailable = $updated.Settings.StartWhenAvailable
    RestartCount = $updated.Settings.RestartCount
    RunLevel = $updated.Principal.RunLevel
    LogonType = $updated.Principal.LogonType
} | Format-List
