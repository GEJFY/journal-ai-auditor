"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Any, Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

# Available LLM Models (2026-02 Latest)
LLM_MODELS = {
    # Anthropic Direct API
    "anthropic": {
        "claude-opus-4-6": {
            "name": "Claude Opus 4.6",
            "tier": "premium",
            "cost": "very_high",
        },
        "claude-sonnet-4-5": {
            "name": "Claude Sonnet 4.5",
            "tier": "balanced",
            "cost": "medium",
        },
        "claude-haiku-4-5": {"name": "Claude Haiku 4.5", "tier": "fast", "cost": "low"},
    },
    # OpenAI Direct API
    "openai": {
        "gpt-5.2": {"name": "GPT-5.2", "tier": "premium", "cost": "very_high"},
        "gpt-5": {"name": "GPT-5", "tier": "premium", "cost": "high"},
        "gpt-5-mini": {"name": "GPT-5 Mini", "tier": "balanced", "cost": "medium"},
        "gpt-5-nano": {"name": "GPT-5 Nano", "tier": "fast", "cost": "low"},
        "gpt-5-codex": {"name": "GPT-5 Codex", "tier": "premium", "cost": "very_high"},
        "o3-pro": {"name": "o3-pro", "tier": "reasoning", "cost": "very_high"},
        "o3": {"name": "o3", "tier": "reasoning", "cost": "high"},
        "o4-mini": {"name": "o4-mini", "tier": "reasoning", "cost": "medium"},
    },
    # Google AI Studio (google-genai SDK)
    "google": {
        "gemini-3-flash-preview": {
            "name": "Gemini 3 Flash Preview",
            "tier": "fast",
            "cost": "low",
        },
        "gemini-2.5-pro": {"name": "Gemini 2.5 Pro", "tier": "premium", "cost": "high"},
        "gemini-2.5-flash-lite": {
            "name": "Gemini 2.5 Flash-Lite",
            "tier": "fast",
            "cost": "very_low",
        },
    },
    # AWS Bedrock (2026-02 Latest)
    "bedrock": {
        "us.anthropic.claude-opus-4-6-20260201-v1:0": {
            "name": "Claude Opus 4.6",
            "tier": "premium",
            "cost": "very_high",
        },
        "us.anthropic.claude-sonnet-4-5-20250929-v1:0": {
            "name": "Claude Sonnet 4.5",
            "tier": "balanced",
            "cost": "medium",
        },
        "us.anthropic.claude-haiku-4-5-20251001-v1:0": {
            "name": "Claude Haiku 4.5",
            "tier": "fast",
            "cost": "low",
        },
        "amazon.nova-premier-v1:0": {
            "name": "Amazon Nova Premier",
            "tier": "premium",
            "cost": "high",
        },
        "amazon.nova-pro-v1:0": {
            "name": "Amazon Nova Pro",
            "tier": "balanced",
            "cost": "medium",
        },
        "amazon.nova-lite-v1:0": {
            "name": "Amazon Nova Lite",
            "tier": "fast",
            "cost": "low",
        },
        "amazon.nova-micro-v1:0": {
            "name": "Amazon Nova Micro",
            "tier": "fast",
            "cost": "very_low",
        },
        "us.deepseek.r1-v1:0": {
            "name": "DeepSeek R1",
            "tier": "reasoning",
            "cost": "medium",
        },
    },
    # Azure AI Foundry (GPT-5 series + Claude)
    "azure_foundry": {
        "gpt-5.2": {"name": "GPT-5.2", "tier": "premium", "cost": "very_high"},
        "gpt-5": {"name": "GPT-5", "tier": "premium", "cost": "high"},
        "gpt-5-nano": {"name": "GPT-5 Nano", "tier": "fast", "cost": "low"},
        "claude-opus-4-6": {
            "name": "Claude Opus 4.6",
            "tier": "premium",
            "cost": "very_high",
        },
        "claude-sonnet-4-5": {
            "name": "Claude Sonnet 4.5",
            "tier": "balanced",
            "cost": "medium",
        },
        "claude-haiku-4-5": {"name": "Claude Haiku 4.5", "tier": "fast", "cost": "low"},
    },
    # GCP Vertex AI (Gemini 3 series, Global Region)
    "vertex_ai": {
        "gemini-3-pro": {"name": "Gemini 3 Pro", "tier": "premium", "cost": "high"},
        "gemini-3-flash-preview": {
            "name": "Gemini 3 Flash Preview",
            "tier": "balanced",
            "cost": "medium",
        },
        "gemini-2.5-pro": {
            "name": "Gemini 2.5 Pro",
            "tier": "balanced",
            "cost": "medium",
        },
        "gemini-2.5-flash-lite": {
            "name": "Gemini 2.5 Flash-Lite",
            "tier": "fast",
            "cost": "very_low",
        },
    },
    # Azure OpenAI (Legacy)
    "azure": {
        "gpt-4o": {"name": "GPT-4o", "tier": "premium", "cost": "high"},
        "gpt-4o-mini": {"name": "GPT-4o Mini", "tier": "balanced", "cost": "low"},
    },
    # Local LLM (Ollama)
    "ollama": {
        "phi4": {"name": "Phi-4 (14B)", "tier": "balanced", "cost": "very_low"},
        "qwen2.5-coder:14b": {
            "name": "Qwen 2.5 Coder 14B",
            "tier": "balanced",
            "cost": "very_low",
        },
        "deepseek-r1:14b": {
            "name": "DeepSeek R1 14B",
            "tier": "reasoning",
            "cost": "very_low",
        },
        "llama3.3:8b": {"name": "Llama 3.3 8B", "tier": "fast", "cost": "very_low"},
        "gemma3:27b": {"name": "Gemma 3 27B", "tier": "premium", "cost": "very_low"},
    },
}

