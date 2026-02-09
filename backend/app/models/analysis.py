"""Analysis result models."""

from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field


class RiskScore(BaseModel):
    """Risk score for a journal entry."""

    journal_id: str
    score: Decimal = Field(ge=0, le=100)
    level: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"]
    factors: list[str] = Field(default_factory=list)
    calculated_at: datetime


class AnomalyFlag(BaseModel):
    """Anomaly detection flag."""

    flag_id: str = Field(
        description="異常フラグID (A01-A10)",
    )
    flag_name: str = Field(
        description="異常フラグ名",
    )
    description: str = Field(
        description="説明",
    )
    detection_method: Literal["RULE", "ML", "STATISTICAL"] = Field(
        description="検出手法",
    )
    confidence: Decimal = Field(
        ge=0,
        le=1,
        description="信頼度 (0-1)",
    )


class RuleViolation(BaseModel):
    """Rule violation record."""

    rule_id: str = Field(
        description="ルールID",
    )
    rule_name: str = Field(
        description="ルール名",
    )
    category: Literal[
        "AMOUNT", "TIME", "ACCOUNT", "APPROVAL", "DESC", "PATTERN", "TREND"
    ] = Field(
        description="カテゴリ",
    )
    severity: Literal["LOW", "MEDIUM", "HIGH", "CRITICAL"] = Field(
        description="重要度",
    )
    message: str = Field(
        description="違反メッセージ",
    )
    evidence: dict | None = Field(
        default=None,
        description="証拠データ",
    )


class AnalysisSession(BaseModel):
    """Analysis session record."""

    session_id: str
    started_at: datetime
    ended_at: datetime | None = None
    status: Literal["running", "completed", "failed", "cancelled"] = "running"
    fiscal_year: int
    filters: dict | None = None
    total_entries_analyzed: int = 0
    total_insights: int = 0
    summary: str | None = None


class Insight(BaseModel):
    """Analysis insight."""

    insight_id: str
    session_id: str
    category: Literal["ANOMALY", "TREND", "RISK", "COMPLIANCE", "EFFICIENCY", "OTHER"]
    title: str
    description: str
    severity: Literal["INFO", "LOW", "MEDIUM", "HIGH", "CRITICAL"] = "INFO"
    evidence: dict | None = None
    affected_journals: list[str] = Field(default_factory=list)
    affected_count: int = 0
    affected_amount: Decimal = Decimal("0")
    recommendation: str | None = None
    created_at: datetime


class AggregatedMetrics(BaseModel):
    """Aggregated metrics for dashboard."""

    # Period metrics
    total_entries: int = 0
    total_journals: int = 0
    total_debit: Decimal = Decimal("0")
    total_credit: Decimal = Decimal("0")

    # Account metrics
    unique_accounts: int = 0
    top_debit_accounts: list[dict] = Field(default_factory=list)
    top_credit_accounts: list[dict] = Field(default_factory=list)

    # Risk metrics
    high_risk_count: int = 0
    medium_risk_count: int = 0
    low_risk_count: int = 0
    anomaly_count: int = 0
    violation_count: int = 0

    # Time metrics
    avg_entries_per_day: float = 0
    peak_entry_dates: list[str] = Field(default_factory=list)
    weekend_entry_count: int = 0
    late_night_entry_count: int = 0

    # User metrics
    unique_preparers: int = 0
    unique_approvers: int = 0
    self_approved_count: int = 0


class BenfordAnalysis(BaseModel):
    """Benford's Law analysis results."""

    digit_position: Literal[1, 2]
    observed_distribution: dict[str, float]
    expected_distribution: dict[str, float]
    chi_square_statistic: float
    p_value: float
    is_conforming: bool
    deviation_digits: list[str] = Field(default_factory=list)
    sample_size: int
