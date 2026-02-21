"""
Agent→レポート統合パイプラインのテスト

オーケストレーターの発見事項永続化、
レポートジェネレーターのagent_findings取り込み、
レポートAPIのagent_findingsレスポンスを検証する。
"""

from unittest.mock import MagicMock, patch

import pytest

# テスト用 agent findings データ
MOCK_AGENT_FINDINGS = [
    {
        "finding_id": "AF-TEST0001",
        "agent_type": "analysis",
        "title": "高額取引の集中パターンを検出",
        "description": "期末3日間に高額取引が集中しています。",
        "severity": "HIGH",
        "category": "amount",
        "affected_amount": 500_000_000,
        "affected_count": 15,
        "recommendation": "期末仕訳の詳細調査を推奨",
        "status": "open",
    },
    {
        "finding_id": "AF-TEST0002",
        "agent_type": "investigation",
        "title": "自己承認仕訳の増加傾向",
        "description": "第4四半期に自己承認仕訳が前期比150%増加。",
        "severity": "MEDIUM",
        "category": "approval",
        "affected_amount": 120_000_000,
        "affected_count": 30,
        "recommendation": "承認フロー見直しを推奨",
        "status": "open",
    },
    {
        "finding_id": "AF-TEST0003",
        "agent_type": "review",
        "title": "ベンフォード分析で軽微な偏差",
        "description": "数字7の出現頻度がやや高い。",
        "severity": "LOW",
        "category": "benford",
        "affected_amount": 0,
        "affected_count": 0,
        "recommendation": "継続的モニタリングを推奨",
        "status": "open",
    },
]

# DB結果としてのタプル形式
MOCK_AGENT_FINDINGS_TUPLES = [
    (
        f["finding_id"],
        f["agent_type"],
        f["title"],
        f["description"],
        f["severity"],
        f["category"],
        f["affected_amount"],
        f["affected_count"],
        f["recommendation"],
        f["status"],
    )
    for f in MOCK_AGENT_FINDINGS
]

# GET /findings/agents 用のタプル（workflow_id, created_at追加）
MOCK_AGENT_FINDINGS_FULL_TUPLES = [
    (
        f["finding_id"],
        "wf-test-001",
        f["agent_type"],
        f["title"],
        f["description"],
        f["severity"],
        f["category"],
        f["affected_amount"],
        f["affected_count"],
        f["recommendation"],
        f["status"],
        "2026-02-17 10:00:00",
    )
    for f in MOCK_AGENT_FINDINGS
]


# ============================================================
# オーケストレーター: _persist_findings テスト
# ============================================================


