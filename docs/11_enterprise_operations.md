# JAIA エンタープライズ運用ガイド

本ドキュメントでは、JAIAシステムのエンタープライズ環境での運用方法を説明します。

## 目次

1. [概要](#1-概要)
2. [インフラストラクチャ構築](#2-インフラストラクチャ構築)
3. [CI/CDパイプライン](#3-cicdパイプライン)
4. [セキュリティ運用](#4-セキュリティ運用)
5. [監視とアラート](#5-監視とアラート)
6. [障害対応](#6-障害対応)
7. [スケーリング](#7-スケーリング)

---

## 1. 概要

### エンタープライズ構成

```
┌─────────────────────────────────────────────────────────────────┐
│                         User Access                              │
│                             ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    Load Balancer                          │   │
│  │               (ALB/Azure LB/Cloud LB)                     │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                             ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                Container Orchestration                     │   │
│  │              (ECS/Container Apps/Cloud Run)               │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐                   │   │
│  │  │Backend 1│  │Backend 2│  │Backend N│  Auto-scaling     │   │
│  │  └─────────┘  └─────────┘  └─────────┘                   │   │
│  └─────────────────────────┬────────────────────────────────┘   │
│                             ↓                                    │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │                    LLM Providers (8社対応)                  │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │   │
│  │  │ Bedrock │  │ Azure   │  │ Vertex  │  │Anthropic│      │   │
│  │  │(Claude  │  │Foundry  │  │  AI     │  │ (Direct)│      │   │
│  │  │Opus 4.6)│  │(GPT-5.2)│  │(Gemini) │  │         │      │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │   │
│  │  ┌─────────┐  ┌─────────┐  ┌─────────┐  ┌─────────┐      │   │
│  │  │ OpenAI  │  │Google AI│  │ Azure   │  │ Ollama  │      │   │
│  │  │(Direct) │  │ Studio  │  │ OpenAI  │  │ (Local) │      │   │
│  │  └─────────┘  └─────────┘  └─────────┘  └─────────┘      │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
```

### 環境構成

| 環境 | 用途 | SLA |
|------|------|-----|
| Development | 開発・テスト | - |
| Staging | 本番前検証 | 99% |
| Production | 本番運用 | 99.9% |

---

## 2. インフラストラクチャ構築

### 2.1 前提条件

```bash
# 必要なツール
- Terraform >= 1.6.0
- AWS CLI / Azure CLI / gcloud CLI
- Docker >= 24.0
- kubectl (オプション)
```

### 2.2 AWS環境構築

```bash
# 1. ディレクトリ移動
cd infrastructure/terraform/aws

# 2. 変数設定
cat > terraform.tfvars <<EOF
aws_region  = "us-east-1"
environment = "production"
app_name    = "jaia"
EOF

# 3. 初期化
terraform init

# 4. プラン確認
terraform plan

# 5. 適用
terraform apply
```

#### 作成されるリソース

| リソース | 説明 |
|----------|------|
| VPC | 専用ネットワーク |
| ECS Cluster | コンテナオーケストレーション |
| ECR | コンテナレジストリ |
| ALB | ロードバランサー |
| S3 | データストレージ |
| Secrets Manager | シークレット管理 |

### 2.3 Azure環境構築

```bash
# 1. Azureログイン
az login

# 2. ディレクトリ移動
cd infrastructure/terraform/azure

# 3. 変数設定
cat > terraform.tfvars <<EOF
location    = "japaneast"
environment = "production"
app_name    = "jaia"
EOF

# 4. 初期化・適用
terraform init
terraform apply
```

### 2.4 GCP環境構築

```bash
# 1. GCPログイン
gcloud auth application-default login

# 2. ディレクトリ移動
cd infrastructure/terraform/gcp

# 3. 変数設定
cat > terraform.tfvars <<EOF
project_id  = "your-project-id"
region      = "asia-northeast1"
environment = "production"
EOF

# 4. 初期化・適用
terraform init
terraform apply
```

---

## 3. CI/CDパイプライン

### 3.1 パイプライン構成

```
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│   Commit    │───▶│   CI Tests  │───▶│   Build     │
└─────────────┘    └─────────────┘    └─────────────┘
                                            │
                                            ▼
┌─────────────┐    ┌─────────────┐    ┌─────────────┐
│ Production  │◀───│   Staging   │◀───│    Dev      │
│   Deploy    │    │   Deploy    │    │   Deploy    │
└─────────────┘    └─────────────┘    └─────────────┘
```

### 3.2 GitHub Secrets設定

以下のシークレットを設定してください：

#### AWS用

| シークレット名 | 説明 |
|---------------|------|
| AWS_ACCESS_KEY_ID | AWSアクセスキーID |
| AWS_SECRET_ACCESS_KEY | AWSシークレットキー |
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

### 3.3 デプロイメント

#### 手動デプロイ

```bash
# GitHub Actionsから手動実行
gh workflow run deploy.yml \
  -f environment=staging \
  -f cloud_provider=aws
```

#### 自動デプロイ

`main`ブランチへのプッシュ時に自動的にstagingへデプロイされます。

---

## 4. セキュリティ運用

### 4.1 セキュリティ機能

JAIAには以下のセキュリティ機能が実装されています：

#### レート制限

```python
# 設定値
RATE_LIMIT_REQUESTS = 100  # 1分あたり
RATE_LIMIT_WINDOW_SECONDS = 60
```

#### IPブロック

```python
# 自動ブロック条件
TEMP_BLOCK_THRESHOLD = 10  # 違反回数
TEMP_BLOCK_DURATION_MINUTES = 15  # ブロック時間
```

#### セキュリティヘッダー

| ヘッダー | 値 |
|----------|-----|
| X-Content-Type-Options | nosniff |
| X-Frame-Options | DENY |
| X-XSS-Protection | 1; mode=block |
| Strict-Transport-Security | max-age=31536000 |
| Content-Security-Policy | default-src 'self' |

### 4.2 セキュリティログ

セキュリティイベントは専用ログファイルに記録されます：

```
logs/security.log
```

監視すべきイベント：

| イベント | 重要度 | 対応 |
|----------|--------|------|
| rate_limit_exceeded | Warning | 監視継続 |
| suspicious_request | Warning | パターン分析 |
| ip_temp_blocked | Warning | 調査 |
| blocked_ip_access | Info | 記録 |

### 4.3 APIキー管理

#### ローテーション手順

1. 新しいキーを生成
2. Secrets Manager/Key Vaultを更新
3. アプリケーションを再デプロイ
4. 古いキーを無効化

```bash
# AWS Secrets Manager更新例
aws secretsmanager put-secret-value \
  --secret-id jaia/production/secrets \
  --secret-string '{"ANTHROPIC_API_KEY": "新しいキー"}'
```

---

## 5. 監視とアラート

### 5.1 ログ構成

```
logs/
├── jaia.log          # アプリケーションログ
├── audit.log         # 監査ログ（365日保持）
├── security.log      # セキュリティログ（365日保持）
└── performance.log   # パフォーマンスログ
```

### 5.2 メトリクス

監視すべき主要メトリクス：

| メトリクス | 閾値 | アラート |
|-----------|------|----------|
| エラー率 | > 1% | Critical |
| レスポンス時間 | > 5秒 | Warning |
| CPU使用率 | > 80% | Warning |
| メモリ使用率 | > 85% | Warning |
| LLM API エラー | > 5% | Critical |

### 5.3 CloudWatch設定例（AWS）

```json
{
  "AlarmName": "JAIA-HighErrorRate",
  "MetricName": "5XXError",
  "Namespace": "AWS/ApplicationELB",
  "Statistic": "Sum",
  "Period": 60,
  "EvaluationPeriods": 5,
  "Threshold": 10,
  "ComparisonOperator": "GreaterThanThreshold"
}
```

---

## 6. 障害対応

### 6.1 障害レベル定義

| レベル | 定義 | 対応時間 |
|--------|------|----------|
| P1 | サービス全停止 | 15分以内 |
| P2 | 主要機能障害 | 30分以内 |
| P3 | 一部機能障害 | 2時間以内 |
| P4 | 軽微な問題 | 翌営業日 |

### 6.2 ロールバック手順

```bash
# 1. 前バージョンを確認
aws ecs describe-task-definition \
  --task-definition jaia-backend \
  --query 'taskDefinition.revision'

# 2. 前バージョンにロールバック
aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --task-definition jaia-backend:前のリビジョン番号

# 3. デプロイ状態確認
aws ecs describe-services \
  --cluster jaia-production \
  --services jaia-backend
```

### 6.3 復旧確認

```bash
# ヘルスチェック
curl https://your-domain/api/v1/health

# ログ確認
aws logs tail /ecs/jaia-production/app --follow
```

---

## 7. スケーリング

### 7.1 オートスケーリング設定

#### AWS ECS

```hcl
# terraform設定
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

### 7.2 手動スケーリング

```bash
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
```

---

## 付録

### A. 環境変数一覧

| 変数名 | 説明 | 必須 |
|--------|------|------|
| ENVIRONMENT | 環境名 | Yes |
| LLM_PROVIDER | LLMプロバイダー | Yes |
| LLM_MODEL | LLMモデル | Yes |
| LOG_LEVEL | ログレベル | No |
| BATCH_SIZE | バッチサイズ | No |
| MAX_WORKERS | ワーカー数 | No |

### B. ポート一覧

| サービス | ポート |
|----------|--------|
| Backend API | 8001 |
| Frontend | 80/443 |
| Metrics | 9090 |

### C. 連絡先

- 緊急連絡: [緊急連絡先]
- 運用チーム: [メールアドレス]
- 開発チーム: [メールアドレス]
