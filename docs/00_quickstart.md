# JAIA クイックスタートガイド

このガイドでは、JAIAを最短で起動する方法を説明します。

## 必要なもの

- Python 3.11以上
- Node.js 20以上
- LLMプロバイダーのAPIキー（いずれか1つ）

## 5分でスタート

### Step 1: リポジトリのクローン

```powershell
git clone https://github.com/your-org/journal-ai-auditor.git
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

#### オプション A: Anthropic Claude（推奨・最も簡単）

```ini
LLM_PROVIDER=anthropic
LLM_MODEL=claude-sonnet-4-5
ANTHROPIC_API_KEY=sk-ant-api03-あなたのキー
```

#### オプション B: OpenAI GPT

```ini
LLM_PROVIDER=openai
LLM_MODEL=gpt-5-mini
OPENAI_API_KEY=sk-proj-あなたのキー
```

#### オプション C: Google Gemini

```ini
LLM_PROVIDER=google
LLM_MODEL=gemini-2.5-flash-lite
GOOGLE_API_KEY=AIzaSy-あなたのキー
```

#### オプション D: Ollama（ローカルLLM・APIキー不要）

```ini
LLM_PROVIDER=ollama
LLM_MODEL=phi4
OLLAMA_BASE_URL=http://localhost:11434
```

> Ollamaのインストール: https://ollama.ai → `ollama pull phi4` でモデル取得

### Step 4: バックエンドの起動

```powershell
# backendディレクトリで実行
python -m uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload
```

✅ `http://127.0.0.1:8001/docs` でAPIドキュメントが表示されれば成功です。

### Step 5: フロントエンドのセットアップ

新しいターミナルを開いて：

```powershell
cd frontend

# 依存関係をインストール
npm install

# 開発サーバーを起動
npm run dev:vite
```

✅ `http://localhost:5180` でアプリが表示されれば成功です。

---

## 次のステップ

1. **サンプルデータをインポート**
   - 「データ取込」ページから仕訳データをアップロード

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

→ `.env`ファイルのAPIキーを確認してください。

### ポートが使用中

```
Address already in use
```

→ 別のポートを使用：

```powershell
python -m uvicorn app.main:app --port 8002
```

---

## 詳細なドキュメント

- [セットアップガイド](./06_setup_guide.md) - 詳細なセットアップ手順
- [クラウド設定ガイド](./10_cloud_setup_guide.md) - AWS/Azure/GCPの設定
- [ユーザーマニュアル](./07_user_manual.md) - 操作方法の詳細
- [運用ガイド](./11_enterprise_operations.md) - エンタープライズ運用

---

## サポート

問題が解決しない場合：

1. GitHub Issuesで報告
2. ドキュメントを確認
3. ログファイル（`logs/jaia.log`）を確認
