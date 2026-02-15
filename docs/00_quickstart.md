# JAIA クイックスタートガイド

このガイドでは、JAIAを最短で起動する方法を説明します。

## 必要なもの

- Python 3.11以上
- Node.js 20以上
- LLMプロバイダーのAPIキー（いずれか1つ、Ollamaならキー不要）

## 対応LLMプロバイダー（8種類）

| プロバイダー | 用途 | APIキー |
|------------|------|---------|
| Ollama | ローカルLLM（初心者向け） | 不要 |
| Anthropic | Claude直接呼出し | 必要 |
| OpenAI | GPT直接呼出し | 必要 |
| Google AI Studio | Gemini直接呼出し | 必要 |
| AWS Bedrock | エンタープライズ（Claude/Nova） | AWS認証 |
| Azure AI Foundry | エンタープライズ（GPT-5/Claude） | 必要 |
| GCP Vertex AI | エンタープライズ（Gemini） | GCP認証 |
| Azure OpenAI | Azure経由GPT | 必要 |

## 5分でスタート

### Step 1: リポジトリのクローン

```powershell
git clone https://github.com/GEJFY/journal-ai-auditor.git
cd journal-ai-auditor
```

### Step 2: バックエンドのセットアップ

```powershell
cd backend

# 仮想環境を作成
python -m venv venv

# 仮想環境を有効化
.\venv\Scripts\activate

# 依存関係をインストール
pip install -r requirements.txt

# 環境設定ファイルを作成
copy .env.example .env
```

### Step 3: APIキーの設定

`.env`ファイルを開いて、使用するLLMプロバイダーのAPIキーを設定します。
最もシンプルなものから順に記載しています。

#### オプション A: Ollama（ローカルLLM・APIキー不要・最も簡単）

```ini
LLM_PROVIDER=ollama
LLM_MODEL=phi4
OLLAMA_BASE_URL=http://localhost:11434
```

> 事前にOllamaをインストール: https://ollama.ai → `ollama pull phi4` でモデル取得

#### オプション B: Anthropic Claude（推奨）

```ini
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-api03-あなたのキー
```

#### オプション C: OpenAI GPT

```ini
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
OPENAI_API_KEY=sk-proj-あなたのキー
```

#### オプション D: Google AI Studio (Gemini)

```ini
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash-lite
GOOGLE_API_KEY=AIzaSy-あなたのキー
```

#### オプション E: AWS Bedrock（エンタープライズ）

```ini
LLM_PROVIDER=bedrock
LLM_MODEL=us.anthropic.claude-sonnet-4-5-20250514-v1:0
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=あなたのシークレットキー
```

> AWS IAMユーザーに `bedrock:InvokeModel` 権限が必要です。

#### オプション F: Azure AI Foundry（エンタープライズ）

```ini
LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5
AZURE_FOUNDRY_ENDPOINT=https://your-resource.services.ai.azure.com/
AZURE_FOUNDRY_API_KEY=あなたのキー
AZURE_FOUNDRY_DEPLOYMENT=gpt-5
AZURE_FOUNDRY_API_VERSION=2026-01-01
```

#### オプション G: GCP Vertex AI（エンタープライズ）

```ini
LLM_PROVIDER=vertex_ai
LLM_MODEL=gemini-2.5-pro
GCP_PROJECT_ID=your-project-id
GCP_LOCATION=us-central1
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

> GCPサービスアカウントに `Vertex AI User` ロールが必要です。

#### オプション H: Azure OpenAI

```ini
LLM_PROVIDER=azure
LLM_MODEL=gpt-4o
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_KEY=あなたのキー
AZURE_OPENAI_DEPLOYMENT=your-deployment-name
```

### Step 4: バックエンドの起動

```powershell
# backendディレクトリで実行
python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload
```

ブラウザで `http://127.0.0.1:8090/docs` を開いてAPIドキュメントが表示されれば成功です。

### Step 5: フロントエンドのセットアップ

新しいターミナルを開いて：

```powershell
cd frontend

# 依存関係をインストール
npm install

# 開発サーバーを起動
npm run dev:vite
```

ブラウザで `http://localhost:5290` を開いてアプリが表示されれば成功です。

---

## 次のステップ

1. **サンプルデータをインポート**
   - 「データ取込」ページから仕訳データ（CSV/Excel）をアップロード

2. **ダッシュボードを確認**
   - リスクスコア、統計情報を確認

3. **AI分析を実行**
   - 「AI分析」ページで仕訳の異常検知を実行

---

## よくある問題

### バックエンドが起動しない

```powershell
# 依存関係を再インストール
pip install -r requirements.txt --force-reinstall
```

### APIキーエラー

```
LLM provider error
```

→ `.env`ファイルのAPIキーとLLM_PROVIDERの設定を確認してください。

### ポートが使用中

```
Address already in use
```

→ 別のポートを使用：

```powershell
python -m uvicorn app.main:app --port 8002
```

### Ollamaに接続できない

```
Connection refused: localhost:11434
```

→ Ollamaが起動していることを確認：

```powershell
ollama serve    # Ollamaサーバーを起動
ollama list     # ダウンロード済みモデルを確認
```

---

## 詳細なドキュメント

- [セットアップガイド](./06_setup_guide.md) - 全8プロバイダーの詳細な設定手順
- [クラウド設定ガイド](./10_cloud_setup_guide.md) - AWS/Azure/GCPの設定
- [ユーザーマニュアル](./07_user_manual.md) - 操作方法の詳細
- [運用ガイド](./11_enterprise_operations.md) - エンタープライズ運用

---

## サポート

問題が解決しない場合：

1. [GitHub Issues](https://github.com/GEJFY/journal-ai-auditor/issues)で報告
2. ドキュメントを確認
3. ログファイル（`logs/jaia.log`）を確認
