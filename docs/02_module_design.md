# JAIA モジュール設計書

## 1. フロントエンドモジュール構成

### 1.1 コンポーネント階層

```
App
├── Layout
│   ├── Header
│   │   ├── Logo
│   │   ├── NavigationTabs (11タブ)
│   │   └── UserMenu
│   ├── Sidebar
│   │   ├── GlobalFilters
│   │   │   ├── PeriodPicker
│   │   │   ├── AccountTreeSelector
│   │   │   ├── AmountRangeSlider
│   │   │   ├── RiskLevelCheckbox
│   │   │   ├── UserSelector
│   │   │   └── KeywordSearch
│   │   └── FilterPresets
│   └── MainContent
│       ├── DashboardTabs
│       │   ├── SummaryTab
│       │   ├── TimeSeriesTab
│       │   ├── AccountAnalysisTab
│       │   ├── TrialBalanceTab
│       │   ├── FinancialMetricsTab
│       │   ├── CashFlowTab
│       │   ├── RiskDetectionTab
│       │   ├── BenfordTab
│       │   ├── UserApprovalTab
│       │   ├── JournalSearchTab
│       │   └── AIAnalysisTab
│       ├── ChatPanel
│       │   ├── MessageList
│       │   ├── InputArea
│       │   └── AgentStatusIndicator
│       └── AgentOperationPanel
│           ├── ProgressBar
│           ├── CurrentOperation
│           ├── FindingsList
│           └── HumanInLoopPrompt
├── ReportViewer
│   ├── PPTPreview
│   └── PDFPreview
└── SettingsModal
    ├── LLMProviderConfig
    ├── ThresholdSettings
    └── RuleManagement
```

### 1.2 状態管理 (Zustand Stores)

```typescript
// stores/filterStore.ts
interface FilterState {
  period: { start: Date; end: Date };
  accounts: string[];
  fsCaption: string[];
  departments: string[];
  amountRange: { min: number; max: number };
  riskLevels: RiskLevel[];
  users: string[];
  keyword: string;
  ruleCategories: string[];

  // Actions
  setPeriod: (period: Period) => void;
  setAccounts: (accounts: string[]) => void;
  resetFilters: () => void;
  loadPreset: (presetId: string) => void;
  savePreset: (name: string) => void;
}

// stores/analysisStore.ts
interface AnalysisState {
  sessionId: string | null;
  phase: AnalysisPhase;
  progress: number;
  findings: Finding[];
  operationLog: OperationLogEntry[];
  pendingQuestion: HumanInLoopQuestion | null;

  // Actions
  startAnalysis: () => Promise<void>;
  stopAnalysis: () => void;
  answerQuestion: (response: string) => void;
}

// stores/dashboardStore.ts
interface DashboardState {
  activeTab: TabId;
  chartData: Record<string, ChartData>;
  isLoading: boolean;
  lastUpdated: Date;

  // Actions
  setActiveTab: (tab: TabId) => void;
  refreshData: () => Promise<void>;
  drillDown: (elementId: string) => void;
}
```

### 1.3 ダッシュボードタブ詳細設計

#### 1.3.1 サマリータブ (SummaryTab)

| コンポーネント | 使用ライブラリ | データソース |
|---------------|---------------|-------------|
| KPICards | 独自実装 | `agg_summary` |
| RiskDistributionDonut | Nivo | `agg_risk_distribution` |
| MonthlyTrendCombo | Recharts | `agg_monthly_summary` |
| TopAccountsBar | Recharts | `agg_top_accounts` |
| RecentAlertsList | AG Grid | `risk_scores` (Top5) |
| RuleViolationHeatmap | D3.js | `agg_rule_violations` |

#### 1.3.2 時系列分析タブ (TimeSeriesTab)

| コンポーネント | 使用ライブラリ | データソース |
|---------------|---------------|-------------|
| DailyTrendArea | Recharts | `agg_by_date` |
| MonthlyComparisonBar | Recharts | `agg_monthly_yoy` |
| YoYWaterfall | Nivo | `agg_variance_yoy` |
| WeekdayHourHeatmap | D3.js | `agg_time_distribution` |
| SeasonalityRadar | Recharts | `agg_seasonality` |

#### 1.3.3 勘定科目分析タブ (AccountAnalysisTab)

