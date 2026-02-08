# JAIA システムアーキテクチャ設計書

## 1. システム全体構成

### 1.1 アーキテクチャ概要図

```
┌─────────────────────────────────────────────────────────────────────────────────┐
│                              JAIA Desktop Application                            │
│                                  (Electron 28.x)                                │
├─────────────────────────────────────────────────────────────────────────────────┤
│                                                                                  │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Presentation Layer (React 18.x)                     │   │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐   │   │
│  │  │  Dashboard   │ │   Chat UI    │ │ Report View  │ │  Settings    │   │   │
│  │  │  (11 Tabs)   │ │  (Natural    │ │   (PPT/PDF   │ │   Panel      │   │   │
│  │  │              │ │   Language)  │ │   Preview)   │ │              │   │   │
│  │  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                    Dashboard Interface Layer (REST API)                  │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │ Chart API  │ │ Filter API │ │  Data API  │ │ Action API │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                     Application Layer (FastAPI 0.109+)                   │   │
│  │  ┌───────────────────────┐  ┌───────────────────────┐                   │   │
│  │  │   AI Agent Engine     │  │    Rule Engine        │                   │   │
│  │  │   (LangGraph 0.0.40+) │  │    (85 Rules)         │                   │   │
│  │  │  ┌─────────────────┐  │  │  ┌─────────────────┐  │                   │   │
│  │  │  │  Orchestrator   │  │  │  │  Amount Rules   │  │                   │   │
│  │  │  │  Explorer       │  │  │  │  Time Rules     │  │                   │   │
│  │  │  │  TrendAnalyzer  │  │  │  │  Account Rules  │  │                   │   │
│  │  │  │  RiskAnalyzer   │  │  │  │  Approval Rules │  │                   │   │
│  │  │  │  FinancialAna.  │  │  │  │  Desc Rules     │  │                   │   │
│  │  │  │  Investigator   │  │  │  │  Pattern Rules  │  │                   │   │
│  │  │  │  Verifier       │  │  │  │  Trend Rules    │  │                   │   │
│  │  │  │  Hypothesis     │  │  │  └─────────────────┘  │                   │   │
│  │  │  │  Visualizer     │  │  │                       │                   │   │
│  │  │  │  Reporter       │  │  │                       │                   │   │
│  │  │  └─────────────────┘  │  └───────────────────────┘                   │   │
│  │  ├───────────────────────┴──────────────────────────┤                   │   │
│  │  │            Insight Generation Engine              │                   │   │
│  │  └───────────────────────────────────────────────────┘                   │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                      Batch Processing Layer (Polars 0.20+)               │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │    ETL     │ │ Aggregation│ │ ML Scoring │ │ Financial  │           │   │
│  │  │  Pipeline  │ │   Engine   │ │ (5 Models) │ │  Metrics   │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                       │                                         │
│                                       ▼                                         │
│  ┌─────────────────────────────────────────────────────────────────────────┐   │
│  │                          Data Layer                                      │   │
│  │  ┌────────────┐ ┌────────────┐ ┌────────────┐ ┌────────────┐           │   │
│  │  │  DuckDB    │ │  SQLite    │ │  Parquet   │ │   Files    │           │   │
│  │  │ (Journal,  │ │ (Metadata, │ │ (Aggregate │ │  (Import,  │           │   │
│  │  │  TB, CoA)  │ │  Rules,    │ │  Cache)    │ │  Reports)  │           │   │
│  │  │            │ │  Sessions) │ │            │ │            │           │   │
│  │  └────────────┘ └────────────┘ └────────────┘ └────────────┘           │   │
│  └─────────────────────────────────────────────────────────────────────────┘   │
│                                                                                  │
├─────────────────────────────────────────────────────────────────────────────────┤
│                           External Services                                      │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │ AWS Bedrock  │ │ Vertex AI   │ │Azure Foundry │ │ Anthropic    │           │
│  │(Claude,Nova) │ │  (Gemini)   │ │(GPT-5,Claude)│ │   Direct     │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐ ┌──────────────┐           │
│  │ OpenAI       │ │ Google AI   │ │ Azure OpenAI │ │   Ollama     │           │
│  │  Direct      │ │  Studio     │ │  (Legacy)    │ │  (Local)     │           │
│  └──────────────┘ └──────────────┘ └──────────────┘ └──────────────┘           │
└─────────────────────────────────────────────────────────────────────────────────┘
```

