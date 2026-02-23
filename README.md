# JAIA - Journal entry AI Analyzer

**AI駆動の仕訳データ分析・内部監査支援システム**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

---

## 概要

JAIA（Journal entry AI Analyzer）は、仕訳データの自動分析と内部監査業務を支援するデスクトップアプリケーションです。AIエージェントが人間の監査人のようにダッシュボードを操作し、異常検知・リスク分析・洞察生成を自律的に実行します。

### 主な特徴

- **AI自律監査エージェント**: 5フェーズ分析ループ（Observe → Hypothesize → Explore → Verify → Synthesize）による完全自律型監査。13種の分析ツール、HITL（Human-in-the-Loop）チェックポイント、SSEリアルタイム進捗表示
- **AI自律分析**: LangGraphベースのマルチエージェントが、探索→分析→検証→報告を自動実行
- **58の監査ルール**: 金額・時間・勘定科目・承認・ML・Benfordの6カテゴリ
- **5つのML異常検知**: Isolation Forest、LOF、One-Class SVM、Autoencoder、アンサンブル
- **Benford分析**: 第1桁・第2桁分析、MAD適合性テスト
- **リスクスコアリング**: 0-100の統合スコア、Critical/High/Medium/Low分類
- **レポート自動生成**: PPT・PDF形式での監査報告書出力（目的別: 監査人向け/経営層向け）
- **カラムマッピング**: ファイル取込時にカラム自動マッピング提案、手動調整、バリデーション
- **詳細分析**: 部門分析、取引先集中度分析、勘定科目フロー分析
- **AICPA準拠**: Audit Data Standards（GL_Detail）に完全対応

---

## アーキテクチャ

```
┌─────────────────────────────────────────────────────────────────┐
│                     JAIA Desktop Application                     │
├─────────────────────────────────────────────────────────────────┤
│  Frontend (Electron + React + TypeScript)                        │
│  - Dashboard: KPI、リスク分布、時系列、Benford分析              │
│  - AI Chat: エージェントとの対話インターフェース                │
│  - Reports: レポート生成・プレビュー・エクスポート              │
├─────────────────────────────────────────────────────────────────┤
│  Backend (FastAPI + Python 3.11)                                 │
│  ├─ API Layer: RESTful API (健全性、インポート、分析、レポート) │
│  ├─ Agents: LangGraph オーケストレーター + 専門エージェント     │
│  ├─ Batch: ETL、ルールエンジン、ML推論、集計処理                │
│  └─ Data: DuckDB (仕訳) + SQLite (メタデータ)                   │
└─────────────────────────────────────────────────────────────────┘
```

---

## クイックスタート

### 動作要件

| 項目 | 要件 |
|------|------|
| OS | Windows 10/11, macOS 12+, Linux (Ubuntu 20.04+) |
| Python | 3.11以上 |
| Node.js | 18以上 |
| メモリ | 8GB以上（推奨16GB） |
| ディスク | 10GB以上の空き容量 |

### インストール

```powershell
# 1. リポジトリをクローン
git clone https://github.com/GEJFY/journal-ai-auditor.git
cd journal-ai-auditor

# 2. セットアップスクリプトを実行
.\scripts\setup.ps1

# 3. 環境変数を設定（オプション：LLM使用時）
# backend/.env を編集してAPIキーを設定
```

### 起動

```powershell
# ワンクリック起動（推奨）
.\start.ps1

# または start.bat をダブルクリック
```

バックエンド（`http://localhost:8090`）とフロントエンド（`http://localhost:5290`）が自動起動します。

個別起動も可能です:

```powershell
.\scripts\start_backend.ps1   # バックエンドのみ
.\scripts\start_frontend.ps1  # フロントエンドのみ
```

### Docker で起動（Web版）

```bash
# 本番モード: バックエンド + フロントエンド（Nginx）が起動
docker-compose up --build
# → http://localhost でアクセス

# 開発モード（推奨）: バックエンドのみDocker + フロントエンドはローカル
docker-compose -f docker-compose.dev.yml up --build
cd frontend && npm run dev
# → http://localhost:5173 でアクセス

# 開発モード（全Docker）
docker-compose -f docker-compose.dev.yml --profile full up
# → http://localhost:5173 でアクセス
```

### 動作確認

```powershell
# ヘルスチェック
curl http://localhost:8090/health

# 統合テスト実行
.\scripts\test_integration.ps1
```

---

## ディレクトリ構成