| コンポーネント | 使用ライブラリ | データソース |
|---------------|---------------|-------------|
| AccountTreemap | D3.js | `chart_of_accounts` + `agg_by_account` |
| AccountDailyLineScatter | Recharts | `agg_by_date_account` |
| MultiAccountMonthlyLine | Recharts | `agg_monthly_account` |
| AccountFlowChord | D3.js | `agg_account_flow` |
| AccountStatsTable | AG Grid | `agg_account_stats` |
| VarianceHighlightTable | AG Grid | `agg_variance_mom` |

#### 1.3.4 異常検知・リスクタブ (RiskDetectionTab)

| コンポーネント | 使用ライブラリ | データソース |
|---------------|---------------|-------------|
| RiskScoreHistogram | Recharts | `risk_scores` |
| RuleViolationRanking | Recharts | `agg_rule_violations` |
| HighRiskJournalTable | AG Grid | `risk_scores` (filtered) |
| RiskTrendStackedArea | Recharts | `agg_risk_trend` |
| MLScoreScatter | Recharts | `risk_scores` |
| AnomalyPatternTSNE | D3.js | `ml_embeddings` |

---

## 2. バックエンドモジュール構成

### 2.1 API層 (FastAPI)

```python
# api/v1/dashboard.py
from fastapi import APIRouter, Depends, Query
from typing import Optional, List

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

@router.get("/summary")
async def get_summary(
    filters: FilterParams = Depends()
) -> SummaryResponse:
    """サマリータブのデータ取得"""
    pass

@router.get("/timeseries")
async def get_timeseries(
    granularity: Literal["daily", "monthly"] = "monthly",
    filters: FilterParams = Depends()
) -> TimeSeriesResponse:
    """時系列分析データ取得"""
    pass

@router.get("/accounts/{account_code}")
async def get_account_detail(
    account_code: str,
    filters: FilterParams = Depends()
) -> AccountDetailResponse:
    """勘定科目詳細データ取得"""
    pass

@router.post("/filter")
async def apply_filter(
    filter_spec: FilterSpec
) -> FilteredDataResponse:
    """フィルタ適用（全タブ共通）"""
    pass

@router.get("/drilldown/{element_type}/{element_id}")
async def drilldown(
    element_type: str,
    element_id: str
) -> DrillDownResponse:
    """ドリルダウン処理"""
    pass
```

### 2.2 サービス層

```python
# services/import_service.py
class ImportService:
    """データインポートサービス"""

    async def validate_file(self, file_path: str) -> ValidationResult:
        """ファイル検証（10チェック項目）"""
        pass

    async def preview_import(self, file_path: str) -> ImportPreview:
        """インポートプレビュー生成"""
        pass

    async def execute_import(
        self,
        file_path: str,
        mapping: ColumnMapping
    ) -> ImportResult:
        """インポート実行"""
        pass


# services/mapping_service.py
class MappingService:
    """科目マッピングサービス"""

    async def auto_map(self, accounts: List[str]) -> List[MappingSuggestion]:
        """自動マッピング提案"""
        pass

    async def ai_suggest(self, account_name: str) -> MappingSuggestion:
        """AI推奨マッピング"""
        pass

    async def apply_template(self, template_id: str) -> None:
        """テンプレート適用"""
        pass


# services/aggregation_service.py
class AggregationService:
    """集計サービス"""

    async def run_all_aggregations(self) -> AggregationResult:
        """全集計テーブル更新"""
        pass

    async def run_incremental(self, since: datetime) -> AggregationResult:
        """差分集計"""
        pass
```

### 2.3 エージェントモジュール

#### 2.3.1 エージェント構成図