### 1.2 レイヤー責務定義

| レイヤー | 責務 | 主要技術 |
|---------|------|----------|
| Presentation | UI表示、ユーザー操作受付、状態管理 | React, Zustand, TailwindCSS |
| Dashboard Interface | エージェント用API提供、UI操作抽象化 | FastAPI REST |
| Application | ビジネスロジック、エージェント処理、ルール評価 | LangGraph, Python |
| Batch Processing | ETL、集計、ML推論、財務計算 | Polars, scikit-learn |
| Data | データ永続化、クエリ最適化 | DuckDB, SQLite, Parquet |

---

## 2. ディレクトリ構成

```
jaia/
├── frontend/                      # Electron + React フロントエンド
│   ├── electron/                  # Electron メインプロセス
│   │   ├── main.ts               # エントリーポイント
│   │   ├── preload.ts            # プリロードスクリプト
│   │   └── ipc/                  # IPC ハンドラー
│   ├── src/                      # React アプリケーション
│   │   ├── components/           # UIコンポーネント
│   │   │   ├── common/           # 共通コンポーネント
│   │   │   ├── dashboard/        # ダッシュボード系
│   │   │   │   ├── tabs/         # 11タブ各コンポーネント
│   │   │   │   ├── charts/       # チャートコンポーネント
│   │   │   │   └── filters/      # フィルターコンポーネント
│   │   │   ├── chat/             # チャットUI
│   │   │   ├── reports/          # レポートビューア
│   │   │   └── settings/         # 設定画面
│   │   ├── hooks/                # カスタムフック
│   │   ├── stores/               # Zustand ストア
│   │   ├── services/             # API クライアント
│   │   ├── types/                # TypeScript 型定義
│   │   └── utils/                # ユーティリティ
│   ├── package.json
│   └── vite.config.ts
│
├── backend/                       # Python バックエンド
│   ├── app/                      # FastAPI アプリケーション
│   │   ├── main.py               # エントリーポイント
│   │   ├── api/                  # API エンドポイント
│   │   │   ├── v1/               # API v1
│   │   │   │   ├── dashboard.py  # Dashboard Interface API
│   │   │   │   ├── import_.py    # データインポート
│   │   │   │   ├── analysis.py   # 分析API
│   │   │   │   ├── reports.py    # レポート生成
│   │   │   │   └── chat.py       # チャットAPI
│   │   │   └── deps.py           # 依存性注入
│   │   ├── core/                 # コア機能
│   │   │   ├── config.py         # 設定管理
│   │   │   ├── security.py       # セキュリティ
│   │   │   └── logging.py        # ロギング
│   │   ├── models/               # Pydantic モデル
│   │   │   ├── journal.py        # 仕訳データ
│   │   │   ├── account.py        # 勘定科目
│   │   │   ├── period.py         # 会計期間
│   │   │   └── insight.py        # 洞察
│   │   └── services/             # サービス層
│   │       ├── import_service.py
│   │       ├── validation_service.py
│   │       └── mapping_service.py
│   │
│   ├── agents/                   # AIエージェント (LangGraph)
│   │   ├── orchestrator.py       # オーケストレーター
│   │   ├── specialists/          # 専門エージェント
│   │   │   ├── explorer.py
│   │   │   ├── trend_analyzer.py
│   │   │   ├── risk_analyzer.py
│   │   │   ├── financial_analyzer.py
│   │   │   ├── investigator.py
│   │   │   ├── verifier.py
│   │   │   ├── hypothesis.py
│   │   │   ├── visualizer.py
│   │   │   └── reporter.py
│   │   ├── tools/                # エージェントツール
│   │   │   ├── dashboard_tools.py
│   │   │   ├── data_tools.py
│   │   │   ├── visualization_tools.py
│   │   │   └── verification_tools.py
│   │   ├── state.py              # 状態管理
│   │   └── graph.py              # LangGraph定義
│   │
│   ├── batch/                    # バッチ処理
│   │   ├── etl/                  # ETL パイプライン
│   │   │   ├── extract.py
│   │   │   ├── transform.py
│   │   │   └── load.py
│   │   ├── aggregation/          # 集計処理
│   │   │   ├── period_aggregator.py
│   │   │   ├── account_aggregator.py
│   │   │   └── trend_calculator.py
│   │   ├── ml/                   # 機械学習
│   │   │   ├── models/
│   │   │   │   ├── isolation_forest.py
│   │   │   │   ├── lof.py
│   │   │   │   ├── one_class_svm.py
│   │   │   │   ├── autoencoder.py
│   │   │   │   └── benford.py
│   │   │   ├── scoring.py        # 統合スコアリング
│   │   │   └── training.py       # モデル学習
│   │   ├── rules/                # ルールエンジン
│   │   │   ├── engine.py
│   │   │   ├── amount_rules.py
│   │   │   ├── time_rules.py
│   │   │   ├── account_rules.py
│   │   │   ├── approval_rules.py
│   │   │   ├── description_rules.py
│   │   │   ├── pattern_rules.py
│   │   │   └── trend_rules.py
│   │   └── financial/            # 財務指標計算
│   │       ├── turnover.py
│   │       ├── liquidity.py
│   │       └── profitability.py
│   │
│   ├── reports/                  # レポート生成
│   │   ├── ppt_generator.py      # PPT生成
│   │   ├── pdf_generator.py      # PDF生成
│   │   ├── templates/            # レポートテンプレート
│   │   └── insights/             # 洞察生成
│   │       ├── generator.py
│   │       ├── prioritizer.py
│   │       └── narrative.py
│   │
│   ├── db/                       # データベース
│   │   ├── duckdb/               # DuckDB関連
│   │   │   ├── connection.py
│   │   │   ├── migrations/
│   │   │   └── queries/
│   │   ├── sqlite/               # SQLite関連
│   │   │   ├── connection.py
│   │   │   └── models.py
│   │   └── repositories/         # リポジトリパターン
│   │       ├── journal_repo.py
│   │       ├── account_repo.py
│   │       └── insight_repo.py
│   │
│   ├── services/llm/             # LLMプロバイダー（8プロバイダー対応）
│   │   ├── models.py             # LLMConfig, LLMResponse, ModelInfo
│   │   └── service.py            # マルチプロバイダーLLMサービス
│   │                             # (Bedrock, Azure Foundry, Vertex AI,
│   │                             #  Anthropic, OpenAI, Google, Azure, Ollama)
│   │
│   ├── tests/                    # テスト
│   │   ├── unit/
│   │   ├── integration/
│   │   └── fixtures/
│   │
│   ├── pyproject.toml
│   └── requirements.txt
│
├── data/                         # データディレクトリ
│   ├── db/                       # データベースファイル
│   │   ├── jaia.duckdb           # メインDB
│   │   └── metadata.sqlite       # メタデータDB
│   ├── cache/                    # キャッシュ (Parquet)
│   ├── import/                   # インポート用一時領域
│   ├── export/                   # エクスポート出力
│   └── templates/                # レポートテンプレート
│
├── docs/                         # ドキュメント
│   ├── 01_system_architecture.md # 本ファイル
│   ├── 02_module_design.md       # モジュール設計
│   ├── 03_database_design.md     # DB設計
│   ├── 04_api_design.md          # API設計
│   └── 05_development_plan.md    # 開発計画
│
├── scripts/                      # ユーティリティスクリプト
│   ├── setup.py                  # 初期セットアップ
│   ├── migrate.py                # DBマイグレーション
│   └── build.py                  # ビルドスクリプト
│
├── .env.example                  # 環境変数サンプル
├── .gitignore
└── README.md
```

