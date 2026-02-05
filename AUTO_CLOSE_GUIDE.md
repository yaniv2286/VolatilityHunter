# Task Scheduler Auto-Close Configuration
# Options for automated window management

## 🚀 AUTO-CLOSE OPTIONS

### Option 1: Standard with Auto-Close (Recommended)
**Script**: `task_scheduler_run.ps1`
**Behavior**: Shows window briefly, then auto-closes
- **Success**: Window closes after 5 seconds
- **Error**: Window closes after 2 seconds
- **Test Mode**: Window stays open for debugging

### Option 2: Completely Silent
**Script**: `task_scheduler_silent.ps1`
**Behavior**: No window ever appears
- **Success**: Completely silent execution
- **Error**: Silent (logged to file only)
- **Best for**: Production automation

### Option 3: Batch File Alternative
**Script**: `task_scheduler_run.bat`
**Behavior**: Traditional batch file with auto-close
- **Success**: Closes after 3 seconds
- **Error**: Closes after 10 seconds

## 📋 SETUP COMMANDS

### Standard Auto-Close (Recommended):
```powershell
powershell -ExecutionPolicy Bypass -File "setup_scheduler.ps1"
```

### Completely Silent:
```powershell
powershell -ExecutionPolicy Bypass -File "setup_scheduler.ps1" -Silent
```

### Test Mode (Window Stays Open):
```powershell
powershell -ExecutionPolicy Bypass -File "task_scheduler_run.ps1" -Test
```

## 🔧 CONFIGURATION DETAILS

### Auto-Close Timing:
- **Standard Success**: 5 seconds
- **Standard Error**: 2 seconds (brief pause to read error)
- **Batch Success**: 3 seconds
- **Batch Error**: 10 seconds
- **Silent Mode**: No window at all

### Task Scheduler Settings:
- **Window Style**: Hidden (no window flash)
- **Execution**: SYSTEM account with highest privileges
- **Network**: Requires network connection
- **Power**: Runs on battery if needed

## 📊 LOGGING

### Standard Mode:
- Console output + log files
- Auto-close message displayed
- Error details shown before closing

### Silent Mode:
- Log files only (no console output)
- All information in `task_scheduler_YYYYMMDD.log`
- Perfect for unattended operation

### Log Locations:
- Task logs: `task_scheduler_YYYYMMDD.log`
- Main logs: `volatility_hunter_YYYYMMDD_HHMMSS.log`
- Auto-cleanup: 7-day retention

## 🎯 RECOMMENDATIONS

### For Production Use:
```powershell
# Silent execution - completely invisible
powershell -ExecutionPolicy Bypass -File "setup_scheduler.ps1" -Silent
```

### For Development/Testing:
```powershell
# Standard with auto-close - see what's happening
powershell -ExecutionPolicy Bypass -File "setup_scheduler.ps1"
```

### For Debugging:
```powershell
# Test mode - window stays open
powershell -ExecutionPolicy Bypass -File "task_scheduler_run.ps1" -Test
```

## ⚙️ CUSTOMIZATION

### Change Auto-Close Delay:
Edit `task_scheduler_run.ps1`:
```powershell
$AutoCloseDelay = 10  # Change from 5 to 10 seconds
```

### Disable Auto-Close:
Edit `task_scheduler_run.ps1`:
```powershell
# Comment out or remove the Start-Sleep lines
if (-not $Test) {
    # Write-Log "Window will auto-close in $AutoCloseDelay seconds..."
    # Start-Sleep -Seconds $AutoCloseDelay
}
```

## 🔍 VERIFICATION

### Check Task Configuration:
```powershell
Get-ScheduledTask -TaskName "VolatilityHunter Daily" | Select-Object Actions, Settings
```

### Test Manual Run:
```powershell
Start-ScheduledTask -TaskName "VolatilityHunter Daily"
```

### View Execution History:
```powershell
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational | Where-Object {$_.Message -like "*VolatilityHunter*"} | Select-Object TimeCreated, LevelDisplayName, Message
```

## 📝 NOTES

- All scripts use `-WindowStyle Hidden` in Task Scheduler
- Auto-close only applies when NOT in Test mode
- Silent mode writes everything to log files
- Batch file alternative provided for compatibility
- System logs all execution regardless of mode

## 🚨 TROUBLESHOOTING

### Window Not Closing:
1. Check if running in Test mode
2. Verify script permissions
3. Check for error messages

### No Logs in Silent Mode:
1. Check log file permissions
2. Verify working directory
3. Check system event logs

### Task Not Running:
1. Run as Administrator to setup
2. Check Task Scheduler service
3. Verify script paths exist
