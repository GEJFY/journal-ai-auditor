# =============================================================================
# JAIA Azure AI Foundry セットアップスクリプト (Azure CLI版)
# =============================================================================
# Terraform不要 - Azure CLIのみでAzure AI Foundry Serviceを作成し、.envを自動設定
#
# 使用方法:
#   .\scripts\setup_azure.ps1
#   .\scripts\setup_azure.ps1 -Model "gpt-4o"          # 低コストモデル
#   .\scripts\setup_azure.ps1 -Location "eastus2"      # リージョン指定
#   .\scripts\setup_azure.ps1 -Destroy                 # リソース削除
# =============================================================================

param(
    [string]$Model = "gpt-5.2-chat",
    [string]$ModelVersion = "2025-12-11",
    [string]$Location = "eastus",
    [int]$Capacity = 10,
    [string]$Environment = "demo",
    [string]$AppName = "jaia",
    [switch]$Destroy
)

$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
if (-not $ProjectRoot) { $ProjectRoot = (Get-Location).Path }
$BackendEnv = Join-Path $ProjectRoot "backend\.env"
$RootEnv = Join-Path $ProjectRoot ".env"

# リソース名
$ResourceGroup = "rg-${AppName}-${Environment}"
$OpenAIName = "aoai-${AppName}-${Environment}"
$DeploymentName = "${Model}-deployment"

Write-Host ""
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host "  JAIA Azure AI Foundry Setup (Azure CLI)" -ForegroundColor Cyan
Write-Host "=================================================================" -ForegroundColor Cyan
Write-Host ""

# -----------------------------------------------------------------
# Step 0: Azure CLI存在確認
# -----------------------------------------------------------------
Write-Host "[Step 0] Prerequisites check..." -ForegroundColor Yellow

$azPath = Get-Command az -ErrorAction SilentlyContinue
if ($azPath) {
    Write-Host "  Azure CLI: OK" -ForegroundColor Green
} else {
    Write-Host "  ERROR: Azure CLI not found." -ForegroundColor Red
    Write-Host "  Install: https://aka.ms/installazurecliwindows" -ForegroundColor Yellow
    exit 1
}

# -----------------------------------------------------------------
# Step 1: Azure Login
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[Step 1] Azure authentication..." -ForegroundColor Yellow
Write-Host "  Clearing cached credentials..." -ForegroundColor Gray
Remove-Item "C:\Users\goyos\.azure\msal_token_cache.json" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\goyos\.azure\msal_token_cache.bin" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\goyos\.azure\msal_http_cache.bin" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\goyos\.azure\accessTokens.json" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\goyos\.azure\azureProfile.json" -Force -ErrorAction SilentlyContinue
Remove-Item "C:\Users\goyos\.azure\service_principal_entries.bin" -Force -ErrorAction SilentlyContinue
Write-Host "  Done." -ForegroundColor Gray

Write-Host "  Please follow the device code instructions below:" -ForegroundColor Yellow
Write-Host ""
az login --use-device-code
if ($LASTEXITCODE -ne 0) {
    Write-Host "  ERROR: Azure login failed." -ForegroundColor Red
    exit 1
}

$account = az account show --output json | ConvertFrom-Json
Write-Host "  Logged in: $($account.user.name)" -ForegroundColor Green
Write-Host "  Subscription: $($account.name)" -ForegroundColor Green

# -----------------------------------------------------------------
# Step 2: Destroy (if requested)
# -----------------------------------------------------------------
if ($Destroy) {
    Write-Host ""
    Write-Host "[Destroy] Removing resource group: $ResourceGroup" -ForegroundColor Red
    $confirm = Read-Host "  Are you sure? (yes/no)"
    if ($confirm -eq "yes") {
        az group delete --name $ResourceGroup --yes --no-wait
        Write-Host "  Deletion started (background). Check Azure Portal for status." -ForegroundColor Green
    } else {
        Write-Host "  Cancelled." -ForegroundColor Yellow
    }
    exit 0
}

# -----------------------------------------------------------------
# Step 3: Create Resource Group
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[Step 2] Creating resources..." -ForegroundColor Yellow
Write-Host "  Resource Group: $ResourceGroup" -ForegroundColor White
Write-Host "  Location:       $Location" -ForegroundColor White
Write-Host "  Model:          $Model ($ModelVersion)" -ForegroundColor White
Write-Host "  Capacity:       ${Capacity}K TPM" -ForegroundColor White
Write-Host ""

