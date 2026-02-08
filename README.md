# JAIA - Journal entry AI Analyzer

**AI駆動の仕訳データ分析・内部監査支援システム**

[![Python](https://img.shields.io/badge/Python-3.11+-blue.svg)](https://python.org)
[![Node.js](https://img.shields.io/badge/Node.js-18+-green.svg)](https://nodejs.org)
[![License](https://img.shields.io/badge/License-Proprietary-red.svg)](LICENSE)

---

## 概要

JAIA（Journal entry AI Analyzer）は、仕訳データの自動分析と内部監査業務を支援するデスクトップアプリケーションです。AIエージェントが人間の監査人のようにダッシュボードを操作し、異常検知・リスク分析・洞察生成を自律的に実行します。

### 主な特徴

- **AI自律分析**: LangGraphベースのマルチエージェントが、探索→分析→検証→報告を自動実行
- **58の監査ルール**: 金額・時間・勘定科目・承認・ML・Benfordの6カテゴリ
- **5つのML異常検知**: Isolation Forest、LOF、One-Class SVM、Autoencoder、アンサンブル
- **Benford分析**: 第1桁・第2桁分析、MAD適合性テスト
- **リスクスコアリング**: 0-100の統合スコア、Critical/High/Medium/Low分類
- **レポート自動生成**: PPT・PDF形式での監査報告書出力
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
git clone https://github.com/your-org/journal-ai-auditor.git
cd journal-ai-auditor

# 2. セットアップスクリプトを実行
.\scripts\setup.ps1

# 3. 環境変数を設定（オプション：LLM使用時）
# backend/.env を編集してAPIキーを設定
```

### 起動

```powershell
# 全サービス起動（バックエンド + フロントエンド）
.\scripts\start_all.ps1

# または個別起動
.\scripts\start_backend.ps1   # バックエンド: http://localhost:8000
.\scripts\start_frontend.ps1  # フロントエンド: http://localhost:3000
```

### 動作確認

```powershell
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

API仕様詳細: [docs/04_api_design.md](docs/04_api_design.md)

---

## 設定

### 環境変数

`backend/.env` ファイルで設定：

```bash
# 基本設定
JAIA_DEBUG=true
JAIA_LOG_LEVEL=INFO

# データベース
DUCKDB_PATH=data/jaia.duckdb
SQLITE_PATH=data/jaia_meta.db

# LLM設定（いずれか1つを設定）
# OpenAI
OPENAI_API_KEY=sk-...

# Azure OpenAI
AZURE_OPENAI_API_KEY=...
AZURE_OPENAI_ENDPOINT=https://...

# Anthropic
ANTHROPIC_API_KEY=sk-ant-...
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

- **Issue報告**: [GitHub Issues](https://github.com/your-org/journal-ai-auditor/issues)
- **ドキュメント**: [docs/](docs/) ディレクトリ

---

## 更新履歴

### v1.0.0 (2026-02-02)
- 初回リリース
- 58監査ルール実装
- 5種ML異常検知
- PPT/PDFレポート生成
- Electron + React フロントエンド