```
journal-ai-auditor/
├── backend/                    # Python バックエンド
│   ├── app/                   # FastAPI アプリケーション
│   │   ├── api/               # APIエンドポイント
│   │   │   └── endpoints/     # 各機能のエンドポイント
│   │   ├── core/              # コア機能（設定、ログ、例外）
│   │   ├── models/            # Pydantic データモデル
│   │   └── services/          # ビジネスロジック
│   ├── agents/                # AIエージェント（LangGraph）
│   ├── batch/                 # バッチ処理
│   │   ├── etl/               # ETLパイプライン
│   │   ├── rules/             # 監査ルールエンジン
│   │   └── ml/                # 機械学習モデル
│   ├── data/                  # データファイル（.duckdb, .db）
│   └── requirements.txt       # Python依存パッケージ
├── frontend/                   # Electron + React フロントエンド
│   ├── electron/              # Electronメインプロセス
│   ├── src/                   # React アプリケーション
│   │   ├── renderer/          # レンダラープロセス
│   │   │   ├── components/    # UIコンポーネント
│   │   │   ├── pages/         # ページコンポーネント
│   │   │   └── lib/           # ユーティリティ
│   └── package.json           # npm依存パッケージ
├── docs/                       # 設計ドキュメント
├── sample_data/                # サンプルデータ
├── scripts/                    # ユーティリティスクリプト
└── README.md                   # 本ファイル
```

---

## 監査ルール一覧

### 6カテゴリ・58ルール

| カテゴリ | ルール数 | 主な検出内容 |
|----------|---------|-------------|
| **金額 (Amount)** | 12 | 重要性基準超過、端数異常、丸め金額、金額急増 |
| **時間 (Time)** | 10 | 営業時間外、週末・祝日、期末集中、月初・月末 |
| **勘定科目 (Account)** | 10 | 異常科目組合せ、PL/BS直接、通常と異なる相手科目 |
| **承認 (Approval)** | 10 | 自己承認、権限超過、承認遅延、承認者不在 |
| **ML異常検知** | 6 | Isolation Forest、LOF、One-Class SVM等のスコア |
| **Benford分析** | 10 | 第1桁・第2桁の分布異常、MAD適合性 |

詳細: [docs/02_module_design.md](docs/02_module_design.md)

---

## API概要

### 主要エンドポイント

| メソッド | エンドポイント | 説明 |
|----------|---------------|------|
| GET | `/health` | ヘルスチェック |
| GET | `/api/v1/health` | API健全性確認 |
| POST | `/api/v1/import/upload` | データインポート |
| GET | `/api/v1/dashboard/summary` | ダッシュボードサマリー |
| GET | `/api/v1/dashboard/kpi` | KPI情報取得 |
| GET | `/api/v1/dashboard/benford` | Benford分析 |
| POST | `/api/v1/batch/execute` | バッチ処理実行 |
| GET | `/api/v1/batch/rules` | ルール一覧取得 |
| GET | `/api/v1/analysis/violations` | 違反仕訳一覧 |
| POST | `/api/v1/agents/analyze` | AI分析実行 |
| GET | `/api/v1/reports/templates` | レポートテンプレート |
| POST | `/api/v1/reports/export/ppt` | PPTエクスポート |
| POST | `/api/v1/reports/export/pdf` | PDFエクスポート |
| POST | `/api/v1/autonomous-audit/start` | 自律型監査開始 |
| POST | `/api/v1/autonomous-audit/start/stream` | SSEストリーミング付き監査開始 |
| GET | `/api/v1/autonomous-audit/{session_id}/status` | セッション進捗取得 |
| GET | `/api/v1/autonomous-audit/{session_id}/hypotheses` | 仮説一覧取得 |
| POST | `/api/v1/autonomous-audit/{session_id}/approve` | 仮説承認（HITL） |
| GET | `/api/v1/autonomous-audit/{session_id}/insights` | インサイト一覧取得 |
| GET | `/api/v1/autonomous-audit/{session_id}/report` | レポート取得 |
| GET | `/api/v1/autonomous-audit/sessions` | セッション履歴 |

API仕様詳細: [docs/04_api_design.md](docs/04_api_design.md)

---

## 設定

### マルチクラウドLLM対応（8プロバイダー）

JAIAは8種類のLLMプロバイダーに対応しています。用途に応じて選択してください。