# リソースグループ
Write-Host "  [2a] Resource Group..." -ForegroundColor Gray
$existingRg = az group show --name $ResourceGroup --output json 2>$null | ConvertFrom-Json
if ($existingRg) {
    Write-Host "    Already exists: $ResourceGroup" -ForegroundColor Yellow
} else {
    az group create `
        --name $ResourceGroup `
        --location $Location `
        --tags Application=JAIA Environment=$Environment ManagedBy=AzureCLI `
        --output none
    Write-Host "    Created: $ResourceGroup" -ForegroundColor Green
}

# -----------------------------------------------------------------
# Step 4: Create Azure OpenAI Service
# -----------------------------------------------------------------
Write-Host "  [2b] Azure OpenAI Service..." -ForegroundColor Gray
$existingAoai = az cognitiveservices account show `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --output json 2>$null | ConvertFrom-Json

if ($existingAoai) {
    Write-Host "    Already exists: $OpenAIName" -ForegroundColor Yellow
} else {
    az cognitiveservices account create `
        --name $OpenAIName `
        --resource-group $ResourceGroup `
        --location $Location `
        --kind OpenAI `
        --sku S0 `
        --custom-domain $OpenAIName `
        --output none
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ERROR: Failed to create Azure OpenAI Service." -ForegroundColor Red
        Write-Host "    Check: Azure OpenAI access may need to be requested at https://aka.ms/oai/access" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "    Created: $OpenAIName" -ForegroundColor Green
}

# -----------------------------------------------------------------
# Step 5: Deploy Model
# -----------------------------------------------------------------
Write-Host "  [2c] Model Deployment ($Model)..." -ForegroundColor Gray
$existingDeploy = az cognitiveservices account deployment show `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --deployment-name $DeploymentName `
    --output json 2>$null | ConvertFrom-Json

if ($existingDeploy) {
    Write-Host "    Already exists: $DeploymentName" -ForegroundColor Yellow
} else {
    az cognitiveservices account deployment create `
        --name $OpenAIName `
        --resource-group $ResourceGroup `
        --deployment-name $DeploymentName `
        --model-name $Model `
        --model-version $ModelVersion `
        --model-format OpenAI `
        --sku-name "GlobalStandard" `
        --sku-capacity $Capacity `
        --output none
    if ($LASTEXITCODE -ne 0) {
        Write-Host "    ERROR: Model deployment failed." -ForegroundColor Red
        Write-Host "    The model '$Model' may not be available in '$Location'." -ForegroundColor Yellow
        Write-Host "    Try: .\scripts\setup_azure.ps1 -Model 'gpt-4o' -ModelVersion '2024-11-20'" -ForegroundColor Yellow
        exit 1
    }
    Write-Host "    Created: $DeploymentName" -ForegroundColor Green
}

Write-Host ""
Write-Host "  All Azure resources created!" -ForegroundColor Green

# -----------------------------------------------------------------
# Step 6: Get Endpoint and Key
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[Step 3] Retrieving credentials..." -ForegroundColor Yellow

$endpoint = (az cognitiveservices account show `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --query "properties.endpoint" `
    --output tsv).Trim()

$apiKey = (az cognitiveservices account keys list `
    --name $OpenAIName `
    --resource-group $ResourceGroup `
    --query "key1" `
    --output tsv).Trim()

if (-not $endpoint -or -not $apiKey) {
    Write-Host "  ERROR: Could not retrieve endpoint/key." -ForegroundColor Red
    exit 1
}

Write-Host "  Endpoint:   $endpoint" -ForegroundColor Green
Write-Host "  Deployment: $DeploymentName" -ForegroundColor Green
Write-Host "  API Key:    ****$($apiKey.Substring([Math]::Max(0, $apiKey.Length - 4)))" -ForegroundColor Green

# -----------------------------------------------------------------
# Step 7: Update backend/.env
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[Step 4] Updating backend/.env..." -ForegroundColor Yellow

$updates = @{
    "LLM_PROVIDER"              = "azure_foundry"
    "LLM_MODEL"                 = $Model
    "AZURE_FOUNDRY_ENDPOINT"    = $endpoint
    "AZURE_FOUNDRY_API_KEY"     = $apiKey
    "AZURE_FOUNDRY_DEPLOYMENT"  = $DeploymentName
    "AZURE_FOUNDRY_API_VERSION" = "2024-10-21"
}

if (Test-Path $BackendEnv) {
    $envContent = Get-Content $BackendEnv -Raw -Encoding UTF8

    foreach ($key in $updates.Keys) {
        $value = $updates[$key]
        if ($envContent -match "(?m)^#?\s*${key}=.*$") {
            $envContent = $envContent -replace "(?m)^#?\s*${key}=.*$", "${key}=${value}"
        } else {
            $envContent += "`n${key}=${value}"
        }
    }

    Set-Content -Path $BackendEnv -Value $envContent.TrimEnd() -Encoding UTF8 -NoNewline
    Write-Host "  Updated: $BackendEnv" -ForegroundColor Green
} else {
    $exampleEnv = Join-Path $ProjectRoot "backend\.env.example"
    if (Test-Path $exampleEnv) {
        Copy-Item $exampleEnv $BackendEnv
        $envContent = Get-Content $BackendEnv -Raw -Encoding UTF8

        foreach ($key in $updates.Keys) {
            $value = $updates[$key]
            $envContent = $envContent -replace "(?m)^#?\s*${key}=.*$", "${key}=${value}"
        }

        Set-Content -Path $BackendEnv -Value $envContent.TrimEnd() -Encoding UTF8 -NoNewline
        Write-Host "  Created: $BackendEnv" -ForegroundColor Green
    } else {
        # 直接作成
        $envLines = $updates.GetEnumerator() | ForEach-Object { "$($_.Key)=$($_.Value)" }
        Set-Content -Path $BackendEnv -Value ($envLines -join "`n") -Encoding UTF8 -NoNewline
        Write-Host "  Created (minimal): $BackendEnv" -ForegroundColor Green
    }
}

