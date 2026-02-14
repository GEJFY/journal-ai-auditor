# JAIA エンタープライズ運用・保守マニュアル

本ドキュメントは、JAIA (Journal AI Auditor) システムのエンタープライズ環境における
運用・保守に必要な全ての手順と知識を体系的にまとめた包括的マニュアルです。

---

## 目次

1. [システム概要とアーキテクチャ](#1-システム概要とアーキテクチャ)
2. [インフラストラクチャ管理（3クラウドプロバイダー）](#2-インフラストラクチャ管理3クラウドプロバイダー)
3. [CI/CD パイプライン運用](#3-cicd-パイプライン運用)
4. [セキュリティ運用](#4-セキュリティ運用)
5. [監視とアラート](#5-監視とアラート)
6. [インシデント対応手順](#6-インシデント対応手順)
7. [スケーリング戦略](#7-スケーリング戦略)
8. [バックアップとリカバリ](#8-バックアップとリカバリ)
9. [ログ管理とローテーション](#9-ログ管理とローテーション)
10. [パフォーマンスチューニング](#10-パフォーマンスチューニング)
11. [データベース保守](#11-データベース保守)
12. [LLM プロバイダーフェイルオーバーと切り替え](#12-llm-プロバイダーフェイルオーバーと切り替え)
13. [災害復旧計画（DR）](#13-災害復旧計画dr)
14. [トラブルシューティングガイド](#14-トラブルシューティングガイド)

---

## 1. システム概要とアーキテクチャ

### 1.1 システム構成

JAIAは仕訳データのAI監査を行うエンタープライズシステムです。以下のコンポーネントで構成されます。

| コンポーネント | 技術スタック | 説明 |
|---------------|-------------|------|
| バックエンド | FastAPI (Python 3.11) | REST API、仕訳分析エンジン |
| フロントエンド | Electron + React + TypeScript | デスクトップUI |
| 分析DB | DuckDB | OLAP用仕訳データ、集計テーブル（17種） |
| メタデータDB | SQLite | メタデータ、設定情報 |
| キャッシュ | Redis 7 (Alpine) | 本番環境スケーリング用 |
| Webサーバー | Nginx (Alpine) | 静的ファイル配信、リバースプロキシ |
| コンテナ | Docker (Multi-stage build) | 本番デプロイメント |
| IaC | Terraform >= 1.6.0 | 3クラウド対応インフラ管理 |
| CI/CD | GitHub Actions | ci.yml, deploy.yml, release.yml |

### 1.2 エンタープライズアーキテクチャ図

```
+-------------------------------------------------------------------+
|                         User Access                                |
|                             |                                      |
|  +----------------------------------------------------------+     |
|  |                    Load Balancer                           |     |
|  |               (ALB/Azure LB/Cloud LB)                     |     |
|  +----------------------------+------------------------------+     |
|                               |                                    |
|  +----------------------------v------------------------------+     |
|  |                Container Orchestration                     |     |
|  |              (ECS/Container Apps/Cloud Run)                |     |
|  |  +---------+  +---------+  +---------+                    |     |
|  |  |Backend 1|  |Backend 2|  |Backend N|  Auto-scaling      |     |
|  |  | :8001   |  | :8001   |  | :8001   |                    |     |
|  |  +----+----+  +----+----+  +----+----+                    |     |
|  |       |            |            |                          |     |
|  |  +----v------------v------------v----+                    |     |
|  |  |        Shared Volumes             |                    |     |
|  |  |  DuckDB (jaia.duckdb)             |                    |     |
|  |  |  SQLite (jaia_meta.db)            |                    |     |
|  |  +-----------------------------------+                    |     |
|  +-----------------------------------------------------------+     |
|                               |                                    |
|  +----------------------------v------------------------------+     |
|  |                    LLM Providers (8社対応)                  |     |
|  |  +---------+  +---------+  +---------+  +---------+       |     |
|  |  | Bedrock |  | Azure   |  | Vertex  |  |Anthropic|       |     |
|  |  |(Claude  |  |Foundry  |  |  AI     |  | (Direct)|       |     |
|  |  |Opus 4.6)|  |(GPT-5.2)|  |(Gemini) |  |         |       |     |
|  |  +---------+  +---------+  +---------+  +---------+       |     |
|  |  +---------+  +---------+  +---------+  +---------+       |     |
|  |  | OpenAI  |  |Google AI|  | Azure   |  | Ollama  |       |     |
|  |  |(Direct) |  | Studio  |  | OpenAI  |  | (Local) |       |     |
|  |  +---------+  +---------+  +---------+  +---------+       |     |
|  +-----------------------------------------------------------+     |
+-------------------------------------------------------------------+
```

### 1.3 環境構成

| 環境 | 用途 | SLA | 最小インスタンス | 最大インスタンス |
|------|------|-----|-----------------|-----------------|
| Development | 開発・テスト | - | 0-1 | 3 |
| Staging | 本番前検証 | 99% | 1 | 3 |
| Production | 本番運用 | 99.9% | 2 | 10 |

### 1.4 ネットワーク構成

| サービス | ポート | プロトコル | 説明 |
|----------|--------|----------|------|
| Backend API | 8001 | HTTP | FastAPI アプリケーション |
| Frontend | 80/443 | HTTP/HTTPS | Nginx 静的配信 |
| Redis | 6379 | TCP | キャッシュ（本番のみ） |
| DuckDB | - | ファイルI/O | 組み込みDB（ポート不要） |
| SQLite | - | ファイルI/O | 組み込みDB（ポート不要） |

---

## 2. インフラストラクチャ管理（3クラウドプロバイダー）

### 2.1 前提条件

以下のツールが必要です。

```bash
# 必要ツールとバージョン
terraform   >= 1.6.0
docker      >= 24.0
aws-cli     >= 2.x     # AWS利用時
az-cli      >= 2.x     # Azure利用時
gcloud-cli  >= 450.0   # GCP利用時
kubectl     (オプション)
gh          >= 2.x     # GitHub CLI
```

### 2.2 AWS環境構築 (ECS + Bedrock)

AWS環境はECSクラスター上でコンテナを実行し、LLMプロバイダーとしてBedrock (Claude Opus 4.6) を使用します。

#### 作成されるリソース一覧

| リソース | Terraform名 | 説明 |
|----------|-------------|------|
| VPC | module.vpc | 専用ネットワーク (10.0.0.0/16) |
| ECS Cluster | aws_ecs_cluster.main | コンテナオーケストレーション (Container Insights有効) |
| ECR | aws_ecr_repository.backend | コンテナレジストリ (プッシュ時スキャン有効) |
| ALB | aws_lb.main | アプリケーションロードバランサー |
| S3 | aws_s3_bucket.data | 監査データストレージ (バージョニング有効) |
| Secrets Manager | aws_secretsmanager_secret.app_secrets | APIキー管理 |
| IAM Role | aws_iam_role.ecs_task_role | Bedrock/S3 アクセス権限 |
| CloudWatch | aws_cloudwatch_log_group.app | ログ保持 (90日) |

#### デプロイ手順

```bash
# 1. ディレクトリ移動
cd infrastructure/terraform/aws

# 2. 変数ファイル作成
cat > terraform.tfvars <<EOF
aws_region       = "us-east-1"
environment      = "production"
app_name         = "jaia"
bedrock_model_id = "anthropic.claude-sonnet-4-6-opus-20260115-v1:0"
EOF

# 3. リモートステート設定（本番環境推奨）
# main.tf 内の backend "s3" ブロックのコメントを解除し、
# S3バケットとDynamoDBテーブルを事前に作成すること

# 4. 初期化
terraform init

# 5. プラン確認（必ず差分を確認すること）
terraform plan -out=tfplan

# 6. 適用
terraform apply tfplan

# 7. 出力値の確認
terraform output
# ecr_repository_url  = "123456789.dkr.ecr.us-east-1.amazonaws.com/jaia-backend"
# ecs_cluster_name    = "jaia-production"
# alb_dns_name        = "jaia-production-alb-xxxxx.us-east-1.elb.amazonaws.com"
```

#### ECRイメージライフサイクルポリシー

ECRリポジトリには自動クリーンアップが設定されています。最新10イメージが保持され、
それ以前のイメージは自動的に削除されます。

#### S3バケットセキュリティ設定

- パブリックアクセス完全ブロック (`block_public_acls`, `block_public_policy` 等)
- サーバーサイド暗号化 (AES256)
- バージョニング有効

### 2.3 Azure環境構築 (Container Apps + Azure Foundry)

Azure環境はContainer Appsでコンテナを実行し、Azure Foundry (GPT-5.2) を使用します。

#### 作成されるリソース一覧

| リソース | Terraform名 | 説明 |
|----------|-------------|------|
| Resource Group | azurerm_resource_group.main | リソースグループ |
| VNet | azurerm_virtual_network.main | 仮想ネットワーク (10.0.0.0/16) |
| Container App Environment | azurerm_container_app_environment.main | コンテナ実行環境 |
| Container Registry | azurerm_container_registry.main | コンテナレジストリ (本番: Premium) |
| Azure OpenAI | azurerm_cognitive_account.openai | GPT-5.2 デプロイメント |
| Key Vault | azurerm_key_vault.main | シークレット管理 |
| Storage Account | azurerm_storage_account.main | データ・レポート保存 (本番: GRS) |
| Log Analytics | azurerm_log_analytics_workspace.main | ログ分析 (90日保持) |

#### デプロイ手順

```bash
# 1. Azureログイン
az login

# 2. ディレクトリ移動
cd infrastructure/terraform/azure

# 3. 変数ファイル作成
cat > terraform.tfvars <<EOF
location     = "japaneast"
environment  = "production"
app_name     = "jaia"
openai_model = "gpt-5-2"
EOF

# 4. 初期化・適用
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

#### Azure固有のセキュリティ設定

- Key Vault: 本番環境では `purge_protection_enabled = true`
- Storage Account: 本番環境では `GRS` レプリケーション、ネットワークルールでサブネット制限
- Container Registry: 本番環境では `Premium` SKU
- OpenAI: 本番環境ではネットワークACLでデフォルト`Deny`

### 2.4 GCP環境構築 (Cloud Run + Vertex AI)

GCP環境はCloud Runでコンテナを実行し、Vertex AI (Gemini 3.0) を使用します。

#### 作成されるリソース一覧

| リソース | Terraform名 | 説明 |
|----------|-------------|------|
| VPC | google_compute_network.main | VPCネットワーク |
| Subnet | google_compute_subnetwork.main | サブネット (10.0.0.0/24) |
| VPC Connector | google_vpc_access_connector.main | Cloud Run VPC接続 |
| Artifact Registry | google_artifact_registry_repository.main | コンテナレジストリ |
| Cloud Run | google_cloud_run_v2_service.backend | コンテナサービス |
| Cloud Storage | google_storage_bucket.data / reports | データ・レポート保存 |
| Secret Manager | google_secret_manager_secret.* | APIキー管理 |
| Service Account | google_service_account.cloud_run | Cloud Run実行アカウント |
| Cloud Armor | google_compute_security_policy.waf | WAF (本番のみ) |

#### デプロイ手順

```bash
# 1. GCPログイン
gcloud auth application-default login

# 2. ディレクトリ移動
cd infrastructure/terraform/gcp

# 3. 変数ファイル作成
cat > terraform.tfvars <<EOF
project_id   = "your-project-id"
region       = "asia-northeast1"
environment  = "production"
gemini_model = "gemini-3.0-flash-preview"
EOF

# 4. 初期化・適用
terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

#### GCP Cloud Armor (WAF) ルール

本番環境では以下のWAFルールが自動適用されます。

| 優先度 | ルール | アクション |
|--------|--------|-----------|
| 1000 | SQLインジェクション検出 | deny(403) |
| 1001 | XSS攻撃検出 | deny(403) |
| 2000 | レート制限 (100req/60sec) | throttle/deny(429) |
| 2147483647 | デフォルト許可 | allow |

### 2.5 Terraformステート管理

#### リモートステート設定（本番環境必須）

各クラウドプロバイダーのbackendブロックを有効化してください。

```hcl
# AWS: S3 + DynamoDB (ロック)
backend "s3" {
  bucket         = "jaia-terraform-state"
  key            = "aws/terraform.tfstate"
  region         = "us-east-1"
  encrypt        = true
  dynamodb_table = "jaia-terraform-locks"
}

# Azure: Azure Blob Storage
backend "azurerm" {
  resource_group_name  = "jaia-terraform-rg"
  storage_account_name = "jaiatfstate"
  container_name       = "tfstate"
  key                  = "azure/terraform.tfstate"
}

# GCP: Cloud Storage
backend "gcs" {
  bucket = "jaia-terraform-state"
  prefix = "gcp/terraform.tfstate"
}
```

#### ステート管理のベストプラクティス

1. ステートファイルは必ず暗号化して保存
2. ステートロック機能を有効化（同時変更防止）
3. `terraform plan` の出力を必ずレビューしてから `apply` を実行
4. 本番環境への `apply` は手動承認フローを経由すること

---

## 3. CI/CD パイプライン運用

### 3.1 パイプライン構成

JAIAには3つのGitHub Actionsワークフローがあります。

```
+-------------+    +-------------+    +-------------+
|   Commit    |--->| CI Pipeline |--->|   Build     |
| (push/PR)   |    | (ci.yml)    |    | Check       |
+-------------+    +------+------+    +------+------+
                          |                   |
                          v                   v
                   +--------------+    +------+------+
                   | Security     |    | Docker      |
                   | Scan         |    | Build       |
                   +--------------+    +------+------+
                                              |
+-------------+    +-------------+    +------v------+
| Production  |<---| Staging     |<---| Deploy      |
| Deploy      |    | Deploy      |    | (deploy.yml)|
| (manual)    |    | (auto)      |    +-------------+
+-------------+    +-------------+

+-------------+    +-------------+
| Tag v*      |--->| Release     |
| (push)      |    | (release.yml|
+-------------+    +------+------+
                          |
               +----------+-----------+
               |                      |
        +------v------+       +------v------+
        | Windows     |       | macOS       |
        | Build       |       | Build       |
        +-------------+       +-------------+
```

### 3.2 CI パイプライン (ci.yml)

トリガー: `main`/`develop` ブランチへの push または PR

#### ジョブ構成と依存関係

| ジョブ名 | 依存 | 内容 |
|---------|------|------|
| backend-lint | - | ruff check/format、mypy 型チェック |
| backend-test | backend-lint | pytest + カバレッジ (Codecov) |
| frontend-lint | - | eslint、format check、TypeScript型チェック |
| frontend-test | frontend-lint | vitest + カバレッジ (Codecov) |
| build | backend-test, frontend-test | Ubuntu/Windows/macOS クロスプラットフォームビルド |
| backend-test-integration | backend-test | Ollama統合テスト (main pushのみ) |
| backend-test-cloud | - | クラウドプロバイダー統合テスト (手動のみ) |
| security-scan | - | Bandit + Safety セキュリティスキャン |
| docker-build | backend-test | Docker イメージビルドテスト |
| terraform-validate | - | AWS/Azure/GCP の Terraform検証 |
| ci-summary | 全ジョブ | パイプラインサマリー出力 |

#### 手動でクラウド統合テストを実行する

```bash
# GitHub CLIで workflow_dispatch を実行
gh workflow run ci.yml

# クラウド統合テストには以下のシークレットが必要:
# ANTHROPIC_API_KEY, OPENAI_API_KEY, GOOGLE_API_KEY
# AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION
# AZURE_FOUNDRY_API_KEY, AZURE_FOUNDRY_ENDPOINT
# GCP_PROJECT_ID
```

### 3.3 デプロイパイプライン (deploy.yml)

トリガー:
- `main` ブランチへの push (backend/** または infrastructure/** の変更時) → staging自動デプロイ
- 手動実行 (workflow_dispatch) → 環境・クラウド選択可能

#### デプロイフロー

1. **Setup**: 環境・クラウドプロバイダーの決定
2. **Build**: Docker Buildx でイメージビルド + アーティファクト保存
3. **Deploy**: 選択されたクラウドへのデプロイ
   - AWS: ECR push → Terraform apply → ECS service更新
   - Azure: ACR push → Terraform apply → Container App更新
   - GCP: Artifact Registry push → Terraform apply → Cloud Run デプロイ
4. **Verify**: ヘルスチェック (10回リトライ、10秒間隔)

#### 手動デプロイ

```bash
# Staging環境にAWSへデプロイ
gh workflow run deploy.yml \
  -f environment=staging \
  -f cloud_provider=aws

# Production環境にAzureへデプロイ
gh workflow run deploy.yml \
  -f environment=production \
  -f cloud_provider=azure

# Production環境にGCPへデプロイ
gh workflow run deploy.yml \
  -f environment=production \
  -f cloud_provider=gcp
```

#### 本番デプロイの安全策

- 本番環境へのデプロイは `workflow_dispatch` (手動実行) でのみ実行可能
- 自動 push トリガーでは staging のみにデプロイされる
- デプロイ後に自動ヘルスチェックが実行される

### 3.4 リリースパイプライン (release.yml)

トリガー: `v*` タグの push

#### リリースフロー

1. Windows/macOS 同時ビルド (Python 3.11 + Node.js 20)
2. Electronアプリのビルド
3. アーティファクトのアップロード
4. ドラフトGitHubリリースの作成

#### リリース手順

```bash
# 1. バージョンタグを作成
git tag v0.2.0

# 2. タグをpush（これによりrelease.ymlが起動）
git push origin v0.2.0

# 3. GitHub上でドラフトリリースを確認・公開
gh release list
gh release edit v0.2.0 --draft=false
```

### 3.5 GitHub Secrets設定一覧

#### 全プロバイダー共通

| シークレット名 | 説明 | 必須 |
|---------------|------|------|
| GITHUB_TOKEN | GitHub自動トークン | 自動 |

#### AWS用

| シークレット名 | 説明 |
|---------------|------|
| AWS_ACCESS_KEY_ID | AWSアクセスキーID |
| AWS_SECRET_ACCESS_KEY | AWSシークレットキー |
| AWS_REGION | AWSリージョン |
| AWS_DEPLOYMENT_URL | デプロイ先URL |

#### Azure用

| シークレット名 | 説明 |
|---------------|------|
| AZURE_CREDENTIALS | Azure認証情報（JSON） |
| AZURE_DEPLOYMENT_URL | デプロイ先URL |

#### GCP用

| シークレット名 | 説明 |
|---------------|------|
| GCP_CREDENTIALS | サービスアカウントJSON |
| GCP_PROJECT_ID | GCPプロジェクトID |
| GCP_DEPLOYMENT_URL | デプロイ先URL |

#### LLMプロバイダー用

| シークレット名 | 説明 |
|---------------|------|
| ANTHROPIC_API_KEY | Anthropic Direct API キー |
| OPENAI_API_KEY | OpenAI Direct API キー |
| GOOGLE_API_KEY | Google AI Studio API キー |
| AZURE_FOUNDRY_API_KEY | Azure Foundry API キー |
| AZURE_FOUNDRY_ENDPOINT | Azure Foundry エンドポイント |

---

## 4. セキュリティ運用

### 4.1 セキュリティアーキテクチャ

JAIAのセキュリティは6層のミドルウェアスタックで構成されています。
リクエストは以下の順序で処理されます。

```
リクエスト受信
    |
    v
[1] SecurityHeadersMiddleware  -- セキュリティヘッダー付与
    |
    v
[2] IPBlockMiddleware          -- IPブロックチェック
    |
    v
[3] RateLimitMiddleware        -- レート制限チェック
    |
    v
[4] SuspiciousActivityMiddleware -- 不正パターン検出
    |
    v
[5] RequestLoggingMiddleware   -- リクエストログ記録
    |
    v
[6] AuditLogMiddleware         -- 監査ログ記録
    |
    v
アプリケーション処理
```

### 4.2 レート制限

スライディングウィンドウ方式のレート制限が実装されています。

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| RATE_LIMIT_REQUESTS | 100 | ウィンドウ内の最大リクエスト数 |
| RATE_LIMIT_WINDOW_SECONDS | 60 | 時間ウィンドウ（秒） |

レスポンスヘッダーにレート制限情報が付与されます。

```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 95
Retry-After: 45  (制限超過時)
```

**ホワイトリストパス**（レート制限除外）:
- `/health`
- `/api/v1/health`
- `/docs`
- `/openapi.json`

### 4.3 IPブロック機能

#### 自動ブロック

不正なリクエストパターンが検出されると、違反カウンターが増加します。
閾値に達すると自動的に一時ブロックされます。

| 設定項目 | 値 | 説明 |
|---------|-----|------|
| TEMP_BLOCK_THRESHOLD | 10 | 一時ブロックまでの違反回数 |
| TEMP_BLOCK_DURATION_MINUTES | 15 | 一時ブロック期間（分） |

#### 手動ブロック管理

```python
# 永久ブロックの追加
from app.core.middleware import ip_block_manager
ip_block_manager.add_permanent_block("192.168.1.100")

# ブロック解除
ip_block_manager.remove_block("192.168.1.100")

# ブロック状態確認
is_blocked = ip_block_manager.is_blocked("192.168.1.100")
```

### 4.4 不正リクエスト検出パターン

以下のパターンがリクエストURL/クエリに含まれる場合、自動的にブロックされます。

| 攻撃タイプ | 検出パターン |
|-----------|-------------|
| ディレクトリトラバーサル | `../`, `..\` |
| XSS | `<script`, `</script>` |
| SQLインジェクション | `' OR `, `" OR ` |
| テンプレートインジェクション | `${`, `#{` |
| SSTI | `{{`, `}}` |

### 4.5 セキュリティヘッダー

全レスポンスに以下のセキュリティヘッダーが自動付与されます。

| ヘッダー | 値 | 目的 |
|---------|-----|------|
| X-Content-Type-Options | nosniff | MIMEタイプスニッフィング防止 |
| X-Frame-Options | DENY | クリックジャッキング防止 |
| X-XSS-Protection | 1; mode=block | XSSフィルター有効化 |
| Strict-Transport-Security | max-age=31536000; includeSubDomains | HTTPS強制 |
| Content-Security-Policy | default-src 'self'; ... | CSP |
| Referrer-Policy | strict-origin-when-cross-origin | リファラー制限 |
| Permissions-Policy | geolocation=(), microphone=(), camera=() | 機能制限 |

### 4.6 CORS設定

```python
# 許可オリジン
allow_origins = ["http://localhost:5180", "http://127.0.0.1:5180"]
allow_methods = ["GET", "POST", "PUT", "DELETE", "OPTIONS"]
allow_headers = ["*"]
allow_credentials = True
```

本番環境では `allow_origins` を実際のドメインに変更してください。

### 4.7 APIキーローテーション手順

#### AWS Secrets Manager

```bash
# 1. 現在のシークレット確認
aws secretsmanager get-secret-value \
  --secret-id jaia/production/secrets \
  --query 'SecretString' --output text | jq .

# 2. 新しいキーを生成（各プロバイダーの管理画面で実施）

# 3. Secrets Managerを更新
aws secretsmanager put-secret-value \
  --secret-id jaia/production/secrets \
  --secret-string '{
    "ANTHROPIC_API_KEY": "sk-ant-新しいキー",
    "OPENAI_API_KEY": "sk-proj-新しいキー",
    "GOOGLE_API_KEY": "AIzaSy新しいキー"
  }'

# 4. ECSサービスを再起動して新キーを適用
aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --force-new-deployment

# 5. ヘルスチェックで正常動作を確認
curl -s https://your-domain/health | jq .

# 6. 古いキーを無効化（各プロバイダーの管理画面で実施）
```

#### Azure Key Vault

```bash
# 1. Key Vaultにシークレットを設定
az keyvault secret set \
  --vault-name kv-jaia-production \
  --name ANTHROPIC-API-KEY \
  --value "sk-ant-新しいキー"

# 2. Container Appを更新
az containerapp update \
  --name ca-jaia-backend \
  --resource-group rg-jaia-production
```

#### GCP Secret Manager

```bash
# 1. 新しいバージョンを作成
echo -n "新しいキー" | gcloud secrets versions add \
  jaia-production-anthropic-api-key \
  --data-file=-

# 2. Cloud Runを再デプロイ
gcloud run services update jaia-backend \
  --region asia-northeast1
```

### 4.8 セキュリティ監査チェックリスト（月次）

- [ ] Bandit/Safetyスキャン結果のレビュー
- [ ] セキュリティログ (`jaia_security.log`) の異常パターン確認
- [ ] ブロックIPリストのレビュー
- [ ] APIキーの有効期限確認
- [ ] 依存パッケージの脆弱性チェック
- [ ] CORS設定の妥当性確認
- [ ] CloudTrail/Activity Log/Audit Logの確認

---

## 5. 監視とアラート

### 5.1 ヘルスチェックエンドポイント

| エンドポイント | レスポンス | 用途 |
|--------------|-----------|------|
| `/health` | `{"status": "healthy", "app": "JAIA", "version": "0.2.0"}` | ALB/LBヘルスチェック |
| `/api/v1/status` | DuckDB/SQLite接続状態、仕訳件数 | 詳細ステータス確認 |

#### Docker ヘルスチェック設定

```dockerfile
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8001/health || exit 1
```

#### ALBヘルスチェック設定 (AWS)

```hcl
health_check {
  enabled             = true
  healthy_threshold   = 2
  interval            = 30
  matcher             = "200"
  path                = "/api/v1/health"
  port                = "traffic-port"
  timeout             = 5
  unhealthy_threshold = 3
}
```

### 5.2 ログファイル構成

```
logs/
├── jaia.log              # メインアプリケーションログ
│                          #   RotatingFileHandler: 10MB x 10世代
│                          #   フォーマット: JSON構造化ログ
│
├── jaia_error.log        # エラー専用ログ (ERROR以上)
│                          #   RotatingFileHandler: 10MB x 10世代
│
├── jaia_audit.log        # 監査ログ
│                          #   TimedRotatingFileHandler: 日次ローテーション
│                          #   保持期間: 90日
│                          #   対象: /api/v1/import, /batch, /analysis, /reports, /agents, /settings
│
├── jaia_performance.log  # パフォーマンスログ
│                          #   RotatingFileHandler: 50MB x 5世代
│                          #   記録: HTTPメソッド, パス, ステータスコード, 処理時間(ms)
│
└── jaia_security.log     # セキュリティイベントログ
                           #   TimedRotatingFileHandler: 日次ローテーション
                           #   保持期間: 365日（コンプライアンス対応）
                           #   記録: レート制限超過, 不正リクエスト, IPブロック
```

### 5.3 ログフォーマット（JSON構造化ログ）

```json
{
  "timestamp": "2026-02-14T10:30:00.000Z",
  "level": "INFO",
  "logger": "app.core.middleware",
  "message": "リクエスト完了: GET /api/v1/status -> 200",
  "request_id": "a1b2c3d4",
  "module": "middleware",
  "function": "dispatch",
  "line": 535,
  "method": "GET",
  "path": "/api/v1/status",
  "status_code": 200,
  "duration_ms": 45.23,
  "client_ip": "10.0.1.50"
}
```

### 5.4 機密データマスキング

ログ出力時に以下のパターンが自動マスキングされます。

| パターン | マスキング例 |
|---------|-------------|
| `sk-ant-api03-xxx...` | `sk-ant-***MASKED***` |
| `sk-proj-xxx...` | `sk-proj-***MASKED***` |
| `AKIA...` (AWS Access Key) | `AKIA***MASKED***` |
| `AIzaSy...` (Google API Key) | `AIzaSy***MASKED***` |
| `password=xxx` | `password=***MASKED***` |
| `secret=xxx` | `secret=***MASKED***` |
| `token=xxx` | `token=***MASKED***` |

### 5.5 監視すべきメトリクス

| メトリクス | 閾値 | アラートレベル | 対応 |
|-----------|------|---------------|------|
| エラー率 (5xx) | > 1% | Critical | 即時調査 |
| レスポンス時間 (P95) | > 5秒 | Warning | パフォーマンス調査 |
| CPU使用率 | > 80% | Warning | スケールアウト検討 |
| メモリ使用率 | > 85% | Warning | メモリリーク調査 |
| LLM APIエラー率 | > 5% | Critical | プロバイダー切り替え検討 |
| ディスク使用率 | > 90% | Critical | ログクリーンアップ |
| DuckDBファイルサイズ | > 10GB | Warning | データアーカイブ検討 |
| レート制限超過回数 | > 100/時 | Warning | 攻撃の可能性調査 |
| IPブロック件数 | > 10/時 | Warning | セキュリティインシデント調査 |

### 5.6 CloudWatch設定例 (AWS)

```json
{
  "AlarmName": "JAIA-HighErrorRate",
  "MetricName": "5XXError",
  "Namespace": "AWS/ApplicationELB",
  "Statistic": "Sum",
  "Period": 60,
  "EvaluationPeriods": 5,
  "Threshold": 10,
  "ComparisonOperator": "GreaterThanThreshold",
  "AlarmActions": ["arn:aws:sns:us-east-1:123456789:jaia-alerts"]
}
```

### 5.7 Azure Monitor設定例

```bash
# Log Analytics クエリ例: エラー率監視
az monitor log-analytics query \
  --workspace log-jaia-production \
  --analytics-query "
    ContainerAppConsoleLogs_CL
    | where TimeGenerated > ago(5m)
    | where Log_s contains 'ERROR'
    | summarize ErrorCount=count() by bin(TimeGenerated, 1m)
    | where ErrorCount > 10
  "
```

### 5.8 GCP Cloud Monitoring設定例

```bash
# Cloud Run メトリクスの確認
gcloud monitoring metrics list \
  --filter="metric.type = starts_with(\"run.googleapis.com\")"

# アラートポリシー作成例
gcloud alpha monitoring policies create \
  --display-name="JAIA High Error Rate" \
  --condition-display-name="5xx Error Rate" \
  --condition-filter="resource.type=\"cloud_run_revision\" AND metric.type=\"run.googleapis.com/request_count\" AND metric.labels.response_code_class=\"5xx\""
```

---

## 6. インシデント対応手順

### 6.1 インシデントレベル定義

| レベル | 定義 | 初動対応時間 | 解決目標時間 | エスカレーション |
|--------|------|-------------|-------------|----------------|
| P1 (Critical) | サービス全停止 | 15分以内 | 1時間 | 即座に管理者通知 |
| P2 (High) | 主要機能障害 | 30分以内 | 4時間 | 1時間で管理者通知 |
| P3 (Medium) | 一部機能障害 | 2時間以内 | 1営業日 | 4時間で管理者通知 |
| P4 (Low) | 軽微な問題 | 翌営業日 | 1週間 | 週次レポート |

### 6.2 インシデント対応フロー

```
検知 -> 初動確認 -> レベル判定 -> 対応チーム召集
  |                                    |
  v                                    v
ログ確認                          復旧作業開始
  |                                    |
  v                                    v
根本原因分析                      ロールバック判断
  |                                    |
  v                                    v
暫定対策実施                      復旧確認
  |                                    |
  v                                    v
恒久対策策定                      ポストモーテム作成
```

### 6.3 ロールバック手順

#### AWS ECS

```bash
# 1. 現在のタスク定義リビジョンを確認
aws ecs describe-services \
  --cluster jaia-production \
  --services jaia-backend \
  --query 'services[0].taskDefinition'

# 2. 前リビジョン一覧を確認
aws ecs list-task-definitions \
  --family-prefix jaia-backend \
  --sort DESC \
  --max-items 5

# 3. 前バージョンにロールバック
aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --task-definition jaia-backend:<前のリビジョン番号>

# 4. デプロイ状態を監視
aws ecs wait services-stable \
  --cluster jaia-production \
  --services jaia-backend

# 5. ヘルスチェック確認
curl -s https://your-domain/health | jq .
curl -s https://your-domain/api/v1/status | jq .
```

#### Azure Container Apps

```bash
# 1. リビジョン一覧を確認
az containerapp revision list \
  --name ca-jaia-backend \
  --resource-group rg-jaia-production \
  --output table

# 2. 前リビジョンにトラフィックを切り替え
az containerapp ingress traffic set \
  --name ca-jaia-backend \
  --resource-group rg-jaia-production \
  --revision-weight <前のリビジョン名>=100
```

#### GCP Cloud Run

```bash
# 1. リビジョン一覧を確認
gcloud run revisions list \
  --service jaia-backend \
  --region asia-northeast1

# 2. 前リビジョンにトラフィックを切り替え
gcloud run services update-traffic jaia-backend \
  --region asia-northeast1 \
  --to-revisions=<前のリビジョン名>=100
```

### 6.4 復旧確認チェックリスト

- [ ] `/health` エンドポイントが200を返す
- [ ] `/api/v1/status` でDuckDB/SQLiteが healthy
- [ ] エラーログに新規エラーが出ていない
- [ ] LLM API呼び出しが正常に動作する
- [ ] パフォーマンスログのレスポンス時間が正常範囲
- [ ] セキュリティログに異常がない

---

## 7. スケーリング戦略

### 7.1 オートスケーリング設定

#### AWS ECS

```hcl
resource "aws_appautoscaling_target" "ecs" {
  max_capacity       = 10
  min_capacity       = 2
  resource_id        = "service/jaia-production/jaia-backend"
  scalable_dimension = "ecs:service:DesiredCount"
  service_namespace  = "ecs"
}

resource "aws_appautoscaling_policy" "cpu" {
  name               = "cpu-scaling"
  policy_type        = "TargetTrackingScaling"
  resource_id        = aws_appautoscaling_target.ecs.resource_id
  scalable_dimension = aws_appautoscaling_target.ecs.scalable_dimension
  service_namespace  = aws_appautoscaling_target.ecs.service_namespace

  target_tracking_scaling_policy_configuration {
    predefined_metric_specification {
      predefined_metric_type = "ECSServiceAverageCPUUtilization"
    }
    target_value = 70.0
  }
}
```

#### Azure Container Apps

Terraform設定では環境に応じたレプリカ数が自動設定されます。

```hcl
# Production: min=2, max=10
# Development/Staging: min=1(or 0), max=3
min_replicas = var.environment == "production" ? 2 : 1
max_replicas = var.environment == "production" ? 10 : 3
```

#### GCP Cloud Run

```hcl
scaling {
  min_instance_count = var.environment == "production" ? 2 : 0
  max_instance_count = var.environment == "production" ? 10 : 3
}
```

### 7.2 手動スケーリング

```bash
# --- AWS ECS ---
# スケールアウト
aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --desired-count 5

# スケールイン
aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --desired-count 2

# --- Azure Container Apps ---
az containerapp update \
  --name ca-jaia-backend \
  --resource-group rg-jaia-production \
  --min-replicas 3 \
  --max-replicas 8

# --- GCP Cloud Run ---
gcloud run services update jaia-backend \
  --region asia-northeast1 \
  --min-instances 3 \
  --max-instances 8
```

### 7.3 スケーリング指針

| 状況 | 推奨アクション | 目安 |
|------|--------------|------|
| 月末・四半期末の仕訳集中 | 事前にスケールアウト | 通常の2-3倍 |
| 監査期間中 | 最大インスタンス数を引き上げ | max=15-20 |
| 夜間・休日 | スケールイン | min=1 (本番) |
| 大量データインポート | 一時的にスケールアウト | 処理完了後にスケールイン |
| LLMバッチ分析 | ワーカー数とバッチサイズを調整 | MAX_WORKERS=8, BATCH_SIZE=5000 |

---

## 8. バックアップとリカバリ

### 8.1 バックアップ対象

| 対象 | ファイル | 説明 | 重要度 |
|------|---------|------|--------|
| 仕訳データ | jaia.duckdb | OLAP分析用メインDB | 最重要 |
| メタデータ | jaia_meta.db | 設定・メタ情報 | 重要 |
| 監査ログ | jaia_audit.log | コンプライアンスログ | 重要 |
| セキュリティログ | jaia_security.log | セキュリティイベント | 重要 |
| Terraformステート | terraform.tfstate | インフラ状態 | 最重要 |

### 8.2 DuckDB バックアップ手順

```bash
# 方法1: ファイルコピー（サービス停止が必要）
# DuckDBはファイルベースDBのため、直接コピーで完全バックアップ可能

# サービス停止
docker-compose stop backend

# バックアップ作成
BACKUP_DATE=$(date +%Y%m%d_%H%M%S)
cp data/jaia.duckdb "backups/jaia_${BACKUP_DATE}.duckdb"

# サービス再開
docker-compose start backend

# 方法2: DuckDB EXPORT（サービス稼働中に可能）
python3 -c "
import duckdb
conn = duckdb.connect('data/jaia.duckdb', read_only=True)
conn.execute(\"EXPORT DATABASE 'backups/jaia_export_$(date +%Y%m%d)' (FORMAT PARQUET)\")
conn.close()
print('DuckDB export completed')
"

# 方法3: S3/Blob/GCSへのバックアップ
# AWS
aws s3 cp data/jaia.duckdb \
  "s3://jaia-production-backup/duckdb/jaia_${BACKUP_DATE}.duckdb"

# Azure
az storage blob upload \
  --account-name stjaiaproduction \
  --container-name jaia-backup \
  --name "duckdb/jaia_${BACKUP_DATE}.duckdb" \
  --file data/jaia.duckdb

# GCP
gsutil cp data/jaia.duckdb \
  "gs://project-jaia-production-backup/duckdb/jaia_${BACKUP_DATE}.duckdb"
```

### 8.3 SQLite バックアップ手順

```bash
# 方法1: sqlite3 .backup コマンド（オンラインバックアップ、推奨）
sqlite3 data/jaia_meta.db ".backup backups/jaia_meta_${BACKUP_DATE}.db"

# 方法2: ファイルコピー（WALモード考慮）
cp data/jaia_meta.db "backups/jaia_meta_${BACKUP_DATE}.db"
# WALファイルも忘れずにコピー
cp data/jaia_meta.db-wal "backups/jaia_meta_${BACKUP_DATE}.db-wal" 2>/dev/null || true
cp data/jaia_meta.db-shm "backups/jaia_meta_${BACKUP_DATE}.db-shm" 2>/dev/null || true
```

### 8.4 自動バックアップスケジュール（推奨）

```bash
# crontab設定例
# 毎日午前2時にDuckDBバックアップ
0 2 * * * /opt/jaia/scripts/backup_duckdb.sh

# 毎日午前3時にSQLiteバックアップ
0 3 * * * /opt/jaia/scripts/backup_sqlite.sh

# 毎週日曜午前4時にログアーカイブ
0 4 * * 0 /opt/jaia/scripts/archive_logs.sh

# 30日以前のバックアップを自動削除
0 5 * * * find /opt/jaia/backups -name "*.duckdb" -mtime +30 -delete
```

### 8.5 リストア手順

```bash
# DuckDB リストア
docker-compose stop backend
cp backups/jaia_20260214_020000.duckdb data/jaia.duckdb
docker-compose start backend

# DuckDB EXPORT からのリストア
python3 -c "
import duckdb
conn = duckdb.connect('data/jaia.duckdb')
conn.execute(\"IMPORT DATABASE 'backups/jaia_export_20260214'\")
conn.close()
print('DuckDB restore completed')
"

# SQLite リストア
docker-compose stop backend
cp backups/jaia_meta_20260214_030000.db data/jaia_meta.db
docker-compose start backend
```

### 8.6 バックアップ検証

月次でリストアテストを実施してください。

```bash
# テスト用DBにリストア
cp backups/jaia_20260214_020000.duckdb /tmp/test_restore.duckdb

# データ整合性チェック
python3 -c "
import duckdb
conn = duckdb.connect('/tmp/test_restore.duckdb', read_only=True)
count = conn.execute('SELECT COUNT(*) FROM journal_entries').fetchone()[0]
tables = conn.execute(\"SELECT table_name FROM information_schema.tables\").fetchall()
print(f'journal_entries: {count} rows')
print(f'Tables: {[t[0] for t in tables]}')
conn.close()
"

# テストファイル削除
rm /tmp/test_restore.duckdb
```

---

## 9. ログ管理とローテーション

### 9.1 ログローテーション設定

| ログファイル | 方式 | サイズ/間隔 | 保持世代 |
|-------------|------|-----------|---------|
| jaia.log | RotatingFileHandler | 10MB | 10世代 |
| jaia_error.log | RotatingFileHandler | 10MB | 10世代 |
| jaia_audit.log | TimedRotatingFileHandler | 日次 (midnight) | 90日 |
| jaia_performance.log | RotatingFileHandler | 50MB | 5世代 |
| jaia_security.log | TimedRotatingFileHandler | 日次 (midnight) | 365日 |

### 9.2 ログレベル設定

```bash
# 環境変数で制御
LOG_LEVEL=INFO     # 本番環境（推奨）
LOG_LEVEL=DEBUG    # 開発環境、トラブルシューティング時
LOG_LEVEL=WARNING  # 最小限のログ出力
```

#### サードパーティライブラリのログレベル

以下のライブラリは WARNING レベルに抑制されています。

- uvicorn / uvicorn.access
- httpx / httpcore
- langchain

### 9.3 ログ出力フォーマット

| 環境 | フォーマット | 特徴 |
|------|-----------|------|
| 開発 (DEBUG=true) | ColoredFormatter | ANSIカラー出力、可読性重視 |
| 本番 (DEBUG=false) | JSONFormatter | 構造化JSON、ログ集約サービス連携 |

### 9.4 クラウドログ統合

#### AWS CloudWatch Logs

ECSタスクのログはCloudWatch Logsに自動転送されます。

```bash
# ログ閲覧
aws logs tail "/ecs/jaia-production/app" --follow

# ログ検索
aws logs filter-log-events \
  --log-group-name "/ecs/jaia-production/app" \
  --filter-pattern "ERROR" \
  --start-time $(date -d '-1 hour' +%s000)
```

#### Azure Log Analytics

Container Appsのログは Log Analytics に自動転送されます。

```bash
# Kusto クエリでログ検索
az monitor log-analytics query \
  --workspace log-jaia-production \
  --analytics-query "
    ContainerAppConsoleLogs_CL
    | where TimeGenerated > ago(1h)
    | where Log_s contains 'ERROR'
    | project TimeGenerated, Log_s
    | order by TimeGenerated desc
  "
```

#### GCP Cloud Logging

Cloud Runのログは Cloud Logging に自動転送されます。

```bash
# ログ閲覧
gcloud logging read \
  "resource.type=cloud_run_revision AND resource.labels.service_name=jaia-backend AND severity>=ERROR" \
  --limit 50 \
  --format json
```

### 9.5 ログ容量管理

```bash
# 現在のログサイズ確認
du -sh logs/*

# 手動ログクリーンアップ（保持ポリシーに従って古いファイルを削除）
find logs/ -name "jaia.log.*" -mtime +30 -delete
find logs/ -name "jaia_error.log.*" -mtime +30 -delete
find logs/ -name "jaia_performance.log.*" -mtime +14 -delete

# 注意: jaia_audit.log と jaia_security.log はコンプライアンス要件のため
#       手動削除は行わないでください
```

---

## 10. パフォーマンスチューニング

### 10.1 アプリケーション設定

| 環境変数 | デフォルト値 | 説明 | チューニング指針 |
|---------|------------|------|----------------|
| BATCH_SIZE | 10000 | バッチ処理サイズ | メモリに余裕があれば20000-50000 |
| MAX_WORKERS | 4 | ワーカープロセス数 | CPUコア数に合わせて調整 |
| CACHE_TTL_SECONDS | 300 | キャッシュ有効期間(秒) | データ更新頻度に応じて調整 |
| LLM_REQUESTS_PER_MINUTE | 60 | LLM APIリクエスト/分 | プロバイダーのレート制限内に設定 |
| LLM_TOKENS_PER_MINUTE | 100000 | LLMトークン/分 | プロバイダーの制限内に設定 |

### 10.2 Uvicorn設定

```bash
# Dockerfile CMD
CMD ["python", "-m", "uvicorn", "app.main:app",
     "--host", "0.0.0.0",
     "--port", "8001",
     "--workers", "4"]

# 本番環境での推奨設定
# --workers: CPUコア数 x 2 + 1 (ただし最大8)
# --timeout-keep-alive: 65 (ALBのidle timeout + 5秒)
# --limit-concurrency: 100 (同時接続数上限)
```

### 10.3 DuckDB パフォーマンス設定

DuckDB接続時に以下の設定が適用されています。

```python
# 並列実行の有効化
conn.execute("SET threads TO 4")
```

#### 追加パフォーマンス設定（必要に応じて）

```sql
-- メモリ制限の調整（デフォルト: 利用可能メモリの80%）
SET memory_limit = '4GB';

-- ソート用一時ディレクトリの指定
SET temp_directory = '/tmp/duckdb_temp';

-- 並列スレッド数の調整
SET threads TO 8;

-- プログレスバーの無効化（バッチ処理時）
SET enable_progress_bar = false;
```

### 10.4 Dockerリソース制限

```yaml
# docker-compose.yml での設定例
services:
  backend:
    deploy:
      resources:
        limits:
          cpus: '2.0'
          memory: 4G
        reservations:
          cpus: '1.0'
          memory: 2G
```

#### クラウド環境でのリソース設定

| クラウド | CPU | メモリ | 設定場所 |
|---------|-----|--------|---------|
| AWS ECS | Task Definition | Task Definition | タスク定義JSON |
| Azure Container Apps | 1.0 CPU | 2Gi | Terraform template.container |
| GCP Cloud Run | 2 CPU | 2Gi | Terraform containers.resources |

### 10.5 パフォーマンス監視

```bash
# パフォーマンスログからスロークエリを抽出
# duration_msが5000ms以上のリクエストを検索
python3 -c "
import json
with open('logs/jaia_performance.log') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('duration_ms', 0) > 5000:
                print(f\"{data['timestamp']} {data['path']} {data['duration_ms']:.0f}ms\")
        except json.JSONDecodeError:
            pass
"
```

---

## 11. データベース保守

### 11.1 DuckDB テーブル構成

JAIAのDuckDBには以下のテーブルが存在します。

#### メインテーブル

| テーブル名 | 説明 |
|-----------|------|
| journal_entries | 仕訳明細データ（メインOLAPテーブル） |
| rule_violations | ルール違反レコード |

#### 集計テーブル（17種）

| # | テーブル名 | 説明 |
|---|-----------|------|
| 1 | agg_by_period_account | 期間 x 勘定科目 集計 |
| 2 | agg_by_date | 日次集計 |
| 3 | agg_by_user | ユーザー活動集計 |
| 4 | agg_by_department | 部門別集計 |
| 5 | agg_by_vendor | 取引先集計 |
| 6 | agg_high_risk | 高リスク仕訳集計 |
| 7 | agg_rule_violations | ルール違反集計 |
| 8 | agg_trend_mom | 前月比トレンド |
| 9 | agg_trend_yoy | 前年比トレンド |
| 10 | agg_benford_distribution | ベンフォード分布 |
| 11 | agg_amount_distribution | 金額分布 |
| 12 | agg_time_distribution | 時間帯分布 |
| 13 | agg_approval_patterns | 承認パターン集計 |
| 14 | agg_account_activity | 勘定科目活動集計 |
| 15 | agg_anomaly_summary | 異常検知サマリー |
| 16 | agg_ml_scores | MLスコア分布 |
| 17 | agg_dashboard_kpi | ダッシュボードKPI集計 |

### 11.2 集計テーブル更新

集計テーブルはデータインポートおよびルール実行後に更新されます。

```python
from app.services.aggregation import AggregationService

# 全集計テーブルを更新
agg_service = AggregationService()
results = agg_service.update_all()

# 特定年度のみ更新
results = agg_service.update_all(fiscal_year=2025)

# 結果確認
for r in results:
    status = "OK" if r.success else f"NG: {r.error}"
    print(f"  {r.table_name}: {r.rows_affected} rows, {r.execution_time_ms:.1f}ms [{status}]")
```

### 11.3 DuckDB最適化

```sql
-- テーブル統計情報の確認
SELECT table_name, estimated_size, column_count
FROM duckdb_tables()
WHERE schema_name = 'main';

-- テーブルサイズの確認
SELECT
    table_name,
    COUNT(*) as row_count
FROM information_schema.tables t
CROSS JOIN LATERAL (
    SELECT COUNT(*) as cnt FROM main.journal_entries
) WHERE table_schema = 'main';

-- VACUUMによるストレージ最適化
VACUUM;

-- 統計情報の更新（クエリ最適化に重要）
ANALYZE;

-- 特定テーブルの統計情報確認
SELECT * FROM duckdb_columns()
WHERE table_name = 'journal_entries';
```

### 11.4 データアーカイブ

```python
# 古い年度のデータをParquetにエクスポートしてアーカイブ
import duckdb

conn = duckdb.connect('data/jaia.duckdb')

# 2年前のデータをエクスポート
conn.execute("""
    COPY (
        SELECT * FROM journal_entries
        WHERE fiscal_year <= 2023
    ) TO 'backups/archive_fy2023.parquet' (FORMAT PARQUET, COMPRESSION ZSTD)
""")

# エクスポート確認後、古いデータを削除（慎重に実施）
# conn.execute("DELETE FROM journal_entries WHERE fiscal_year <= 2023")
# conn.execute("VACUUM")

conn.close()
```

### 11.5 SQLite保守

```bash
# 整合性チェック
sqlite3 data/jaia_meta.db "PRAGMA integrity_check;"

# データベース最適化
sqlite3 data/jaia_meta.db "VACUUM;"

# WALチェックポイント（WALファイルのマージ）
sqlite3 data/jaia_meta.db "PRAGMA wal_checkpoint(FULL);"

# データベースサイズ確認
sqlite3 data/jaia_meta.db "SELECT page_count * page_size FROM pragma_page_count(), pragma_page_size();"
```

---

## 12. LLM プロバイダーフェイルオーバーと切り替え

### 12.1 対応LLMプロバイダー一覧

JAIAは8つのLLMプロバイダーをサポートしています。

| プロバイダー | 設定値 | 主要モデル | 用途 |
|------------|-------|-----------|------|
| AWS Bedrock | `bedrock` | Claude Opus 4.6, Sonnet 4.5, Haiku 4.5, Nova Premier | エンタープライズ推奨 |
| Azure AI Foundry | `azure_foundry` | GPT-5.2, GPT-5, GPT-5 Nano, Claude Opus 4.6 | 最高精度 |
| GCP Vertex AI | `vertex_ai` | Gemini 3 Pro, Gemini 3 Flash, Gemini 2.5 Pro | バランス型 |
| Anthropic Direct | `anthropic` | Claude Opus 4.6, Sonnet 4.5, Haiku 4.5 | 直接API |
| OpenAI Direct | `openai` | GPT-5.2, GPT-5, o3-pro, o4-mini | 直接API |
| Google AI Studio | `google` | Gemini 3 Flash, Gemini 2.5 Pro | 開発用 |
| Azure OpenAI | `azure` | GPT-4o, GPT-4o Mini | レガシー |
| Ollama (Local) | `ollama` | Phi-4, DeepSeek R1, Llama 3.3, Gemma 3 | ローカル開発 |

### 12.2 推奨モデル選択ガイド

| ユースケース | 推奨プロバイダー | 推奨モデル | 説明 |
|------------|----------------|-----------|------|
| 最高精度 | azure_foundry | gpt-5.2 | ARC-AGI 90%+ |
| 高精度・エージェント | bedrock | Claude Opus 4.6 | 複雑な調査向け |
| バランス型 | vertex_ai | Gemini 3 Pro | 日常分析向け |
| コスト重視 | vertex_ai | Gemini 3 Flash | $0.50/1M入力 |
| 超高速 | azure_foundry | GPT-5 Nano | $0.05/1M入力 |
| ローカル開発 | ollama | Phi-4 (14B) | クラウド不要 |

### 12.3 プロバイダー切り替え手順

```bash
# 環境変数を変更してプロバイダーを切り替え
# 例: Bedrock → Azure Foundry に切り替え

# 方法1: docker-compose の環境変数を変更
export LLM_PROVIDER=azure_foundry
export LLM_MODEL=gpt-5.2
docker-compose up -d backend

# 方法2: ECSタスク定義の環境変数を更新
aws ecs register-task-definition \
  --family jaia-backend \
  --container-definitions '[{
    "name": "backend",
    "environment": [
      {"name": "LLM_PROVIDER", "value": "azure_foundry"},
      {"name": "LLM_MODEL", "value": "gpt-5.2"}
    ]
  }]'

aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --force-new-deployment

# 方法3: Azure Container App の環境変数を更新
az containerapp update \
  --name ca-jaia-backend \
  --resource-group rg-jaia-production \
  --set-env-vars LLM_PROVIDER=azure_foundry LLM_MODEL=gpt-5.2
```

### 12.4 フェイルオーバー戦略

```
+-------------------+
| Primary Provider  |
| (bedrock/Claude)  |
+---------+---------+
          |
          | 障害検知 (5xx > 5%, timeout > 30s)
          v
+---------+---------+
| Secondary Provider|
| (azure_foundry/   |
|  GPT-5.2)         |
+---------+---------+
          |
          | 障害検知
          v
+---------+---------+
| Tertiary Provider |
| (vertex_ai/       |
|  Gemini 3 Pro)    |
+---------+---------+
          |
          | 全クラウド障害
          v
+---------+---------+
| Local Fallback    |
| (ollama/Phi-4)    |
+-------------------+
```

#### フェイルオーバー判断基準

| 指標 | 閾値 | アクション |
|------|------|-----------|
| API エラー率 | > 5% (5分間) | 次のプロバイダーに切り替え |
| レスポンスタイムアウト | > 30秒 | 次のプロバイダーに切り替え |
| レート制限到達 | 429 レスポンス多発 | 次のプロバイダーに切り替え |
| 全クラウド障害 | 全プロバイダーエラー | Ollama (ローカル) にフォールバック |

### 12.5 LLMコスト管理

```bash
# LLMリクエスト数の制限設定
LLM_REQUESTS_PER_MINUTE=60
LLM_TOKENS_PER_MINUTE=100000

# コスト見積もりの目安 (2026年2月時点)
# Claude Opus 4.6:    $15/1M入力, $75/1M出力
# GPT-5.2:            $10/1M入力, $50/1M出力
# Gemini 3 Flash:     $0.50/1M入力, $2/1M出力
# GPT-5 Nano:         $0.05/1M入力, $0.25/1M出力
# Ollama (Local):     無料（ハードウェアコストのみ）
```

---

## 13. 災害復旧計画（DR）

### 13.1 RPO/RTO目標

| 環境 | RPO (目標復旧時点) | RTO (目標復旧時間) |
|------|-------------------|-------------------|
| Production | 1時間 | 4時間 |
| Staging | 24時間 | 8時間 |
| Development | 7日間 | 翌営業日 |

### 13.2 災害シナリオと対応

#### シナリオ1: 単一コンテナ障害

**影響**: 一部リクエストの遅延・エラー
**対応**: オートスケーリングによる自動復旧

```bash
# ECSの場合、unhealthyなタスクは自動的に置換される
# 確認コマンド
aws ecs describe-services \
  --cluster jaia-production \
  --services jaia-backend \
  --query 'services[0].{desired:desiredCount,running:runningCount,pending:pendingCount}'
```

#### シナリオ2: データベースファイル破損

**影響**: サービス停止
**対応**: バックアップからリストア

```bash
# 1. サービス停止
docker-compose stop backend

# 2. 破損ファイルを退避
mv data/jaia.duckdb data/jaia.duckdb.corrupted

# 3. 最新バックアップからリストア
cp backups/jaia_latest.duckdb data/jaia.duckdb

# 4. サービス再開
docker-compose start backend

# 5. 集計テーブルの再構築
python3 -c "
from app.services.aggregation import AggregationService
results = AggregationService().update_all()
for r in results:
    print(f'{r.table_name}: {\"OK\" if r.success else r.error}')
"
```

#### シナリオ3: クラウドリージョン障害

**影響**: 特定クラウドプロバイダーでのサービス停止
**対応**: 別クラウドへのフェイルオーバー

```bash
# 1. 別クラウドプロバイダーへのデプロイ
gh workflow run deploy.yml \
  -f environment=production \
  -f cloud_provider=azure  # AWS障害時はAzureへ

# 2. DNSの切り替え（使用しているDNSサービスに依存）
# Route53/Azure DNS/Cloud DNSのCNAMEを変更

# 3. LLMプロバイダーの切り替え
# AWS Bedrock障害時 → Azure Foundry or Vertex AI に切り替え
```

#### シナリオ4: LLMプロバイダー全停止

**影響**: AI分析機能の停止（データインポート・ダッシュボードは正常動作）
**対応**: ローカルLLMへのフォールバック

```bash
# Ollama (ローカルLLM) への切り替え
export LLM_PROVIDER=ollama
export LLM_MODEL=phi4

# Ollamaが未インストールの場合
curl -fsSL https://ollama.ai/install.sh | sh
ollama serve &
ollama pull phi4

# サービス再起動
docker-compose up -d backend
```

### 13.3 DR訓練チェックリスト（四半期実施推奨）

- [ ] バックアップからのDuckDBリストア訓練
- [ ] バックアップからのSQLiteリストア訓練
- [ ] 別クラウドへのフェイルオーバーデプロイ訓練
- [ ] LLMプロバイダー切り替え訓練
- [ ] ロールバック手順の実施確認
- [ ] 連絡体制の確認
- [ ] RPO/RTOの達成可否検証
- [ ] 訓練結果のドキュメント化

### 13.4 データ冗長化戦略

| クラウド | ストレージ冗長化 | 設定 |
|---------|-----------------|------|
| AWS S3 | バージョニング有効 + AES256暗号化 | `versioning = "Enabled"` |
| Azure Storage | GRSレプリケーション (本番) | `account_replication_type = "GRS"` |
| GCP Cloud Storage | バージョニング有効 + 365日ライフサイクル | `versioning { enabled = true }` |

---

## 14. トラブルシューティングガイド

### 14.1 ヘルスチェック失敗

**症状**: `/health` が 200 以外を返す、ALB/LB が unhealthy と判定する

```bash
# 1. コンテナログの確認
docker logs jaia-backend --tail 100

# 2. ポート接続の確認
curl -v http://localhost:8001/health

# 3. DuckDB/SQLiteの状態確認
curl -s http://localhost:8001/api/v1/status | jq .

# 4. リソース使用量の確認
docker stats jaia-backend --no-stream

# 5. よくある原因
# - DuckDBファイルのロック（同時接続制限）
# - メモリ不足
# - ディスク容量不足
# - 環境変数の設定ミス
```

### 14.2 LLM API 呼び出しエラー

**症状**: 仕訳分析やエージェント機能がエラーを返す

```bash
# 1. LLM設定の確認
echo "Provider: $LLM_PROVIDER"
echo "Model: $LLM_MODEL"

# 2. APIキーの設定確認（値は表示されないので存在だけ確認）
env | grep -i "API_KEY\|FOUNDRY\|BEDROCK" | sed 's/=.*/=***/'

# 3. プロバイダー別の接続テスト
# Bedrock
aws bedrock-runtime invoke-model \
  --model-id anthropic.claude-sonnet-4-5-20250929-v1:0 \
  --body '{"anthropic_version":"bedrock-2023-05-31","max_tokens":100,"messages":[{"role":"user","content":"test"}]}' \
  /tmp/response.json

# 4. エラーログの確認
# jaia_error.log で LLM関連のエラーを検索
python3 -c "
import json
with open('logs/jaia_error.log') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'llm' in data.get('message', '').lower() or 'api' in data.get('message', '').lower():
                print(f\"{data['timestamp']} {data['message']}\")
        except:
            pass
"
```

### 14.3 パフォーマンス低下

**症状**: レスポンス時間が5秒を超える

```bash
# 1. パフォーマンスログの確認
# 直近1時間のスロークエリを表示
python3 -c "
import json
from datetime import datetime, timedelta

cutoff = (datetime.utcnow() - timedelta(hours=1)).isoformat()
with open('logs/jaia_performance.log') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('timestamp', '') > cutoff and data.get('duration_ms', 0) > 5000:
                print(f\"{data['path']}: {data['duration_ms']:.0f}ms\")
        except:
            pass
"

# 2. DuckDB接続の確認
python3 -c "
import duckdb, time
start = time.time()
conn = duckdb.connect('data/jaia.duckdb', read_only=True)
count = conn.execute('SELECT COUNT(*) FROM journal_entries').fetchone()[0]
elapsed = (time.time() - start) * 1000
print(f'Connection + count query: {elapsed:.1f}ms ({count} rows)')
conn.close()
"

# 3. コンテナリソースの確認
docker stats jaia-backend --no-stream

# 4. 対策
# - BATCH_SIZE を減らす
# - MAX_WORKERS を増やす
# - 集計テーブルの再構築（古い集計データが断片化している可能性）
# - DuckDB VACUUM の実行
# - コンテナのスケールアウト
```

### 14.4 データインポートエラー

**症状**: 仕訳データのインポートが失敗する

```bash
# 1. インポート関連のエラーログを確認
# jaia_error.log で import 関連のエラーを検索

# 2. DuckDBのディスク容量確認
df -h data/
ls -lh data/jaia.duckdb

# 3. DuckDBテーブルの整合性確認
python3 -c "
import duckdb
conn = duckdb.connect('data/jaia.duckdb', read_only=True)
tables = conn.execute(\"SELECT table_name FROM information_schema.tables WHERE table_schema = 'main'\").fetchall()
for (name,) in tables:
    try:
        count = conn.execute(f'SELECT COUNT(*) FROM {name}').fetchone()[0]
        print(f'{name}: {count} rows')
    except Exception as e:
        print(f'{name}: ERROR - {e}')
conn.close()
"

# 4. 典型的な原因と対策
# - ファイルフォーマットエラー → CSVのエンコーディング・区切り文字を確認
# - メモリ不足 → BATCH_SIZE を減らす
# - ディスク容量不足 → 古いデータをアーカイブ
# - DuckDBロック → 他の接続を確認・サービス再起動
```

### 14.5 Docker起動エラー

**症状**: コンテナが起動しない、CrashLoopBackOff

```bash
# 1. コンテナログの確認
docker logs jaia-backend

# 2. イメージのビルド確認
docker build -t jaia-backend:test -f Dockerfile .

# 3. 環境変数の確認
docker-compose config

# 4. ボリュームの確認
docker volume ls
docker volume inspect jaia-data

# 5. ネットワークの確認
docker network ls
docker network inspect jaia-network

# 6. よくある原因
# - 必要な環境変数が未設定
# - ボリュームのパーミッションエラー
# - ポートの競合
# - メモリ制限の不足
```

### 14.6 Terraformエラー

```bash
# 1. ステートの確認
terraform state list

# 2. ステートのリフレッシュ（実際のリソースとの同期）
terraform plan -refresh-only

# 3. リソースの再インポート（ステートとの不整合解消）
terraform import aws_ecs_cluster.main jaia-production

# 4. ロックの解除（前回のapplyが中断した場合）
terraform force-unlock <LOCK_ID>

# 5. 特定リソースのみ適用
terraform apply -target=aws_ecs_cluster.main
```

### 14.7 セキュリティ関連の問題

```bash
# 1. ブロックされたIPの確認
# セキュリティログから一時ブロックイベントを検索
python3 -c "
import json
with open('logs/jaia_security.log') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('event_type') in ('ip_temp_blocked', 'ip_permanent_blocked'):
                print(f\"{data['timestamp']} {data['event_type']}: {data.get('client_ip')}\")
        except:
            pass
"

# 2. レート制限の状況確認
# security.log から rate_limit_exceeded イベントを集計
python3 -c "
import json
from collections import Counter

ips = Counter()
with open('logs/jaia_security.log') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('event_type') == 'rate_limit_exceeded':
                ips[data.get('client_ip', 'unknown')] += 1
        except:
            pass

for ip, count in ips.most_common(10):
    print(f'{ip}: {count} times')
"

# 3. 不正リクエストパターンの確認
python3 -c "
import json
with open('logs/jaia_security.log') as f:
    for line in f:
        try:
            data = json.loads(line)
            if data.get('event_type') == 'suspicious_request':
                print(f\"{data['timestamp']} pattern={data.get('pattern_matched')} ip={data.get('client_ip')} path={data.get('path')}\")
        except:
            pass
"
```

---

## 付録

### A. 環境変数一覧

| 変数名 | デフォルト値 | 説明 | 必須 |
|--------|------------|------|------|
| ENVIRONMENT | development | 環境名 (development/staging/production) | Yes |
| DEBUG | false | デバッグモード | No |
| HOST | 127.0.0.1 | バインドホスト | No |
| PORT | 8001 | バインドポート | No |
| LLM_PROVIDER | bedrock | LLMプロバイダー | Yes |
| LLM_MODEL | us.anthropic.claude-opus-4-6-... | LLMモデル | Yes |
| DATA_DIR | ./data | データディレクトリ | No |
| DUCKDB_PATH | ./data/jaia.duckdb | DuckDB パス | No |
| SQLITE_PATH | ./data/jaia_meta.db | SQLite パス | No |
| BATCH_SIZE | 10000 | バッチサイズ | No |
| MAX_WORKERS | 4 | ワーカー数 | No |
| CACHE_TTL_SECONDS | 300 | キャッシュTTL(秒) | No |
| LOG_LEVEL | INFO | ログレベル | No |
| LLM_REQUESTS_PER_MINUTE | 60 | LLMリクエスト/分制限 | No |
| LLM_TOKENS_PER_MINUTE | 100000 | LLMトークン/分制限 | No |
| ANTHROPIC_API_KEY | - | Anthropic APIキー | プロバイダー依存 |
| OPENAI_API_KEY | - | OpenAI APIキー | プロバイダー依存 |
| GOOGLE_API_KEY | - | Google AI APIキー | プロバイダー依存 |
| AWS_REGION | us-east-1 | AWSリージョン | Bedrock使用時 |
| AWS_ACCESS_KEY_ID | - | AWSアクセスキー | Bedrock使用時 |
| AWS_SECRET_ACCESS_KEY | - | AWSシークレットキー | Bedrock使用時 |
| AZURE_FOUNDRY_ENDPOINT | - | Azure Foundryエンドポイント | Azure Foundry使用時 |
| AZURE_FOUNDRY_API_KEY | - | Azure Foundry APIキー | Azure Foundry使用時 |
| AZURE_FOUNDRY_API_VERSION | 2026-01-01 | API バージョン | No |
| GCP_PROJECT_ID | - | GCPプロジェクトID | Vertex AI使用時 |
| GCP_LOCATION | global | GCPロケーション | No |
| OLLAMA_BASE_URL | http://localhost:11434 | Ollama URL | Ollama使用時 |
| OLLAMA_MODEL | phi4 | Ollamaモデル | Ollama使用時 |

### B. Docker Compose サービス構成

| サービス | イメージ | ポート | ボリューム | プロファイル |
|---------|---------|--------|-----------|------------|
| backend | ビルド (Dockerfile) | 8001:8001 | jaia-data:/app/data | デフォルト |
| frontend | nginx:alpine | 80:80 | ./frontend/dist | デフォルト |
| redis | redis:7-alpine | 6379:6379 | redis-data:/data | production |

### C. 運用カレンダー

| 頻度 | タスク |
|------|--------|
| 毎日 | ヘルスチェック確認、エラーログレビュー |
| 毎週 | パフォーマンスログ分析、セキュリティログレビュー |
| 毎月 | APIキー有効期限確認、セキュリティ監査、依存パッケージ更新確認 |
| 四半期 | DR訓練実施、バックアップリストアテスト、スケーリング戦略見直し |
| 半年 | Terraform/IaC レビュー、SLA達成状況確認 |
| 年次 | セキュリティログアーカイブ、年次セキュリティレビュー |

### D. 連絡先

| 役割 | 連絡先 | 備考 |
|------|--------|------|
| 運用チーム | [運用チームメールアドレス] | 平日 9:00-18:00 |
| 開発チーム | [開発チームメールアドレス] | 平日 9:00-18:00 |
| 緊急連絡 | [緊急連絡先電話番号] | P1/P2 インシデント時 |
| セキュリティ | [セキュリティチームメールアドレス] | セキュリティインシデント時 |

### E. 改訂履歴

| 日付 | バージョン | 変更内容 | 担当者 |
|------|-----------|---------|--------|
| 2026-02-14 | 2.0 | 全面改訂: 包括的運用保守マニュアルとして再構成 | - |
| - | 1.0 | 初版作成 | - |