```
┌─────────────────────────────────────────────────────────────────┐
│                        Orchestrator                             │
│  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐            │
│  │ PlanEngine   │ │ TaskQueue    │ │ StateManager │            │
│  │              │ │              │ │              │            │
│  │ - create_plan│ │ - enqueue    │ │ - get_state  │            │
│  │ - prioritize │ │ - dequeue    │ │ - update     │            │
│  │ - adjust     │ │ - peek       │ │ - checkpoint │            │
│  └──────────────┘ └──────────────┘ └──────────────┘            │
└─────────────────────────────────────────────────────────────────┘
                              │
                    dispatch_agent()
                              │
        ┌─────────────────────┼─────────────────────┐
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│   Explorer    │   │ TrendAnalyzer │   │ RiskAnalyzer  │
│               │   │               │   │               │
│ Tools:        │   │ Tools:        │   │ Tools:        │
│ - view_summary│   │ - compare_    │   │ - get_rule_   │
│ - view_kpi    │   │   periods     │   │   violations  │
│ - scan_risk   │   │ - analyze_    │   │ - analyze_    │
│               │   │   seasonality │   │   pattern     │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│FinancialAna.  │   │ Investigator  │   │   Verifier    │
│               │   │               │   │               │
│ Tools:        │   │ Tools:        │   │ Tools:        │
│ - get_kpis    │   │ - search_     │   │ - check_      │
│ - analyze_    │   │   journals    │   │   validity    │
│   ratios      │   │ - get_related │   │ - search_     │
│               │   │ - add_note    │   │   counter_evd │
└───────────────┘   └───────────────┘   └───────────────┘
        │                     │                     │
        ▼                     ▼                     ▼
┌───────────────┐   ┌───────────────┐   ┌───────────────┐
│  Hypothesis   │   │  Visualizer   │   │   Reporter    │
│               │   │               │   │               │
│ Tools:        │   │ Tools:        │   │ Tools:        │
│ - generate_   │   │ - generate_   │   │ - create_ppt  │
│   hypothesis  │   │   chart       │   │ - create_pdf  │
│ - suggest_    │   │ - create_     │   │ - export_     │
│   investigation│  │   table       │   │   report      │
└───────────────┘   └───────────────┘   └───────────────┘
```

#### 2.3.2 エージェント実装詳細

```python
# agents/orchestrator.py
from langgraph.graph import StateGraph, END
from typing import TypedDict, Annotated
import operator

class AnalysisState(TypedDict):
    """分析セッション状態"""
    session_id: str
    current_phase: str
    analysis_plan: dict
    findings: Annotated[list, operator.add]
    visited_views: list
    applied_filters: list
    verification_results: list
    human_feedback: list
    is_complete: bool

class OrchestratorAgent:
    """オーケストレーターエージェント"""

    def __init__(self, llm_provider, tools):
        self.llm = llm_provider
        self.tools = tools
        self.graph = self._build_graph()

    def _build_graph(self) -> StateGraph:
        """LangGraphワークフロー構築"""
        graph = StateGraph(AnalysisState)

        # ノード定義
        graph.add_node("plan", self.create_plan)
        graph.add_node("explore", self.run_explorer)
        graph.add_node("analyze", self.run_specialists)
        graph.add_node("verify", self.run_verifier)
        graph.add_node("hypothesize", self.run_hypothesis)
        graph.add_node("human_check", self.check_human_input)
        graph.add_node("report", self.generate_report)

        # エッジ定義
        graph.set_entry_point("plan")
        graph.add_edge("plan", "explore")
        graph.add_edge("explore", "analyze")
        graph.add_conditional_edges(
            "analyze",
            self.should_continue,
            {
                "verify": "verify",
                "human_check": "human_check",
                "complete": "report"
            }
        )
        graph.add_edge("verify", "hypothesize")
        graph.add_conditional_edges(
            "hypothesize",
            self.need_more_investigation,
            {
                "continue": "analyze",
                "complete": "report"
            }
        )
        graph.add_edge("human_check", "analyze")
        graph.add_edge("report", END)

        return graph.compile()

    async def run(self, initial_state: AnalysisState) -> AnalysisState:
        """分析実行"""
        return await self.graph.ainvoke(initial_state)
```

#### 2.3.3 エージェントツール定義

