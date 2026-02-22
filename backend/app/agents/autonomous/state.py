"""自律型監査エージェントの状態定義。

5フェーズ分析ループ (Observe→Hypothesize→Explore→Verify→Synthesize) の
各フェーズ間で共有される状態を定義する。
"""

from dataclasses import dataclass, field
from enum import StrEnum
from typing import Any, TypedDict

from langchain_core.messages import BaseMessage


class AuditPhase(StrEnum):
    """5フェーズ分析ライフサイクル。"""

    OBSERVE = "observe"
    HYPOTHESIZE = "hypothesize"
    EXPLORE = "explore"
    VERIFY = "verify"
    SYNTHESIZE = "synthesize"
    COMPLETE = "complete"
    ERROR = "error"


@dataclass
class Hypothesis:
    """仮説フェーズで生成される検証可能な仮説。"""

    id: str  # e.g. "H-001"
    title: str
    description: str
    rationale: str
    test_approach: str
    tools_to_use: list[str] = field(default_factory=list)
    priority: int = 1
    status: str = "pending"  # pending / testing / supported / refuted / inconclusive
    evidence_for: list[str] = field(default_factory=list)
    evidence_against: list[str] = field(default_factory=list)
    grounding_score: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "rationale": self.rationale,
            "test_approach": self.test_approach,
            "tools_to_use": self.tools_to_use,
            "priority": self.priority,
            "status": self.status,
            "evidence_for": self.evidence_for,
            "evidence_against": self.evidence_against,
            "grounding_score": self.grounding_score,
        }


@dataclass
class AuditInsight:
    """統合フェーズで生成される構造化されたインサイト。"""

    id: str  # e.g. "INS-001"
    title: str
    description: str
    category: str  # risk, anomaly, trend, compliance, concentration, etc.
    severity: str  # CRITICAL, HIGH, MEDIUM, LOW, INFO
    evidence: list[dict[str, Any]] = field(default_factory=list)
    grounding_score: float = 0.0
    affected_amount: float = 0.0
    affected_count: int = 0
    recommendations: list[str] = field(default_factory=list)
    related_hypotheses: list[str] = field(default_factory=list)
    supporting_data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "description": self.description,
            "category": self.category,
            "severity": self.severity,
            "evidence": self.evidence,
            "grounding_score": self.grounding_score,
            "affected_amount": self.affected_amount,
            "affected_count": self.affected_count,
            "recommendations": self.recommendations,
            "related_hypotheses": self.related_hypotheses,
            "supporting_data": self.supporting_data,
        }


class AutonomousAuditState(TypedDict, total=False):
    """自律型監査エージェントのグラフ状態。

    LangGraph StateGraph を流れる状態辞書。
    base.AgentState のパターンを拡張し、フェーズ固有のフィールドを追加。
    """

    # 入力
    session_id: str
    fiscal_year: int
    scope: dict[str, Any]  # period_from, period_to, accounts 等のフィルタ

    # 会話履歴
    messages: list[BaseMessage]

    # フェーズ管理
    current_phase: str  # AuditPhase の値
    phase_history: list[dict[str, Any]]

    # Observe フェーズ出力
    observations: dict[str, Any]  # データ統計・パターン・異常サマリ
    notable_patterns: list[str]  # LLM が特定した注目パターン

    # Hypothesize フェーズ出力
    hypotheses: list[dict[str, Any]]  # Hypothesis.to_dict() のリスト
    approved_hypotheses: list[str]  # 承認済み仮説 ID

    # Explore フェーズ出力
    tool_results: list[dict[str, Any]]  # ToolResult.to_dict() のリスト
    exploration_log: list[dict[str, Any]]  # ツール呼び出しログ

    # Verify フェーズ出力
    verified_hypotheses: list[dict[str, Any]]  # 検証済み仮説

    # Synthesize フェーズ出力
    insights: list[dict[str, Any]]  # AuditInsight.to_dict() のリスト
    executive_summary: str  # LLM 生成エグゼクティブサマリー

    # 処理制御
    step_count: int
    max_steps: int
    max_hypotheses: int  # 生成する仮説の最大数 (デフォルト 5)
    max_tools_per_hypothesis: int  # 仮説あたりのツール呼び出し最大数 (デフォルト 3)

    # HITL
    awaiting_approval: bool
    human_feedback: str | None

    # メタデータ
    started_at: str
    completed_at: str | None
    error: str | None
