"""LLM Service - Multi-provider LLM integration (2026 Cloud Edition).

Supports:
- Anthropic Direct API (Claude Opus 4, Sonnet 4, Haiku 3.5)
- OpenAI Direct API (GPT-4o, o1, o3-mini)
- Google AI Studio (Gemini 2.0)
- AWS Bedrock (Claude Sonnet 4.6 Opus, Nova) - Enterprise Recommended
- Azure Foundry (GPT-5.2, GPT-5-nano, Claude) - Latest Models
- GCP Vertex AI (Gemini 3.0 Flash/Pro Preview) - Cost Effective
- Azure OpenAI (Legacy GPT-4o)
"""

import time
from typing import Optional, AsyncGenerator
from functools import lru_cache

from app.core.config import settings, LLM_MODELS, RECOMMENDED_MODELS
from .models import LLMConfig, LLMResponse, ModelInfo


class LLMService:
    """Multi-provider LLM service."""

    def __init__(self, config: Optional[LLMConfig] = None):
        """Initialize LLM service.

        Args:
            config: Optional LLM configuration. Uses settings if not provided.
        """
        self.config = config or LLMConfig(
            provider=settings.llm_provider,
            model=settings.llm_model,
        )
        self._client = None

    def _get_client(self):
        """Get or create the LLM client."""
        if self._client is not None:
            return self._client

        provider = self.config.provider

        if provider == "anthropic":
            from anthropic import Anthropic
            self._client = Anthropic(api_key=settings.anthropic_api_key)

        elif provider == "openai":
            from openai import OpenAI
            self._client = OpenAI(api_key=settings.openai_api_key)

        elif provider == "google":
            import google.generativeai as genai
            genai.configure(api_key=settings.google_api_key)
            self._client = genai

        elif provider == "bedrock":
            import boto3
            self._client = boto3.client(
                "bedrock-runtime",
                region_name=settings.aws_region,
            )

        elif provider == "azure":
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=settings.azure_openai_api_key,
                api_version=settings.azure_openai_api_version,
                azure_endpoint=settings.azure_openai_endpoint,
            )

        elif provider == "azure_foundry":
            from openai import AzureOpenAI
            self._client = AzureOpenAI(
                api_key=settings.azure_foundry_api_key,
                api_version=settings.azure_foundry_api_version,
                azure_endpoint=settings.azure_foundry_endpoint,
            )

        elif provider == "vertex_ai":
            import vertexai
            from vertexai.generative_models import GenerativeModel
            vertexai.init(
                project=settings.gcp_project_id,
                location=settings.gcp_location,
            )
            self._client = {"vertexai": vertexai, "GenerativeModel": GenerativeModel}

        return self._client

    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        **kwargs,
    ) -> LLMResponse:
        """Generate a response from the LLM.

        Args:
            prompt: User prompt.
            system: Optional system prompt.
            **kwargs: Additional parameters.

        Returns:
            LLMResponse with generated content.
        """
        start_time = time.perf_counter()
        client = self._get_client()

        provider = self.config.provider
        model = self.config.model

        if provider == "anthropic":
            response = self._generate_anthropic(client, prompt, system, **kwargs)
        elif provider == "openai":
            response = self._generate_openai(client, prompt, system, **kwargs)
        elif provider == "google":
            response = self._generate_google(client, prompt, system, **kwargs)
        elif provider == "bedrock":
            response = self._generate_bedrock(client, prompt, system, **kwargs)
        elif provider == "azure":
            response = self._generate_azure(client, prompt, system, **kwargs)
        elif provider == "azure_foundry":
            response = self._generate_azure_foundry(client, prompt, system, **kwargs)
        elif provider == "vertex_ai":
            response = self._generate_vertex_ai(client, prompt, system, **kwargs)
        else:
            raise ValueError(f"Unknown provider: {provider}")

        response.latency_ms = (time.perf_counter() - start_time) * 1000
        return response

    def _generate_anthropic(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using Anthropic API."""
        messages = [{"role": "user", "content": prompt}]

        response = client.messages.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            system=system or "",
            messages=messages,
        )

        return LLMResponse(
            content=response.content[0].text,
            model=response.model,
            provider="anthropic",
            usage={
                "input_tokens": response.usage.input_tokens,
                "output_tokens": response.usage.output_tokens,
            },
            raw_response=response,
        )

    def _generate_openai(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using OpenAI API."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="openai",
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            raw_response=response,
        )

    def _generate_google(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using Google Generative AI."""
        model = client.GenerativeModel(
            self.config.model,
            system_instruction=system,
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            },
        )

        return LLMResponse(
            content=response.text,
            model=self.config.model,
            provider="google",
            usage={
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
            },
            raw_response=response,
        )

    def _generate_bedrock(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using AWS Bedrock."""
        import json

        model_id = self.config.model

        if "anthropic" in model_id:
            # Anthropic models on Bedrock
            body = {
                "anthropic_version": "bedrock-2023-05-31",
                "max_tokens": self.config.max_tokens,
                "temperature": self.config.temperature,
                "messages": [{"role": "user", "content": prompt}],
            }
            if system:
                body["system"] = system
        else:
            # Amazon Nova or other models
            body = {
                "inputText": prompt,
                "textGenerationConfig": {
                    "maxTokenCount": self.config.max_tokens,
                    "temperature": self.config.temperature,
                },
            }

        response = client.invoke_model(
            modelId=model_id,
            body=json.dumps(body),
        )

        result = json.loads(response["body"].read())

        if "anthropic" in model_id:
            content = result["content"][0]["text"]
            usage = {
                "input_tokens": result["usage"]["input_tokens"],
                "output_tokens": result["usage"]["output_tokens"],
            }
        else:
            content = result["results"][0]["outputText"]
            usage = {}

        return LLMResponse(
            content=content,
            model=model_id,
            provider="bedrock",
            usage=usage,
            raw_response=result,
        )

    def _generate_azure(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using Azure OpenAI."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        response = client.chat.completions.create(
            model=settings.azure_openai_deployment or self.config.model,
            max_tokens=self.config.max_tokens,
            temperature=self.config.temperature,
            messages=messages,
        )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="azure",
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            raw_response=response,
        )

    def _generate_azure_foundry(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using Azure Foundry (GPT-5 series + Claude)."""
        messages = []
        if system:
            messages.append({"role": "system", "content": system})
        messages.append({"role": "user", "content": prompt})

        model = self.config.model
        deployment = settings.azure_foundry_deployment or model

        # Handle Claude models on Azure Foundry
        if "claude" in model.lower():
            # Claude models use Anthropic-style API on Azure Foundry
            response = client.chat.completions.create(
                model=deployment,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
            )
        else:
            # GPT-5 series models
            response = client.chat.completions.create(
                model=deployment,
                max_tokens=self.config.max_tokens,
                temperature=self.config.temperature,
                messages=messages,
            )

        return LLMResponse(
            content=response.choices[0].message.content,
            model=response.model,
            provider="azure_foundry",
            usage={
                "input_tokens": response.usage.prompt_tokens,
                "output_tokens": response.usage.completion_tokens,
            },
            raw_response=response,
        )

    def _generate_vertex_ai(
        self, client, prompt: str, system: Optional[str], **kwargs
    ) -> LLMResponse:
        """Generate using GCP Vertex AI (Gemini 3.0 series)."""
        GenerativeModel = client["GenerativeModel"]

        model = GenerativeModel(
            self.config.model,
            system_instruction=system,
        )

        response = model.generate_content(
            prompt,
            generation_config={
                "temperature": self.config.temperature,
                "max_output_tokens": self.config.max_tokens,
            },
        )

        return LLMResponse(
            content=response.text,
            model=self.config.model,
            provider="vertex_ai",
            usage={
                "input_tokens": response.usage_metadata.prompt_token_count,
                "output_tokens": response.usage_metadata.candidates_token_count,
            },
            raw_response=response,
        )

    @staticmethod
    def get_available_models() -> dict[str, list[ModelInfo]]:
        """Get all available models grouped by provider."""
        result = {}
        for provider, models in LLM_MODELS.items():
            result[provider] = [
                ModelInfo(
                    id=model_id,
                    name=info["name"],
                    provider=provider,
                    tier=info["tier"],
                    cost=info["cost"],
                )
                for model_id, info in models.items()
            ]
        return result

    @staticmethod
    def get_recommended_models() -> dict[str, dict]:
        """Get recommended models for different use cases."""
        return RECOMMENDED_MODELS


@lru_cache()
def get_llm_service() -> LLMService:
    """Get cached LLM service instance."""
    return LLMService()
