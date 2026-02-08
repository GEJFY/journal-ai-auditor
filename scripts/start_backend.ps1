# JAIA Backend Startup Script
# PowerShell script to start the FastAPI backend server

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host "=== JAIA Backend Server ===" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray

# Change to backend directory
Set-Location $BackendDir

# Check if virtual environment exists
$VenvPath = Join-Path $BackendDir "venv"
$VenvActivate = Join-Path $VenvPath "Scripts\Activate.ps1"

if (-not (Test-Path $VenvPath)) {
    Write-Host "Creating virtual environment..." -ForegroundColor Yellow
    python -m venv venv
}

# Activate virtual environment
Write-Host "Activating virtual environment..." -ForegroundColor Yellow
& $VenvActivate

# Install/update dependencies
$RequirementsPath = Join-Path $BackendDir "requirements.txt"
if (Test-Path $RequirementsPath) {
    Write-Host "Installing dependencies..." -ForegroundColor Yellow
    pip install -r $RequirementsPath --quiet
}

# Create data directory if not exists
$DataDir = Join-Path $BackendDir "data"
if (-not (Test-Path $DataDir)) {
    Write-Host "Creating data directory..." -ForegroundColor Yellow
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

# Set environment variables
$env:PYTHONPATH = $BackendDir
$env:JAIA_DEBUG = "true"
$env:JAIA_LOG_LEVEL = "INFO"

# Start the server
Write-Host ""
Write-Host "Starting JAIA Backend Server..." -ForegroundColor Green
Write-Host "API Docs: http://localhost:8000/docs" -ForegroundColor Cyan
Write-Host "Health Check: http://localhost:8000/health" -ForegroundColor Cyan
Write-Host ""

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