| プロバイダー | 主なモデル | 用途 |
|------------|-----------|------|
| **Ollama** | phi4, llama3.3 | ローカル実行（APIキー不要） |
| **Anthropic** | Claude Opus 4.6, Sonnet 4.5 | 高精度分析（推奨） |
| **OpenAI** | GPT-5.2, GPT-5-mini | 汎用分析 |
| **Google AI Studio** | Gemini 2.5 Pro/Flash | 高速処理 |
| **AWS Bedrock** | Claude, Amazon Nova | エンタープライズ（AWS統合） |
| **Azure AI Foundry** | GPT-5, Claude | エンタープライズ（Azure統合） |
| **GCP Vertex AI** | Gemini 3 Pro | エンタープライズ（GCP統合） |
| **Azure OpenAI** | GPT-4o | Azure経由GPTアクセス |

### 環境変数

`backend/.env` ファイルで設定：

```bash
# 基本設定
JAIA_DEBUG=true
JAIA_LOG_LEVEL=INFO

# データベース
DUCKDB_PATH=data/jaia.duckdb
SQLITE_PATH=data/jaia_meta.db

# LLMプロバイダー選択（以下から1つ選択）
LLM_PROVIDER=anthropic  # anthropic / openai / google / bedrock / azure_foundry / vertex_ai / azure / ollama

# Anthropic Direct
ANTHROPIC_API_KEY=sk-ant-...

# OpenAI Direct
OPENAI_API_KEY=sk-...

# Google AI Studio
GOOGLE_API_KEY=AIzaSy...

# Ollama（ローカルLLM）
OLLAMA_BASE_URL=http://localhost:11434

# AWS Bedrock
AWS_REGION=us-east-1
AWS_ACCESS_KEY_ID=AKIA...
AWS_SECRET_ACCESS_KEY=...

# Azure AI Foundry
AZURE_FOUNDRY_ENDPOINT=https://...
AZURE_FOUNDRY_API_KEY=...

# GCP Vertex AI
GCP_PROJECT_ID=your-project
GCP_LOCATION=us-central1

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://...
AZURE_OPENAI_API_KEY=...
```

### ルール閾値のカスタマイズ

`backend/app/core/config.py` で閾値を調整可能：

```python
# 重要性基準（デフォルト: 1億円）
MATERIALITY_THRESHOLD = 100_000_000

# リスクスコア閾値
RISK_THRESHOLD_CRITICAL = 80
RISK_THRESHOLD_HIGH = 60
RISK_THRESHOLD_MEDIUM = 40
```

---

## 開発

### テスト実行

```powershell
# バックエンドテスト
cd backend
python -m pytest tests/ -v --cov=app

# 型チェック
python -m mypy app/
```

### コーディング規約

- Python: PEP 8準拠、型ヒント必須
- TypeScript: ESLint + Prettier
- コメント: 日本語
- コード: 英語（変数名、関数名）

---

## ライセンス

Proprietary License - Copyright (c) 2026 Go Yoshizawa. All rights reserved. 詳細は [LICENSE](LICENSE) を参照

---

## サポート

- **Issue報告**: [GitHub Issues](https://github.com/GEJFY/journal-ai-auditor/issues)
- **ドキュメント**: [docs/](docs/) ディレクトリ

---

## セキュリティ

セキュリティに関する詳細は [SECURITY.md](SECURITY.md) を参照してください。

脆弱性を発見した場合は、GitHub Issueではなく直接メンテナーに報告してください。

---

## 更新履歴

詳細は [CHANGELOG.md](CHANGELOG.md) を参照してください。

### v0.4.0 (2026-02-23)

- AI自律監査エージェント（5フェーズ分析ループ）
- 13種の分析ツール + AuditToolRegistry
- HITL（Human-in-the-Loop）チェックポイント
- SSEストリーミング対応
- 8つの自律型監査APIエンドポイント
- AutonomousAuditPage（フェーズ進捗、4タブUI）

### v0.3.0 (2026-02-23)

- カラムマッピングUI（自動提案付き）
- マルチステップインポートフロー
- 詳細分析ページ（部門・取引先・勘定フロー）
- フロントエンドDocker対応

### v0.2.1 (2026-02-15)

- Azure AI Foundry SDK移行
- ポート統一 (Backend:8090 / Frontend:5290)
- セキュリティヘッダー強化
- CORS環境変数化
- ドキュメント整備

### v0.2.0 (2026-02-09)

- マルチクラウドLLM対応（8プロバイダー）
- Docker/Terraform/CI/CD追加
- エンタープライズセキュリティ機能

### v0.1.0 (2026-02-02)

- 初回リリース
- 58監査ルール実装
- 5種ML異常検知
- PPT/PDFレポート生成
- Electron + React フロントエンド
