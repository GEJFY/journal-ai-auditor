# JAIA Frontend Startup Script
# PowerShell script to start the Electron + React frontend

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host "=== JAIA Frontend Application ===" -ForegroundColor Cyan
Write-Host "Project Root: $ProjectRoot" -ForegroundColor Gray

# Change to frontend directory
Set-Location $FrontendDir

# Check if node_modules exists
$NodeModules = Join-Path $FrontendDir "node_modules"
if (-not (Test-Path $NodeModules)) {
    Write-Host "Installing npm dependencies..." -ForegroundColor Yellow
    npm install
}

# Start the development server
Write-Host ""
Write-Host "Starting JAIA Frontend..." -ForegroundColor Green
Write-Host "Development URL: http://localhost:5173" -ForegroundColor Cyan
Write-Host ""

npm run dev