# ルート.envも更新
if (Test-Path $RootEnv) {
    $rootContent = Get-Content $RootEnv -Raw -Encoding UTF8
    foreach ($key in @("LLM_PROVIDER", "LLM_MODEL", "AZURE_FOUNDRY_ENDPOINT", "AZURE_FOUNDRY_DEPLOYMENT")) {
        $value = $updates[$key]
        if ($rootContent -match "(?m)^#?\s*${key}=.*$") {
            $rootContent = $rootContent -replace "(?m)^#?\s*${key}=.*$", "${key}=${value}"
        }
    }
    Set-Content -Path $RootEnv -Value $rootContent.TrimEnd() -Encoding UTF8 -NoNewline
    Write-Host "  Updated: $RootEnv" -ForegroundColor Green
}

# -----------------------------------------------------------------
# Step 8: Verify
# -----------------------------------------------------------------
Write-Host ""
Write-Host "[Step 5] Configuration summary..." -ForegroundColor Yellow

$verifyContent = Get-Content $BackendEnv -Encoding UTF8
$verifyLines = $verifyContent | Where-Object { $_ -match "^(LLM_PROVIDER|LLM_MODEL|AZURE_FOUNDRY)" }
foreach ($line in $verifyLines) {
    if ($line -match "API_KEY") {
        Write-Host "  $($line.Split('=')[0])=****" -ForegroundColor Gray
    } else {
        Write-Host "  $line" -ForegroundColor Gray
    }
}

# -----------------------------------------------------------------
# Done
# -----------------------------------------------------------------
Write-Host ""
Write-Host "=================================================================" -ForegroundColor Green
Write-Host "  Setup Complete!" -ForegroundColor Green
Write-Host "=================================================================" -ForegroundColor Green
Write-Host ""
Write-Host "  Next steps:" -ForegroundColor White
Write-Host "    1. Start backend:  .\scripts\start_backend.ps1" -ForegroundColor White
Write-Host "    2. Start frontend: .\scripts\start_frontend.ps1" -ForegroundColor White
Write-Host "    3. Run demo:       .\scripts\demo.ps1" -ForegroundColor White
Write-Host ""
Write-Host "  To destroy resources:" -ForegroundColor Gray
Write-Host "    .\scripts\setup_azure.ps1 -Destroy" -ForegroundColor Gray
Write-Host ""
Write-Host "  Monthly cost estimate (demo usage):" -ForegroundColor Gray
Write-Host "    gpt-5.2-chat (10K TPM):  ~`$20-50/month" -ForegroundColor Gray
Write-Host "    gpt-4o (10K TPM):        ~`$15-30/month" -ForegroundColor Gray
Write-Host ""
