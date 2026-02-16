# JAIA デプロイメントランブック

本ドキュメントは JAIA のデプロイメント手順をステップバイステップでまとめたランブックです。
詳細な運用手順は [11_enterprise_operations.md](11_enterprise_operations.md) を参照してください。

---

## 目次

1. [デプロイ前チェックリスト](#1-デプロイ前チェックリスト)
2. [ローカル開発環境](#2-ローカル開発環境)
3. [Docker 単体デプロイ](#3-docker-単体デプロイ)
4. [クラウドデプロイ (Terraform)](#4-クラウドデプロイ-terraform)
5. [CI/CD パイプライン](#5-cicd-パイプライン)
6. [デプロイ後の検証](#6-デプロイ後の検証)
7. [ロールバック手順](#7-ロールバック手順)
8. [バックアップ・リストア](#8-バックアップリストア)

---

## 1. デプロイ前チェックリスト

デプロイを実行する前に以下を確認してください。

### 全環境共通

- [ ] CI パイプライン (ci.yml) が全てグリーン
- [ ] `main` ブランチが最新の状態
- [ ] CHANGELOG に変更内容が記載済み
- [ ] データベースのバックアップを取得済み（本番環境）

### 環境変数

- [ ] `LLM_PROVIDER` と `LLM_MODEL` が正しく設定
- [ ] 対応する API キーが設定済み（`.env` ファイルまたはシークレットマネージャー）
- [ ] `ENVIRONMENT` が正しい値 (`development` / `staging` / `production`)

### クラウドデプロイ追加チェック

- [ ] クラウド CLI にログイン済み (`aws`, `az`, `gcloud`)
- [ ] Terraform ステートのリモートバックエンドが設定済み（本番環境）
- [ ] `terraform.tfvars` に環境固有の値を設定済み
- [ ] IAM / サービスアカウントに必要な権限が付与済み

---

## 2. ローカル開発環境

### セットアップスクリプト（推奨）

```powershell
# Windows: PowerShell で実行
.\scripts\setup.ps1
```

### 手動セットアップ

```bash
# 1. バックエンド
cd backend
python -m venv venv
source venv/bin/activate    # Windows: venv\Scripts\activate
pip install -r requirements.txt

# 2. フロントエンド
cd ../frontend
npm install

# 3. 起動
# バックエンド (ポート 8090)
cd ../backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload

# フロントエンド (ポート 5290)
cd ../frontend
npm run dev
```

### 動作確認

```bash
# ヘルスチェック
curl http://localhost:8090/health
# → {"status": "healthy", "app": "JAIA", "version": "0.2.0"}

# API ステータス
curl http://localhost:8090/api/v1/status
```

---

## 3. Docker 単体デプロイ

### 基本デプロイ

```bash
# 1. .env ファイルを作成（初回のみ）
cat > .env <<EOF
ENVIRONMENT=production
LLM_PROVIDER=bedrock
LLM_MODEL=anthropic.claude-sonnet-4-6-opus-20260115-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=your-key-id
AWS_SECRET_ACCESS_KEY=your-secret-key
EOF

# 2. イメージビルド & 起動
docker-compose up -d --build

# 3. ステータス確認
docker-compose ps
docker logs jaia-backend --tail 20

# 4. ヘルスチェック
curl http://localhost:8090/health
```

### Redis 付きデプロイ（本番推奨）

```bash
docker-compose --profile production up -d --build
```

### 停止・再起動

```bash
# 停止
docker-compose down

# 再起動（データ保持）
docker-compose restart backend

# 完全リセット（データ削除）
docker-compose down -v
```

---

## 4. クラウドデプロイ (Terraform)

### 4.1 AWS (ECS + Bedrock)

```bash
cd infrastructure/terraform/aws

# 変数ファイル作成
cat > terraform.tfvars <<EOF
aws_region       = "us-east-1"
environment      = "production"
app_name         = "jaia"
bedrock_model_id = "anthropic.claude-sonnet-4-6-opus-20260115-v1:0"
EOF

# デプロイ
terraform init
terraform plan -out=tfplan
terraform apply tfplan

# 出力値の確認
terraform output
```

作成されるリソース: VPC, ECS Cluster, ECR, ALB, S3, Secrets Manager, IAM Role, CloudWatch

### 4.2 Azure (Container Apps + Azure Foundry)

```bash
az login
cd infrastructure/terraform/azure

cat > terraform.tfvars <<EOF
location     = "japaneast"
environment  = "production"
app_name     = "jaia"
openai_model = "gpt-5-2"
EOF

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

作成されるリソース: Resource Group, VNet, Container App, ACR, Azure OpenAI, Key Vault, Storage, Log Analytics

### 4.3 GCP (Cloud Run + Vertex AI)

```bash
gcloud auth application-default login
cd infrastructure/terraform/gcp

cat > terraform.tfvars <<EOF
project_id   = "your-project-id"
region       = "asia-northeast1"
environment  = "production"
gemini_model = "gemini-3.0-flash-preview"
EOF

terraform init
terraform plan -out=tfplan
terraform apply tfplan
```

作成されるリソース: VPC, Subnet, Artifact Registry, Cloud Run, Cloud Storage, Secret Manager, Cloud Armor (WAF)

### 4.4 Terraform ステート管理

本番環境ではリモートバックエンドを使用してください。
詳細: [11_enterprise_operations.md](11_enterprise_operations.md) セクション 2.5

---

## 5. CI/CD パイプライン

### 5.1 CI パイプライン (自動実行)

`main` ブランチへの push / PR で自動実行されます。

| ジョブ | 内容 |
|-------|------|
| backend-lint | ruff check/format |
| backend-test | pytest + カバレッジ (50%閾値) |
| frontend-lint | eslint + typecheck |
| frontend-test | vitest + カバレッジ |
| security-scan | Bandit + Safety |
| terraform-validate | AWS/Azure/GCP 検証 |
| build | Ubuntu/Windows/macOS ビルド |
| docker-build | Docker イメージビルド |

### 5.2 デプロイパイプライン

```bash
# Staging 自動デプロイ: main ブランチ push 時 (backend/** 変更時)

# 手動デプロイ
gh workflow run deploy.yml \
  -f environment=staging \
  -f cloud_provider=aws

# 本番デプロイ (手動のみ)
gh workflow run deploy.yml \
  -f environment=production \
  -f cloud_provider=aws
```

### 5.3 リリース

```bash
# バージョンタグを作成 → release.yml が自動実行
git tag v0.2.0
git push origin v0.2.0

# ドラフトリリースを公開
gh release edit v0.2.0 --draft=false
```

---

## 6. デプロイ後の検証

### ヘルスチェック

```bash
# 基本ヘルスチェック
curl -s https://your-domain/health | jq .

# 詳細ステータス (DB接続状態、仕訳件数)
curl -s https://your-domain/api/v1/status | jq .
```

### スモークテスト

```bash
# API レスポンス確認
curl -s https://your-domain/api/v1/dashboard/summary?fiscal_year=2025 | jq .

# OpenAPI ドキュメント
curl -s https://your-domain/docs
```

### ログ確認

```bash
# Docker
docker logs jaia-backend --tail 50

# AWS
aws logs tail "/ecs/jaia-production/app" --follow

# Azure
az containerapp logs show --name ca-jaia-backend --resource-group rg-jaia-production

# GCP
gcloud logging read "resource.type=cloud_run_revision AND resource.labels.service_name=jaia-backend" --limit 50
```

---

## 7. ロールバック手順

### Docker

```bash
# 前回のイメージに戻す
docker-compose down
git checkout HEAD~1
docker-compose up -d --build
```

### AWS ECS

```bash
# 前タスク定義にロールバック
aws ecs list-task-definitions --family-prefix jaia-backend --sort DESC --max-items 5
aws ecs update-service \
  --cluster jaia-production \
  --service jaia-backend \
  --task-definition jaia-backend:<前のリビジョン>
aws ecs wait services-stable --cluster jaia-production --services jaia-backend
```

### Azure Container Apps

```bash
az containerapp revision list --name ca-jaia-backend --resource-group rg-jaia-production -o table
az containerapp ingress traffic set \
  --name ca-jaia-backend \
  --resource-group rg-jaia-production \
  --revision-weight <前のリビジョン>=100
```

### GCP Cloud Run

```bash
gcloud run revisions list --service jaia-backend --region asia-northeast1
gcloud run services update-traffic jaia-backend \
  --region asia-northeast1 \
  --to-revisions=<前のリビジョン>=100
```

---

## 8. バックアップ・リストア

### バックアップ実行

```bash
# ローカル
./scripts/backup_db.sh

# Docker volume から
./scripts/backup_db.sh --docker

# gzip 圧縮付き
./scripts/backup_db.sh --compress

# バックアップ一覧
./scripts/restore_db.sh --list
```

### リストア実行

```bash
# 最新バックアップからリストア
./scripts/restore_db.sh --latest

# 指定タイムスタンプでリストア
./scripts/restore_db.sh --timestamp 20260216_020000

# Docker volume にリストア
./scripts/restore_db.sh --latest --docker
```

詳細なバックアップ戦略: [11_enterprise_operations.md](11_enterprise_operations.md) セクション 8

---

## 関連ドキュメント

- [00_quickstart.md](00_quickstart.md) — クイックスタート
- [06_setup_guide.md](06_setup_guide.md) — 開発環境セットアップ
- [10_cloud_setup_guide.md](10_cloud_setup_guide.md) — クラウド環境構築
- [11_enterprise_operations.md](11_enterprise_operations.md) — エンタープライズ運用マニュアル
- [15_troubleshooting.md](15_troubleshooting.md) — トラブルシューティング
