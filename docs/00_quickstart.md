# JAIA クイックスタートガイド

JAIAを最短で起動する方法を説明します。

---

## 必要なもの

| 項目 | 要件 |
| ---- | ---- |
| Python | 3.11以上 |
| Node.js | 18以上 |
| OS | Windows 10/11 |
| メモリ | 8GB以上推奨 |

---

## 初回セットアップ（1回だけ）

PowerShellを開いて、以下を順に実行します。

```powershell
# 1. リポジトリをクローン
git clone https://github.com/GEJFY/journal-ai-auditor.git
cd journal-ai-auditor

# 2. セットアップスクリプトを実行（Python venv作成、依存インストール、npm install を自動実行）
.\scripts\setup.ps1

# 3. 環境設定ファイルを編集（LLMのAPIキーを設定）
notepad backend\.env
```

> `.env` が自動作成されない場合: `copy backend\.env.example backend\.env`

### APIキー設定（.envファイル）

使いたいLLMプロバイダーを1つ選んで設定します。

**Azure AI Foundry（現在の設定）:**

```ini
LLM_PROVIDER=azure_foundry
LLM_MODEL=gpt-5.2
AZURE_FOUNDRY_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_FOUNDRY_API_KEY=your-api-key
AZURE_FOUNDRY_DEPLOYMENT=your-deployment-name
```

**Ollama（APIキー不要・最も簡単）:**

```ini
LLM_PROVIDER=ollama
LLM_MODEL=phi4
```

> Ollama使用時は事前に [ollama.ai](https://ollama.ai) からインストールし、`ollama pull phi4` を実行

その他のプロバイダー設定は [backend/.env.example](../backend/.env.example) を参照してください。

---

## 起動（毎回）

### 方法1: ワンクリック起動（推奨）

```powershell
# プロジェクトのルートディレクトリで
.\start.ps1
```

バックエンドとフロントエンドが自動で起動します。

### 方法2: バッチファイルで起動

エクスプローラーから `start.bat` をダブルクリック

### 方法3: 手動起動

**ターミナル1（バックエンド）:**

```powershell
cd backend
.\venv\Scripts\Activate.ps1
python -m uvicorn app.main:app --host 127.0.0.1 --port 8090 --reload
```

**ターミナル2（フロントエンド）:**

```powershell
cd frontend
npm run dev
```

---

## 動作確認

起動後、以下のURLにアクセスできれば成功です。

| URL | 内容 |
| --- | ---- |
| `http://localhost:8090/health` | ヘルスチェック（JSON応答） |
| `http://localhost:8090/docs` | Swagger UI（API一覧） |
| `http://localhost:5290` | フロントエンド（Electron/ブラウザ） |

---

## サンプルデータで試す

1. フロントエンドの「データ取込」画面を開く
2. `sample_data/` フォルダ内のファイルをアップロード:
   - マスタデータ: `01_chart_of_accounts.csv`、`02_department_master.csv` など
   - 仕訳データ: CSVまたはExcelファイル
3. 「ダッシュボード」でKPI・リスク分析を確認
4. 「AI分析」で自然言語での質問を試す

---

## よくある問題

| 問題 | 対処 |
| ---- | ---- |
| バックエンドが起動しない | `.\venv\Scripts\Activate.ps1` で仮想環境を有効化してから再実行 |
| ポートが使用中 | 他のアプリを停止するか、`backend\.env` の `PORT=8090` を変更 |
| LLMエラー | `backend\.env` のAPIキーとプロバイダー設定を確認 |
| フロントエンドが開かない | `cd frontend && npm install` で依存パッケージを再インストール |
| Electronエラー | `cd frontend && npm run build:main` でElectronメインプロセスをビルド |

詳細は [トラブルシューティングガイド](15_troubleshooting.md) を参照。

---

## 次のステップ

- [ユーザー操作マニュアル](09_user_guide_ja.md) - 画面操作の詳細
- [セットアップガイド](06_setup_guide.md) - LLMプロバイダー別の詳細設定
- [API リファレンス](08_api_quick_reference.md) - 全41エンドポイント
- [デモガイド](13_demo_guide.md) - デモシナリオ
