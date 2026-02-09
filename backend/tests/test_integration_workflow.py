"""Workflow integration tests.

Tests for the AgentOrchestrator's workflow coordination logic.
Mocks LLM calls but tests the full orchestration flow.
"""

from datetime import datetime
from unittest.mock import patch

from app.agents.base import AgentConfig, AgentType
from app.agents.orchestrator import AgentOrchestrator, WorkflowResult


class TestWorkflowResult:
    """WorkflowResult データクラスのテスト."""

    def test_default_values(self):
        """デフォルト値の確認."""
        result = WorkflowResult(
            workflow_id="WF-001",
            workflow_type="full_audit",
        )
        assert result.workflow_id == "WF-001"
        assert result.workflow_type == "full_audit"
        assert isinstance(result.started_at, datetime)
        assert result.completed_at is None
        assert result.agent_results == {}
        assert result.final_output is None
        assert result.success is False
        assert result.error is None

    def test_to_dict(self):
        """dict変換."""
        result = WorkflowResult(
            workflow_id="WF-002",
            workflow_type="investigation",
            success=True,
            final_output="完了",
        )
        result.completed_at = datetime(2024, 12, 31, 23, 59, 59)
        d = result.to_dict()
        assert d["workflow_id"] == "WF-002"
        assert d["workflow_type"] == "investigation"
        assert d["success"] is True
        assert d["final_output"] == "完了"
        assert d["completed_at"] is not None

    def test_to_dict_without_completed(self):
        """completed_at未設定時のdict変換."""
        result = WorkflowResult(
            workflow_id="WF-003",
            workflow_type="qa",
        )
        d = result.to_dict()
        assert d["completed_at"] is None


class TestOrchestratorInit:
    """AgentOrchestrator 初期化テスト."""

    @patch("app.agents.orchestrator.AnalysisAgent")
    @patch("app.agents.orchestrator.InvestigationAgent")
    @patch("app.agents.orchestrator.DocumentationAgent")
    @patch("app.agents.orchestrator.QAAgent")
    @patch("app.agents.orchestrator.ReviewAgent")
    def test_default_init(
        self, mock_review, mock_qa, mock_doc, mock_inv, mock_analysis
    ):
        """デフォルト初期化."""
        orch = AgentOrchestrator()
        assert orch.config.agent_type == AgentType.ORCHESTRATOR

    @patch("app.agents.orchestrator.AnalysisAgent")
    @patch("app.agents.orchestrator.InvestigationAgent")
    @patch("app.agents.orchestrator.DocumentationAgent")
    @patch("app.agents.orchestrator.QAAgent")
    @patch("app.agents.orchestrator.ReviewAgent")
    def test_custom_config(
        self, mock_review, mock_qa, mock_doc, mock_inv, mock_analysis
    ):
        """カスタム設定での初期化."""
        config = AgentConfig(
            agent_type=AgentType.ORCHESTRATOR,
            model_provider="anthropic",
            model_name="claude-sonnet-4-5",
        )
        orch = AgentOrchestrator(config=config)
        assert orch.config.model_provider == "anthropic"
        assert orch.config.model_name == "claude-sonnet-4-5"


