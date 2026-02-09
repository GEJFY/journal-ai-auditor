"""Cloud provider integration tests.

Each test is skipped unless the corresponding API key / credentials
are available as environment variables. Run manually with:

    ANTHROPIC_API_KEY=... pytest tests/test_integration_cloud.py -v
"""

import os

import pytest

from app.services.llm.models import LLMConfig
from app.services.llm.service import LLMService

# --------------------------------------------------
# Anthropic Direct
# --------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("ANTHROPIC_API_KEY"),
    reason="ANTHROPIC_API_KEY not set",
)
class TestAnthropicIntegration:
    @pytest.fixture
    def service(self):
        return LLMService(
            LLMConfig(provider="anthropic", model="claude-haiku-4-5", max_tokens=100)
        )

    def test_generate(self, service):
        response = service.generate("Say hello in Japanese")
        assert response.content
        assert response.provider == "anthropic"
        assert response.input_tokens > 0


# --------------------------------------------------
# OpenAI Direct
# --------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("OPENAI_API_KEY"),
    reason="OPENAI_API_KEY not set",
)
class TestOpenAIIntegration:
    @pytest.fixture
    def service(self):
        return LLMService(
            LLMConfig(provider="openai", model="gpt-5-nano", max_tokens=100)
        )

    def test_generate(self, service):
        response = service.generate("What is 1+1?")
        assert response.content
        assert "2" in response.content


# --------------------------------------------------
# Google AI Studio
# --------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("GOOGLE_API_KEY"),
    reason="GOOGLE_API_KEY not set",
)
class TestGoogleIntegration:
    @pytest.fixture
    def service(self):
        return LLMService(
            LLMConfig(provider="google", model="gemini-2.5-flash-lite", max_tokens=100)
        )

    def test_generate(self, service):
        response = service.generate("Say hi")
        assert response.content
        assert response.provider == "google"


# --------------------------------------------------
# AWS Bedrock
# --------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("AWS_ACCESS_KEY_ID"),
    reason="AWS_ACCESS_KEY_ID not set",
)
class TestBedrockIntegration:
    @pytest.fixture
    def service(self):
        return LLMService(
            LLMConfig(
                provider="bedrock",
                model="us.anthropic.claude-haiku-4-5-20251001-v1:0",
                max_tokens=100,
            )
        )

    def test_generate(self, service):
        response = service.generate("Say hello")
        assert response.content
        assert response.provider == "bedrock"


# --------------------------------------------------
# Azure AI Foundry
# --------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("AZURE_FOUNDRY_API_KEY"),
    reason="AZURE_FOUNDRY_API_KEY not set",
)
class TestAzureFoundryIntegration:
    @pytest.fixture
    def service(self):
        return LLMService(
            LLMConfig(provider="azure_foundry", model="gpt-5-nano", max_tokens=100)
        )

    def test_generate(self, service):
        response = service.generate("What is 2+2?")
        assert response.content
        assert response.provider == "azure_foundry"


# --------------------------------------------------
# GCP Vertex AI
# --------------------------------------------------


@pytest.mark.skipif(
    not os.getenv("GCP_PROJECT_ID"),
    reason="GCP_PROJECT_ID not set",
)
class TestVertexAIIntegration:
    @pytest.fixture
    def service(self):
        return LLMService(
            LLMConfig(
                provider="vertex_ai",
                model="gemini-2.5-flash-lite",
                max_tokens=100,
            )
        )

    def test_generate(self, service):
        response = service.generate("Say hello")
        assert response.content
        assert response.provider == "vertex_ai"
