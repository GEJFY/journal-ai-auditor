"""LLM service unit tests with mock providers."""

import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

from app.services.llm.models import LLMConfig, LLMResponse, ModelInfo
from app.services.llm.service import LLMService
from app.core.config import LLM_MODELS, RECOMMENDED_MODELS


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
            "anthropic", "openai", "google", "bedrock",
            "azure", "azure_foundry", "vertex_ai", "ollama",
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
            "anthropic", "openai", "google", "bedrock",
            "azure_foundry", "vertex_ai", "azure", "ollama",
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
