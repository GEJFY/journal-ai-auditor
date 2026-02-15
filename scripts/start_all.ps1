# JAIA Full Stack Startup Script
# Starts both backend and frontend in separate windows

$ErrorActionPreference = "Stop"

# Get script directory
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JAIA - Journal entry AI Analyzer" -ForegroundColor Cyan
Write-Host "  Full Stack Development Server" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# Start Backend in new window
Write-Host "Starting Backend Server..." -ForegroundColor Yellow
$BackendScript = Join-Path $ScriptDir "start_backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $BackendScript

# Wait for backend to start
Write-Host "Waiting for backend to initialize..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# Start Frontend in new window
Write-Host "Starting Frontend Application..." -ForegroundColor Yellow
$FrontendScript = Join-Path $ScriptDir "start_frontend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $FrontendScript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  JAIA is starting up!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Backend API:  http://localhost:8090" -ForegroundColor Cyan
Write-Host "API Docs:     http://localhost:8090/docs" -ForegroundColor Cyan
Write-Host "Frontend:     http://localhost:5290" -ForegroundColor Cyan
Write-Host ""
Write-Host "Press any key to exit this window..." -ForegroundColor Gray
$null = $Host.UI.RawUI.ReadKey("NoEcho,IncludeKeyDown")