---

## 3. 通信フロー

### 3.1 データインポートフロー

```
User                 Frontend              Backend API           Batch            Database
 │                      │                      │                   │                  │
 │  ファイル選択         │                      │                   │                  │
 │─────────────────────>│                      │                   │                  │
 │                      │  POST /api/v1/import/validate            │                  │
 │                      │─────────────────────>│                   │                  │
 │                      │                      │  検証処理          │                  │
 │                      │                      │──────────────────>│                  │
 │                      │    検証結果          │<──────────────────│                  │
 │                      │<─────────────────────│                   │                  │
 │  プレビュー表示      │                      │                   │                  │
 │<─────────────────────│                      │                   │                  │
 │                      │                      │                   │                  │
 │  インポート確定      │                      │                   │                  │
 │─────────────────────>│                      │                   │                  │
 │                      │  POST /api/v1/import/execute             │                  │
 │                      │─────────────────────>│                   │                  │
 │                      │                      │  ETL実行           │                  │
 │                      │                      │──────────────────>│                  │
 │                      │                      │                   │  データ格納      │
 │                      │                      │                   │─────────────────>│
 │                      │                      │                   │  集計処理        │
 │                      │                      │                   │─────────────────>│
 │                      │                      │                   │  ML推論          │
 │                      │                      │                   │─────────────────>│
 │                      │   完了通知           │<──────────────────│                  │
 │                      │<─────────────────────│                   │                  │
 │  完了表示            │                      │                   │                  │
 │<─────────────────────│                      │                   │                  │
```

