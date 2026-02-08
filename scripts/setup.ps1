# JAIA Development Environment Setup Script
# Run this once to set up the development environment

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JAIA Development Environment Setup" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Check Python
Write-Host "Checking Python installation..." -ForegroundColor Yellow
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  Found: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Python not found. Please install Python 3.11+" -ForegroundColor Red
    exit 1
}

# Check Node.js
Write-Host "Checking Node.js installation..." -ForegroundColor Yellow
try {
    $nodeVersion = node --version 2>&1
    Write-Host "  Found: Node.js $nodeVersion" -ForegroundColor Green
} catch {
    Write-Host "  ERROR: Node.js not found. Please install Node.js 18+" -ForegroundColor Red
    exit 1
}

# Setup Backend
Write-Host ""
Write-Host "Setting up Backend..." -ForegroundColor Yellow
$BackendDir = Join-Path $ProjectRoot "backend"
Set-Location $BackendDir

# Create virtual environment
$VenvPath = Join-Path $BackendDir "venv"
if (-not (Test-Path $VenvPath)) {
    Write-Host "  Creating virtual environment..." -ForegroundColor Gray
    python -m venv venv
}

# Activate and install dependencies
$VenvActivate = Join-Path $VenvPath "Scripts\Activate.ps1"
& $VenvActivate

$RequirementsPath = Join-Path $BackendDir "requirements.txt"
if (Test-Path $RequirementsPath) {
    Write-Host "  Installing Python dependencies..." -ForegroundColor Gray
    pip install -r $RequirementsPath --quiet
}

# Create data directory
$DataDir = Join-Path $BackendDir "data"
if (-not (Test-Path $DataDir)) {
    Write-Host "  Creating data directory..." -ForegroundColor Gray
    New-Item -ItemType Directory -Path $DataDir | Out-Null
}

Write-Host "  Backend setup complete!" -ForegroundColor Green

# Setup Frontend
Write-Host ""
Write-Host "Setting up Frontend..." -ForegroundColor Yellow
$FrontendDir = Join-Path $ProjectRoot "frontend"
Set-Location $FrontendDir

# Install npm dependencies
Write-Host "  Installing npm dependencies..." -ForegroundColor Gray
npm install --silent

Write-Host "  Frontend setup complete!" -ForegroundColor Green

# Create .env file if not exists
Write-Host ""
Write-Host "Checking environment configuration..." -ForegroundColor Yellow
$EnvFile = Join-Path $BackendDir ".env"
if (-not (Test-Path $EnvFile)) {
    Write-Host "  Creating .env file from template..." -ForegroundColor Gray
    $EnvContent = @"
# JAIA Configuration
JAIA_DEBUG=true
JAIA_LOG_LEVEL=INFO

# Database
DUCKDB_PATH=data/jaia.duckdb
SQLITE_PATH=data/jaia_meta.db

# LLM Configuration (optional)
# OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_ENDPOINT=your-endpoint
# ANTHROPIC_API_KEY=your-api-key
"@
    Set-Content -Path $EnvFile -Value $EnvContent
    Write-Host "  .env file created. Please configure API keys if needed." -ForegroundColor Yellow
}

# Return to project root
Set-Location $ProjectRoot

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "To start the development servers, run:" -ForegroundColor Cyan
Write-Host "  .\scripts\start_all.ps1" -ForegroundColor White
Write-Host ""
Write-Host "Or start them separately:" -ForegroundColor Cyan
Write-Host "  .\scripts\start_backend.ps1" -ForegroundColor White
Write-Host "  .\scripts\start_frontend.ps1" -ForegroundColor White
Write-Host ""
