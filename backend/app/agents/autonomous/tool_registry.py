"""自律型監査エージェント用ツールレジストリ。

既存の LangChain @tool 関数と新規分析ツールを統一的に管理し、
LLM がツール選択するための JSON Schema を提供する。
"""

import logging
import time
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ToolResult:
    """分析ツールの標準化された実行結果。"""

    tool_name: str
    success: bool
    summary: str  # 人間が読める要約 (200字以内)
    key_findings: list[str] = field(default_factory=list)  # 主要発見事項
    evidence_refs: list[dict[str, Any]] = field(default_factory=list)
    data: dict[str, Any] = field(default_factory=dict)  # 詳細データ
    error: str | None = None
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        return {
            "tool_name": self.tool_name,
            "success": self.success,
            "summary": self.summary,
            "key_findings": self.key_findings,
            "evidence_refs": self.evidence_refs[:10],  # 最大10件
            "data": self.data,
            "error": self.error,
            "execution_time_ms": round(self.execution_time_ms, 2),
        }


@dataclass
class ToolDefinition:
    """分析ツールの定義。LLM 向け JSON Schema を提供する。"""

    name: str
    description: str  # 日本語説明
    category: str  # population, account, anomaly, pattern, trend, flow, compliance
    parameters: dict[str, Any]  # JSON Schema properties
    execute_fn: Callable[..., ToolResult]
    required_params: list[str] = field(default_factory=lambda: ["fiscal_year"])

    def to_json_schema(self) -> dict[str, Any]:
        """LLM ツール選択用の JSON Schema を生成。"""
        return {
            "name": self.name,
            "description": self.description,
            "category": self.category,
            "parameters": {
                "type": "object",
                "properties": self.parameters,
                "required": self.required_params,
            },
        }


class AuditToolRegistry:
    """監査分析ツールのレジストリ。

    ツールの登録・検索・実行を一元管理する。
    LLM がツールを選択するための JSON Schema を提供し、
    統一的な ToolResult 形式で結果を返す。
    """

    def __init__(self) -> None:
        self._tools: dict[str, ToolDefinition] = {}

    def register(self, tool_def: ToolDefinition) -> None:
        """ツールをレジストリに登録。"""
        self._tools[tool_def.name] = tool_def
        logger.debug("ツール登録: %s (%s)", tool_def.name, tool_def.category)

    def get_tool(self, name: str) -> ToolDefinition | None:
        return self._tools.get(name)

    def get_tools_by_category(self, category: str) -> list[ToolDefinition]:
        return [t for t in self._tools.values() if t.category == category]

    def get_all_schemas(self) -> list[dict[str, Any]]:
        """全ツールの JSON Schema を返す（LLM ツール選択用）。"""
        return [t.to_json_schema() for t in self._tools.values()]

    def get_tool_names(self) -> list[str]:
        return list(self._tools.keys())

    def get_categories(self) -> list[str]:
        return sorted({t.category for t in self._tools.values()})

    def execute(self, name: str, **kwargs: Any) -> ToolResult:
        """ツールを名前で実行し、ToolResult を返す。"""
        tool = self._tools.get(name)
        if not tool:
            return ToolResult(
                tool_name=name,
                success=False,
                summary=f"不明なツール: {name}",
                error=f"ツール '{name}' がレジストリに存在しません",
            )

        start = time.perf_counter()
        try:
            result = tool.execute_fn(**kwargs)
            result.execution_time_ms = (time.perf_counter() - start) * 1000
            logger.info(
                "ツール実行完了: %s (%.0fms, findings=%d)",
                name,
                result.execution_time_ms,
                len(result.key_findings),
            )
            return result
        except Exception as e:
            elapsed = (time.perf_counter() - start) * 1000
            logger.error("ツール実行エラー: %s - %s", name, str(e))
            return ToolResult(
                tool_name=name,
                success=False,
                summary=f"ツール実行エラー: {e}",
                error=str(e),
                execution_time_ms=elapsed,
            )

    def __len__(self) -> int:
        return len(self._tools)

    def __contains__(self, name: str) -> bool:
        return name in self._tools