class TestKeywordClassify:
    """キーワードベースの分類テスト."""

    @patch("app.agents.orchestrator.AnalysisAgent")
    @patch("app.agents.orchestrator.InvestigationAgent")
    @patch("app.agents.orchestrator.DocumentationAgent")
    @patch("app.agents.orchestrator.QAAgent")
    @patch("app.agents.orchestrator.ReviewAgent")
    def setup_method(
        self,
        method,
        mock_review=None,
        mock_qa=None,
        mock_doc=None,
        mock_inv=None,
        mock_analysis=None,
    ):
        """テストごとにOrchestratorを初期化."""
        with (
            patch("app.agents.orchestrator.AnalysisAgent"),
            patch("app.agents.orchestrator.InvestigationAgent"),
            patch("app.agents.orchestrator.DocumentationAgent"),
            patch("app.agents.orchestrator.QAAgent"),
            patch("app.agents.orchestrator.ReviewAgent"),
        ):
            self.orch = AgentOrchestrator()

    def test_analysis_keywords(self):
        """分析関連キーワードの分類."""
        assert self.orch._keyword_classify("リスク分析をしてください") == "analysis"
        assert self.orch._keyword_classify("異常パターンの検出") == "analysis"
        assert self.orch._keyword_classify("統計分布を確認") == "analysis"

    def test_investigation_keywords(self):
        """調査関連キーワードの分類."""
        assert (
            self.orch._keyword_classify("この仕訳を詳しく調査して") == "investigation"
        )
        assert self.orch._keyword_classify("原因を深掘りしたい") == "investigation"

    def test_documentation_keywords(self):
        """文書化関連キーワードの分類."""
        assert (
            self.orch._keyword_classify("レポートを作成してください") == "documentation"
        )
        assert (
            self.orch._keyword_classify("マネジメントレターの作成") == "documentation"
        )

    def test_review_keywords(self):
        """レビュー関連キーワードの分類."""
        assert self.orch._keyword_classify("発見事項のレビュー") == "review"
        assert self.orch._keyword_classify("是正措置の評価") == "review"

    def test_qa_fallback(self):
        """Q&Aフォールバック."""
        assert self.orch._keyword_classify("こんにちは") == "qa"
        assert self.orch._keyword_classify("使い方を教えて") == "qa"


class TestExtractFindings:
    """発見事項抽出のテスト."""

    @patch("app.agents.orchestrator.AnalysisAgent")
    @patch("app.agents.orchestrator.InvestigationAgent")
    @patch("app.agents.orchestrator.DocumentationAgent")
    @patch("app.agents.orchestrator.QAAgent")
    @patch("app.agents.orchestrator.ReviewAgent")
    def setup_method(self, method, *mocks):
        with (
            patch("app.agents.orchestrator.AnalysisAgent"),
            patch("app.agents.orchestrator.InvestigationAgent"),
            patch("app.agents.orchestrator.DocumentationAgent"),
            patch("app.agents.orchestrator.QAAgent"),
            patch("app.agents.orchestrator.ReviewAgent"),
        ):
            self.orch = AgentOrchestrator()

    def test_extract_from_result_with_summary(self):
        """summary付き結果からの発見事項抽出."""
        result = {
            "summary": {
                "findings": ["高額ラウンド取引が検出されました", "期末集中仕訳"],
                "insights": ["全体的にリスクは低い"],
            }
        }
        findings = self.orch._extract_findings_from_result(result, "analysis")
        assert len(findings) >= 3
        assert findings[0]["source"] == "analysis"
        assert findings[0]["severity"] == "MEDIUM"
        assert findings[2]["severity"] == "LOW"

    def test_extract_from_empty_result(self):
        """空の結果."""
        findings = self.orch._extract_findings_from_result({}, "analysis")
        assert findings == []

    def test_extract_from_messages(self):
        """メッセージからの発見事項抽出."""
        messages = [
            {"content": "通常の処理結果です"},
            {"content": "高リスク仕訳が3件検出されました。不正の可能性があります。"},
            {"content": "異常パターンとして自己承認が複数見つかりました。要注意です。"},
        ]
        findings = self.orch._extract_findings_from_messages(messages, "investigation")
        assert len(findings) >= 2
        # 不正 keyword -> HIGH severity
        high_findings = [f for f in findings if f["severity"] == "HIGH"]
        assert len(high_findings) >= 1

    def test_extract_from_empty_messages(self):
        """空メッセージ."""
        findings = self.orch._extract_findings_from_messages([], "test")
        assert findings == []

    def test_extract_from_none_messages(self):
        """Noneメッセージ."""
        findings = self.orch._extract_findings_from_messages(None, "test")
        assert findings == []


