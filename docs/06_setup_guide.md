# JAIA セットアップガイド

## 2026 Cloud Edition - マルチプロバイダー対応（8社対応）

本ドキュメントでは、JAIA（Journal entry AI Analyzer）の開発環境および本番環境のセットアップ手順を、初めての方でもステップバイステップで進められるよう詳細に説明します。

**最終更新**: 2026年2月

---

## 目次

1. [JAIAとは？](#1-jaiaとは)
2. [動作要件](#2-動作要件)
3. [開発環境セットアップ](#3-開発環境セットアップ)
4. [LLM設定（8プロバイダー対応）](#4-llm設定8プロバイダー対応)
5. [動作確認](#5-動作確認)
6. [本番環境セットアップ](#6-本番環境セットアップ)
7. [Docker によるデプロイ](#7-docker-によるデプロイ)
8. [セキュリティ設定](#8-セキュリティ設定)
9. [トラブルシューティング](#9-トラブルシューティング)
10. [付録](#付録)

---

## 1. JAIAとは？

JAIA（Journal entry AI Analyzer）は、企業の仕訳データを自動で分析し、内部監査業務を支援するアプリケーションです。

**何ができるの？**

- 仕訳データの異常を58の監査ルールで自動検出
- AIエージェントが監査人のように分析・レポート作成
- リスクスコアリング（0〜100点）で優先度を可視化
- ベンフォード分析で数値の不正パターンを検出
- PPT/PDF形式の監査報告書を自動生成

**技術スタック**

| コンポーネント | 技術 | 説明 |
|-------------|------|------|
| バックエンド | Python 3.11 + FastAPI | REST API サーバー |
| フロントエンド | React + TypeScript | Web UI（ダッシュボード等） |
| データベース | DuckDB + SQLite | 仕訳データ + メタデータ |
| AI | LangGraph + 8社LLM | マルチエージェント分析 |

---

## 2. 動作要件

### 2.1 必須ソフトウェア

以下のソフトウェアがインストールされている必要があります。

| ソフトウェア | バージョン | 確認コマンド | インストール方法 |
|-------------|-----------|-------------|----------------|
| **Python** | 3.11以上 | `python --version` | [python.org](https://www.python.org/downloads/) |
| **Node.js** | 18以上 | `node --version` | [nodejs.org](https://nodejs.org/) |
| **npm** | 9以上 | `npm --version` | Node.jsに同梱 |
| **Git** | 2.30以上 | `git --version` | [git-scm.com](https://git-scm.com/downloads) |

> **初心者の方へ**: Pythonをインストールする際、「Add Python to PATH」にチェックを入れてください。Node.jsはLTS版（推奨版）を選んでください。

### 2.2 推奨スペック

| 項目 | 最小要件 | 推奨 |
|------|---------|------|
| OS | Windows 10, macOS 12, Ubuntu 20.04 | Windows 11, macOS 14, Ubuntu 22.04 |
| CPU | 4コア | 8コア以上 |
| メモリ | 8GB | 16GB以上 |
| ディスク | 10GB空き | SSD 20GB以上 |

### 2.3 ネットワーク要件

- インターネット接続（パッケージダウンロード時に必要）
- クラウドLLM使用時は外部接続が必要
- Ollama（ローカルLLM）使用時はオフライン動作可能

---

## 3. 開発環境セットアップ

### 3.1 リポジトリのクローン

まず、プロジェクトのソースコードをダウンロードします。

```powershell
# ターミナル（PowerShell）を開いて実行
git clone https://github.com/GEJFY/journal-ai-auditor.git

# プロジェクトディレクトリに移動
cd journal-ai-auditor
```

> **「git clone」とは？** GitHubにあるソースコードをローカルPCにコピーするコマンドです。

### 3.2 自動セットアップ（推奨）

PowerShellを開き、以下を実行するだけで全てセットアップされます：

```powershell
# セットアップスクリプトを実行
.\scripts\setup.ps1
```

このスクリプトは以下を自動で行います：
1. Pythonバージョンの確認
2. Node.jsバージョンの確認
3. バックエンド仮想環境の作成
4. Python依存パッケージのインストール
5. フロントエンドnpm依存パッケージのインストール
6. データディレクトリの作成
7. `.env`ファイルの作成（テンプレートから）

> **エラーが出た場合は？** → [3.3 手動セットアップ](#33-手動セットアップ) に進んでください。

### 3.3 手動セットアップ

自動セットアップが失敗した場合や、各ステップを理解したい方向けの手順です。

#### ステップ 1: バックエンドの準備

```powershell
# backendディレクトリに移動
cd backend

# Python仮想環境を作成（プロジェクト専用のPython環境）
python -m venv venv

# 仮想環境を有効化（プロンプトの先頭に (venv) が表示されます）
.\venv\Scripts\Activate.ps1

# 依存パッケージをインストール（数分かかります）
pip install -e ".[dev]"

# データディレクトリを作成
mkdir -p data
```

> **「仮想環境」とは？** プロジェクト専用のPython環境です。他のプロジェクトとパッケージが混ざらないようにします。

> **PowerShellでエラーが出る場合**: 実行ポリシーを変更する必要があります：
> ```powershell
> Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
> ```

#### ステップ 2: 環境変数の設定

```powershell
# テンプレートから.envファイルを作成
copy .env.example .env
```

作成された `backend/.env` ファイルをテキストエディタで開き、LLMプロバイダーの設定を行います（次の章で詳しく説明します）。

#### ステップ 3: フロントエンドの準備

```powershell
# プロジェクトルートに戻る
cd ..

# frontendディレクトリに移動
cd frontend

# npm依存パッケージをインストール（数分かかります）
npm install
```

#### ステップ 4: 起動確認

2つのターミナルを開きます。

**ターミナル1 — バックエンド:**

```powershell
cd backend
.\venv\Scripts\activate
python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload
```

成功すると以下が表示されます：

```
INFO:     Uvicorn running on http://127.0.0.1:8090 (Press CTRL+C to quit)
INFO:     Started reloader process
```

ブラウザで http://127.0.0.1:8090/docs を開くと、API仕様書が表示されます。

**ターミナル2 — フロントエンド:**

```powershell
cd frontend
npm run dev
```

成功すると以下が表示されます：

```
  VITE v6.x.x  ready in xxx ms

  ➜  Local:   http://localhost:5290/
```

ブラウザで http://localhost:5290 を開くと、JAIAのダッシュボードが表示されます。

---

## 4. LLM設定（8プロバイダー対応）

JAIAは8つのLLMプロバイダーに対応しています。AI分析機能を使用するには、いずれか1つを設定してください。

### 4.1 プロバイダー比較表

| # | プロバイダー | 推奨モデル | コスト | 特徴 | 難易度 |
|---|-------------|-----------|--------|------|--------|
| 1 | **Ollama** | phi4 | 無料 | ローカル実行、APIキー不要 | ★☆☆ 簡単 |
| 2 | **Anthropic** | claude-sonnet-4-5 | 中 | 高品質、簡単なAPI設定 | ★☆☆ 簡単 |
| 3 | **OpenAI** | gpt-5-mini | 中 | 汎用性が高い | ★☆☆ 簡単 |
| 4 | **Google AI** | gemini-2.5-flash-lite | 低 | 開発向け、低コスト | ★☆☆ 簡単 |
| 5 | **AWS Bedrock** | Claude Opus 4.6 | 高 | エンタープライズ推奨 | ★★★ 上級 |
| 6 | **Azure Foundry** | GPT-5.2 | 高 | 最高精度 | ★★★ 上級 |
| 7 | **GCP Vertex AI** | Gemini 3 Pro | 中 | 最新Geminiシリーズ | ★★★ 上級 |
| 8 | **Azure OpenAI** | GPT-4o | 中 | レガシー（既存ユーザー向け） | ★★☆ 中級 |

> **初心者の方へ**: まず **Ollama**（無料・APIキー不要）から始めることをお勧めします。

### 4.2 Ollama（ローカルLLM・最も簡単）

APIキー不要で、PC上でAIを動かします。

#### インストール手順

1. https://ollama.ai にアクセスし、「Download」をクリック
2. お使いのOS用のインストーラーを実行
3. ターミナルを開いて、モデルをダウンロード：

```powershell
# phi4モデルをダウンロード（約8GB、数分かかります）
ollama pull phi4

# ダウンロード完了後、正常動作を確認
ollama run phi4 "Hello"
```

#### 設定

`backend/.env` ファイルに以下を記載：

```ini
LLM_PROVIDER=ollama
LLM_MODEL=phi4
OLLAMA_BASE_URL=http://localhost:11434
```

#### 利用可能なモデル

| モデル | サイズ | 特徴 | ダウンロードコマンド |
|--------|--------|------|-------------------|
| phi4 | 8GB | バランス良好（推奨） | `ollama pull phi4` |
| gemma3:27b | 16GB | 高精度 | `ollama pull gemma3:27b` |
| qwen2.5-coder:14b | 9GB | コード分析に強い | `ollama pull qwen2.5-coder:14b` |
| deepseek-r1:14b | 9GB | 推論能力が高い | `ollama pull deepseek-r1:14b` |
| llama3.3:8b | 5GB | 軽量・高速 | `ollama pull llama3.3:8b` |

### 4.3 Anthropic Claude（直接API）

[Anthropic Console](https://console.anthropic.com/) でAPIキーを取得し、設定します。

#### APIキー取得手順

1. https://console.anthropic.com/ にアクセス
2. アカウントを作成（メールアドレスで登録）
3. 「API Keys」→「Create Key」でキーを生成
4. 生成されたキー（`sk-ant-api03-...`）をコピー

#### 設定

```ini
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-api03-あなたのキーをここに貼り付け
```

#### 利用可能なモデル

| モデル | 特徴 | コスト |
|--------|------|--------|
| claude-opus-4-6 | 最高精度、複雑な分析向け | 非常に高い |
| claude-sonnet-4-5 | バランス良好（推奨） | 中 |
| claude-haiku-4-5 | 高速・低コスト | 低 |

### 4.4 OpenAI GPT（直接API）

[OpenAI Platform](https://platform.openai.com/) でAPIキーを取得します。

#### APIキー取得手順

1. https://platform.openai.com/ にアクセス
2. アカウントを作成
3. 「API Keys」→「Create new secret key」
4. 生成されたキー（`sk-proj-...`）をコピー

#### 設定

```ini
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
OPENAI_API_KEY=sk-proj-あなたのキーをここに貼り付け
```

#### 利用可能なモデル

| モデル | 特徴 | コスト |
|--------|------|--------|
| gpt-5.2 | 最高精度（ARC-AGI 90%+） | 非常に高い |
| gpt-5 | 高精度 | 高 |
| gpt-5-mini | バランス良好（推奨） | 中 |
| gpt-5-nano | 超高速・低コスト | 低 |
| o3-pro | 推論特化（数学・論理） | 非常に高い |
| o3 | 推論特化 | 高 |
| o4-mini | 推論特化・軽量 | 中 |

### 4.5 Google AI Studio

[Google AI Studio](https://aistudio.google.com/) でAPIキーを取得します。

#### APIキー取得手順

1. https://aistudio.google.com/ にアクセス
2. Googleアカウントでサインイン
3. 「Get API key」→「Create API key」
4. 生成されたキー（`AIzaSy-...`）をコピー

#### 設定

```ini
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash-lite
GOOGLE_API_KEY=AIzaSy-あなたのキーをここに貼り付け
```

#### 利用可能なモデル

| モデル | 特徴 | コスト |
|--------|------|--------|
| gemini-3-flash-preview | 最新（プレビュー） | 低 |
| gemini-2.5-pro | 高精度 | 高 |
| gemini-2.5-flash-lite | 開発向け（推奨） | 非常に低い |

### 4.6 AWS Bedrock（エンタープライズ推奨）

AWSアカウントとIAM権限が必要です。エンタープライズ環境で最も安定した選択肢です。

#### 前提条件

- AWSアカウント
- IAMユーザーまたはロールに `bedrock:InvokeModel` 権限
- 使用するモデルのアクセスリクエスト承認済み

#### セットアップ手順

1. [AWS Console](https://console.aws.amazon.com/bedrock/) → Amazon Bedrock
2. 「Model access」→ 使用したいモデルの「Request model access」をクリック
3. 承認を待つ（数分〜数時間）
4. IAMでアクセスキーを作成

#### 設定

```ini
LLM_PROVIDER=bedrock
LLM_MODEL=us.anthropic.claude-opus-4-6-20260201-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAxxxxxxxxxxxxxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
```

#### 利用可能なモデル

| モデルID | モデル名 | 特徴 |
|---------|---------|------|
| us.anthropic.claude-opus-4-6-20260201-v1:0 | Claude Opus 4.6 | 最高精度 |
| us.anthropic.claude-sonnet-4-5-20250929-v1:0 | Claude Sonnet 4.5 | バランス |
| us.anthropic.claude-haiku-4-5-20251001-v1:0 | Claude Haiku 4.5 | 高速 |
| amazon.nova-premier-v1:0 | Nova Premier | AWS製・高精度 |
| amazon.nova-pro-v1:0 | Nova Pro | AWS製・バランス |
| amazon.nova-lite-v1:0 | Nova Lite | AWS製・高速 |
| amazon.nova-micro-v1:0 | Nova Micro | AWS製・超高速 |
| us.deepseek.r1-v1:0 | DeepSeek R1 | 推論特化 |

### 4.7 Azure AI Foundry（最新GPT-5シリーズ）

GPT-5.2やClaude Opus 4.6を含む最新モデルにアクセスできます。

#### 前提条件

- Azureサブスクリプション
- Azure AI Foundryリソースの作成

#### セットアップ手順

1. [Azure Portal](https://portal.azure.com/) → 「Azure AI Foundry」を検索
2. リソースを作成 → デプロイメントを追加
3. エンドポイントURLとAPIキーを取得

#### 設定

```ini
LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5.2
AZURE_FOUNDRY_ENDPOINT=https://your-foundry.openai.azure.com/
AZURE_FOUNDRY_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_FOUNDRY_DEPLOYMENT=gpt-5-2-deployment
AZURE_FOUNDRY_API_VERSION=2026-01-01
```

#### 利用可能なモデル

| モデル | 特徴 | コスト |
|--------|------|--------|
| gpt-5.2 | 最高精度（推奨） | 非常に高い |
| gpt-5 | 高精度 | 高 |
| gpt-5-nano | 超高速 | 低 |
| claude-opus-4-6 | Claude最高精度 | 非常に高い |
| claude-sonnet-4-5 | Claudeバランス | 中 |
| claude-haiku-4-5 | Claude高速 | 低 |

### 4.8 GCP Vertex AI（Gemini 3シリーズ）

Google Cloudの最新Geminiモデルにアクセスできます。

#### 前提条件

- GCPプロジェクト
- Vertex AI API の有効化
- サービスアカウントキー

#### セットアップ手順

1. [GCP Console](https://console.cloud.google.com/) → 「Vertex AI」
2. 「API を有効にする」をクリック
3. IAM → サービスアカウント → キーを作成（JSON形式）
4. ダウンロードしたJSONファイルを `credentials/` に配置

> **重要**: Gemini 3.0シリーズは **Globalリージョンのみ** 対応。Gemini 2.5はリージョナル（us-central1等）も利用可。

#### 設定

```ini
LLM_PROVIDER=vertex_ai
LLM_MODEL=gemini-3-flash-preview
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global
GCP_CREDENTIALS_PATH=./credentials/gcp-credentials.json
```

#### 利用可能なモデル

| モデル | リージョン | 特徴 |
|--------|----------|------|
| gemini-3-pro | global のみ | 最高精度 |
| gemini-3-flash-preview | global のみ | バランス（推奨） |
| gemini-2.5-pro | us-central1 等 | 安定版 |
| gemini-2.5-flash-lite | us-central1 等 | 低コスト |

### 4.9 Azure OpenAI（レガシー）

既存のAzure OpenAIリソースをお持ちの方向けです。新規の方はAzure Foundryを推奨します。

#### 設定

```ini
LLM_PROVIDER=azure
LLM_MODEL=gpt-4o
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=xxxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
AZURE_OPENAI_DEPLOYMENT=gpt-4o-deployment
```

### 4.10 接続テスト

設定後、以下のコマンドで接続を確認します：

```powershell
cd backend
.\venv\Scripts\activate
python -c "
from app.core.config import settings
print(f'Provider: {settings.llm_provider}')
print(f'Model:    {settings.llm_model}')
print('Configuration OK')
"
```

出力例：

```
Provider: ollama
Model:    phi4
Configuration OK
```

### 4.11 ユースケース別おすすめ構成

| ユースケース | プロバイダー | モデル | 理由 |
|-------------|-------------|--------|------|
| 初めて試す | Ollama | phi4 | 無料、APIキー不要 |
| 個人開発 | Anthropic | claude-sonnet-4-5 | 高品質、簡単 |
| コスト重視 | Google AI | gemini-2.5-flash-lite | 非常に低コスト |
| 最高精度 | Azure Foundry | gpt-5.2 | ARC-AGI 90%+ |
| エンタープライズ | AWS Bedrock | Claude Opus 4.6 | セキュリティ・可用性 |
| 大量処理 | Vertex AI | gemini-3-flash-preview | 高速・低コスト |
| オフライン環境 | Ollama | gemma3:27b | ネットワーク不要 |

---

## 5. 動作確認

### 5.1 ヘルスチェック

バックエンド起動後、以下のURLにアクセス：

- http://127.0.0.1:8090/health → `{"status":"healthy"}` が表示されればOK
- http://127.0.0.1:8090/docs → Swagger UIでAPIを確認

### 5.2 統合テスト

```powershell
# プロジェクトルートで実行
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

### 5.3 ユニットテスト

```powershell
# バックエンドテスト（338テスト）
cd backend
.\venv\Scripts\activate
python -m pytest tests/ -v

# フロントエンドテスト（46テスト）
cd frontend
npm test
```

---

## 6. 本番環境セットアップ

### 6.1 サーバー構成

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

### 6.2 本番用環境変数

```bash
# .env.production
JAIA_DEBUG=false
JAIA_LOG_LEVEL=WARNING
ENVIRONMENT=production

# データベース
DUCKDB_PATH=/app/data/jaia.duckdb
SQLITE_PATH=/app/data/jaia_meta.db

# CORS設定
CORS_ORIGINS=["https://your-domain.com"]

# レート制限
RATE_LIMIT_ENABLED=true
RATE_LIMIT_REQUESTS=100
RATE_LIMIT_WINDOW=60
```

---

## 7. Docker によるデプロイ

JAIAはバックエンド・フロントエンドの両方をDockerで起動できます。

### 7.1 本番モード（Web版 — これだけで完結）

```bash
# バックエンド + フロントエンド（Nginx）を一括起動
docker-compose up -d --build

# → http://localhost でアクセス（ポート80）
# → http://localhost:8090/docs でAPI仕様書

# ログ確認
docker-compose logs -f

# 停止
docker-compose down
```

フロントエンドはマルチステージビルド（Node.js でビルド → Nginx Alpine で配信）で、`frontend/Dockerfile` で定義されています。

### 7.2 開発モード（推奨 — バックエンドDocker + ローカルVite）

```bash
# バックエンドをDocker、フロントエンドはローカル（HMR高速）
docker-compose -f docker-compose.dev.yml up --build

# 別ターミナルでフロントエンド起動
cd frontend
npm run dev

# → http://localhost:5173 でアクセス
```

### 7.3 開発モード（全Docker）

```bash
# バックエンド + フロントエンド両方Docker（--profile full）
docker-compose -f docker-compose.dev.yml --profile full up

# → http://localhost:5173 でアクセス
```

> **注意**: Windows Docker上ではファイル監視にポーリングを使用するため、HMRが若干遅くなります。高速な開発にはセクション 7.2 を推奨します。

### 7.4 バックエンド単体ビルド

```bash
# backend/ ディレクトリをコンテキストとしてビルド
cd backend
docker build -t jaia-backend:latest .

# 実行
docker run -d \
  --name jaia-backend \
  -p 8090:8090 \
  -e LLM_PROVIDER=ollama \
  -e LLM_MODEL=phi4 \
  -v jaia-data:/app/data \
  jaia-backend:latest
```

### 7.5 ファイアウォール設定

```bash
# バックエンドポート
ufw allow 8090/tcp

# フロントエンドポート（Nginx使用時）
ufw allow 80/tcp

# SSH（管理用）
ufw allow 22/tcp

# 有効化
ufw enable
```

---

## 8. セキュリティ設定

### 8.1 エンタープライズセキュリティ機能

JAIAには以下のセキュリティ機能が組み込まれています：

| 機能 | 説明 | 設定値 |
|------|------|--------|
| レート制限 | IPベースのリクエスト制限 | 100リクエスト/分 |
| IPブロック | 違反者の自動ブロック | 10回違反で15分ブロック |
| 不正検出 | SQLi/XSS/ディレクトリトラバーサル | 自動検出・ブロック |
| セキュリティヘッダー | HSTS, CSP, X-Frame-Options等 | 自動付与 |

### 8.2 APIキーの保護

- APIキーは **`.env`ファイルのみ** に記載（Gitにコミットしない）
- `.gitignore` に `.env` が含まれていることを確認
- ログ出力時はAPIキーが自動マスキングされます：

```
Before: API call failed: key=sk-ant-api03-abcdefghijk
After:  API call failed: key=sk-ant-***MASKED***
```

### 8.3 ログファイル

```
backend/logs/
├── jaia.log              # アプリケーションログ
├── jaia_error.log        # エラーログ
├── jaia_audit.log        # 監査ログ（90日保持）
├── jaia_security.log     # セキュリティログ（365日保持）
└── jaia_performance.log  # パフォーマンスログ
```

---

## 9. トラブルシューティング

### 9.1 よくある問題と解決方法

#### Python仮想環境の問題

**症状**: `venv\Scripts\Activate.ps1` が実行できない

**原因**: PowerShellの実行ポリシーがスクリプト実行を許可していない

**解決方法**:
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

#### OneDrive同期の問題

**症状**: 仮想環境作成時にエラーが発生する

**原因**: OneDriveがvenvディレクトリを同期しようとして競合する

**解決方法**:
1. OneDriveの同期を一時停止（タスクバーのOneDriveアイコンを右クリック）
2. 仮想環境を作成 (`python -m venv venv`)
3. OneDriveの同期を再開

#### ポート競合

**症状**: `Address already in use`

**原因**: 別のプロセスが同じポートを使用中

**解決方法**:
```powershell
# 使用中のポートを確認
netstat -ano | findstr :8090

# プロセスを終了（PIDを指定）
taskkill /PID <表示されたPID> /F

# または別のポートで起動
python -m uvicorn app.main:app --port 8002
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

#### LLM接続エラー

**症状**: `LLM provider error` または `API key is invalid`

**チェックリスト**:
1. `.env` ファイルの `LLM_PROVIDER` が正しいプロバイダー名か確認
2. APIキーに余分な空白や改行がないか確認
3. APIキーの有効期限が切れていないか確認
4. Ollama使用時は `ollama serve` が起動しているか確認

### 9.2 データベースの初期化

データベースを完全にリセットしたい場合：

```powershell
cd backend

# データベースファイルを削除
Remove-Item data/jaia.duckdb -ErrorAction SilentlyContinue
Remove-Item data/jaia_meta.db -ErrorAction SilentlyContinue

# アプリケーション再起動で自動作成
python -m uvicorn app.main:app --reload
```

### 9.3 ログの確認

```powershell
# リアルタイムログ表示（デバッグモード）
cd backend
python -m uvicorn app.main:app --reload --log-level debug
```

### 9.4 サポート

問題が解決しない場合：

1. [GitHub Issues](https://github.com/GEJFY/journal-ai-auditor/issues) で報告
2. ログファイル（`backend/logs/jaia.log`）を添付
3. 環境情報（OS、Pythonバージョン、エラーメッセージ）を記載

---

## 付録

### A. 動作確認チェックリスト

| # | 項目 | 確認コマンド | 期待結果 |
|---|------|-------------|---------|
| 1 | Python | `python --version` | 3.11.x 以上 |
| 2 | Node.js | `node --version` | 18.x.x 以上 |
| 3 | バックエンド起動 | `curl http://localhost:8090/health` | `{"status":"healthy"}` |
| 4 | フロントエンド起動 | ブラウザで http://localhost:5290 | ダッシュボード表示 |
| 5 | 統合テスト | `.\scripts\test_integration.ps1` | All tests passed |

### B. ファイルパス一覧

| 項目 | パス |
|------|------|
| バックエンド設定 | `backend/.env` |
| メインログ | `backend/logs/jaia.log` |
| DuckDBデータベース | `backend/data/jaia.duckdb` |
| SQLiteメタデータ | `backend/data/jaia_meta.db` |
| サンプルデータ | `sample_data/` |
| GCP認証情報 | `credentials/gcp-credentials.json` |

### C. ポート一覧

| サービス | デフォルトポート | 設定変数 |
|---------|----------------|---------|
| バックエンドAPI | 8090 | `PORT` |
| フロントエンド（開発） | 5290 | `vite.config.ts` |
| Ollama | 11434 | `OLLAMA_BASE_URL` |

### D. 8プロバイダー設定早見表

| プロバイダー | `.env` の `LLM_PROVIDER` | 必須環境変数 |
|-------------|------------------------|------------|
| Ollama | `ollama` | `OLLAMA_BASE_URL` |
| Anthropic | `anthropic` | `ANTHROPIC_API_KEY` |
| OpenAI | `openai` | `OPENAI_API_KEY` |
| Google AI | `google` | `GOOGLE_API_KEY` |
| AWS Bedrock | `bedrock` | `AWS_REGION`, `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY` |
| Azure Foundry | `azure_foundry` | `AZURE_FOUNDRY_ENDPOINT`, `AZURE_FOUNDRY_API_KEY`, `AZURE_FOUNDRY_DEPLOYMENT` |
| GCP Vertex AI | `vertex_ai` | `GCP_PROJECT_ID`, `GCP_LOCATION`, `GCP_CREDENTIALS_PATH` |
| Azure OpenAI | `azure` | `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT` |
