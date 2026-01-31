# VolatilityHunter Launcher Script (PowerShell)
# Usage: .\run.ps1 [command]
# Commands: update, update-full, scan, server (default)

param(
    [string]$Command = "server"
)

Write-Host "🎯 VolatilityHunter Launcher" -ForegroundColor Cyan
Write-Host "================================" -ForegroundColor Cyan

# Activate virtual environment
$venvPath = ".\venv\Scripts\Activate.ps1"
if (Test-Path $venvPath) {
    Write-Host "✓ Activating virtual environment..." -ForegroundColor Green
    & $venvPath
} else {
    Write-Host "⚠ Virtual environment not found. Run: python -m venv venv" -ForegroundColor Yellow
    exit 1
}

# Check if .env exists
if (-not (Test-Path ".env")) {
    Write-Host "⚠ .env file not found. Please configure your API keys." -ForegroundColor Yellow
}

# Run the appropriate command
Write-Host "Running command: $Command" -ForegroundColor Cyan
Write-Host ""

switch ($Command) {
    "update" {
        python main.py update
    }
    "update-full" {
        python main.py update-full
    }
    "scan" {
        python main.py scan
    }
    "server" {
        Write-Host "Starting Flask server at http://localhost:8080" -ForegroundColor Green
        python main.py
    }
    default {
        Write-Host "Unknown command: $Command" -ForegroundColor Red
        Write-Host "Available commands: update, update-full, scan, server" -ForegroundColor Yellow
        exit 1
    }
}
