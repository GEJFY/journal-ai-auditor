# JAIA デモ実行スクリプト
#
# このスクリプトは以下を実行します:
# 1. 環境の確認
# 2. サンプルデータのロード
# 3. バックエンドの起動
# 4. 基本的なAPIテスト
#
# 使用方法:
#   .\scripts\demo.ps1

$ErrorActionPreference = "Continue"

# スクリプトディレクトリを取得
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"
$SampleDataDir = Join-Path $ProjectRoot "sample_data"

function Write-Step {
    param([string]$Step, [string]$Message)
    Write-Host ""
    Write-Host "[$Step] $Message" -ForegroundColor Cyan
    Write-Host ("-" * 50) -ForegroundColor Gray
}

function Test-Endpoint {
    param([string]$Name, [string]$Url)

    try {
        $response = Invoke-RestMethod -Uri $Url -Method GET -TimeoutSec 10
        Write-Host "  ✓ $Name" -ForegroundColor Green
        return $true
    } catch {
        Write-Host "  ✗ $Name - $($_.Exception.Message)" -ForegroundColor Red
        return $false
    }
}

Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  JAIA Demo Script" -ForegroundColor Magenta
Write-Host "  Journal entry AI Analyzer" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta

# Step 1: 環境確認
Write-Step "1/5" "環境を確認しています..."

# Python確認
try {
    $pythonVersion = python --version 2>&1
    Write-Host "  ✓ Python: $pythonVersion" -ForegroundColor Green
} catch {
    Write-Host "  ✗ Python が見つかりません" -ForegroundColor Red
    exit 1
}

# 仮想環境確認
$VenvPath = Join-Path $BackendDir "venv"
if (Test-Path $VenvPath) {
    Write-Host "  ✓ 仮想環境: 存在" -ForegroundColor Green
} else {
    Write-Host "  ! 仮想環境が見つかりません。セットアップを実行してください。" -ForegroundColor Yellow
    Write-Host "    .\scripts\setup.ps1" -ForegroundColor Gray
}

# サンプルデータ確認
$JournalFile = Join-Path $SampleDataDir "10_journal_entries.csv"
if (Test-Path $JournalFile) {
    $rowCount = (Get-Content $JournalFile | Measure-Object -Line).Lines - 1
    Write-Host "  ✓ サンプルデータ: $rowCount 件" -ForegroundColor Green
} else {
    Write-Host "  ! サンプルデータが見つかりません" -ForegroundColor Yellow
}

# Step 2: 仮想環境を有効化
Write-Step "2/5" "仮想環境を有効化しています..."

$VenvActivate = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    & $VenvActivate
    Write-Host "  ✓ 仮想環境を有効化しました" -ForegroundColor Green
} else {
    Write-Host "  ! 仮想環境をスキップ（システムPythonを使用）" -ForegroundColor Yellow
}

# Step 3: バックエンドが起動しているか確認
Write-Step "3/5" "バックエンドの状態を確認しています..."

$BackendRunning = $false
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 5
    if ($health.status -eq "healthy") {
        Write-Host "  ✓ バックエンドは既に起動しています" -ForegroundColor Green
        $BackendRunning = $true
    }
} catch {
    Write-Host "  ! バックエンドが起動していません" -ForegroundColor Yellow
    Write-Host "    別のターミナルで以下を実行してください:" -ForegroundColor Gray
    Write-Host "    .\scripts\start_backend.ps1" -ForegroundColor White
    Write-Host ""
    Write-Host "  バックエンドを起動しますか？ (Y/N)" -ForegroundColor Yellow
    $answer = Read-Host
    if ($answer -eq "Y" -or $answer -eq "y") {
        Write-Host "  バックエンドを起動しています..." -ForegroundColor Yellow
        Set-Location $BackendDir
        Start-Process -FilePath "python" -ArgumentList "-m", "uvicorn", "app.main:app", "--host", "127.0.0.1", "--port", "8001" -WindowStyle Normal
        Set-Location $ProjectRoot

        Write-Host "  起動を待機しています..." -ForegroundColor Gray
        Start-Sleep -Seconds 5

        # 再度確認
        try {
            $health = Invoke-RestMethod -Uri "http://localhost:8001/health" -Method GET -TimeoutSec 10
            if ($health.status -eq "healthy") {
                Write-Host "  ✓ バックエンドが起動しました" -ForegroundColor Green
                $BackendRunning = $true
            }
        } catch {
            Write-Host "  ✗ バックエンドの起動に失敗しました" -ForegroundColor Red
        }
    }
}

if (-not $BackendRunning) {
    Write-Host ""
    Write-Host "バックエンドが起動していないため、デモを続行できません。" -ForegroundColor Red
    Write-Host "以下のコマンドでバックエンドを起動してから再実行してください:" -ForegroundColor Yellow
    Write-Host "  .\scripts\start_backend.ps1" -ForegroundColor White
    exit 1
}

# Step 4: APIエンドポイントのテスト
Write-Step "4/5" "APIエンドポイントをテストしています..."

$BaseUrl = "http://localhost:8001"
$AllPassed = $true

$AllPassed = (Test-Endpoint "Health Check" "$BaseUrl/health") -and $AllPassed
$AllPassed = (Test-Endpoint "API Health" "$BaseUrl/api/v1/health") -and $AllPassed
$AllPassed = (Test-Endpoint "API Status" "$BaseUrl/api/v1/status") -and $AllPassed
$AllPassed = (Test-Endpoint "Dashboard Summary" "$BaseUrl/api/v1/dashboard/summary?fiscal_year=2024") -and $AllPassed
$AllPassed = (Test-Endpoint "Dashboard KPI" "$BaseUrl/api/v1/dashboard/kpi?fiscal_year=2024") -and $AllPassed
$AllPassed = (Test-Endpoint "Benford Analysis" "$BaseUrl/api/v1/dashboard/benford?fiscal_year=2024") -and $AllPassed
$AllPassed = (Test-Endpoint "Batch Rules" "$BaseUrl/api/v1/batch/rules") -and $AllPassed
$AllPassed = (Test-Endpoint "Report Templates" "$BaseUrl/api/v1/reports/templates") -and $AllPassed

# Step 5: 結果サマリー
Write-Step "5/5" "デモ結果サマリー"

if ($AllPassed) {
    Write-Host ""
    Write-Host "  ★ 全てのテストが成功しました！" -ForegroundColor Green
    Write-Host ""
    Write-Host "  次のステップ:" -ForegroundColor Cyan
    Write-Host "  1. ブラウザで Swagger UI を開く:" -ForegroundColor White
    Write-Host "     http://localhost:8001/docs" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  2. フロントエンドを起動する:" -ForegroundColor White
    Write-Host "     .\scripts\start_frontend.ps1" -ForegroundColor Yellow
    Write-Host ""
    Write-Host "  3. サンプルデータをインポートする:" -ForegroundColor White
    Write-Host "     POST http://localhost:8001/api/v1/import/upload" -ForegroundColor Yellow
} else {
    Write-Host ""
    Write-Host "  一部のテストが失敗しました。" -ForegroundColor Yellow
    Write-Host "  ログを確認してください: backend/logs/" -ForegroundColor Gray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Magenta
Write-Host "  Demo Complete" -ForegroundColor Magenta
Write-Host "========================================" -ForegroundColor Magenta
