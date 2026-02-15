"""LLM service unit tests with mock providers."""

from datetime import datetime
from unittest.mock import MagicMock, patch

import pytest

from app.core.config import LLM_MODELS, RECOMMENDED_MODELS
from app.services.llm.models import LLMConfig, LLMResponse, ModelInfo
from app.services.llm.service import LLMService

# --------------------------------------------------
# LLMConfig tests
# --------------------------------------------------


class TestLLMConfig:
    """Test LLMConfig dataclass."""

    def test_default_values(self):
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-5")
        assert config.temperature == 0.0
        assert config.max_tokens == 4096
        assert config.top_p == 1.0
        assert config.timeout == 120
        assert config.options == {}

    def test_all_providers_valid(self):
        providers = [
            "anthropic",
            "openai",
            "google",
            "bedrock",
            "azure",
            "azure_foundry",
            "vertex_ai",
            "ollama",
        ]
        for p in providers:
            config = LLMConfig(provider=p, model="test")
            assert config.provider == p


# --------------------------------------------------
# LLMResponse tests
# --------------------------------------------------


class TestLLMResponse:
    """Test LLMResponse dataclass."""

    def test_token_properties(self):
        response = LLMResponse(
            content="テスト応答",
            model="claude-sonnet-4-5",
            provider="anthropic",
            usage={"input_tokens": 100, "output_tokens": 50},
        )
        assert response.input_tokens == 100
        assert response.output_tokens == 50
        assert response.total_tokens == 150

    def test_empty_usage(self):
        response = LLMResponse(
            content="test",
            model="test",
            provider="ollama",
        )
        assert response.input_tokens == 0
        assert response.output_tokens == 0
        assert response.total_tokens == 0

    def test_created_at(self):
        response = LLMResponse(content="", model="", provider="")
        assert isinstance(response.created_at, datetime)


# --------------------------------------------------
# ModelInfo tests
# --------------------------------------------------


class TestModelInfo:
    """Test ModelInfo dataclass."""

    def test_model_info(self):
        info = ModelInfo(
            id="claude-opus-4-6",
            name="Claude Opus 4.6",
            provider="anthropic",
            tier="premium",
            cost="very_high",
            supports_vision=True,
        )
        assert info.supports_tools is True
        assert info.max_tokens == 4096
        assert info.supports_vision is True


# --------------------------------------------------
# LLMService tests
# --------------------------------------------------


class TestLLMService:
    """Test LLMService initialization and dispatch."""

    def test_default_initialization(self):
        with patch("app.services.llm.service.settings") as mock_s:
            mock_s.llm_provider = "ollama"
            mock_s.llm_model = "phi4"
            service = LLMService()
            assert service.config.provider == "ollama"
            assert service.config.model == "phi4"

    def test_custom_config(self):
        config = LLMConfig(provider="anthropic", model="claude-opus-4-6")
        service = LLMService(config=config)
        assert service.config.provider == "anthropic"

    def test_get_client_anthropic(self):
        config = LLMConfig(provider="anthropic", model="claude-opus-4-6")
        service = LLMService(config=config)
        with patch("app.services.llm.service.settings") as mock_s:
            mock_s.anthropic_api_key = "test-key"
            with patch("anthropic.Anthropic") as mock_cls:
                mock_cls.return_value = MagicMock()
                client = service._get_client()
                assert client is not None

    def test_get_client_ollama(self):
        config = LLMConfig(provider="ollama", model="phi4")
        service = LLMService(config=config)
        with patch("app.services.llm.service.settings") as mock_s:
            mock_s.ollama_base_url = "http://localhost:11434"
            with patch("httpx.Client") as mock_cls:
                mock_cls.return_value = MagicMock()
                client = service._get_client()
                assert client is not None

    def test_generate_unknown_provider_raises(self):
        config = LLMConfig.__new__(LLMConfig)
        config.provider = "nonexistent"
        config.model = "test"
        config.temperature = 0.0
        config.max_tokens = 100
        config.top_p = 1.0
        config.timeout = 30
        config.options = {}
        service = LLMService(config=config)
        service._client = MagicMock()
        with pytest.raises(ValueError, match="Unknown provider"):
            service.generate("test prompt")

    def test_generate_ollama(self):
        config = LLMConfig(provider="ollama", model="phi4")
        service = LLMService(config=config)
        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "テスト応答です"},
            "prompt_eval_count": 10,
            "eval_count": 20,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        service._client = mock_client

        result = service.generate("テストプロンプト", system="system prompt")
        assert result.content == "テスト応答です"
        assert result.provider == "ollama"
        assert result.input_tokens == 10
        assert result.output_tokens == 20