# Recommended models by use case (2026-02 Latest)
RECOMMENDED_MODELS = {
    "highest_accuracy": {
        "provider": "azure_foundry",
        "model": "gpt-5.2",
        "description": "最高精度 - GPT-5.2 (ARC-AGI 90%+)",
    },
    "high_accuracy": {
        "provider": "bedrock",
        "model": "us.anthropic.claude-opus-4-6-20260201-v1:0",
        "description": "高精度 - Claude Opus 4.6、エージェント・複雑な調査向け",
    },
    "balanced": {
        "provider": "vertex_ai",
        "model": "gemini-3-pro",
        "description": "バランス - Gemini 3 Pro、日常分析向け",
    },
    "cost_effective": {
        "provider": "vertex_ai",
        "model": "gemini-3-flash-preview",
        "description": "コスト重視 - Gemini 3 Flash、大量処理向け ($0.50/1M入力)",
    },
    "ultra_fast": {
        "provider": "azure_foundry",
        "model": "gpt-5-nano",
        "description": "超高速 - GPT-5 Nano ($0.05/1M入力)",
    },
    "local_dev": {
        "provider": "ollama",
        "model": "phi4",
        "description": "ローカル開発 - Phi-4 14B、クラウド不要・無料",
    },
}


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # Application
    app_name: str = "JAIA"
    app_version: str = "0.2.0"
    debug: bool = False
    environment: Literal["development", "staging", "production"] = "development"

    # Server
    host: str = "127.0.0.1"
    port: int = 8001

    # Database paths
    data_dir: Path = Field(default_factory=lambda: Path("./data"))
    duckdb_path: Path = Field(default_factory=lambda: Path("./data/jaia.duckdb"))
    sqlite_path: Path = Field(default_factory=lambda: Path("./data/jaia_meta.db"))

    # LLM Providers - Multi-cloud + Local (2026-02)
    llm_provider: Literal[
        "anthropic",
        "openai",
        "google",
        "bedrock",
        "azure_foundry",
        "vertex_ai",
        "azure",
        "ollama",
    ] = "bedrock"
    llm_model: str = "us.anthropic.claude-opus-4-6-20260201-v1:0"

    # Anthropic Direct API
    anthropic_api_key: str | None = None

    # OpenAI Direct API
    openai_api_key: str | None = None

    # Google AI Studio
    google_api_key: str | None = None

    # AWS Bedrock (Recommended for Enterprise)
    aws_region: str = "us-east-1"
    aws_access_key_id: str | None = None
    aws_secret_access_key: str | None = None
    aws_bedrock_endpoint: str | None = None  # Optional custom endpoint

    # Azure AI Foundry (GPT-5 series + Claude) - azure-ai-inference SDK
    azure_foundry_endpoint: str | None = None
    azure_foundry_api_key: str | None = None
    azure_foundry_deployment: str | None = None
    azure_foundry_api_version: str = "2024-10-21"

    # GCP Vertex AI (Gemini 3.0 series)
    # Gemini 3.0: "global" リージョンのみ対応
    # Gemini 2.5: "us-central1" 等リージョナルエンドポイント利用可
    gcp_project_id: str | None = None
    gcp_location: str = "global"
    gcp_credentials_path: str | None = None  # Path to service account JSON

    # Azure OpenAI (Legacy)
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-10-21"

    # Local LLM (Ollama)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "phi4"

    # Performance
    batch_size: int = 10000
    max_workers: int = 4
    cache_ttl_seconds: int = 300

    # Rate Limiting
    llm_requests_per_minute: int = 60
    llm_tokens_per_minute: int = 100000

    # Logging
    log_level: str = "INFO"
    log_format: str = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"

    def ensure_data_dir(self) -> None:
        """Ensure data directory exists."""
        self.data_dir.mkdir(parents=True, exist_ok=True)

    def get_available_models(self) -> dict[str, Any]:
        """Get available models for current provider."""
        return LLM_MODELS.get(self.llm_provider, {})

    def get_recommended_model(self, use_case: str = "balanced") -> dict[str, Any]:
        """Get recommended model for use case."""
        return RECOMMENDED_MODELS.get(use_case, RECOMMENDED_MODELS["balanced"])


settings = Settings()
