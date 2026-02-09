"""Agent implementation unit tests.

create_llm(), BaseAgent基盤, オーケストレーターのルーティング/抽出ロジックをテスト。
LLMは全てモックで差し替え。
"""

from unittest.mock import MagicMock, patch

import pytest

from app.agents.base import (
    AgentConfig,
    AgentResult,
    AgentState,
    AgentType,
    create_llm,
)

# =========================================================
# create_llm テスト (全8プロバイダー)
# =========================================================


class TestCreateLLM:
    """create_llm() のプロバイダー別インスタンス生成テスト"""

    @patch("app.agents.base.settings")
    def test_create_llm_anthropic(self, mock_s):
        mock_s.anthropic_api_key = "test-key"
        with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.ANALYSIS,
                model_provider="anthropic",
                model_name="claude-sonnet-4-5",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_openai(self, mock_s):
        mock_s.openai_api_key = "test-key"
        with patch("langchain_openai.ChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.QA,
                model_provider="openai",
                model_name="gpt-5",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_azure(self, mock_s):
        mock_s.azure_openai_deployment = "dep"
        mock_s.azure_openai_endpoint = "https://test.openai.azure.com/"
        mock_s.azure_openai_api_key = "key"
        mock_s.azure_openai_api_version = "2024-12-01"
        with patch("langchain_openai.AzureChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.REVIEW,
                model_provider="azure",
                model_name="gpt-4o",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_azure_foundry(self, mock_s):
        mock_s.azure_foundry_deployment = "gpt52"
        mock_s.azure_foundry_endpoint = "https://test.ai.azure.com/"
        mock_s.azure_foundry_api_key = "key"
        mock_s.azure_foundry_api_version = "2024-12-01"
        with patch("langchain_openai.AzureChatOpenAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.INVESTIGATION,
                model_provider="azure_foundry",
                model_name="gpt-5.2",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_bedrock(self, mock_s):
        mock_s.aws_region = "us-east-1"
        with patch("langchain_aws.ChatBedrockConverse") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.ANALYSIS,
                model_provider="bedrock",
                model_name="us.anthropic.claude-opus-4-6-20260201-v1:0",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_vertex_ai(self, mock_s):
        mock_s.gcp_project_id = "my-project"
        mock_s.gcp_location = "global"
        with patch("langchain_google_vertexai.ChatVertexAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.DOCUMENTATION,
                model_provider="vertex_ai",
                model_name="gemini-3-pro",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_google(self, mock_s):
        mock_s.google_api_key = "test-key"
        with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.QA,
                model_provider="google",
                model_name="gemini-2.5-pro",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    @patch("app.agents.base.settings")
    def test_create_llm_ollama(self, mock_s):
        mock_s.ollama_base_url = "http://localhost:11434"
        with patch("langchain_ollama.ChatOllama") as mock_cls:
            mock_cls.return_value = MagicMock()
            config = AgentConfig(
                agent_type=AgentType.QA,
                model_provider="ollama",
                model_name="phi4",
            )
            llm = create_llm(config)
            mock_cls.assert_called_once()
            assert llm is not None

    def test_create_llm_unknown_raises(self):
        config = AgentConfig(
            agent_type=AgentType.QA,
            model_provider="nonexistent",
            model_name="test",
        )
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm(config)


# =========================================================
# AgentConfig テスト
# =========================================================


class TestAgentConfig:
    """AgentConfig データクラスのテスト"""

    def test_defaults(self):
        config = AgentConfig(agent_type=AgentType.ANALYSIS)
        assert config.model_provider == "anthropic"
        assert config.model_name == "claude-sonnet-4-5"
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.max_steps == 10
        assert config.enable_tools is True

    def test_custom_values(self):
        config = AgentConfig(
            agent_type=AgentType.INVESTIGATION,
            model_provider="ollama",
            model_name="phi4",
            temperature=0.3,
            max_steps=5,
        )
        assert config.model_provider == "ollama"
        assert config.max_steps == 5


# =========================================================
# AgentResult テスト
# =========================================================


class TestAgentResult:
    """AgentResult のテスト"""

    def test_to_dict(self):
        result = AgentResult(
            agent_type=AgentType.ANALYSIS,
            task="テストタスク",
            success=True,
            findings=[{"title": "テスト発見"}],
            recommendations=["推奨事項1"],
            step_count=3,
            execution_time_ms=1500.123,
        )
        d = result.to_dict()
        assert d["agent_type"] == "analysis"
        assert d["success"] is True
        assert d["execution_time_ms"] == 1500.12
        assert len(d["findings"]) == 1

    def test_error_result(self):
        result = AgentResult(
            agent_type=AgentType.QA,
            task="エラータスク",
            success=False,
            error="テストエラー",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert d["error"] == "テストエラー"

    def test_default_fields(self):
        result = AgentResult(
            agent_type=AgentType.REVIEW,
            task="task",
            success=True,
        )
        assert result.findings == []
        assert result.recommendations == []
        assert result.insights == []
        assert result.messages == []
        assert result.execution_time_ms == 0.0
        assert result.error is None


# =========================================================
# BaseAgent インフラテスト (_should_continue, _create_initial_state)
# =========================================================


class TestBaseAgentInfra:
    """BaseAgent の補助メソッドテスト"""

    def _make_mock_agent(self):
        """テスト用にBaseAgentをモック的に構築"""
        from app.agents.base import BaseAgent

        class _TestAgent(BaseAgent):
            @property
            def agent_type(self):
                return AgentType.QA

            @property
            def system_prompt(self):
                return "テスト用システムプロンプト"

            def _build_graph(self):
                return MagicMock()

        with patch("app.agents.base.create_llm", return_value=MagicMock()):
            agent = _TestAgent()
        return agent

    def test_create_initial_state(self):
        agent = self._make_mock_agent()
        state = agent._create_initial_state("タスク", {"key": "value"})
        assert state["task"] == "タスク"
        assert state["context"] == {"key": "value"}
        assert state["step_count"] == 0
        assert state["current_agent"] == "qa"
        assert len(state["messages"]) == 2  # System + Human

    def test_should_continue_end_on_max_steps(self):
        agent = self._make_mock_agent()
        state = AgentState(
            task="t",
            context={},
            messages=[MagicMock(content="test")],
            current_agent="qa",
            step_count=10,
            max_steps=10,
            findings=[],
            recommendations=[],
            insights=[],
            started_at="",
        )
        assert agent._should_continue(state) == "end"

    def test_should_continue_end_on_error(self):
        agent = self._make_mock_agent()
        state = AgentState(
            task="t",
            context={},
            messages=[MagicMock(content="test")],
            current_agent="qa",
            step_count=1,
            max_steps=10,
            findings=[],
            recommendations=[],
            insights=[],
            started_at="",
            error="エラー発生",
        )
        assert agent._should_continue(state) == "end"

    def test_should_continue_tools_on_tool_calls(self):
        agent = self._make_mock_agent()
        last_msg = MagicMock()
        last_msg.tool_calls = [{"name": "tool1"}]
        state = AgentState(
            task="t",
            context={},
            messages=[MagicMock(), last_msg],
            current_agent="qa",
            step_count=1,
            max_steps=10,
            findings=[],
            recommendations=[],
            insights=[],
            started_at="",
        )
        assert agent._should_continue(state) == "tools"

    def test_should_continue_end_no_tool_calls(self):
        agent = self._make_mock_agent()
        last_msg = MagicMock(spec=[])  # tool_calls属性なし
        state = AgentState(
            task="t",
            context={},
            messages=[MagicMock(), last_msg],
            current_agent="qa",
            step_count=1,
            max_steps=10,
            findings=[],
            recommendations=[],
            insights=[],
            started_at="",
        )
        assert agent._should_continue(state) == "end"

    def test_full_system_prompt_with_prefix(self):
        agent = self._make_mock_agent()
        agent.config.system_prompt_prefix = "PREFIX"
        assert agent.full_system_prompt.startswith("PREFIX")
        assert "テスト用システムプロンプト" in agent.full_system_prompt

    def test_full_system_prompt_without_prefix(self):
        agent = self._make_mock_agent()
        assert agent.full_system_prompt == "テスト用システムプロンプト"

    def test_register_tool(self):
        agent = self._make_mock_agent()
        mock_tool = MagicMock()
        agent.register_tool(mock_tool)
        assert mock_tool in agent.tools

    def test_register_tools(self):
        agent = self._make_mock_agent()
        tools = [MagicMock(), MagicMock()]
        agent.register_tools(tools)
        assert len(agent.tools) == 2


# =========================================================
# Orchestrator ルーティング/抽出ロジック テスト
# =========================================================


class TestOrchestratorKeywordClassify:
    """AgentOrchestrator._keyword_classify() のテスト"""

    def test_analysis_keywords(self):
        from app.agents.orchestrator import AgentOrchestrator

        assert AgentOrchestrator._keyword_classify("リスク分析を実施してください") == "analysis"
        assert AgentOrchestrator._keyword_classify("異常パターンを調べて") == "analysis"
        assert AgentOrchestrator._keyword_classify("統計的な分布を見たい") == "analysis"

    def test_investigation_keywords(self):
        from app.agents.orchestrator import AgentOrchestrator

        assert AgentOrchestrator._keyword_classify("この仕訳を調査して") == "investigation"
        assert AgentOrchestrator._keyword_classify("原因を深掘りしてください") == "investigation"

    def test_documentation_keywords(self):
        from app.agents.orchestrator import AgentOrchestrator

        assert AgentOrchestrator._keyword_classify("レポートを作成して") == "documentation"
        assert AgentOrchestrator._keyword_classify("報告書を生成してください") == "documentation"
        assert AgentOrchestrator._keyword_classify("マネジメントレターを書いて") == "documentation"

    def test_review_keywords(self):
        from app.agents.orchestrator import AgentOrchestrator

        assert AgentOrchestrator._keyword_classify("発見事項をレビューして") == "review"
        assert AgentOrchestrator._keyword_classify("是正措置を提案してください") == "review"

    def test_default_to_qa(self):
        from app.agents.orchestrator import AgentOrchestrator

        assert AgentOrchestrator._keyword_classify("こんにちは") == "qa"
        assert AgentOrchestrator._keyword_classify("教えてください") == "qa"


class TestOrchestratorExtractFindings:
    """発見事項抽出ロジックのテスト"""

    def _make_orchestrator(self):
        with patch("app.agents.orchestrator.AnalysisAgent"), \
             patch("app.agents.orchestrator.InvestigationAgent"), \
             patch("app.agents.orchestrator.DocumentationAgent"), \
             patch("app.agents.orchestrator.QAAgent"), \
             patch("app.agents.orchestrator.ReviewAgent"):
            from app.agents.orchestrator import AgentOrchestrator
            return AgentOrchestrator()

    def test_extract_from_summary_dict(self):
        orch = self._make_orchestrator()
        result = {
            "summary": {
                "findings": ["高額仕訳の異常パターン", "未承認仕訳"],
                "insights": ["売上傾向の変化"],
            }
        }
        findings = orch._extract_findings_from_result(result, "analysis")
        assert len(findings) >= 3
        assert findings[0]["source"] == "analysis"

    def test_extract_from_empty_dict(self):
        orch = self._make_orchestrator()
        findings = orch._extract_findings_from_result({}, "test")
        assert findings == []

    def test_extract_from_messages(self):
        orch = self._make_orchestrator()
        messages = [
            {"role": "assistant", "content": "高リスク仕訳を10件発見しました。異常パターンが存在します。"},
            {"role": "assistant", "content": "特に問題なし"},
        ]
        findings = orch._extract_findings_from_messages(messages, "investigation")
        assert len(findings) > 0
        assert any(f["source"] == "investigation" for f in findings)

    def test_extract_from_empty_messages(self):
        orch = self._make_orchestrator()
        findings = orch._extract_findings_from_messages([], "test")
        assert findings == []

    def test_high_severity_keywords(self):
        orch = self._make_orchestrator()
        messages = [{"content": "不正の疑いがある重要な仕訳が発見されました"}]
        findings = orch._extract_findings_from_messages(messages, "investigation")
        high_findings = [f for f in findings if f["severity"] == "HIGH"]
        assert len(high_findings) > 0


class TestOrchestratorPromptBuilding:
    """プロンプト構築メソッドのテスト"""

    def _make_orchestrator(self):
        with patch("app.agents.orchestrator.AnalysisAgent"), \
             patch("app.agents.orchestrator.InvestigationAgent"), \
             patch("app.agents.orchestrator.DocumentationAgent"), \
             patch("app.agents.orchestrator.QAAgent"), \
             patch("app.agents.orchestrator.ReviewAgent"):
            from app.agents.orchestrator import AgentOrchestrator
            return AgentOrchestrator()

    def test_build_investigation_prompt_with_findings(self):
        orch = self._make_orchestrator()
        findings = [
            {"severity": "HIGH", "title": "高額仕訳の異常"},
            {"severity": "MEDIUM", "title": "日付の不整合"},
        ]
        prompt = orch._build_investigation_prompt(2024, findings)
        assert "2024" in prompt
        assert "高額仕訳の異常" in prompt
        assert "日付の不整合" in prompt
        assert "分析エージェントからの引き継ぎ事項" in prompt

    def test_build_investigation_prompt_no_findings(self):
        orch = self._make_orchestrator()
        prompt = orch._build_investigation_prompt(2024, [])
        assert "2024" in prompt
        assert "詳細調査を実施" in prompt

    def test_build_review_prompt(self):
        orch = self._make_orchestrator()
        findings = [
            {"severity": "HIGH", "title": "不正リスク"},
            {"severity": "MEDIUM", "title": "金額異常"},
            {"severity": "LOW", "title": "軽微な逸脱"},
        ]
        prompt = orch._build_review_prompt(2024, findings)
        assert "全3件" in prompt
        assert "高リスク" in prompt
        assert "不正リスク" in prompt

    def test_build_documentation_context(self):
        orch = self._make_orchestrator()
        all_findings = [
            {"severity": "HIGH", "title": "f1"},
            {"severity": "MEDIUM", "title": "f2"},
            {"severity": "LOW", "title": "f3"},
        ]
        context = orch._build_documentation_context(
            2024, {}, [], all_findings, {}
        )
        assert "2024" in context
        assert "高: 1" in context
        assert "中: 1" in context
        assert "低: 1" in context


class TestWorkflowResult:
    """WorkflowResult のテスト"""

    def test_to_dict(self):
        from app.agents.orchestrator import WorkflowResult

        result = WorkflowResult(
            workflow_id="test-id",
            workflow_type="full_audit",
            success=True,
            final_output="完了",
        )
        d = result.to_dict()
        assert d["workflow_id"] == "test-id"
        assert d["success"] is True
        assert d["final_output"] == "完了"

    def test_to_dict_with_completed_at(self):
        from datetime import datetime

        from app.agents.orchestrator import WorkflowResult

        result = WorkflowResult(
            workflow_id="id",
            workflow_type="qa",
            completed_at=datetime(2024, 4, 1, 12, 0),
        )
        d = result.to_dict()
        assert d["completed_at"] is not None

    def test_to_dict_without_completed_at(self):
        from app.agents.orchestrator import WorkflowResult

        result = WorkflowResult(
            workflow_id="id",
            workflow_type="qa",
        )
        d = result.to_dict()
        assert d["completed_at"] is None


class TestOrchestratorAvailableWorkflows:
    """get_available_workflows() のテスト"""

    def test_returns_workflows(self):
        with patch("app.agents.orchestrator.AnalysisAgent"), \
             patch("app.agents.orchestrator.InvestigationAgent"), \
             patch("app.agents.orchestrator.DocumentationAgent"), \
             patch("app.agents.orchestrator.QAAgent"), \
             patch("app.agents.orchestrator.ReviewAgent"):
            from app.agents.orchestrator import AgentOrchestrator
            orch = AgentOrchestrator()
            workflows = orch.get_available_workflows()
            assert len(workflows) == 4
            ids = [w["id"] for w in workflows]
            assert "full_audit" in ids
            assert "investigation" in ids
            assert "qa" in ids
            assert "documentation" in ids
