# JAIA テスト実行スクリプト
#
# 使用方法:
#   .\scripts\run_tests.ps1              # 全テスト実行
#   .\scripts\run_tests.ps1 -Unit        # ユニットテストのみ
#   .\scripts\run_tests.ps1 -Integration # 統合テストのみ
#   .\scripts\run_tests.ps1 -E2E         # E2Eテストのみ
#   .\scripts\run_tests.ps1 -Coverage    # カバレッジレポート付き

param(
    [switch]$Unit,
    [switch]$Integration,
    [switch]$E2E,
    [switch]$Coverage,
    [switch]$Verbose
)

$ErrorActionPreference = "Continue"

# スクリプトディレクトリを取得
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$BackendDir = Join-Path $ProjectRoot "backend"

Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  JAIA Test Runner" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""

# バックエンドディレクトリに移動
Set-Location $BackendDir

# 仮想環境を有効化
$VenvActivate = Join-Path $BackendDir "venv\Scripts\Activate.ps1"
if (Test-Path $VenvActivate) {
    Write-Host "仮想環境を有効化しています..." -ForegroundColor Yellow
    & $VenvActivate
} else {
    Write-Host "警告: 仮想環境が見つかりません。システムのPythonを使用します。" -ForegroundColor Yellow
}

# pytestの引数を構築
$PytestArgs = @()

# テストタイプの選択
if ($Unit) {
    $PytestArgs += "tests/test_rules.py"
    $PytestArgs += "tests/test_health.py"
    Write-Host "ユニットテストを実行します..." -ForegroundColor Green
} elseif ($Integration) {
    $PytestArgs += "tests/test_api_integration.py"
    Write-Host "統合テストを実行します..." -ForegroundColor Green
} elseif ($E2E) {
    $PytestArgs += "tests/test_e2e.py"
    Write-Host "E2Eテストを実行します..." -ForegroundColor Green
} else {
    $PytestArgs += "tests/"
    Write-Host "全テストを実行します..." -ForegroundColor Green
}

# オプション
if ($Coverage) {
    $PytestArgs += "--cov=app"
    $PytestArgs += "--cov-report=html"
    $PytestArgs += "--cov-report=term-missing"
    Write-Host "カバレッジレポートを生成します..." -ForegroundColor Yellow
}

if ($Verbose) {
    $PytestArgs += "-v"
    $PytestArgs += "-s"
} else {
    $PytestArgs += "-v"
}

# テスト実行
Write-Host ""
Write-Host "実行コマンド: python -m pytest $($PytestArgs -join ' ')" -ForegroundColor Gray
Write-Host ""

$StartTime = Get-Date
python -m pytest @PytestArgs
$ExitCode = $LASTEXITCODE
$EndTime = Get-Date
$Duration = $EndTime - $StartTime

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  テスト完了" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host ""
Write-Host "実行時間: $($Duration.TotalSeconds.ToString('F2')) 秒" -ForegroundColor White

if ($ExitCode -eq 0) {
    Write-Host "結果: 成功" -ForegroundColor Green
} else {
    Write-Host "結果: 失敗 (Exit Code: $ExitCode)" -ForegroundColor Red
}

if ($Coverage) {
    $CoverageReportPath = Join-Path $BackendDir "htmlcov\index.html"
    if (Test-Path $CoverageReportPath) {
        Write-Host ""
        Write-Host "カバレッジレポート: $CoverageReportPath" -ForegroundColor Cyan
    }
}

# 元のディレクトリに戻る
Set-Location $ProjectRoot

exit $ExitCode