```python
# agents/tools/dashboard_tools.py
from langchain.tools import tool
from pydantic import BaseModel, Field

class ViewChartInput(BaseModel):
    chart_id: str = Field(description="チャートID")
    filters: dict = Field(default={}, description="適用フィルタ")

@tool(args_schema=ViewChartInput)
async def view_chart(chart_id: str, filters: dict = {}) -> dict:
    """チャートのデータと画像を取得する

    Args:
        chart_id: 取得するチャートのID
        filters: 適用するフィルタ条件

    Returns:
        data: チャートの生データ
        image_base64: チャート画像（Base64）
        insights: 自動抽出された洞察
    """
    pass

@tool
async def apply_filter(filter_spec: dict) -> dict:
    """グローバルフィルタを適用する

    Args:
        filter_spec: フィルタ仕様
            - period: {start, end}
            - accounts: [account_codes]
            - risk_levels: [Critical, High, Medium, Low]
            - amount_range: {min, max}

    Returns:
        affected_charts: 影響を受けるチャートリスト
        record_count: フィルタ後のレコード数
    """
    pass

@tool
async def drill_down(element_id: str) -> dict:
    """チャート要素をドリルダウンする

    Args:
        element_id: ドリルダウン対象の要素ID

    Returns:
        detail_data: 詳細データ
        related_journals: 関連仕訳リスト
    """
    pass

@tool
async def search_journals(query: dict) -> list:
    """仕訳を検索する

    Args:
        query: 検索条件
            - account_code: 勘定科目コード
            - amount_range: {min, max}
            - date_range: {start, end}
            - description_keyword: 摘要キーワード
            - risk_level: リスクレベル

    Returns:
        journals: 条件に合致する仕訳リスト
    """
    pass

@tool
async def add_note(journal_id: str, note: str, note_type: str = "Comment") -> bool:
    """仕訳にメモを追加する

    Args:
        journal_id: 仕訳ID
        note: メモ内容
        note_type: 種別（Question/Comment/Issue/Resolution）

    Returns:
        success: 成功フラグ
    """
    pass

@tool
async def add_tag(journal_id: str, tag: str) -> bool:
    """仕訳にタグを付与する

    Args:
        journal_id: 仕訳ID
        tag: タグ名（要確認/要調査/異常/確認済/問題なし/クライアント確認）

    Returns:
        success: 成功フラグ
    """
    pass
```

### 2.4 バッチ処理モジュール

#### 2.4.1 ETLパイプライン

```python
# batch/etl/pipeline.py
from dataclasses import dataclass
from typing import List
import polars as pl

@dataclass
class ETLConfig:
    source_file: str
    file_type: str
    encoding: str = "utf-8"
    date_format: str = "%Y-%m-%d"

class ETLPipeline:
    """ETLパイプライン"""

    def __init__(self, config: ETLConfig):
        self.config = config

    async def extract(self) -> pl.DataFrame:
        """データ抽出"""
        if self.config.file_type == "csv":
            return pl.read_csv(
                self.config.source_file,
                encoding=self.config.encoding
            )
        elif self.config.file_type == "xlsx":
            return pl.read_excel(self.config.source_file)
        # ... other formats

    async def transform(self, df: pl.DataFrame) -> pl.DataFrame:
        """データ変換"""
        return (
            df
            # 日付正規化
            .with_columns([
                pl.col("Effective_Date").str.to_date(self.config.date_format),
                pl.col("Entry_Date").str.to_date(self.config.date_format),
            ])
            # 金額正規化
            .with_columns([
                pl.when(pl.col("Amount") > 0)
                .then(pl.col("Amount"))
                .otherwise(0)
                .alias("debit_amount"),
                pl.when(pl.col("Amount") < 0)
                .then(pl.col("Amount").abs())
                .otherwise(0)
                .alias("credit_amount"),
            ])
            # 必須カラム検証
            .with_columns([
                pl.col("JE_Number").fill_null("UNKNOWN"),
            ])
        )

    async def load(self, df: pl.DataFrame) -> int:
        """データロード"""
        # DuckDBへの書き込み
        pass

    async def run(self) -> ETLResult:
        """パイプライン実行"""
        df = await self.extract()
        df = await self.transform(df)
        count = await self.load(df)
        return ETLResult(records_loaded=count)
```

#### 2.4.2 ルールエンジン