# --------------------------------------------------
# Model catalog tests
# --------------------------------------------------


class TestModelCatalog:
    """Test LLM model definitions."""

    def test_all_providers_in_catalog(self):
        expected = [
            "anthropic",
            "openai",
            "google",
            "bedrock",
            "azure_foundry",
            "vertex_ai",
            "azure",
            "ollama",
        ]
        for p in expected:
            assert p in LLM_MODELS, f"Provider {p} missing from LLM_MODELS"

    def test_each_provider_has_models(self):
        for provider, models in LLM_MODELS.items():
            assert len(models) > 0, f"Provider {provider} has no models"

    def test_model_structure(self):
        for provider, models in LLM_MODELS.items():
            for model_id, info in models.items():
                assert "name" in info, f"{provider}/{model_id} missing name"
                assert "tier" in info, f"{provider}/{model_id} missing tier"
                assert "cost" in info, f"{provider}/{model_id} missing cost"

    def test_recommended_models_exist(self):
        assert "highest_accuracy" in RECOMMENDED_MODELS
        assert "high_accuracy" in RECOMMENDED_MODELS
        assert "balanced" in RECOMMENDED_MODELS
        assert "cost_effective" in RECOMMENDED_MODELS
        assert "local_dev" in RECOMMENDED_MODELS

    def test_recommended_models_reference_valid_providers(self):
        for use_case, rec in RECOMMENDED_MODELS.items():
            assert rec["provider"] in LLM_MODELS, (
                f"Recommended {use_case} references unknown provider {rec['provider']}"
            )

    def test_ollama_models(self):
        ollama = LLM_MODELS["ollama"]
        assert "phi4" in ollama
        assert "llama3.3:8b" in ollama
        assert all(m["cost"] == "very_low" for m in ollama.values())

    def test_get_available_models(self):
        result = LLMService.get_available_models()
        assert "anthropic" in result
        assert "ollama" in result
        assert isinstance(result["anthropic"][0], ModelInfo)

    def test_get_recommended_models(self):
        result = LLMService.get_recommended_models()
        assert "local_dev" in result
        assert result["local_dev"]["provider"] == "ollama"


# --------------------------------------------------
# Generate method tests for all providers
# --------------------------------------------------


class TestGenerateAnthropic:
    """Test _generate_anthropic method."""

    def test_generate_anthropic_success(self):
        config = LLMConfig(provider="anthropic", model="claude-sonnet-4-5")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="Anthropicの回答")]
        mock_response.model = "claude-sonnet-4-5"
        mock_response.usage.input_tokens = 50
        mock_response.usage.output_tokens = 100
        mock_client.messages.create.return_value = mock_response
        service._client = mock_client

        result = service.generate("テストプロンプト", system="システムプロンプト")
        assert result.content == "Anthropicの回答"
        assert result.provider == "anthropic"
        assert result.input_tokens == 50
        assert result.output_tokens == 100

    def test_generate_anthropic_no_system(self):
        config = LLMConfig(provider="anthropic", model="claude-opus-4-6")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.content = [MagicMock(text="回答")]
        mock_response.model = "claude-opus-4-6"
        mock_response.usage.input_tokens = 10
        mock_response.usage.output_tokens = 20
        mock_client.messages.create.return_value = mock_response
        service._client = mock_client

        result = service.generate("プロンプト")
        assert result.content == "回答"
        # system="" が渡される
        call_args = mock_client.messages.create.call_args
        assert call_args.kwargs["system"] == ""