### 3.2 ダッシュボード表示フロー

```
User                 Frontend              Backend API           Cache             Database
 │                      │                      │                   │                  │
 │  タブ切り替え        │                      │                   │                  │
 │─────────────────────>│                      │                   │                  │
 │                      │  GET /api/v1/dashboard/{tab}             │                  │
 │                      │─────────────────────>│                   │                  │
 │                      │                      │  キャッシュ確認    │                  │
 │                      │                      │──────────────────>│                  │
 │                      │                      │    (Hit)           │                  │
 │                      │                      │<──────────────────│                  │
 │                      │   集計データ         │                   │                  │
 │                      │<─────────────────────│  (200ms以下)       │                  │
 │  チャート表示        │                      │                   │                  │
 │<─────────────────────│                      │                   │                  │
 │                      │                      │                   │                  │
 │  フィルタ適用        │                      │                   │                  │
 │─────────────────────>│                      │                   │                  │
 │                      │  GET /api/v1/dashboard/{tab}?filters=... │                  │
 │                      │─────────────────────>│                   │                  │
 │                      │                      │  集計テーブル参照  │                  │
 │                      │                      │────────────────────────────────────>│
 │                      │   フィルタ済データ   │                   │                  │
 │                      │<─────────────────────│                   │                  │
 │  更新表示            │                      │                   │                  │
 │<─────────────────────│                      │                   │                  │
```

### 3.3 自律分析フロー

```
User                Frontend            Backend API          Agent Engine          LLM
 │                      │                    │                    │                  │
 │  分析開始            │                    │                    │                  │
 │─────────────────────>│                    │                    │                  │
 │                      │ POST /api/v1/analysis/start              │                  │
 │                      │───────────────────>│                    │                  │
 │                      │                    │  セッション作成    │                  │
 │                      │                    │───────────────────>│                  │
 │                      │   session_id       │                    │                  │
 │                      │<───────────────────│                    │                  │
 │                      │                    │                    │                  │
 │                      │  SSE: 進捗ストリーム                     │                  │
 │                      │<═══════════════════════════════════════>│                  │
 │                      │                    │                    │                  │
 │                      │                    │    ┌──────────────────────────┐      │
 │                      │                    │    │ Orchestrator              │      │
 │                      │                    │    │  ├─ create_analysis_plan  │──────│
 │                      │                    │    │  ├─ dispatch(Explorer)    │      │
 │                      │                    │    │  └─ ...                   │      │
 │  進捗表示            │                    │    └──────────────────────────┘      │
 │<═════════════════════│                    │                    │                  │
 │                      │                    │    ┌──────────────────────────┐      │
 │                      │                    │    │ Explorer                  │      │
 │                      │                    │    │  ├─ view_summary_tab      │      │
 │                      │                    │    │  ├─ view_kpi_cards        │      │
 │                      │                    │    │  └─ scan_risk_distribution│      │
 │  操作履歴表示        │                    │    └──────────────────────────┘      │
 │<═════════════════════│                    │                    │                  │
 │                      │                    │                    │                  │
 │                      │                    │    ┌──────────────────────────┐      │
 │                      │                    │    │ Human-in-the-Loop        │      │
 │  質問受信            │                    │    │  (Critical発見時)        │      │
 │<═════════════════════│                    │    └──────────────────────────┘      │
 │  回答入力            │                    │                    │                  │
 │═════════════════════>│                    │                    │                  │
 │                      │                    │                    │                  │
 │                      │                    │    ...分析継続...   │                  │
 │                      │                    │                    │                  │
 │  完了・レポート      │ GET /api/v1/reports/{session_id}        │                  │
 │<─────────────────────│───────────────────>│                    │                  │
```