```python
# batch/rules/engine.py
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import List, Optional
import polars as pl

@dataclass
class RuleResult:
    rule_id: str
    matched: bool
    score: int
    details: Optional[dict] = None

class AuditRule(ABC):
    """監査ルール基底クラス"""

    rule_id: str
    category: str
    severity: str  # Critical, High, Medium, Low
    score: int
    description: str

    @abstractmethod
    def evaluate(self, journal: dict) -> RuleResult:
        """単一仕訳の評価"""
        pass

    def batch_evaluate(self, df: pl.DataFrame) -> pl.DataFrame:
        """バッチ評価（オーバーライド可能）"""
        # デフォルト実装: 行ごとにevaluate呼び出し
        pass


# 金額ルール例
class AMT001_MaterialityThreshold(AuditRule):
    """AMT_001: 重要性基準値超過"""

    rule_id = "AMT_001"
    category = "金額"
    severity = "Critical"
    score = 40
    description = "金額が重要性基準値を超過"

    def __init__(self, threshold: float = 100_000_000):
        self.threshold = threshold

    def evaluate(self, journal: dict) -> RuleResult:
        amount = abs(journal.get("Amount", 0))
        matched = amount >= self.threshold
        return RuleResult(
            rule_id=self.rule_id,
            matched=matched,
            score=self.score if matched else 0,
            details={"amount": amount, "threshold": self.threshold}
        )

    def batch_evaluate(self, df: pl.DataFrame) -> pl.DataFrame:
        """Polarsによる高速バッチ評価"""
        return df.with_columns([
            (pl.col("Amount").abs() >= self.threshold)
            .alias(f"rule_{self.rule_id}_matched"),
            pl.when(pl.col("Amount").abs() >= self.threshold)
            .then(self.score)
            .otherwise(0)
            .alias(f"rule_{self.rule_id}_score")
        ])


class RuleEngine:
    """ルールエンジン"""

    def __init__(self):
        self.rules: List[AuditRule] = []

    def register_rule(self, rule: AuditRule):
        self.rules.append(rule)

    def register_all_rules(self):
        """全85ルールを登録"""
        # 金額ルール (15)
        self.register_rule(AMT001_MaterialityThreshold())
        # ... 他のルール

    async def evaluate_all(self, df: pl.DataFrame) -> pl.DataFrame:
        """全ルール評価"""
        for rule in self.rules:
            df = rule.batch_evaluate(df)

        # 統合スコア計算
        score_cols = [c for c in df.columns if c.endswith("_score")]
        df = df.with_columns([
            pl.sum_horizontal(score_cols).alias("rule_risk_score")
        ])

        return df
```

#### 2.4.3 機械学習異常検知

```python
# batch/ml/models/isolation_forest.py
from sklearn.ensemble import IsolationForest
import polars as pl
import numpy as np

class IsolationForestModel:
    """Isolation Forest異常検知モデル"""

    def __init__(self, contamination: float = 0.1, n_estimators: int = 100):
        self.model = IsolationForest(
            contamination=contamination,
            n_estimators=n_estimators,
            random_state=42
        )
        self.feature_columns = [
            "amount_abs",
            "amount_log",
            "hour_of_day",
            "day_of_week",
            "days_since_period_start",
        ]

    def prepare_features(self, df: pl.DataFrame) -> np.ndarray:
        """特徴量準備"""
        return (
            df.select([
                pl.col("Amount").abs().alias("amount_abs"),
                pl.col("Amount").abs().log1p().alias("amount_log"),
                pl.col("Entry_Date").dt.hour().alias("hour_of_day"),
                pl.col("Entry_Date").dt.weekday().alias("day_of_week"),
                # ... more features
            ])
            .to_numpy()
        )

    def fit(self, df: pl.DataFrame):
        """モデル学習"""
        X = self.prepare_features(df)
        self.model.fit(X)

    def predict(self, df: pl.DataFrame) -> pl.DataFrame:
        """異常スコア予測"""
        X = self.prepare_features(df)
        scores = self.model.decision_function(X)
        # スコアを0-1に正規化
        normalized_scores = (scores - scores.min()) / (scores.max() - scores.min())

        return df.with_columns([
            pl.lit(normalized_scores).alias("anomaly_score_if")
        ])


# batch/ml/scoring.py
class IntegratedScorer:
    """統合スコアリング"""

    def __init__(self, rule_weight: float = 0.6, ml_weight: float = 0.4):
        self.rule_weight = rule_weight
        self.ml_weight = ml_weight

    def calculate(self, df: pl.DataFrame) -> pl.DataFrame:
        """統合リスクスコア計算"""
        # MLスコアの統合（5手法の平均）
        ml_cols = [
            "anomaly_score_if",
            "anomaly_score_lof",
            "anomaly_score_svm",
            "reconstruction_error",
            "benford_score"
        ]
        df = df.with_columns([
            pl.mean_horizontal(ml_cols).alias("ml_risk_score")
        ])

        # ルールスコアの正規化（0-100）
        max_rule_score = 200  # 想定最大スコア
        df = df.with_columns([
            (pl.col("rule_risk_score") / max_rule_score * 100)
            .clip(0, 100)
            .alias("rule_risk_score_normalized")
        ])

        # 統合スコア
        df = df.with_columns([
            (
                pl.col("rule_risk_score_normalized") * self.rule_weight +
                pl.col("ml_risk_score") * 100 * self.ml_weight
            )
            .clip(0, 100)
            .alias("integrated_risk_score")
        ])

        # リスクレベル分類
        df = df.with_columns([
            pl.when(pl.col("integrated_risk_score") >= 81)
            .then(pl.lit("Critical"))
            .when(pl.col("integrated_risk_score") >= 61)
            .then(pl.lit("High"))
            .when(pl.col("integrated_risk_score") >= 31)
            .then(pl.lit("Medium"))
            .otherwise(pl.lit("Low"))
            .alias("risk_level")
        ])

        return df
```

