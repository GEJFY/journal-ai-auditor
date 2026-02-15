# JAIA ワンクリック起動スクリプト
# 使い方: .\start.ps1

$ErrorActionPreference = "Continue"
$ProjectRoot = Split-Path -Parent $MyInvocation.MyCommand.Path
$BackendDir = Join-Path $ProjectRoot "backend"
$FrontendDir = Join-Path $ProjectRoot "frontend"

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JAIA - Journal entry AI Analyzer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# ============================================
# 前提条件チェック
# ============================================
$ok = $true

# Python
try {
    $pyVer = python --version 2>&1
    Write-Host "  [OK] $pyVer" -ForegroundColor Green
} catch {
    Write-Host "  [NG] Python が見つかりません (3.11+ 必要)" -ForegroundColor Red
    $ok = $false
}

# Node.js
try {
    $nodeVer = node --version 2>&1
    Write-Host "  [OK] Node.js $nodeVer" -ForegroundColor Green
} catch {
    Write-Host "  [NG] Node.js が見つかりません (18+ 必要)" -ForegroundColor Red
    $ok = $false
}

# 仮想環境
$VenvActivate = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "  [OK] Python仮想環境" -ForegroundColor Green
} else {
    Write-Host "  [NG] 仮想環境がありません。初回セットアップを実行してください:" -ForegroundColor Red
    Write-Host "       .\scripts\setup.ps1" -ForegroundColor Yellow
    $ok = $false
}

# node_modules
$NodeModules = Join-Path $FrontendDir "node_modules"
if (Test-Path $NodeModules) {
    Write-Host "  [OK] npm packages" -ForegroundColor Green
} else {
    Write-Host "  [NG] npm packages がありません。初回セットアップを実行してください:" -ForegroundColor Red
    Write-Host "       .\scripts\setup.ps1" -ForegroundColor Yellow
    $ok = $false
}

# .env
$EnvFile = Join-Path $BackendDir ".env"
if (Test-Path $EnvFile) {
    Write-Host "  [OK] 環境設定ファイル (.env)" -ForegroundColor Green
} else {
    Write-Host "  [!!] .env ファイルがありません。テンプレートからコピーします..." -ForegroundColor Yellow
    Copy-Item (Join-Path $BackendDir ".env.example") $EnvFile
    Write-Host "       backend/.env を編集してAPIキーを設定してください" -ForegroundColor Yellow
}

if (-not $ok) {
    Write-Host ""
    Write-Host "  前提条件を満たしていません。上記を確認してください。" -ForegroundColor Red
    exit 1
}

Write-Host ""

# ============================================
# バックエンド起動
# ============================================
Write-Host "[1/2] バックエンドを起動しています..." -ForegroundColor Yellow
$BackendScript = Join-Path $ProjectRoot "scripts\start_backend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $BackendScript

Write-Host "  起動を待機中（5秒）..." -ForegroundColor Gray
Start-Sleep -Seconds 5

# ヘルスチェック
try {
    $health = Invoke-RestMethod -Uri "http://localhost:8090/health" -TimeoutSec 10
    Write-Host "  [OK] バックエンド起動確認: $($health.status)" -ForegroundColor Green
} catch {
    Write-Host "  [!!] バックエンドの応答待ち（起動に時間がかかっています）" -ForegroundColor Yellow
}

# ============================================
# フロントエンド起動
# ============================================
Write-Host "[2/2] フロントエンドを起動しています..." -ForegroundColor Yellow
$FrontendScript = Join-Path $ProjectRoot "scripts\start_frontend.ps1"
Start-Process powershell -ArgumentList "-NoExit", "-File", $FrontendScript

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  起動完了！" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "  バックエンド API:  http://localhost:8090" -ForegroundColor Cyan
Write-Host "  Swagger UI:        http://localhost:8090/docs" -ForegroundColor Cyan
Write-Host "  フロントエンド:    http://localhost:5290" -ForegroundColor Cyan
Write-Host ""
Write-Host "  Electron ウィンドウが自動で開きます。" -ForegroundColor White
Write-Host "  開かない場合は http://localhost:5290 をブラウザで開いてください。" -ForegroundColor Gray
Write-Host ""
Write-Host "  終了するには、開いた各ターミナルウィンドウを閉じてください。" -ForegroundColor Gray
Write-Host ""
