# JAIA Integration Test Script
# Tests the basic API endpoints

$ErrorActionPreference = "Continue"

$BaseUrl = "http://localhost:8000"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JAIA Integration Tests" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

$TestResults = @()

function Test-Endpoint {
    param (
        [string]$Name,
        [string]$Url,
        [string]$Method = "GET",
        [string]$Body = $null
    )

    Write-Host "Testing: $Name" -ForegroundColor Yellow -NoNewline

    try {
        $params = @{
            Uri = $Url
            Method = $Method
            ContentType = "application/json"
            TimeoutSec = 10
        }

        if ($Body) {
            $params.Body = $Body
        }

        $response = Invoke-RestMethod @params
        Write-Host " [PASS]" -ForegroundColor Green
        return @{ Name = $Name; Status = "PASS"; Response = $response }
    } catch {
        Write-Host " [FAIL]" -ForegroundColor Red
        Write-Host "  Error: $($_.Exception.Message)" -ForegroundColor Gray
        return @{ Name = $Name; Status = "FAIL"; Error = $_.Exception.Message }
    }
}

# Test Health Check
$TestResults += Test-Endpoint -Name "Health Check" -Url "$BaseUrl/health"

# Test API v1 Health
$TestResults += Test-Endpoint -Name "API Health" -Url "$BaseUrl/api/v1/health"

# Test Dashboard Summary (requires data)
$TestResults += Test-Endpoint -Name "Dashboard Summary" -Url "$BaseUrl/api/v1/dashboard/summary?fiscal_year=2024"

# Test Dashboard KPI
$TestResults += Test-Endpoint -Name "Dashboard KPI" -Url "$BaseUrl/api/v1/dashboard/kpi?fiscal_year=2024"

# Test Dashboard Benford
$TestResults += Test-Endpoint -Name "Benford Analysis" -Url "$BaseUrl/api/v1/dashboard/benford?fiscal_year=2024"

# Test Batch Rules
$TestResults += Test-Endpoint -Name "Batch Rules" -Url "$BaseUrl/api/v1/batch/rules"

# Test Report Templates
$TestResults += Test-Endpoint -Name "Report Templates" -Url "$BaseUrl/api/v1/reports/templates"

# Test Analysis Violations
$TestResults += Test-Endpoint -Name "Analysis Violations" -Url "$BaseUrl/api/v1/analysis/violations?fiscal_year=2024"

# Summary
Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Test Summary" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan

$PassCount = ($TestResults | Where-Object { $_.Status -eq "PASS" }).Count
$FailCount = ($TestResults | Where-Object { $_.Status -eq "FAIL" }).Count
$TotalCount = $TestResults.Count

Write-Host ""
Write-Host "Total Tests: $TotalCount" -ForegroundColor White
Write-Host "Passed: $PassCount" -ForegroundColor Green
Write-Host "Failed: $FailCount" -ForegroundColor $(if ($FailCount -gt 0) { "Red" } else { "Green" })
Write-Host ""

if ($FailCount -eq 0) {
    Write-Host "All tests passed!" -ForegroundColor Green
} else {
    Write-Host "Some tests failed. Check the backend server is running." -ForegroundColor Yellow
}