### 2.5 レポート生成モジュール

```python
# reports/ppt_generator.py
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RgbColor
from dataclasses import dataclass
from typing import List

@dataclass
class SlideContent:
    title: str
    layout_type: str
    content: dict

class PPTGenerator:
    """PPT自動生成"""

    COLORS = {
        "primary": RgbColor(0x1E, 0x3A, 0x5F),      # ネイビー
        "secondary": RgbColor(0x2E, 0x86, 0xAB),    # ティール
        "accent": RgbColor(0xF1, 0x8F, 0x01),       # オレンジ
        "critical": RgbColor(0xDC, 0x35, 0x45),     # 赤
        "high": RgbColor(0xFD, 0x7E, 0x14),         # 橙
        "medium": RgbColor(0xFF, 0xC1, 0x07),       # 黄
        "low": RgbColor(0x28, 0xA7, 0x45),          # 緑
    }

    def __init__(self, template_path: str = None):
        if template_path:
            self.prs = Presentation(template_path)
        else:
            self.prs = Presentation()
            self._setup_master()

    def generate(self, insights: List[dict], period: dict) -> bytes:
        """PPT生成（10スライド標準）"""
        # 1. 表紙
        self._add_title_slide(period)

        # 2. エグゼクティブサマリー
        self._add_executive_summary(insights)

        # 3. 期間サマリー
        self._add_period_summary(period)

        # 4. リスク概況
        self._add_risk_overview(insights)

        # 5-7. 重要発見事項（Top3）
        top_insights = sorted(insights, key=lambda x: x["priority_score"], reverse=True)[:3]
        for i, insight in enumerate(top_insights, 1):
            self._add_finding_slide(insight, i)

        # 8. 財務指標ハイライト
        self._add_financial_highlights()

        # 9. 提言・アクションアイテム
        self._add_recommendations(insights)

        # 10. Appendix
        self._add_appendix()

        # バイナリ出力
        import io
        output = io.BytesIO()
        self.prs.save(output)
        return output.getvalue()

    def _add_title_slide(self, period: dict):
        """表紙スライド"""
        slide = self.prs.slides.add_slide(self.prs.slide_layouts[6])  # Blank
        # ... 実装
```

---

## 3. モジュール間依存関係

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend                                │
│  components → stores → services (API clients)                   │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼ HTTP/SSE
┌─────────────────────────────────────────────────────────────────┐
│                      API Layer (FastAPI)                        │
│  api/v1/* → services/* → repositories/*                        │
└─────────────────────────────────────────────────────────────────┘
                              │
          ┌───────────────────┼───────────────────┐
          ▼                   ▼                   ▼
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│     Agents      │ │     Batch       │ │    Reports      │
│ orchestrator    │ │ etl, rules, ml  │ │ ppt, pdf        │
│ specialists     │ │ aggregation     │ │ insights        │
│ tools           │ │ financial       │ │                 │
└─────────────────┘ └─────────────────┘ └─────────────────┘
          │                   │                   │
          └───────────────────┼───────────────────┘
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                      Data Layer                                 │
│  db/duckdb (journal, aggregates)                               │
│  db/sqlite (metadata, rules, sessions)                         │
│  repositories/*                                                 │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                   LLM Providers (8種類)                          │
│  anthropic, openai, google, bedrock, azure_foundry,            │
│  vertex_ai, azure, ollama                                       │
└─────────────────────────────────────────────────────────────────┘
```

---

**次のステップ**: [03_database_design.md](03_database_design.md) でデータベース詳細設計を行います。