class TestBuildPrompts:
    """プロンプト構築のテスト."""

    @patch("app.agents.orchestrator.AnalysisAgent")
    @patch("app.agents.orchestrator.InvestigationAgent")
    @patch("app.agents.orchestrator.DocumentationAgent")
    @patch("app.agents.orchestrator.QAAgent")
    @patch("app.agents.orchestrator.ReviewAgent")
    def setup_method(self, method, *mocks):
        with (
            patch("app.agents.orchestrator.AnalysisAgent"),
            patch("app.agents.orchestrator.InvestigationAgent"),
            patch("app.agents.orchestrator.DocumentationAgent"),
            patch("app.agents.orchestrator.QAAgent"),
            patch("app.agents.orchestrator.ReviewAgent"),
        ):
            self.orch = AgentOrchestrator()

    def test_investigation_prompt_with_findings(self):
        """発見事項付きの調査プロンプト."""
        findings = [
            {"source": "analysis", "title": "高額取引検出", "severity": "HIGH"},
            {"source": "analysis", "title": "自己承認パターン", "severity": "MEDIUM"},
        ]
        prompt = self.orch._build_investigation_prompt(2024, findings)
        assert "2024" in prompt
        assert "高額取引検出" in prompt
        assert "自己承認パターン" in prompt
        assert "引き継ぎ事項" in prompt

    def test_investigation_prompt_without_findings(self):
        """発見事項なしの調査プロンプト."""
        prompt = self.orch._build_investigation_prompt(2024, [])
        assert "2024" in prompt
        assert "調査対象" in prompt

    def test_review_prompt(self):
        """レビュープロンプトの構築."""
        findings = [
            {"source": "analysis", "title": "高額ラウンド取引", "severity": "HIGH"},
            {"source": "investigation", "title": "期末集中仕訳", "severity": "MEDIUM"},
            {"source": "analysis", "title": "全体低リスク", "severity": "LOW"},
        ]
        prompt = self.orch._build_review_prompt(2024, findings)
        assert "2024" in prompt
        assert "全3件" in prompt
        assert "高リスク" in prompt
        assert "中リスク" in prompt

    def test_documentation_context(self):
        """文書化コンテキストの構築."""
        context = self.orch._build_documentation_context(
            fiscal_year=2024,
            analysis_result={"summary": {"findings": []}},
            investigation_findings=[
                {"source": "investigation", "title": "テスト", "severity": "HIGH"},
            ],
            all_findings=[
                {"source": "analysis", "title": "F1", "severity": "HIGH"},
                {"source": "investigation", "title": "F2", "severity": "MEDIUM"},
                {"source": "analysis", "title": "F3", "severity": "LOW"},
            ],
            review_result={"status": "completed"},
        )
        assert "2024" in context
        assert "3件" in context
        assert "高: 1" in context
        assert "中: 1" in context
        assert "低: 1" in context


class TestAvailableWorkflows:
    """利用可能ワークフロー一覧のテスト."""

    @patch("app.agents.orchestrator.AnalysisAgent")
    @patch("app.agents.orchestrator.InvestigationAgent")
    @patch("app.agents.orchestrator.DocumentationAgent")
    @patch("app.agents.orchestrator.QAAgent")
    @patch("app.agents.orchestrator.ReviewAgent")
    def test_get_workflows(self, *mocks):
        with (
            patch("app.agents.orchestrator.AnalysisAgent"),
            patch("app.agents.orchestrator.InvestigationAgent"),
            patch("app.agents.orchestrator.DocumentationAgent"),
            patch("app.agents.orchestrator.QAAgent"),
            patch("app.agents.orchestrator.ReviewAgent"),
        ):
            orch = AgentOrchestrator()

        workflows = orch.get_available_workflows()
        assert len(workflows) >= 4
        ids = [w["id"] for w in workflows]
        assert "full_audit" in ids
        assert "investigation" in ids
        assert "qa" in ids
        assert "documentation" in ids

        for w in workflows:
            assert "id" in w
            assert "name" in w
            assert "description" in w