---

## 4. プロセス間通信

### 4.1 Electron IPC通信

```typescript
// Main Process ←→ Renderer Process

// チャネル定義
const IPC_CHANNELS = {
  // ファイル操作
  FILE_OPEN_DIALOG: 'file:open-dialog',
  FILE_SAVE_DIALOG: 'file:save-dialog',

  // バックエンド通信
  API_REQUEST: 'api:request',
  API_STREAM: 'api:stream',

  // ウィンドウ操作
  WINDOW_MINIMIZE: 'window:minimize',
  WINDOW_MAXIMIZE: 'window:maximize',
  WINDOW_CLOSE: 'window:close',

  // 通知
  NOTIFICATION_SHOW: 'notification:show',
} as const;
```

### 4.2 バックエンドAPI通信

- **REST API**: 同期的なリクエスト/レスポンス
- **SSE (Server-Sent Events)**: 自律分析の進捗ストリーミング
- **WebSocket** (将来): リアルタイム双方向通信（オプション）

---

## 5. セキュリティ設計

### 5.1 データ保護

| 対象 | 保護方式 |
|------|----------|
| データベースファイル | AES-256暗号化 |
| API通信 | ローカル通信のためHTTPで可（オプションでHTTPS） |
| LLMへの送信データ | PII自動マスキング、金額丸め処理 |
| 認証情報 | 環境変数または暗号化設定ファイル |

### 5.2 監査ログ

```python
# ログ記録対象
AUDIT_EVENTS = [
    "user.login",
    "data.import",
    "data.export",
    "analysis.start",
    "analysis.complete",
    "agent.action",
    "report.generate",
    "settings.change",
]
```

---

## 6. 性能設計

### 6.1 キャッシング戦略

| キャッシュ層 | 対象 | TTL |
|-------------|------|-----|
| メモリ (Zustand) | UIフィルタ状態、選択状態 | セッション中 |
| Parquetファイル | 事前集計結果 | バッチ処理まで |
| DuckDB | 集計テーブル | 明示的更新まで |

### 6.2 事前集計による高速化

```sql
-- 集計テーブル例: 期間×勘定科目
CREATE TABLE agg_by_period_account AS
SELECT
    fiscal_year,
    accounting_period,
    gl_account_number,
    COUNT(*) as count,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as sum_debit,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as sum_credit,
    AVG(ABS(amount)) as avg_amount,
    STDDEV(amount) as std_amount,
    MIN(amount) as min_amount,
    MAX(amount) as max_amount
FROM journal_entries
GROUP BY fiscal_year, accounting_period, gl_account_number;
```

---

## 7. 拡張性設計

### 7.1 LLMプロバイダー抽象化

```python
from abc import ABC, abstractmethod

class LLMProvider(ABC):
    """LLMプロバイダー抽象基底クラス"""

    @abstractmethod
    async def generate(self, prompt: str, **kwargs) -> str:
        pass

    @abstractmethod
    async def stream(self, prompt: str, **kwargs) -> AsyncIterator[str]:
        pass

class BedrockProvider(LLMProvider):
    """AWS Bedrock実装"""
    pass

class VertexAIProvider(LLMProvider):
    """Google Vertex AI実装"""
    pass
```

### 7.2 ルールエンジン拡張

```python
from abc import ABC, abstractmethod

class AuditRule(ABC):
    """監査ルール抽象基底クラス"""

    rule_id: str
    category: str
    severity: str
    score: int

    @abstractmethod
    def evaluate(self, journal: JournalEntry) -> RuleResult:
        pass
```

---

## 8. デプロイメント構成

### 8.1 開発環境

```yaml
# docker-compose.dev.yml
services:
  backend:
    build: ./backend
    volumes:
      - ./backend:/app
      - ./data:/data
    ports:
      - "8000:8000"
    environment:
      - ENV=development
```

### 8.2 本番ビルド

```bash
# Electronアプリケーションビルド
npm run build          # フロントエンドビルド
pyinstaller backend/   # Pythonバックエンドバンドル
electron-builder       # Electronパッケージング

# 出力
# - Windows: JAIA-Setup.exe
# - macOS: JAIA.dmg
```

---

**次のステップ**: [02_module_design.md](02_module_design.md) でモジュール詳細設計を行います。
