"""AuditToolRegistry のユニットテスト。"""

import pytest

from app.agents.autonomous.tool_registry import (
    AuditToolRegistry,
    ToolDefinition,
    ToolResult,
)


def _make_tool(name: str = "test_tool", category: str = "test") -> ToolDefinition:
    """テスト用ツール定義を生成。"""
    return ToolDefinition(
        name=name,
        description=f"{name} の説明",
        category=category,
        parameters={"fiscal_year": {"type": "integer"}},
        execute_fn=lambda fiscal_year=2024: ToolResult(
            tool_name=name,
            success=True,
            summary=f"{name} executed for {fiscal_year}",
            key_findings=["finding1"],
        ),
    )


class TestToolResult:
    def test_to_dict(self):
        result = ToolResult(
            tool_name="pop",
            success=True,
            summary="OK",
            key_findings=["a", "b"],
            data={"count": 10},
        )
        d = result.to_dict()
        assert d["tool_name"] == "pop"
        assert d["success"] is True
        assert d["key_findings"] == ["a", "b"]
        assert d["data"]["count"] == 10
        assert d["error"] is None

    def test_evidence_refs_truncated(self):
        refs = [{"id": str(i)} for i in range(20)]
        result = ToolResult(
            tool_name="t", success=True, summary="s", evidence_refs=refs
        )
        d = result.to_dict()
        assert len(d["evidence_refs"]) == 10


class TestToolDefinition:
    def test_to_json_schema(self):
        tool = _make_tool("my_tool", "anomaly")
        schema = tool.to_json_schema()
        assert schema["name"] == "my_tool"
        assert schema["category"] == "anomaly"
        assert "properties" in schema["parameters"]
        assert "fiscal_year" in schema["parameters"]["required"]


class TestAuditToolRegistry:
    def test_register_and_get(self):
        registry = AuditToolRegistry()
        tool = _make_tool("t1")
        registry.register(tool)
        assert "t1" in registry
        assert registry.get_tool("t1") is tool
        assert len(registry) == 1

    def test_get_tool_names(self):
        registry = AuditToolRegistry()
        registry.register(_make_tool("a"))
        registry.register(_make_tool("b"))
        assert set(registry.get_tool_names()) == {"a", "b"}

    def test_get_tools_by_category(self):
        registry = AuditToolRegistry()
        registry.register(_make_tool("a", "pop"))
        registry.register(_make_tool("b", "anomaly"))
        registry.register(_make_tool("c", "pop"))
        pop_tools = registry.get_tools_by_category("pop")
        assert len(pop_tools) == 2

    def test_get_categories(self):
        registry = AuditToolRegistry()
        registry.register(_make_tool("a", "pop"))
        registry.register(_make_tool("b", "anomaly"))
        cats = registry.get_categories()
        assert cats == ["anomaly", "pop"]

    def test_get_all_schemas(self):
        registry = AuditToolRegistry()
        registry.register(_make_tool("x"))
        schemas = registry.get_all_schemas()
        assert len(schemas) == 1
        assert schemas[0]["name"] == "x"

    def test_execute_success(self):
        registry = AuditToolRegistry()
        registry.register(_make_tool("t"))
        result = registry.execute("t", fiscal_year=2024)
        assert result.success is True
        assert result.tool_name == "t"
        assert result.execution_time_ms > 0

    def test_execute_unknown_tool(self):
        registry = AuditToolRegistry()
        result = registry.execute("missing")
        assert result.success is False
        assert "missing" in result.summary

    def test_execute_error_handling(self):
        def failing_fn(**kwargs):
            raise ValueError("boom")

        registry = AuditToolRegistry()
        registry.register(
            ToolDefinition(
                name="bad",
                description="d",
                category="c",
                parameters={},
                execute_fn=failing_fn,
            )
        )
        result = registry.execute("bad")
        assert result.success is False
        assert "boom" in result.error
        assert result.execution_time_ms >= 0


class TestCreateDefaultRegistry:
    def test_all_tools_registered(self):
        from app.agents.autonomous_tools import create_default_registry

        registry = create_default_registry()
        assert len(registry) == 13
        expected = {
            "population_statistics",
            "account_balance_analysis",
            "financial_ratio_analysis",
            "t_account_analysis",
            "sankey_flow_data",
            "time_series_trend",
            "stratification_analysis",
            "duplicate_detection",
            "round_amount_analysis",
            "journal_entry_testing",
            "correlation_analysis",
            "rule_risk_summary",
            "ml_anomaly_summary",
        }
        assert set(registry.get_tool_names()) == expected

    def test_all_schemas_valid(self):
        from app.agents.autonomous_tools import create_default_registry

        registry = create_default_registry()
        schemas = registry.get_all_schemas()
        for s in schemas:
            assert "name" in s
            assert "description" in s
            assert "category" in s
            assert "parameters" in s
            assert s["parameters"]["type"] == "object"
