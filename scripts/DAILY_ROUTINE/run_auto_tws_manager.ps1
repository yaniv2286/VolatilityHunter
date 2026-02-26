# ============================================================================= 
# AUTOMATED TWS MANAGER - 24/7 AUTO-PILOT (PowerShell)
# =============================================================================

Write-Host "==========================================================="
Write-Host "AUTOMATED TWS MANAGER - 24/7 AUTO-PILOT"
Write-Host "==========================================================="
Write-Host "Starting: $(Get-Date)"
Write-Host ""
Write-Host "This will AUTOMATICALLY:"
Write-Host "1. Start TWS if not running"
Write-Host "2. Wait for TWS to load"
Write-Host "3. Auto-detect when API is enabled"
Write-Host "4. Start keep-alive service"
Write-Host "5. Monitor 24/7 and restart if needed"
Write-Host ""
Write-Host "NO MANUAL INTERVENTION REQUIRED!"
Write-Host ""

# Check if Python is available
try {
    python --version | Out-Null
} catch {
    Write-Host "ERROR: Python not found in PATH"
    Read-Host "Press Enter to exit..."
    exit 1
}

# Start the automated TWS manager
Set-Location "D:\GitHub\VolatilityHunter"
& "venv\Scripts\Activate.ps1"
python scripts/auto_tws_manager.py

Write-Host ""
Write-Host "Auto TWS Manager stopped"
Read-Host "Press Enter to exit..."
