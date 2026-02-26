# ============================================================================= 
# VOLATILITYHUNTER V10.0 - MASTER PRODUCTION GATEKEEPER (PowerShell)
# Purpose: Health Check -> Live Trading System
# =============================================================================

Write-Host "VOLATILITYHUNTER V10.0 - MASTER PRODUCTION GATEKEEPER"
Write-Host "Purpose: Health Check -> Live Trading System"
Write-Host "============================================================================"

# 1. SETUP & ENVIRONMENT
Set-Location "D:\GitHub\VolatilityHunter"
$env:TOKENIZERS_PARALLELISM = "false"

# Activate the Environment
& "venv\Scripts\Activate.ps1"

# 2. HEALTH CHECK
Write-Host "[V10] Starting Health Check..."
python health_check.py
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "[CRITICAL ERROR] Health Check Failed."
    Write-Host "Possible causes: No Internet, IBKR Gateway Closed, or Tiingo API Down."
    Write-Host ""
    Read-Host "Press Enter to exit..."
    exit $LASTEXITCODE
}

# 3. LIVE TRADING
Write-Host ""
Write-Host "[V10] Health is GREEN. Launching Live Trader..."
Write-Host "[IST] Trading Window Initialized."
Write-Host ""

# Launch in a separate window so we can monitor
Start-Process cmd -ArgumentList "/k", "python main_agent_system.py"

Write-Host "VolatilityHunter trading system launched successfully!"
Write-Host "Trading window is now active."
