"""Integration tests using Ollama (local LLM).

These tests require Ollama to be running locally.
Skip automatically if Ollama is not available.
"""

import os
import pytest
import httpx

from app.services.llm.models import LLMConfig
from app.services.llm.service import LLMService


def is_ollama_running() -> bool:
    """Check if Ollama is running at localhost:11434."""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=3)
        return response.status_code == 200
    except Exception:
        return False


def get_ollama_model() -> str:
    """Get an available Ollama model for testing."""
    try:
        response = httpx.get("http://localhost:11434/api/tags", timeout=3)
        if response.status_code == 200:
            models = response.json().get("models", [])
            if models:
                return models[0]["name"]
    except Exception:
        pass
    return "phi4"


OLLAMA_AVAILABLE = is_ollama_running()
SKIP_REASON = "Ollama not running at localhost:11434"


@pytest.mark.skipif(not OLLAMA_AVAILABLE, reason=SKIP_REASON)
class TestOllamaServiceIntegration:
    """Test LLMService with real Ollama instance."""

    @pytest.fixture
    def service(self):
        model = get_ollama_model()
        config = LLMConfig(provider="ollama", model=model, max_tokens=100)
        return LLMService(config=config)

    def test_basic_generation(self, service):
        response = service.generate("Say hello in Japanese. Reply with one word only.")
        assert response.content
        assert len(response.content) > 0
        assert response.provider == "ollama"

    def test_generation_with_system_prompt(self, service):
        response = service.generate(
            "What is 2+2?",
            system="You are a math tutor. Answer briefly.",
        )
        assert "4" in response.content

    def test_token_usage_reported(self, service):
        response = service.generate("Say hi")
        assert response.input_tokens > 0 or response.output_tokens > 0

    def test_latency_tracked(self, service):
        response = service.generate("Say hello")
        assert response.latency_ms > 0


@pytest.mark.skipif(not OLLAMA_AVAILABLE, reason=SKIP_REASON)
class TestOllamaAgentIntegration:
    """Test agent layer with Ollama."""

    def test_create_llm_ollama(self):
        from app.agents.base import AgentConfig, AgentType, create_llm

        model = get_ollama_model()
        config = AgentConfig(
            agent_type=AgentType.QA,
            model_provider="ollama",
            model_name=model,
            max_tokens=100,
        )
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.agents.base.settings.ollama_base_url", "http://localhost:11434")
            llm = create_llm(config)
            assert llm is not None

    def test_llm_invoke(self):
        from langchain_core.messages import HumanMessage
        from app.agents.base import AgentConfig, AgentType, create_llm

        model = get_ollama_model()
        config = AgentConfig(
            agent_type=AgentType.QA,
            model_provider="ollama",
            model_name=model,
            max_tokens=50,
        )
        with pytest.MonkeyPatch.context() as mp:
            mp.setattr("app.agents.base.settings.ollama_base_url", "http://localhost:11434")
            llm = create_llm(config)
            response = llm.invoke([HumanMessage(content="Say hello")])
            assert response.content
            assert len(response.content) > 0
