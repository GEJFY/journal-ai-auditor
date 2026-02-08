"""Application configuration using Pydantic Settings."""

from pathlib import Path
from typing import Literal

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict


# Available LLM Models (2026 Latest)
LLM_MODELS = {
    # Anthropic Direct API - High accuracy, best for complex analysis
    "anthropic": {
        "claude-opus-4": {"name": "Claude Opus 4", "tier": "premium", "cost": "high"},
        "claude-sonnet-4": {"name": "Claude Sonnet 4", "tier": "balanced", "cost": "medium"},
        "claude-haiku-3.5": {"name": "Claude Haiku 3.5", "tier": "fast", "cost": "low"},
    },
    # OpenAI Direct API
    "openai": {
        "gpt-4o": {"name": "GPT-4o", "tier": "premium", "cost": "high"},
        "gpt-4o-mini": {"name": "GPT-4o Mini", "tier": "balanced", "cost": "low"},
        "o1": {"name": "o1", "tier": "reasoning", "cost": "very_high"},
        "o3-mini": {"name": "o3-mini", "tier": "reasoning", "cost": "medium"},
    },
    # Google AI Studio
    "google": {
        "gemini-2.0-flash": {"name": "Gemini 2.0 Flash", "tier": "fast", "cost": "very_low"},
        "gemini-2.0-pro": {"name": "Gemini 2.0 Pro", "tier": "balanced", "cost": "medium"},
    },
    # AWS Bedrock (2026 Latest)
    "bedrock": {
        "anthropic.claude-sonnet-4-6-opus-20260115-v1:0": {"name": "Claude Sonnet 4.6 Opus", "tier": "premium", "cost": "high"},
        "anthropic.claude-sonnet-4-20251022-v1:0": {"name": "Claude Sonnet 4", "tier": "balanced", "cost": "medium"},
        "anthropic.claude-haiku-3-5-20251022-v1:0": {"name": "Claude Haiku 3.5", "tier": "fast", "cost": "low"},
        "amazon.nova-pro-v1:0": {"name": "Amazon Nova Pro", "tier": "balanced", "cost": "medium"},
        "amazon.nova-lite-v1:0": {"name": "Amazon Nova Lite", "tier": "fast", "cost": "low"},
    },
    # Azure Foundry (2026 Latest - GPT-5 series + Claude)
    "azure_foundry": {
        "gpt-5.2": {"name": "GPT-5.2", "tier": "premium", "cost": "very_high"},
        "gpt-5-nano": {"name": "GPT-5 Nano", "tier": "fast", "cost": "low"},
        "gpt-4o": {"name": "GPT-4o", "tier": "balanced", "cost": "medium"},
        "claude-sonnet-4": {"name": "Claude Sonnet 4", "tier": "balanced", "cost": "medium"},
        "claude-haiku-3.5": {"name": "Claude Haiku 3.5", "tier": "fast", "cost": "low"},
    },
    # GCP Vertex AI (2026 Latest - Gemini 3.0 series)
    "vertex_ai": {
        "gemini-3.0-flash-preview": {"name": "Gemini 3.0 Flash Preview", "tier": "fast", "cost": "low"},
        "gemini-3.0-pro-preview": {"name": "Gemini 3.0 Pro Preview", "tier": "premium", "cost": "high"},
        "gemini-2.0-flash": {"name": "Gemini 2.0 Flash", "tier": "fast", "cost": "very_low"},
        "gemini-2.0-pro": {"name": "Gemini 2.0 Pro", "tier": "balanced", "cost": "medium"},
    },
    # Azure OpenAI (Legacy)
    "azure": {
        "gpt-4o": {"name": "GPT-4o", "tier": "premium", "cost": "high"},
        "gpt-4o-mini": {"name": "GPT-4o Mini", "tier": "balanced", "cost": "low"},
    },
}

# Recommended models by use case (2026 Latest)
RECOMMENDED_MODELS = {
    "highest_accuracy": {
        "provider": "azure_foundry",
        "model": "gpt-5.2",
        "description": "最高精度 - GPT-5.2による最先端分析",
    },
    "high_accuracy": {
        "provider": "bedrock",
        "model": "anthropic.claude-sonnet-4-6-opus-20260115-v1:0",
        "description": "高精度 - Claude Sonnet 4.6 Opus、複雑な調査向け",
    },
    "balanced": {
        "provider": "vertex_ai",
        "model": "gemini-3.0-pro-preview",
        "description": "バランス - Gemini 3.0 Pro、日常分析向け",
    },
    "cost_effective": {
        "provider": "vertex_ai",
        "model": "gemini-3.0-flash-preview",
        "description": "コスト重視 - Gemini 3.0 Flash、大量処理向け",
    },
    "ultra_fast": {
        "provider": "azure_foundry",
        "model": "gpt-5-nano",
        "description": "超高速 - GPT-5 Nano、リアルタイム処理向け",
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

    # LLM Providers - Extended for 2026 (Cloud-first)
    llm_provider: Literal[
        "anthropic", "openai", "google",
        "bedrock", "azure_foundry", "vertex_ai", "azure"
    ] = "bedrock"
    llm_model: str = "anthropic.claude-sonnet-4-6-opus-20260115-v1:0"  # Default: Latest Bedrock model

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

    # Azure Foundry (GPT-5 series + Claude)
    azure_foundry_endpoint: str | None = None
    azure_foundry_api_key: str | None = None
    azure_foundry_deployment: str | None = None
    azure_foundry_api_version: str = "2026-01-01"

    # GCP Vertex AI (Gemini 3.0 series)
    gcp_project_id: str | None = None
    gcp_location: str = "us-central1"
    gcp_credentials_path: str | None = None  # Path to service account JSON

    # Azure OpenAI (Legacy)
    azure_openai_endpoint: str | None = None
    azure_openai_api_key: str | None = None
    azure_openai_deployment: str | None = None
    azure_openai_api_version: str = "2024-10-21"

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

    def get_available_models(self) -> dict:
        """Get available models for current provider."""
        return LLM_MODELS.get(self.llm_provider, {})

    def get_recommended_model(self, use_case: str = "balanced") -> dict:
        """Get recommended model for use case."""
        return RECOMMENDED_MODELS.get(use_case, RECOMMENDED_MODELS["balanced"])


settings = Settings()
