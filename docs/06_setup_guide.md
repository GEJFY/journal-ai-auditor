# JAIA セットアップガイド

## 2026 Cloud Edition - マルチプロバイダー対応

本ドキュメントでは、JAIA（Journal entry AI Analyzer）の開発環境および本番環境のセットアップ手順を詳細に説明します。

**最終更新**: 2026年2月

---

## 目次

1. [動作要件](#1-動作要件)
2. [開発環境セットアップ](#2-開発環境セットアップ)
3. [本番環境セットアップ](#3-本番環境セットアップ)
4. [LLM設定](#4-llm設定)
5. [セキュリティ設定](#5-セキュリティ設定)
6. [トラブルシューティング](#6-トラブルシューティング)

---

## 1. 動作要件

### 1.1 必須ソフトウェア

| ソフトウェア | バージョン | 確認コマンド |
|-------------|-----------|-------------|
| Python | 3.11以上 | `python --version` |
| Node.js | 18以上 | `node --version` |
| npm | 9以上 | `npm --version` |
| Git | 2.30以上 | `git --version` |

### 1.2 推奨スペック

| 項目 | 最小要件 | 推奨 |
|------|---------|------|
| OS | Windows 10, macOS 12, Ubuntu 20.04 | Windows 11, macOS 14, Ubuntu 22.04 |
| CPU | 4コア | 8コア以上 |
| メモリ | 8GB | 16GB以上 |
| ディスク | 10GB空き | SSD 20GB以上 |

### 1.3 ネットワーク要件

- インターネット接続（パッケージダウンロード時）
- LLM API使用時は外部接続が必要
- ローカル実行時はオフライン動作可能

---

## 2. 開発環境セットアップ

### 2.1 自動セットアップ（推奨）

PowerShellを管理者権限で開き、以下を実行：

```powershell
# リポジトリをクローン
git clone https://github.com/your-org/journal-ai-auditor.git
cd journal-ai-auditor

# セットアップスクリプトを実行
.\scripts\setup.ps1
```

セットアップスクリプトは以下を自動実行します：
- Pythonバージョン確認
- Node.jsバージョン確認
- バックエンド仮想環境作成
- Python依存パッケージインストール
- フロントエンドnpm依存パッケージインストール
- データディレクトリ作成
- .envファイル作成（テンプレートから）

### 2.2 手動セットアップ

自動セットアップが失敗した場合の手動手順：

#### 2.2.1 バックエンドセットアップ

```powershell
# バックエンドディレクトリに移動
cd backend

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
.\venv\Scripts\Activate.ps1

# 依存パッケージをインストール
pip install -r requirements.txt

# データディレクトリを作成
mkdir data
```

#### 2.2.2 フロントエンドセットアップ

```powershell
# フロントエンドディレクトリに移動
cd frontend

# npm依存パッケージをインストール
npm install
```

#### 2.2.3 環境変数設定

`backend/.env` ファイルを作成：

```bash
# JAIA Configuration
JAIA_DEBUG=true
JAIA_LOG_LEVEL=INFO

# Database
DUCKDB_PATH=data/jaia.duckdb
SQLITE_PATH=data/jaia_meta.db

# LLM Configuration (optional)
# OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_API_KEY=your-api-key
# AZURE_OPENAI_ENDPOINT=your-endpoint
# ANTHROPIC_API_KEY=your-api-key
```

### 2.3 起動確認

```powershell
# 全サービスを起動
.\scripts\start_all.ps1

# 統合テストを実行
.\scripts\test_integration.ps1
```

成功時の出力例：

```
========================================
  JAIA Integration Tests
========================================

Testing: Health Check [PASS]
Testing: API Health [PASS]
Testing: Dashboard Summary [PASS]
Testing: Dashboard KPI [PASS]
Testing: Benford Analysis [PASS]
Testing: Batch Rules [PASS]
Testing: Report Templates [PASS]
Testing: Analysis Violations [PASS]

========================================
  Test Summary
========================================

Total Tests: 8
Passed: 8
Failed: 0

All tests passed!
```

---

## 3. 本番環境セットアップ

### 3.1 サーバー構成

本番環境では以下の構成を推奨：

```
                  ┌─────────────────┐
                  │   Load Balancer │
                  └────────┬────────┘
                           │
           ┌───────────────┼───────────────┐
           │               │               │
    ┌──────┴──────┐ ┌──────┴──────┐ ┌──────┴──────┐
    │  App Server │ │  App Server │ │  App Server │
    │  (FastAPI)  │ │  (FastAPI)  │ │  (FastAPI)  │
    └──────┬──────┘ └──────┬──────┘ └──────┬──────┘
           │               │               │
           └───────────────┼───────────────┘
                           │
                  ┌────────┴────────┐
                  │    Database     │
                  │    (DuckDB)     │
                  └─────────────────┘
```

### 3.2 Dockerによるデプロイ

#### 3.2.1 Dockerfileの作成

`backend/Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# 依存パッケージをコピー・インストール
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# アプリケーションをコピー
COPY . .

# データディレクトリを作成
RUN mkdir -p /app/data

# ポート公開
EXPOSE 8000

# ヘルスチェック
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
  CMD curl -f http://localhost:8000/health || exit 1

# 起動コマンド
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "4"]
```

#### 3.2.2 Docker Compose

`docker-compose.yml`:

```yaml
version: '3.8'

services:
  backend:
    build: ./backend
    ports:
      - "8000:8000"
    environment:
      - JAIA_DEBUG=false
      - JAIA_LOG_LEVEL=WARNING
    volumes:
      - jaia-data:/app/data
    restart: unless-stopped

  frontend:
    build: ./frontend
    ports:
      - "3000:3000"
    depends_on:
      - backend
    restart: unless-stopped

volumes:
  jaia-data:
```

#### 3.2.3 起動

```bash
# ビルドと起動
docker-compose up -d --build

# ログ確認
docker-compose logs -f

# 停止
docker-compose down
```

### 3.3 セキュリティ設定

#### 3.3.1 本番用環境変数

```bash
# .env.production
JAIA_DEBUG=false
JAIA_LOG_LEVEL=WARNING

# データベース暗号化キー（本番必須）
DUCKDB_ENCRYPTION_KEY=your-32-byte-encryption-key

# CORS設定
CORS_ORIGINS=["https://your-domain.com"]

# レート制限
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

#### 3.3.2 ファイアウォール設定

```bash
# バックエンドポート
ufw allow 8000/tcp

# フロントエンドポート
ufw allow 3000/tcp

# SSH（管理用）
ufw allow 22/tcp

# 有効化
ufw enable
```

---

## 4. LLM設定

### 4.1 対応プロバイダー一覧（2026年最新）

| プロバイダー | 推奨モデル | 特徴 |
| ------------- | ---------- | ------ |
| **AWS Bedrock** | Claude Opus 4.6 | エンタープライズ推奨 |
| **Azure Foundry** | GPT-5.2 | 最高精度 |
| **GCP Vertex AI** | Gemini 2.5 Flash Lite | コスト重視 |
| **Anthropic** | Claude Sonnet 4.5 | バランス良好 |
| **OpenAI** | GPT-5 | 汎用 |
| **Google AI** | Gemini 2.5 Flash Lite | 開発向け |
| **Azure OpenAI** | GPT-4o | レガシー |
| **Ollama** | phi4 | ローカル開発 |

### 4.2 AWS Bedrock（エンタープライズ推奨）

```bash
# backend/.env
LLM_PROVIDER=bedrock
LLM_MODEL=us.anthropic.claude-opus-4-6-20260201-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

### 4.3 Azure Foundry（最新GPT-5）

```bash
# backend/.env
LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5.2
AZURE_FOUNDRY_ENDPOINT=https://your-foundry.openai.azure.com/
AZURE_FOUNDRY_API_KEY=xxxxxxxx
AZURE_FOUNDRY_DEPLOYMENT=gpt-5-2-deployment
AZURE_FOUNDRY_API_VERSION=2026-01-01
```

### 4.4 GCP Vertex AI（コスト重視）

```bash
# backend/.env
LLM_PROVIDER=vertex_ai
LLM_MODEL=gemini-2.5-flash-lite
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GCP_CREDENTIALS_PATH=./credentials/gcp-credentials.json
```

### 4.5 Anthropic Claude（直接API）

```bash
# backend/.env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxxxxxxxxxxxxxxxx
```

### 4.6 OpenAI GPT（直接API）

```bash
# backend/.env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
OPENAI_API_KEY=sk-proj-xxxxxxxxxxxxxxxxxxxx
```

### 4.7 Google AI Studio

```bash
# backend/.env
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash-lite
GOOGLE_API_KEY=AIzaSy-xxxxxxxxxxxxxxxxxxxx
```

### 4.8 Ollama（ローカルLLM）

```bash
# Ollamaインストール（https://ollama.ai）
# モデルの取得
ollama pull phi4

# backend/.env
LLM_PROVIDER=ollama
LLM_MODEL=phi4
OLLAMA_BASE_URL=http://localhost:11434
```

### 4.9 接続テスト

```powershell
cd backend
.\venv\Scripts\activate
python -c "
from app.core.config import settings
print(f'Provider: {settings.llm_provider}')
print(f'Model: {settings.llm_model}')
print('Configuration OK')
"
```

---

## 5. セキュリティ設定

### 5.1 エンタープライズセキュリティ機能

JAIAには以下のセキュリティ機能が実装されています：

| 機能 | 説明 | 設定値 |
| ------ | ------ | -------- |
| レート制限 | IPベースのリクエスト制限 | 100リクエスト/分 |
| IPブロック | 違反者の自動ブロック | 10回違反で15分ブロック |
| 不正検出 | SQLi/XSS/ディレクトリトラバーサル | 自動検出・ブロック |
| セキュリティヘッダー | HSTS, CSP, X-Frame-Options等 | 自動付与 |

### 5.2 ログファイル

```
logs/
├── jaia.log          # アプリケーションログ
├── jaia_error.log    # エラーログ
├── jaia_audit.log    # 監査ログ（90日保持）
├── jaia_security.log # セキュリティログ（365日保持）
└── jaia_performance.log  # パフォーマンスログ
```

### 5.3 機密データの保護

ログ出力時にAPIキーは自動的にマスキングされます：

```
Before: API call failed: key=sk-ant-api03-abcdefghijk
After:  API call failed: key=sk-ant-***MASKED***
```

---

## 6. トラブルシューティング

### 5.1 よくある問題と解決方法

#### Python仮想環境の問題

**症状**: `venv\Scripts\Activate.ps1` が実行できない

**解決方法**:
```powershell
# PowerShell実行ポリシーを変更
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### OneDrive同期の問題

**症状**: 仮想環境作成時にエラー

**解決方法**:
1. OneDriveの同期を一時停止
2. 仮想環境を作成
3. OneDriveの同期を再開

#### ポート競合

**症状**: `Address already in use`

**解決方法**:
```powershell
# 使用中のポートを確認
netstat -ano | findstr :8000

# プロセスを終了（PIDを指定）
taskkill /PID <PID> /F
```

#### npm依存パッケージのエラー

**症状**: `npm install` 時にエラー

**解決方法**:
```powershell
# キャッシュをクリア
npm cache clean --force

# node_modulesを削除して再インストール
Remove-Item -Recurse -Force node_modules
npm install
```

### 5.2 ログの確認

#### バックエンドログ

```powershell
# リアルタイムログ表示
cd backend
python -m uvicorn app.main:app --reload --log-level debug
```

#### ログファイルの場所

```
backend/
└── logs/
    ├── jaia.log          # メインログ
    ├── jaia_error.log    # エラーログ
    └── jaia_audit.log    # 監査ログ
```

### 5.3 データベースの初期化

データベースを初期化する場合：

```powershell
# バックエンドディレクトリで実行
cd backend

# データベースファイルを削除
Remove-Item data/jaia.duckdb -ErrorAction SilentlyContinue
Remove-Item data/jaia_meta.db -ErrorAction SilentlyContinue

# アプリケーション再起動で自動作成
python -m uvicorn app.main:app --reload
```

### 5.4 サポート

問題が解決しない場合：

1. [GitHub Issues](https://github.com/your-org/journal-ai-auditor/issues) で報告
2. ログファイルを添付
3. 環境情報（OS、Pythonバージョン等）を記載

---

## 付録

### A. 動作確認チェックリスト

| # | 項目 | 確認コマンド | 期待結果 |
|---|------|-------------|---------|
| 1 | Python | `python --version` | 3.11.x |
| 2 | Node.js | `node --version` | 18.x.x |
| 3 | バックエンド起動 | `curl http://localhost:8000/health` | `{"status":"healthy"}` |
| 4 | フロントエンド起動 | ブラウザで http://localhost:3000 | ダッシュボード表示 |
| 5 | 統合テスト | `.\scripts\test_integration.ps1` | All tests passed |

### B. ファイルパス一覧

| 項目 | パス |
|------|------|
| 設定ファイル | `backend/.env` |
| メインログ | `backend/logs/jaia.log` |
| DuckDBデータベース | `backend/data/jaia.duckdb` |
| SQLiteメタデータ | `backend/data/jaia_meta.db` |
| サンプルデータ | `sample_data/` |
