"""AutonomousAuditAgent のユニットテスト。

LLM 呼び出しをモックし、フェーズ遷移と状態管理をテストする。
"""

import json
from unittest.mock import MagicMock, patch

import pytest

from app.agents.autonomous.agent import AutonomousAuditAgent, _extract_json
from app.agents.autonomous.state import AuditPhase
from app.agents.autonomous.tool_registry import (
    AuditToolRegistry,
    ToolDefinition,
    ToolResult,
)


def _mock_registry() -> AuditToolRegistry:
    """テスト用の最小レジストリを生成。"""
    registry = AuditToolRegistry()

    def pop_fn(fiscal_year: int = 2024, **kwargs) -> ToolResult:
        return ToolResult(
            tool_name="population_statistics",
            success=True,
            summary="10,000件の仕訳を確認",
            key_findings=["総額100億円", "手動仕訳20%"],
            data={"total_count": 10000, "total_debit": 10_000_000_000},
        )

    def rule_fn(fiscal_year: int = 2024, **kwargs) -> ToolResult:
        return ToolResult(
            tool_name="rule_risk_summary",
            success=True,
            summary="50件の違反を検出",
            key_findings=["HIGH 10件"],
            data={"total_violations": 50},
        )

    def ml_fn(fiscal_year: int = 2024, **kwargs) -> ToolResult:
        return ToolResult(
            tool_name="ml_anomaly_summary",
            success=True,
            summary="15件の異常を検出",
            key_findings=["IF 8件"],
            data={"total_anomalies": 15},
        )

    def strat_fn(fiscal_year: int = 2024, **kwargs) -> ToolResult:
        return ToolResult(
            tool_name="stratification_analysis",
            success=True,
            summary="金額層別分析完了",
            key_findings=["1億円超3件"],
            data={},
        )

    for name, fn in [
        ("population_statistics", pop_fn),
        ("rule_risk_summary", rule_fn),
        ("ml_anomaly_summary", ml_fn),
        ("stratification_analysis", strat_fn),
    ]:
        registry.register(
            ToolDefinition(
                name=name,
                description=f"{name} desc",
                category="test",
                parameters={"fiscal_year": {"type": "integer"}},
                execute_fn=fn,
            )
        )
    return registry


class TestExtractJson:
    def test_plain_json(self):
        text = '{"key": "value"}'
        assert _extract_json(text) == {"key": "value"}

    def test_json_in_code_block(self):
        text = 'Some text\n```json\n{"a": 1}\n```\nmore text'
        assert _extract_json(text) == {"a": 1}

    def test_json_in_generic_block(self):
        text = '```\n{"b": 2}\n```'
        assert _extract_json(text) == {"b": 2}

    def test_invalid_json_raises(self):
        with pytest.raises(json.JSONDecodeError):
            _extract_json("not json")