class TestGenerateOpenAI:
    """Test _generate_openai method."""

    def test_generate_openai_success(self):
        config = LLMConfig(provider="openai", model="gpt-5")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="OpenAIの回答"))]
        mock_response.model = "gpt-5"
        mock_response.usage.prompt_tokens = 30
        mock_response.usage.completion_tokens = 60
        mock_client.chat.completions.create.return_value = mock_response
        service._client = mock_client

        result = service.generate("テスト", system="システム")
        assert result.content == "OpenAIの回答"
        assert result.provider == "openai"
        assert result.input_tokens == 30
        assert result.output_tokens == 60

    def test_generate_openai_with_system_message(self):
        config = LLMConfig(provider="openai", model="gpt-5-mini")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="回答"))]
        mock_response.model = "gpt-5-mini"
        mock_response.usage.prompt_tokens = 10
        mock_response.usage.completion_tokens = 20
        mock_client.chat.completions.create.return_value = mock_response
        service._client = mock_client

        service.generate("プロンプト", system="システム")
        call_args = mock_client.chat.completions.create.call_args
        messages = call_args.kwargs["messages"]
        assert messages[0]["role"] == "system"
        assert messages[1]["role"] == "user"


class TestGenerateGoogle:
    """Test _generate_google method."""

    def test_generate_google_success(self):
        config = LLMConfig(provider="google", model="gemini-2.5-pro")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Googleの回答"
        mock_response.usage_metadata.prompt_token_count = 20
        mock_response.usage_metadata.candidates_token_count = 40
        mock_client.models.generate_content.return_value = mock_response
        service._client = mock_client

        with patch("google.genai.types") as mock_types:
            mock_types.GenerateContentConfig.return_value = MagicMock()
            result = service.generate("テスト", system="システム")

        assert result.content == "Googleの回答"
        assert result.provider == "google"
        assert result.input_tokens == 20
        assert result.output_tokens == 40


class TestGenerateBedrock:
    """Test _generate_bedrock method."""

    def test_generate_bedrock_anthropic_model(self):
        config = LLMConfig(
            provider="bedrock",
            model="us.anthropic.claude-opus-4-6-20260201-v1:0",
        )
        service = LLMService(config=config)

        import json as json_mod

        mock_client = MagicMock()
        response_body = {
            "content": [{"text": "Bedrock Anthropicの回答"}],
            "usage": {"input_tokens": 15, "output_tokens": 30},
        }
        mock_body = MagicMock()
        mock_body.read.return_value = json_mod.dumps(response_body).encode()
        mock_client.invoke_model.return_value = {"body": mock_body}
        service._client = mock_client

        result = service.generate("テスト", system="システム")
        assert result.content == "Bedrock Anthropicの回答"
        assert result.provider == "bedrock"
        assert result.input_tokens == 15
        assert result.output_tokens == 30

    def test_generate_bedrock_nova_model(self):
        config = LLMConfig(provider="bedrock", model="amazon.nova-pro-v1:0")
        service = LLMService(config=config)

        import json as json_mod

        mock_client = MagicMock()
        response_body = {
            "results": [{"outputText": "Nova Proの回答"}],
        }
        mock_body = MagicMock()
        mock_body.read.return_value = json_mod.dumps(response_body).encode()
        mock_client.invoke_model.return_value = {"body": mock_body}
        service._client = mock_client

        result = service.generate("テスト")
        assert result.content == "Nova Proの回答"
        assert result.provider == "bedrock"
        assert result.usage == {}


