"""LLM Data Models."""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Literal


@dataclass
class LLMConfig:
    """Configuration for LLM calls."""

    provider: Literal[
        "anthropic", "openai", "google", "bedrock",
        "azure", "azure_foundry", "vertex_ai", "ollama",
    ]
    model: str
    temperature: float = 0.0
    max_tokens: int = 4096
    top_p: float = 1.0
    timeout: int = 120

    # Provider-specific options
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class LLMResponse:
    """Response from LLM."""

    content: str
    model: str
    provider: str
    usage: dict[str, int] = field(default_factory=dict)
    latency_ms: float = 0.0
    created_at: datetime = field(default_factory=datetime.now)
    raw_response: Any = None

    @property
    def input_tokens(self) -> int:
        return self.usage.get("input_tokens", 0)

    @property
    def output_tokens(self) -> int:
        return self.usage.get("output_tokens", 0)

    @property
    def total_tokens(self) -> int:
        return self.input_tokens + self.output_tokens


@dataclass
class ModelInfo:
    """Information about an LLM model."""

    id: str
    name: str
    provider: str
    tier: Literal["premium", "balanced", "fast", "reasoning"]
    cost: Literal["very_high", "high", "medium", "low", "very_low"]
    max_tokens: int = 4096
    supports_vision: bool = False
    supports_tools: bool = True
    description: str = ""
