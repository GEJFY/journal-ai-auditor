# JAIA クラウドプロバイダー設定ガイド（2026年最新版）

AI分析機能に使用するLLMプロバイダーの設定方法を説明します。

## 目次

1. [概要](#1-概要)
2. [AWS Bedrock（推奨・エンタープライズ）](#2-aws-bedrock推奨エンタープライズ)
3. [Azure AI Foundry（最新GPT-5）](#3-azure-ai-foundry最新gpt-5)
4. [GCP Vertex AI（コスパ・Gemini 3.0）](#4-gcp-vertex-aiコスパgemini-30)
5. [Anthropic Claude（直接API）](#5-anthropic-claude直接api)
6. [OpenAI GPT（直接API）](#6-openai-gpt直接api)
7. [Google AI Studio](#7-google-ai-studio)
8. [Azure OpenAI（レガシー）](#8-azure-openaiレガシー)
9. [Ollama（ローカルLLM）](#9-ollamaローカルllm)
10. [Dockerデプロイメント](#10-dockerデプロイメント)
11. [設定の確認](#11-設定の確認)
12. [トラブルシューティング](#12-トラブルシューティング)

---

## 1. 概要

### 対応プロバイダーとモデル（2026年2月最新）

| プロバイダー | モデル | Tier | コスト | 推奨用途 |
|-------------|--------|------|--------|---------|
| **AWS Bedrock** | Claude Opus 4.6 | Premium | 高 | **エンタープライズ推奨** |
| | Claude Sonnet 4.5 | Balanced | 中 | 汎用分析 |
| | Claude Haiku 4.5 | Fast | 低 | 高速処理 |
| | Amazon Nova Premier | Premium | 高 | AWS最適化 |
| **Azure Foundry** | GPT-5.2 | Premium | 非常に高 | **最高精度** |
| | GPT-5 Nano | Fast | 低 | 超高速処理 |
| | Claude Opus 4.6 | Premium | 高 | マルチモデル |
| **GCP Vertex AI** | Gemini 3 Pro | Premium | 高 | 高精度分析 |
| | Gemini 3 Flash Preview | Fast | 低 | **コスト重視** |
| | Gemini 2.5 Flash Lite | Fast | 非常に低 | バッチ処理 |
| **Anthropic** | Claude Opus 4.6 | Premium | 高 | 最高精度 |
| | Claude Sonnet 4.5 | Balanced | 中 | デフォルト推奨 |
| **OpenAI** | GPT-5.2 | Premium | 高 | 最先端分析 |
| | o3-pro | Reasoning | 非常に高 | 複雑な推論 |
| | o4-mini | Fast | 低 | 高速推論 |
| **Ollama** | Phi-4 | Local | 無料 | **開発・テスト** |
| | DeepSeek R1:14b | Local | 無料 | ローカル推論 |

### 推奨設定（ユースケース別）

| 用途 | プロバイダー | モデル | 説明 |
|------|-------------|--------|------|
| **最高精度** | Azure Foundry | gpt-5.2 | GPT-5.2による最先端分析 |
| **高精度** | AWS Bedrock | Claude Opus 4.6 | 複雑な調査、レポート生成 |
| **バランス** | GCP Vertex AI | gemini-3-pro | 日常的な分析（global リージョン） |
| **コスト重視** | GCP Vertex AI | gemini-2.5-flash-lite | 大量データ処理（リージョナル可） |
| **超高速** | Azure Foundry | gpt-5-nano | リアルタイム処理 |
| **ローカル開発** | Ollama | phi4 | GPU不要、即座に開始 |

### 設定ファイル

```bash
# backend/.env
LLM_PROVIDER=bedrock  # bedrock | azure_foundry | vertex_ai | anthropic | openai | google | azure | ollama
LLM_MODEL=us.anthropic.claude-opus-4-6-20260201-v1:0
```

---

## 2. AWS Bedrock（推奨・エンタープライズ）

### 利用可能モデル（2026年最新）

| モデル ID | 名前 | 特徴 | 推奨用途 |
|----------|------|------|---------|
| us.anthropic.claude-opus-4-6-20260201-v1:0 | Claude Opus 4.6 | 最新最高精度 | **エンタープライズ推奨** |
| us.anthropic.claude-sonnet-4-5-20250929-v1:0 | Claude Sonnet 4.5 | バランス良好 | 通常分析 |
| us.anthropic.claude-haiku-4-5-20251001-v1:0 | Claude Haiku 4.5 | 超高速 | 大量処理 |
| amazon.nova-premier-v1:0 | Amazon Nova Premier | AWS最高精度 | 大規模分析 |
| amazon.nova-pro-v1:0 | Amazon Nova Pro | AWS最適化 | AWSネイティブ |
| amazon.nova-lite-v1:0 | Amazon Nova Lite | 低コスト | バッチ処理 |
| amazon.nova-micro-v1:0 | Amazon Nova Micro | 超低コスト | テキスト処理 |

### セットアップ

1. AWS Management Consoleで Bedrock モデルアクセスを有効化
2. IAMユーザー/ロールを作成
3. 環境設定：

```bash
# backend/.env
LLM_PROVIDER=bedrock
LLM_MODEL=us.anthropic.claude-opus-4-6-20260201-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxx
```

### IAMポリシー

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": [
      "bedrock:InvokeModel",
      "bedrock:InvokeModelWithResponseStream"
    ],
    "Resource": "arn:aws:bedrock:*::foundation-model/*"
  }]
}
```

### 接続テスト

```powershell
cd backend
.\venv\Scripts\activate
python -c "
from app.services.llm import LLMService, LLMConfig
config = LLMConfig(provider='bedrock', model='us.anthropic.claude-opus-4-6-20260201-v1:0')
service = LLMService(config)
print('Bedrock connection: OK')
"
```

---

## 3. Azure AI Foundry（最新GPT-5）

### 利用可能モデル（2026年最新）

| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| gpt-5.2 | 最新GPT-5、最高精度 | **最先端分析** |
| gpt-5-nano | GPT-5軽量版、超高速 | リアルタイム処理 |
| gpt-4o | GPT-4最新、安定 | 汎用分析 |
| claude-sonnet-4 | Claude on Azure | マルチモデル |
| claude-haiku-3.5 | Claude高速 | 大量処理 |

### セットアップ

1. [Azure Portal](https://portal.azure.com/) で Azure AI Foundry リソースを作成
2. モデルをデプロイ
3. 環境設定：

```bash
# backend/.env
LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5.2
AZURE_FOUNDRY_ENDPOINT=https://your-foundry.openai.azure.com/
AZURE_FOUNDRY_API_KEY=xxxxxxxx
AZURE_FOUNDRY_DEPLOYMENT=gpt-5-2-deployment
AZURE_FOUNDRY_API_VERSION=2024-10-21
```

### 接続テスト

```powershell
python -c "
from app.services.llm import LLMService, LLMConfig
config = LLMConfig(provider='azure_foundry', model='gpt-5.2')
service = LLMService(config)
print('Azure AI Foundry connection: OK')
"
```

---

## 4. GCP Vertex AI（コスパ・Gemini 3.0）

### 利用可能モデル（2026年最新）

| モデル | 特徴 | リージョン | 推奨用途 |
|--------|------|-----------|---------|
| gemini-3-pro | Gemini 3最高精度 | **global のみ** | 高精度分析 |
| gemini-3-flash-preview | Gemini 3高速 | **global のみ** | 高速分析 |
| gemini-2.5-pro | Gemini 2.5バランス | global / リージョナル | 通常分析 |
| gemini-2.5-flash-lite | Gemini 2.5超低コスト | global / リージョナル | **コスト重視** |

> **重要**: Gemini 3.0シリーズは `GCP_LOCATION=global` でのみ利用可能です。
> Gemini 2.5は `us-central1`、`asia-northeast1` 等のリージョナルエンドポイントでも利用できます。

### セットアップ

1. [Google Cloud Console](https://console.cloud.google.com/) でプロジェクト作成
2. Vertex AI APIを有効化
3. サービスアカウントを作成し、JSONキーをダウンロード
4. 環境設定：

```bash
# backend/.env（Gemini 3.0を使用する場合）
LLM_PROVIDER=vertex_ai
LLM_MODEL=gemini-3-flash-preview
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global
GCP_CREDENTIALS_PATH=./credentials/gcp-credentials.json

# Gemini 2.5を使用する場合はリージョナルも可
# LLM_MODEL=gemini-2.5-flash-lite
# GCP_LOCATION=us-central1
```

### サービスアカウント権限

```
roles/aiplatform.user
```

### 接続テスト

```powershell
python -c "
from app.services.llm import LLMService, LLMConfig
config = LLMConfig(provider='vertex_ai', model='gemini-3-flash-preview')
service = LLMService(config)
print('Vertex AI connection: OK')
"
```

---

## 5. Anthropic Claude（直接API）

### 利用可能モデル

| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| claude-opus-4-6 | 最高精度、深い分析力 | 重要レポート |
| claude-sonnet-4-5 | バランス良好、高速 | **通常利用** |
| claude-haiku-4-5 | 超高速、低コスト | 大量処理 |

### セットアップ

1. [Anthropic Console](https://console.anthropic.com/) でAPIキー取得
2. 環境設定：

```bash
# backend/.env
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-api03-xxxxxx
```

---

## 6. OpenAI GPT（直接API）

### 利用可能モデル

| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| gpt-5.2 | 最新最高精度 | **最先端分析** |
| gpt-5 | GPT-5フラッグシップ | 汎用高精度 |
| gpt-5-mini | GPT-5軽量版 | 日常利用 |
| gpt-5-nano | GPT-5超軽量 | 超高速処理 |
| o3-pro | 最高推論精度 | 複雑な問題解決 |
| o3 | 高速推論 | 推論タスク |
| o4-mini | 推論（軽量） | コスパ推論 |

### セットアップ

```bash
# backend/.env
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-nano
OPENAI_API_KEY=sk-proj-xxxxxx
```

---

## 7. Google AI Studio

### 利用可能モデル

| モデル | 特徴 | 推奨用途 |
|--------|------|---------|
| gemini-3-flash-preview | Gemini 3.0最速 | 高速分析 |
| gemini-2.5-pro | Gemini 2.5高精度 | 汎用分析 |
| gemini-2.5-flash-lite | 超低コスト | **コスト重視** |

### セットアップ

```bash
# backend/.env
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash-lite
GOOGLE_API_KEY=AIzaSyxxxxxx
```

---

## 8. Azure OpenAI（レガシー）

### セットアップ

```bash
# backend/.env
LLM_PROVIDER=azure
LLM_MODEL=gpt-4o
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=xxxxxxxx
AZURE_OPENAI_DEPLOYMENT=gpt-4o-deployment
AZURE_OPENAI_API_VERSION=2024-10-21
```

---

## 9. Ollama（ローカルLLM）

クラウドAPI不要でローカル環境のみでAI分析が可能。開発・テスト・デモ用途に最適。

### 利用可能モデル

| モデル | パラメータ | 特徴 | 推奨用途 |
|--------|-----------|------|---------|
| phi4 | 14B | Microsoft製、バランス良好 | **開発推奨** |
| qwen2.5-coder:14b | 14B | コード特化 | コード分析 |
| deepseek-r1:14b | 14B | 推論特化 | 推論タスク |
| llama3.3:8b | 8B | Meta製、汎用 | 軽量テスト |
| gemma3:27b | 27B | Google製、高精度 | 高品質ローカル |

### セットアップ

1. Ollamaをインストール:

```bash
# Linux/macOS
curl -fsSL https://ollama.ai/install.sh | sh

# Windows
# https://ollama.com/download からインストーラーをダウンロード
```

2. モデルをダウンロード:

```bash
# 推奨モデル（約8GB）
ollama pull phi4

# 軽量テスト用（約4GB）
ollama pull llama3.3:8b
```

3. 環境設定:

```bash
# backend/.env
LLM_PROVIDER=ollama
LLM_MODEL=phi4
OLLAMA_BASE_URL=http://localhost:11434
```

### 動作確認

```bash
# Ollamaサーバー起動（通常は自動起動）
ollama serve

# モデル一覧確認
ollama list

# テスト生成
ollama run phi4 "Hello, world!"
```

### 接続テスト

```powershell
python -c "
from app.services.llm import LLMService, LLMConfig
config = LLMConfig(provider='ollama', model='phi4')
service = LLMService(config)
response = service.generate('Say hello in Japanese')
print(f'Response: {response.content}')
"
```

### 注意事項

- GPU（NVIDIA/AMD）があると高速化されるが、CPU でも動作可能
- phi4 (14B) は 16GB RAM 以上を推奨
- llama3.3:8b は 8GB RAM でも動作可能
- 本番環境での使用は非推奨（精度・安定性の観点）

---

## 10. Dockerデプロイメント

### 開発環境

```bash
# .envファイルを作成
cp .env.example .env
# APIキーを設定

# 開発用コンテナ起動
docker-compose -f docker-compose.dev.yml up -d

# ログ確認
docker-compose -f docker-compose.dev.yml logs -f
```

### 本番環境（クラウドプロバイダー別）

#### AWS Bedrock使用時

```bash
# .env
LLM_PROVIDER=bedrock
LLM_MODEL=us.anthropic.claude-opus-4-6-20260201-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIAxxxxxxxx
AWS_SECRET_ACCESS_KEY=xxxxxxxx

# 起動
docker-compose up -d
```

#### Azure Foundry使用時

```bash
# .env
LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5.2
AZURE_FOUNDRY_ENDPOINT=https://your-foundry.openai.azure.com/
AZURE_FOUNDRY_API_KEY=xxxxxxxx
AZURE_FOUNDRY_DEPLOYMENT=gpt-5-2-deployment

# 起動
docker-compose up -d
```

#### GCP Vertex AI使用時

```bash
# .env
LLM_PROVIDER=vertex_ai
LLM_MODEL=gemini-3-flash-preview
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=global
GCP_CREDENTIALS_PATH=./credentials/gcp-credentials.json

# 起動
docker-compose up -d
```

### Docker Compose設定

```yaml
# docker-compose.yml
services:
  backend:
    build: .
    ports:
      - "8090:8090"
    environment:
      - LLM_PROVIDER=${LLM_PROVIDER:-bedrock}
      - LLM_MODEL=${LLM_MODEL:-anthropic.claude-sonnet-4-6-opus-20260115-v1:0}
      # AWS Bedrock
      - AWS_REGION=${AWS_REGION:-us-east-1}
      - AWS_ACCESS_KEY_ID=${AWS_ACCESS_KEY_ID:-}
      - AWS_SECRET_ACCESS_KEY=${AWS_SECRET_ACCESS_KEY:-}
      # Azure Foundry
      - AZURE_FOUNDRY_ENDPOINT=${AZURE_FOUNDRY_ENDPOINT:-}
      - AZURE_FOUNDRY_API_KEY=${AZURE_FOUNDRY_API_KEY:-}
      - AZURE_FOUNDRY_DEPLOYMENT=${AZURE_FOUNDRY_DEPLOYMENT:-}
      # GCP Vertex AI
      - GCP_PROJECT_ID=${GCP_PROJECT_ID:-}
      - GCP_LOCATION=${GCP_LOCATION:-us-central1}
      - GOOGLE_APPLICATION_CREDENTIALS=/app/credentials/gcp-credentials.json
    volumes:
      - jaia-data:/app/data
      - ${GCP_CREDENTIALS_PATH:-./credentials}:/app/credentials:ro

  frontend:
    image: nginx:alpine
    ports:
      - "80:80"
    depends_on:
      - backend
```

### ヘルスチェック

```bash
# バックエンド
curl http://localhost:8090/health

# API
curl http://localhost:8090/api/v1/health
```

---

## 11. 設定の確認

### コマンドラインで確認

```powershell
cd backend
.\venv\Scripts\activate
python -c "
from app.core.config import settings, LLM_MODELS, RECOMMENDED_MODELS
print(f'Provider: {settings.llm_provider}')
print(f'Model: {settings.llm_model}')
print(f'Available models: {list(LLM_MODELS[settings.llm_provider].keys())}')
"
```

### 利用可能モデル一覧

```powershell
python -c "
from app.services.llm import LLMService
models = LLMService.get_available_models()
for provider, model_list in models.items():
    print(f'\n{provider}:')
    for m in model_list:
        print(f'  - {m.id} ({m.tier}, {m.cost})')
"
```

### 推奨モデル一覧

```powershell
python -c "
from app.services.llm import LLMService
recommended = LLMService.get_recommended_models()
for use_case, info in recommended.items():
    print(f'{use_case}: {info[\"provider\"]}/{info[\"model\"]} - {info[\"description\"]}')
"
```

---

## 12. トラブルシューティング

### 共通の問題

| エラー | 原因 | 解決策 |
|--------|------|--------|
| 接続エラー | APIキー未設定 | .envファイルを確認 |
| 認証エラー | キー無効/期限切れ | 新しいキーを生成 |
| モデル不明 | モデルID誤り | 利用可能モデル一覧を確認 |
| レート制限 | リクエスト過多 | 待機して再試行 |

### プロバイダー別

#### AWS Bedrock

- モデルアクセスを有効化必須（Consoleで設定）
- IAMポリシー設定必須
- リージョン: us-east-1 または us-west-2 推奨

#### Azure AI Foundry

- GPT-5モデルはプレビュー申請が必要な場合あり
- デプロイメント名を確認
- APIバージョンは `2024-10-21`
- SDK: `azure-ai-inference` (`pip install azure-ai-inference azure-core`)

#### GCP Vertex AI

- Vertex AI APIを有効化必須
- サービスアカウントに `roles/aiplatform.user` 権限付与
- **Gemini 3.0は `GCP_LOCATION=global` のみ対応**（リージョナルエンドポイント不可）
- Gemini 2.5は `us-central1` 等リージョナルでも利用可

---

## セキュリティベストプラクティス

1. **APIキーの保護**
   - `.env`ファイルに保存
   - `.gitignore`に追加
   - 本番では環境変数/シークレットマネージャー使用

2. **クラウドプロバイダー認証**
   - AWS: IAMロール使用（EC2/ECS）
   - Azure: Managed Identity使用
   - GCP: Workload Identity使用

3. **最小権限の原則**
   - 必要な権限のみ付与
   - 環境ごとに別キーを使用

4. **監視**
   - 使用量ダッシュボードを確認
   - 異常なアクセスをアラート

5. **キーローテーション**
   - 定期的に更新
   - 漏洩時は即座に無効化