class TestGenerateAzure:
    """Test _generate_azure method."""

    def test_generate_azure_success(self):
        config = LLMConfig(provider="azure", model="gpt-4o")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Azureの回答"))]
        mock_response.model = "gpt-4o"
        mock_response.usage.prompt_tokens = 25
        mock_response.usage.completion_tokens = 50
        mock_client.chat.completions.create.return_value = mock_response
        service._client = mock_client

        with patch("app.services.llm.service.settings") as mock_s:
            mock_s.azure_openai_deployment = "my-deployment"
            result = service.generate("テスト", system="システム")

        assert result.content == "Azureの回答"
        assert result.provider == "azure"
        assert result.input_tokens == 25


class TestGenerateAzureFoundry:
    """Test _generate_azure_foundry method (azure-ai-inference SDK)."""

    @patch("app.services.llm.service.settings")
    def test_generate_azure_foundry_gpt5(self, mock_s):
        config = LLMConfig(provider="azure_foundry", model="gpt-5.2")
        service = LLMService(config=config)
        mock_s.azure_foundry_deployment = "gpt52-deploy"

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [MagicMock(message=MagicMock(content="Foundryの回答"))]
        mock_response.model = "gpt-5.2"
        mock_response.usage.prompt_tokens = 20
        mock_response.usage.completion_tokens = 40
        mock_client.complete.return_value = mock_response
        service._client = mock_client

        with patch.dict("sys.modules", {
            "azure": MagicMock(),
            "azure.ai": MagicMock(),
            "azure.ai.inference": MagicMock(),
            "azure.ai.inference.models": MagicMock(),
        }):
            result = service.generate("テスト")

        assert result.content == "Foundryの回答"
        assert result.provider == "azure_foundry"

    @patch("app.services.llm.service.settings")
    def test_generate_azure_foundry_claude(self, mock_s):
        config = LLMConfig(provider="azure_foundry", model="claude-sonnet-4-5")
        service = LLMService(config=config)
        mock_s.azure_foundry_deployment = None

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(message=MagicMock(content="Claude on Foundry"))
        ]
        mock_response.model = "claude-sonnet-4-5"
        mock_response.usage.prompt_tokens = 15
        mock_response.usage.completion_tokens = 35
        mock_client.complete.return_value = mock_response
        service._client = mock_client

        with patch.dict("sys.modules", {
            "azure": MagicMock(),
            "azure.ai": MagicMock(),
            "azure.ai.inference": MagicMock(),
            "azure.ai.inference.models": MagicMock(),
        }):
            result = service.generate("テスト")

        assert result.content == "Claude on Foundry"
        assert result.provider == "azure_foundry"


class TestGenerateVertexAI:
    """Test _generate_vertex_ai method."""

    def test_generate_vertex_ai_success(self):
        config = LLMConfig(provider="vertex_ai", model="gemini-3-pro")
        service = LLMService(config=config)

        mock_model_instance = MagicMock()
        mock_response = MagicMock()
        mock_response.text = "Vertex AIの回答"
        mock_response.usage_metadata.prompt_token_count = 25
        mock_response.usage_metadata.candidates_token_count = 50
        mock_model_instance.generate_content.return_value = mock_response

        mock_generative_model = MagicMock(return_value=mock_model_instance)
        service._client = {
            "vertexai": MagicMock(),
            "GenerativeModel": mock_generative_model,
        }

        result = service.generate("テスト", system="システム")
        assert result.content == "Vertex AIの回答"
        assert result.provider == "vertex_ai"
        assert result.input_tokens == 25
        assert result.output_tokens == 50
        # GenerativeModelにsystem_instruction引数が渡される
        mock_generative_model.assert_called_once_with(
            "gemini-3-pro", system_instruction="システム"
        )


class TestGenerateLatency:
    """Test latency measurement."""

    def test_latency_is_recorded(self):
        config = LLMConfig(provider="ollama", model="phi4")
        service = LLMService(config=config)

        mock_client = MagicMock()
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "message": {"content": "回答"},
            "prompt_eval_count": 5,
            "eval_count": 10,
        }
        mock_response.raise_for_status = MagicMock()
        mock_client.post.return_value = mock_response
        service._client = mock_client

        result = service.generate("テスト")
        assert result.latency_ms >= 0
