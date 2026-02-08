# JAIA インフラストラクチャ

JAIAのクラウドインフラストラクチャをTerraformで管理します。

## ディレクトリ構造

```
infrastructure/
├── terraform/
│   ├── aws/          # AWS構成（ECS, Bedrock）
│   ├── azure/        # Azure構成（Container Apps, OpenAI）
│   ├── gcp/          # GCP構成（Cloud Run, Vertex AI）
│   └── modules/      # 共通モジュール
│       └── vpc/      # VPCモジュール
└── README.md
```

## 前提条件

- Terraform >= 1.6.0
- 各クラウドのCLIツール
- 適切なIAM権限

## クイックスタート

### AWS

```bash
cd terraform/aws

# 変数ファイル作成
cat > terraform.tfvars <<EOF
aws_region  = "us-east-1"
environment = "development"
EOF

# 初期化と適用
terraform init
terraform apply
```

### Azure

```bash
cd terraform/azure

az login

cat > terraform.tfvars <<EOF
location    = "japaneast"
environment = "development"
EOF

terraform init
terraform apply
```

### GCP

```bash
cd terraform/gcp

gcloud auth application-default login

cat > terraform.tfvars <<EOF
project_id  = "your-project-id"
region      = "asia-northeast1"
environment = "development"
EOF

terraform init
terraform apply
```

## 環境変数

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| environment | 環境名 | development |
| app_name | アプリ名 | jaia |

### AWS固有

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| aws_region | AWSリージョン | us-east-1 |
| bedrock_model_id | Bedrockモデル | claude-sonnet-4-6-opus |

### Azure固有

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| location | Azureリージョン | japaneast |
| openai_model | OpenAIモデル | gpt-5-2 |

### GCP固有

| 変数 | 説明 | デフォルト |
|------|------|-----------|
| project_id | GCPプロジェクトID | 必須 |
| region | GCPリージョン | asia-northeast1 |
| gemini_model | Geminiモデル | gemini-3.0-flash-preview |

## リモートステート

本番環境ではリモートステートを使用することを推奨します。

### AWS

```hcl
terraform {
  backend "s3" {
    bucket         = "jaia-terraform-state"
    key            = "aws/terraform.tfstate"
    region         = "us-east-1"
    encrypt        = true
    dynamodb_table = "jaia-terraform-locks"
  }
}
```

### Azure

```hcl
terraform {
  backend "azurerm" {
    resource_group_name  = "jaia-terraform-rg"
    storage_account_name = "jaiatfstate"
    container_name       = "tfstate"
    key                  = "azure/terraform.tfstate"
  }
}
```

### GCP

```hcl
terraform {
  backend "gcs" {
    bucket = "jaia-terraform-state"
    prefix = "gcp/terraform.tfstate"
  }
}
```

## 作成されるリソース

### AWS

- VPC、サブネット
- ECSクラスター
- ECRリポジトリ
- Application Load Balancer
- S3バケット
- Secrets Manager
- IAMロール（Bedrockアクセス）

### Azure

- リソースグループ
- Virtual Network
- Container App Environment
- Container Registry
- Azure OpenAI Service
- Key Vault
- Storage Account

### GCP

- VPCネットワーク
- Cloud Run サービス
- Artifact Registry
- Cloud Storage
- Secret Manager
- Service Account
- Cloud Armor（本番のみ）

## クリーンアップ

```bash
terraform destroy
```

**注意**: 本番環境では`prevent_destroy`が有効になっている場合があります。

## セキュリティ

- 全ストレージは暗号化済み
- プライベートサブネット使用
- セキュリティグループ/NSG設定済み
- シークレットはSecrets Manager/Key Vault/Secret Managerで管理