class TestOrchestratorPersistence:
    """オーケストレーターの発見事項永続化テスト."""

    def test_persist_findings_inserts_to_db(self):
        """_persist_findingsがDBにINSERTすることを確認."""
        mock_db = MagicMock()

        with patch("app.agents.orchestrator.duckdb_manager", mock_db):
            from app.agents.orchestrator import AgentOrchestrator

            orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)

            findings = [
                {"title": "テスト発見事項1", "severity": "HIGH"},
                {"title": "テスト発見事項2", "severity": "MEDIUM"},
            ]

            count = orchestrator._persist_findings("wf-001", "analysis", 2024, findings)

            assert count == 2
            assert mock_db.execute.call_count == 2

            # INSERT文が呼ばれることを検証
            first_call = mock_db.execute.call_args_list[0]
            assert "INSERT INTO audit_findings" in first_call[0][0]
            params = first_call[0][1]
            assert params[1] == "wf-001"  # workflow_id
            assert params[2] == "analysis"  # agent_type
            assert params[3] == 2024  # fiscal_year

    def test_persist_findings_handles_error(self):
        """DB例外発生時もスキップして続行することを確認."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = [
            Exception("DB error"),
            None,  # 2件目は成功
        ]

        with patch("app.agents.orchestrator.duckdb_manager", mock_db):
            from app.agents.orchestrator import AgentOrchestrator

            orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)

            findings = [
                {"title": "失敗する発見事項"},
                {"title": "成功する発見事項"},
            ]

            count = orchestrator._persist_findings(
                "wf-002", "investigation", 2024, findings
            )

            assert count == 1

    def test_persist_findings_empty_list(self):
        """空リストの場合0件を返すことを確認."""
        with patch("app.agents.orchestrator.duckdb_manager", MagicMock()):
            from app.agents.orchestrator import AgentOrchestrator

            orchestrator = AgentOrchestrator.__new__(AgentOrchestrator)
            count = orchestrator._persist_findings("wf-003", "review", 2024, [])
            assert count == 0


# ============================================================
# PPTレポート: agent_findings スライドテスト
# ============================================================


class TestPPTAgentFindings:
    """PPTレポートのagent_findingsスライドテスト."""

    def _create_generator(self, agent_findings_tuples):
        """モック付きPPTジェネレーターを作成."""
        mock_db = MagicMock()

        # クエリ別にモック応答を設定
        def side_effect(query, params=None):
            if "audit_findings" in query:
                return agent_findings_tuples
            if "rule_violations" in query:
                return [("高額取引", 100)]
            # monthly trend: GROUP BY accounting_period
            if "accounting_period" in query and "GROUP BY" in query:
                return [(i, 1000, 100_000_000, 5) for i in range(1, 13)]
            # risk distribution: GROUP BY level
            if "level" in query and "GROUP BY" in query:
                return [("high", 50), ("medium", 200), ("low", 2000), ("minimal", 7750)]
            # benford digits
            if "SUBSTR" in query:
                return [(d, 1000 + d * 100) for d in range(1, 10)]
            # Summary stats (7 columns)
            return [(10000, 500, 5_000_000_000, "2024-04-01", "2025-03-31", 50, 25.3)]

        mock_db.execute = MagicMock(side_effect=side_effect)

        with patch("app.services.report_generator.duckdb_manager", mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(fiscal_year=2024, include_agent_findings=True)
            gen = PPTReportGenerator(config)
            return gen

    def test_ppt_with_agent_findings(self):
        """agent_findingsがある場合、スライドが追加されること."""
        gen = self._create_generator(MOCK_AGENT_FINDINGS_TUPLES)
        ppt_bytes = gen.generate()

        assert len(ppt_bytes) > 0
        # 通常10スライド + agent_findingsスライドで11スライド
        assert len(gen.prs.slides) == 11

    def test_ppt_without_agent_findings(self):
        """agent_findingsがない場合、スライドが追加されないこと."""
        gen = self._create_generator([])
        ppt_bytes = gen.generate()

        assert len(ppt_bytes) > 0
        assert len(gen.prs.slides) == 10


# ============================================================
# PDFレポート: agent_findings セクションテスト
# ============================================================


class TestPDFAgentFindings:
    """PDFレポートのagent_findingsセクションテスト."""

    def test_pdf_with_agent_findings(self):
        """agent_findingsがある場合、PDFが正常に生成されること."""
        mock_db = MagicMock()

        def side_effect(query, params=None):
            if "audit_findings" in query:
                return MOCK_AGENT_FINDINGS_TUPLES
            if "rule_violations" in query:
                return [("高額取引", 100)]
            if "accounting_period" in query and "GROUP BY" in query:
                return [(i, 1000, 100_000_000, 5) for i in range(1, 13)]
            if "level" in query and "GROUP BY" in query:
                return [("high", 50), ("medium", 200), ("low", 2000), ("minimal", 7750)]
            if "SUBSTR" in query:
                return [(d, 1000 + d * 100) for d in range(1, 10)]
            return [(10000, 500, 5_000_000_000, "2024-04-01", "2025-03-31", 50, 25.3)]

        mock_db.execute = MagicMock(side_effect=side_effect)

        with patch("app.services.report_generator.duckdb_manager", mock_db):
            from app.services.report_generator import PDFReportGenerator, ReportConfig

            config = ReportConfig(fiscal_year=2024, include_agent_findings=True)
            gen = PDFReportGenerator(config)
            pdf_bytes = gen.generate()

            assert len(pdf_bytes) > 0
            assert len(gen._agent_findings) == 3


# ============================================================
# レポートAPI: agent_findings レスポンステスト
# ============================================================


class TestReportAPIAgentFindings:
    """レポートAPIのagent_findings関連テスト."""

    def test_query_agent_findings_returns_list(self):
        """_query_agent_findingsがリストを返すこと."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MOCK_AGENT_FINDINGS_FULL_TUPLES

        from app.api.endpoints.reports import _query_agent_findings

        result = _query_agent_findings(mock_db, 2024)

        assert len(result) == 3
        assert result[0]["finding_id"] == "AF-TEST0001"
        assert result[0]["severity"] == "HIGH"
        assert result[0]["workflow_id"] == "wf-test-001"

    def test_query_agent_findings_handles_error(self):
        """DBエラー時に空リストを返すこと."""
        mock_db = MagicMock()
        mock_db.execute.side_effect = Exception("table not found")

        from app.api.endpoints.reports import _query_agent_findings

        result = _query_agent_findings(mock_db, 2024)
        assert result == []

    @pytest.mark.asyncio
    async def test_summary_report_includes_agent_findings(self):
        """サマリーレポートにagent_findingsが含まれること."""
        mock_db = MagicMock()

        def side_effect(query, params=None):
            if "audit_findings" in query:
                return MOCK_AGENT_FINDINGS_FULL_TUPLES[:1]
            if "rule_violations" in query:
                return [("R001", "高額取引", "high", 100)]
            return [
                (10000, 500, 5_000_000_000, "2024-04-01", "2025-03-31", 156, 50, 25.3)
            ]

        mock_db.execute = MagicMock(side_effect=side_effect)

        with patch("app.api.endpoints.reports.get_db", return_value=mock_db):
            from app.api.endpoints.reports import (
                ReportRequest,
                ReportType,
                generate_report,
            )

            request = ReportRequest(
                report_type=ReportType.SUMMARY,
                fiscal_year=2024,
            )
            result = await generate_report(request)

            assert "agent_findings" in result
            assert isinstance(result["agent_findings"], list)

    @pytest.mark.asyncio
    async def test_agent_findings_endpoint(self):
        """GET /findings/agents エンドポイントが正常動作すること."""
        mock_db = MagicMock()
        mock_db.execute.return_value = MOCK_AGENT_FINDINGS_FULL_TUPLES

        with patch("app.api.endpoints.reports.get_db", return_value=mock_db):
            from app.api.endpoints.reports import get_agent_findings

            result = await get_agent_findings(
                fiscal_year=2024,
                workflow_id=None,
                severity=None,
                limit=50,
            )

            assert "findings" in result
            assert "total_count" in result
            assert "severity_summary" in result
            assert result["total_count"] == 3
            assert "HIGH" in result["severity_summary"]
