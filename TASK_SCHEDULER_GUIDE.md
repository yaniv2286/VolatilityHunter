# VolatilityHunter Task Scheduler Setup Guide
# Complete instructions for automated daily execution

## 🚀 QUICK SETUP (Run as Administrator)

### Step 1: Open PowerShell as Administrator
1. Right-click Start button
2. Select "Windows PowerShell (Admin)"
3. Navigate to project directory:
   ```powershell
   cd D:\GitHub\VolatilityHunter
   ```

### Step 2: Run Setup Script
```powershell
powershell -ExecutionPolicy Bypass -File "setup_scheduler.ps1"
```

### Step 3: Verify Installation
```powershell
Get-ScheduledTask -TaskName "VolatilityHunter Daily"
```

## 📋 MANUAL SETUP (Alternative)

### Create Task Manually:
1. Open Task Scheduler (taskschd.msc)
2. Click "Create Task" in Actions panel
3. General Tab:
   - Name: "VolatilityHunter Daily"
   - Description: "VolatilityHunter Daily Automated Trading System"
   - Select "Run with highest privileges"
   - Select "Run whether user is logged on or not"

4. Trigger Tab:
   - Click "New..."
   - Begin: Daily
   - Start: 09:00:00 AM
   - Enabled: ✓

5. Actions Tab:
   - Action: Start a program
   - Program/script: powershell.exe
   - Add arguments: -ExecutionPolicy Bypass -File "D:\GitHub\VolatilityHunter\task_scheduler_run.ps1"
   - Start in: D:\GitHub\VolatilityHunter

6. Conditions Tab:
   - Start the task only if the computer is on AC power: ✗
   - Start the task only if the computer is connected to the network: ✓
   - Wake the computer to run this task: ✓

7. Settings Tab:
   - Allow task to be run on demand: ✓
   - Run task as soon as possible after a scheduled start is missed: ✓
   - Stop the task if it runs longer than: 4 hours
   - If the task is already running, then the following rule applies: Do not start a new instance

## 🔧 MANAGEMENT COMMANDS

### View Task Status:
```powershell
Get-ScheduledTask -TaskName "VolatilityHunter Daily" | Select-Object State, LastRunTime, NextRunTime
```

### Run Task Manually:
```powershell
Start-ScheduledTask -TaskName "VolatilityHunter Daily"
```

### View Task History:
```powershell
Get-WinEvent -LogName Microsoft-Windows-TaskScheduler/Operational | Where-Object {$_.Message -like "*VolatilityHunter*"} | Select-Object TimeCreated, LevelDisplayName, Message | Format-Table -Wrap
```

### Remove Task:
```powershell
Unregister-ScheduledTask -TaskName "VolatilityHunter Daily" -Confirm:$false
```

## 📊 MONITORING

### Log Files Location:
- Main logs: `D:\GitHub\VolatilityHunter\volatility_hunter.log`
- Task Scheduler logs: `D:\GitHub\VolatilityHunter\task_scheduler_YYYYMMDD.log`
- Execution logs: `D:\GitHub\VolatilityHunter\volatility_hunter_YYYYMMDD_HHMMSS.log`

### Email Notifications:
- Daily reports sent to your configured email
- Includes portfolio performance, signals, and execution summary
- Log files attached automatically

## ⚠️ TROUBLESHOOTING

### Common Issues:

1. **Access Denied**: Run PowerShell as Administrator
2. **Python not found**: Ensure Python is in system PATH
3. **Virtual environment missing**: Run setup script first
4. **Network issues**: Check internet connection during execution time

### Debug Mode:
```powershell
# Run with detailed logging
powershell -ExecutionPolicy Bypass -File "task_scheduler_run.ps1" -Test

# Check last execution
Get-ScheduledTaskInfo -TaskName "VolatilityHunter Daily"
```

## 📅 SCHEDULE RECOMMENDATIONS

### Market Hours:
- **Daily Scan**: 9:00 AM (before market open)
- **Pre-market Check**: 8:30 AM (optional)
- **Post-market Review**: 4:30 PM (optional)

### Weekends:
- No trading on weekends
- System will run but no market data available
- Consider disabling on Saturday/Sunday

## 🔒 SECURITY

### File Permissions:
- Ensure scripts have appropriate permissions
- Virtual environment should be accessible
- Log directory should be writable

### Network:
- Task requires internet connection for market data
- Consider backup schedule if network unreliable

## 📞 SUPPORT

### If issues occur:
1. Check log files for error messages
2. Run manual test: `python main.py`
3. Verify email configuration in `.env`
4. Check Task Scheduler history

### Emergency Stop:
```powershell
# Disable task temporarily
Disable-ScheduledTask -TaskName "VolatilityHunter Daily"

# Re-enable when ready
Enable-ScheduledTask -TaskName "VolatilityHunter Daily"
```
