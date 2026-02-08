"""Agent unit tests with mock LLM.

Tests agent infrastructure without real API calls.
"""

import pytest
from unittest.mock import patch, MagicMock, AsyncMock
from dataclasses import dataclass

from app.agents.base import (
    AgentConfig,
    AgentType,
    AgentResult,
    AgentState,
    create_llm,
)
from app.agents.orchestrator import AgentOrchestrator


# --------------------------------------------------
# create_llm() factory tests
# --------------------------------------------------


class TestCreateLLM:
    """Test LLM factory for all providers."""

    def test_create_llm_anthropic(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="anthropic",
            model_name="claude-sonnet-4-5",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.anthropic_api_key = "test-key"
            with patch("langchain_anthropic.ChatAnthropic") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()
                assert llm is not None

    def test_create_llm_openai(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="openai",
            model_name="gpt-5",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.openai_api_key = "test-key"
            with patch("langchain_openai.ChatOpenAI") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()
                assert llm is not None

    def test_create_llm_azure(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="azure",
            model_name="gpt-4o",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.azure_openai_deployment = "test-deploy"
            mock_settings.azure_openai_endpoint = "https://test.openai.azure.com"
            mock_settings.azure_openai_api_key = "test-key"
            mock_settings.azure_openai_api_version = "2024-10-21"
            with patch("langchain_openai.AzureChatOpenAI") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()
                assert llm is not None

    def test_create_llm_azure_foundry(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="azure_foundry",
            model_name="gpt-5.2",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.azure_foundry_deployment = None
            mock_settings.azure_foundry_endpoint = "https://test.ai.azure.com"
            mock_settings.azure_foundry_api_key = "test-key"
            mock_settings.azure_foundry_api_version = "2026-01-01"
            with patch("langchain_openai.AzureChatOpenAI") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()
                # model_name should be used as deployment when no explicit deployment
                call_kwargs = mock_cls.call_args[1]
                assert call_kwargs["azure_deployment"] == "gpt-5.2"

    def test_create_llm_bedrock(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="bedrock",
            model_name="us.anthropic.claude-opus-4-6-20260201-v1:0",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.aws_region = "us-east-1"
            with patch("langchain_aws.ChatBedrockConverse") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()
                call_kwargs = mock_cls.call_args[1]
                assert call_kwargs["region_name"] == "us-east-1"

    def test_create_llm_vertex_ai(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="vertex_ai",
            model_name="gemini-3-pro",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.gcp_project_id = "test-project"
            mock_settings.gcp_location = "us-central1"
            with patch("langchain_google_vertexai.ChatVertexAI") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()

    def test_create_llm_google(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="google",
            model_name="gemini-3-flash-preview",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.google_api_key = "test-key"
            with patch("langchain_google_genai.ChatGoogleGenerativeAI") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()

    def test_create_llm_ollama(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="ollama",
            model_name="phi4",
        )
        with patch("app.agents.base.settings") as mock_settings:
            mock_settings.ollama_base_url = "http://localhost:11434"
            with patch("langchain_ollama.ChatOllama") as mock_cls:
                mock_cls.return_value = MagicMock()
                llm = create_llm(config)
                mock_cls.assert_called_once()
                call_kwargs = mock_cls.call_args[1]
                assert call_kwargs["model"] == "phi4"

    def test_create_llm_unknown_raises(self):
        config = AgentConfig(
            agent_type=AgentType.ANALYSIS,
            model_provider="unknown_provider",
            model_name="test",
        )
        with pytest.raises(ValueError, match="Unknown LLM provider"):
            create_llm(config)


# --------------------------------------------------
# AgentConfig / AgentResult tests
# --------------------------------------------------


class TestAgentConfig:
    """Test AgentConfig defaults and behavior."""

    def test_default_values(self):
        config = AgentConfig(agent_type=AgentType.ANALYSIS)
        assert config.model_provider == "anthropic"
        assert config.model_name == "claude-sonnet-4-5"
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.max_steps == 10

    def test_custom_values(self):
        config = AgentConfig(
            agent_type=AgentType.INVESTIGATION,
            model_provider="bedrock",
            model_name="us.anthropic.claude-opus-4-6-20260201-v1:0",
            temperature=0.3,
            max_tokens=8192,
        )
        assert config.model_provider == "bedrock"
        assert config.temperature == 0.3


class TestAgentResult:
    """Test AgentResult dataclass."""

    def test_to_dict(self):
        result = AgentResult(
            agent_type=AgentType.ANALYSIS,
            task="テスト分析",
            success=True,
            findings=[{"title": "test finding"}],
            recommendations=["推奨事項1"],
            step_count=3,
            execution_time_ms=1234.5678,
        )
        d = result.to_dict()
        assert d["agent_type"] == "analysis"
        assert d["success"] is True
        assert d["step_count"] == 3
        assert d["execution_time_ms"] == 1234.57
        assert len(d["findings"]) == 1

    def test_error_result(self):
        result = AgentResult(
            agent_type=AgentType.QA,
            task="質問",
            success=False,
            error="Connection failed",
        )
        d = result.to_dict()
        assert d["success"] is False
        assert "Connection failed" in d["error"]


# --------------------------------------------------
# Orchestrator logic tests (no LLM calls)
# --------------------------------------------------


class TestOrchestratorLogic:
    """Test orchestrator helper methods without LLM."""

    @pytest.fixture
    def orchestrator(self):
        with patch("app.agents.base.create_llm") as mock_create:
            mock_create.return_value = MagicMock()
            orch = AgentOrchestrator.__new__(AgentOrchestrator)
            orch.config = AgentConfig(agent_type=AgentType.ORCHESTRATOR)
            return orch

    def test_keyword_classify_analysis(self, orchestrator):
        assert orchestrator._keyword_classify("リスク分析してください") == "analysis"
        assert orchestrator._keyword_classify("異常パターンの統計") == "analysis"

    def test_keyword_classify_investigation(self, orchestrator):
        assert orchestrator._keyword_classify("この仕訳を調査して") == "investigation"
        assert orchestrator._keyword_classify("原因を追跡") == "investigation"

    def test_keyword_classify_documentation(self, orchestrator):
        assert orchestrator._keyword_classify("レポートを作成して") == "documentation"
        assert orchestrator._keyword_classify("マネジメントレター") == "documentation"

    def test_keyword_classify_review(self, orchestrator):
        assert orchestrator._keyword_classify("発見事項をレビュー") == "review"
        assert orchestrator._keyword_classify("是正措置の評価") == "review"

    def test_keyword_classify_default_qa(self, orchestrator):
        assert orchestrator._keyword_classify("こんにちは") == "qa"
        assert orchestrator._keyword_classify("explain this") == "qa"

    def test_extract_findings_from_result(self, orchestrator):
        result = {
            "summary": {
                "findings": ["高リスク仕訳が100件検出", "自己承認パターンあり"],
                "insights": ["週末処理が増加傾向"],
            }
        }
        findings = orchestrator._extract_findings_from_result(result, "analysis")
        assert len(findings) >= 2
        assert findings[0]["source"] == "analysis"
        assert findings[0]["severity"] == "MEDIUM"
        assert findings[2]["severity"] == "LOW"

    def test_extract_findings_from_messages(self, orchestrator):
        messages = [
            {"content": "分析を開始します"},
            {"content": "高リスクの異常パターンが検出されました。不正の可能性が懸念されます。"},
            {"content": "短い行"},
        ]
        findings = orchestrator._extract_findings_from_messages(messages, "test")
        assert len(findings) >= 1
        high_findings = [f for f in findings if f["severity"] == "HIGH"]
        assert len(high_findings) >= 1  # "不正" triggers HIGH

    def test_extract_findings_empty(self, orchestrator):
        assert orchestrator._extract_findings_from_messages([], "test") == []
        assert orchestrator._extract_findings_from_messages(None, "test") == []

    def test_build_investigation_prompt(self, orchestrator):
        findings = [
            {"severity": "HIGH", "title": "自己承認仕訳が多い"},
            {"severity": "MEDIUM", "title": "高額仕訳集中"},
        ]
        prompt = orchestrator._build_investigation_prompt(2025, findings)
        assert "2025" in prompt
        assert "自己承認" in prompt
        assert "高額仕訳" in prompt
        assert "[HIGH]" in prompt

    def test_build_review_prompt(self, orchestrator):
        findings = [
            {"severity": "HIGH", "title": "重大な発見"},
            {"severity": "MEDIUM", "title": "中程度の発見"},
            {"severity": "LOW", "title": "軽微な発見"},
        ]
        prompt = orchestrator._build_review_prompt(2025, findings)
        assert "全3件" in prompt
        assert "高リスク" in prompt
        assert "中リスク" in prompt
        assert "低リスク" in prompt

    def test_build_documentation_context(self, orchestrator):
        all_findings = [
            {"severity": "HIGH", "title": "発見A"},
            {"severity": "MEDIUM", "title": "発見B"},
        ]
        ctx = orchestrator._build_documentation_context(
            2025, {}, [all_findings[0]], all_findings, {}
        )
        assert "2025" in ctx
        assert "2件" in ctx
        assert "高: 1" in ctx

    def test_get_available_workflows(self, orchestrator):
        workflows = orchestrator.get_available_workflows()
        assert len(workflows) == 4
        ids = [w["id"] for w in workflows]
        assert "full_audit" in ids
        assert "investigation" in ids
        assert "qa" in ids
        assert "documentation" in ids
