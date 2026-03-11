# PowerShell script to create 24/7 IB Gateway Monitor task
# Run this as Administrator

Write-Host "Creating 24/7 IB Gateway Monitor task..." -ForegroundColor Green

# Delete old tasks
Write-Host "Deleting old tasks..." -ForegroundColor Yellow
schtasks /delete /tn "Auto_IBGateway_Manager" /f 2>$null
schtasks /delete /tn "IBGateway_Monitor_247" /f 2>$null

# Create the new 24/7 task
Write-Host "Creating new 24/7 task..." -ForegroundColor Yellow
$result = schtasks /create /tn "IBGateway_Monitor_247" /tr "cmd /c 'D:\GitHub\VolatilityHunter\scripts\DAILY_ROUTINE\run_auto_tws_manager.bat'" /sc minute /mo 5 /ru SYSTEM /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "✅ SUCCESS: 24/7 IB Gateway Monitor task created!" -ForegroundColor Green
    Write-Host ""
    Write-Host "Task Details:" -ForegroundColor Cyan
    Write-Host "- Name: IBGateway_Monitor_247"
    Write-Host "- Schedule: Every 5 minutes (24/7)"
    Write-Host "- User: SYSTEM (background service)"
    Write-Host ""
    
    Write-Host "Verifying task..." -ForegroundColor Yellow
    schtasks /query /tn "IBGateway_Monitor_247" /fo LIST
    
    Write-Host ""
    Write-Host "Starting task manually to test..." -ForegroundColor Yellow
    schtasks /run /tn "IBGateway_Monitor_247"
    
    Write-Host ""
    Write-Host "✅ Task will start monitoring within 5 minutes." -ForegroundColor Green
    Write-Host "✅ IB Gateway will be automatically started and maintained 24/7." -ForegroundColor Green
} else {
    Write-Host "❌ FAILED: Could not create task." -ForegroundColor Red
    Write-Host ""
    Write-Host "Make sure you're running this as Administrator:" -ForegroundColor Yellow
    Write-Host "1. Right-click on PowerShell" -ForegroundColor White
    Write-Host "2. 'Run as administrator'" -ForegroundColor White
    Write-Host "3. Run this script again" -ForegroundColor White
}

Write-Host ""
Write-Host "Press any key to exit..." -ForegroundColor Cyan
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
