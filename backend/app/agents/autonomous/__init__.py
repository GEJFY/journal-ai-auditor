"""自律型監査エージェントパッケージ。

5フェーズ分析ループ (Observe→Hypothesize→Explore→Verify→Synthesize) で
仕訳データを自律的に探索・分析し、監査インサイトを生成する。
"""

from app.agents.autonomous.agent import AutonomousAuditAgent
from app.agents.autonomous.state import (
    AuditInsight,
    AuditPhase,
    AutonomousAuditState,
    Hypothesis,
)
from app.agents.autonomous.tool_registry import (
    AuditToolRegistry,
    ToolDefinition,
    ToolResult,
)

__all__ = [
    "AutonomousAuditAgent",
    "AuditInsight",
    "AuditPhase",
    "AutonomousAuditState",
    "Hypothesis",
    "AuditToolRegistry",
    "ToolDefinition",
    "ToolResult",
]