class TestAutonomousAuditAgent:
    def test_init(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        assert agent.registry is registry
        assert agent.config is not None

    def test_create_initial_state(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024, auto_approve=True)
        assert state["fiscal_year"] == 2024
        assert state["current_phase"] == AuditPhase.OBSERVE
        assert state["awaiting_approval"] is False
        assert state["session_id"] is not None
        assert len(state["hypotheses"]) == 0

    def test_create_initial_state_hitl(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024, auto_approve=False)
        assert state["awaiting_approval"] is True

    def test_observe_node(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024)

        # LLM をモック
        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {"notable_patterns": ["パターン1", "パターン2"]},
            ensure_ascii=False,
        )
        agent.llm = MagicMock()
        agent.llm.invoke.return_value = mock_response

        result = agent._observe_node(state)
        assert result["current_phase"] == AuditPhase.OBSERVE
        assert len(result["notable_patterns"]) == 2
        assert "population_statistics" in result["observations"]

    def test_hypothesize_node(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024)
        state["observations"] = {"pop": {"summary": "test"}}
        state["notable_patterns"] = ["pattern1"]

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "hypotheses": [
                    {
                        "id": "H-001",
                        "title": "テスト仮説",
                        "description": "説明",
                        "rationale": "根拠",
                        "test_approach": "検証方法",
                        "tools_to_use": ["stratification_analysis"],
                        "priority": 1,
                    }
                ]
            },
            ensure_ascii=False,
        )
        agent.llm = MagicMock()
        agent.llm.invoke.return_value = mock_response

        result = agent._hypothesize_node(state)
        assert result["current_phase"] == AuditPhase.HYPOTHESIZE
        assert len(result["hypotheses"]) == 1
        assert result["hypotheses"][0]["id"] == "H-001"

    def test_after_hypothesize_auto_approve(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024, auto_approve=True)
        assert agent._after_hypothesize(state) == "explore"

    def test_after_hypothesize_hitl(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024, auto_approve=False)
        assert agent._after_hypothesize(state) == "await"

    def test_explore_node(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024)
        state["hypotheses"] = [
            {
                "id": "H-001",
                "title": "test",
                "description": "d",
                "rationale": "r",
                "test_approach": "t",
                "tools_to_use": ["stratification_analysis"],
                "priority": 1,
                "status": "pending",
                "grounding_score": 0.0,
                "evidence_for": [],
                "evidence_against": [],
            }
        ]

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "tool_calls": [
                    {
                        "hypothesis_id": "H-001",
                        "tool_name": "stratification_analysis",
                        "parameters": {"fiscal_year": 2024},
                        "reason": "分布確認",
                    }
                ]
            },
            ensure_ascii=False,
        )
        agent.llm = MagicMock()
        agent.llm.invoke.return_value = mock_response

        result = agent._explore_node(state)
        assert result["current_phase"] == AuditPhase.EXPLORE
        assert len(result["tool_results"]) == 1
        assert result["tool_results"][0]["tool_name"] == "stratification_analysis"

    def test_verify_node(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024)
        state["hypotheses"] = [
            {
                "id": "H-001",
                "title": "test",
                "description": "d",
                "rationale": "r",
                "test_approach": "t",
                "tools_to_use": [],
                "priority": 1,
                "status": "pending",
                "grounding_score": 0.0,
                "evidence_for": [],
                "evidence_against": [],
            }
        ]
        state["tool_results"] = [
            {"tool_name": "strat", "summary": "ok", "key_findings": ["f1"]}
        ]

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "verifications": [
                    {
                        "hypothesis_id": "H-001",
                        "grounding_score": 0.85,
                        "verdict": "supported",
                        "evidence_for": ["ev1"],
                        "evidence_against": [],
                        "needs_more_exploration": False,
                    }
                ]
            },
            ensure_ascii=False,
        )
        agent.llm = MagicMock()
        agent.llm.invoke.return_value = mock_response

        result = agent._verify_node(state)
        assert result["current_phase"] == AuditPhase.VERIFY
        hyp = result["hypotheses"][0]
        assert hyp["status"] == "supported"
        assert hyp["grounding_score"] == 0.85

    def test_synthesize_node(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024)
        state["verified_hypotheses"] = [
            {"id": "H-001", "title": "t", "status": "supported"}
        ]
        state["tool_results"] = [
            {"tool_name": "pop", "summary": "ok", "key_findings": []}
        ]

        mock_response = MagicMock()
        mock_response.content = json.dumps(
            {
                "insights": [
                    {
                        "id": "INS-001",
                        "title": "重要インサイト",
                        "description": "詳細",
                        "category": "risk",
                        "severity": "HIGH",
                        "affected_amount": 50000000,
                        "affected_count": 10,
                        "recommendations": ["推奨1"],
                        "related_hypotheses": ["H-001"],
                    }
                ],
                "executive_summary": "テストサマリー",
            },
            ensure_ascii=False,
        )
        agent.llm = MagicMock()
        agent.llm.invoke.return_value = mock_response

        result = agent._synthesize_node(state)
        assert result["current_phase"] == AuditPhase.SYNTHESIZE
        assert len(result["insights"]) == 1
        assert result["insights"][0]["severity"] == "HIGH"
        assert result["executive_summary"] == "テストサマリー"

    def test_finalize_node(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        state = agent._create_initial_state(2024)
        state["hypotheses"] = [{"id": "H-001", "status": "supported"}]
        state["insights"] = [
            {"id": "INS-001", "severity": "HIGH", "title": "t", "description": "d",
             "category": "risk", "evidence": [], "grounding_score": 0.8,
             "affected_amount": 0, "affected_count": 0, "recommendations": []}
        ]
        state["exploration_log"] = [{"tool": "t1"}]
        state["executive_summary"] = "summary"

        # DB 書き込みをモック
        with patch("app.agents.autonomous.agent.duckdb_manager") as mock_db:
            mock_conn = MagicMock()
            mock_db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
            mock_db.connect.return_value.__exit__ = MagicMock(return_value=False)

            result = agent._finalize_node(state)

        assert result["current_phase"] == AuditPhase.COMPLETE
        assert result["completed_at"] is not None

    def test_graph_structure(self):
        registry = _mock_registry()
        agent = AutonomousAuditAgent(registry=registry)
        graph = agent.graph
        assert graph is not None
        # 2回目はキャッシュ
        assert agent.graph is graph
