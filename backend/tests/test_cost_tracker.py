"""LLM コスト追跡のテスト."""

import pytest

from app.db.sqlite import sqlite_manager
from app.services.llm.cost_tracker import (
    calculate_cost,
    get_daily_costs,
    get_summary,
    log_usage,
)


@pytest.fixture(autouse=True)
def _init_db():
    """テスト用にスキーマを初期化する。"""
    sqlite_manager.initialize_schema()


class TestCalculateCost:
    """コスト算出のテスト。"""

    def test_anthropic_opus(self):
        cost = calculate_cost("anthropic", "claude-opus-4-6", 1_000_000, 500_000)
        # input: $15/M * 1M = $15, output: $75/M * 0.5M = $37.5
        assert cost == pytest.approx(52.5, abs=0.01)

    def test_anthropic_haiku(self):
        cost = calculate_cost("anthropic", "claude-haiku-4-5", 100_000, 50_000)
        # input: $0.80/M * 0.1M = $0.08, output: $4.00/M * 0.05M = $0.20
        assert cost == pytest.approx(0.28, abs=0.01)

    def test_ollama_free(self):
        cost = calculate_cost("ollama", "phi4", 1_000_000, 1_000_000)
        assert cost == 0.0

    def test_unknown_model(self):
        cost = calculate_cost("anthropic", "unknown-model", 1000, 1000)
        assert cost == 0.0

    def test_bedrock_nova_pro(self):
        cost = calculate_cost(
            "bedrock", "amazon.nova-pro-v1:0", 500_000, 250_000
        )
        # input: $0.80/M * 0.5M = $0.40, output: $3.20/M * 0.25M = $0.80
        assert cost == pytest.approx(1.2, abs=0.01)


class TestLogUsage:
    """使用ログ記録のテスト。"""

    def test_log_and_retrieve(self):
        record_id = log_usage(
            provider="anthropic",
            model="claude-sonnet-4-5",
            input_tokens=10000,
            output_tokens=5000,
            latency_ms=1234.5,
            request_type="analysis",
        )
        assert record_id > 0

        rows = sqlite_manager.execute(
            "SELECT * FROM llm_usage_log WHERE id = ?", (record_id,)
        )
        assert len(rows) == 1
        assert rows[0]["provider"] == "anthropic"
        assert rows[0]["model"] == "claude-sonnet-4-5"
        assert rows[0]["input_tokens"] == 10000
        assert rows[0]["output_tokens"] == 5000
        assert rows[0]["estimated_cost_usd"] > 0

    def test_log_multiple(self):
        for i in range(3):
            log_usage(
                provider="openai",
                model="gpt-5-mini",
                input_tokens=1000 * (i + 1),
                output_tokens=500 * (i + 1),
                request_type="general",
            )

        rows = sqlite_manager.execute(
            "SELECT COUNT(*) as cnt FROM llm_usage_log WHERE provider = 'openai'"
        )
        assert rows[0]["cnt"] >= 3


class TestGetSummary:
    """サマリー取得のテスト。"""

    def test_empty_summary(self):
        summary = get_summary(days=1)
        assert summary["total_requests"] >= 0

    def test_summary_with_data(self):
        log_usage("anthropic", "claude-haiku-4-5", 5000, 2000, request_type="analysis")
        log_usage("anthropic", "claude-haiku-4-5", 3000, 1000, request_type="general")

        summary = get_summary(days=30)
        assert summary["total_requests"] >= 2
        assert summary["total_input_tokens"] >= 8000
        assert summary["total_cost_usd"] > 0
        assert "by_provider" in summary
        assert "by_request_type" in summary


class TestGetDailyCosts:
    """日別コスト取得のテスト。"""

    def test_daily_costs(self):
        log_usage("google", "gemini-3-flash-preview", 10000, 5000)

        daily = get_daily_costs(days=7)
        assert isinstance(daily, list)
        if daily:
            assert "date" in daily[0]
            assert "cost_usd" in daily[0]
            assert "requests" in daily[0]


class TestLLMUsageAPI:
    """LLM Usage APIエンドポイントのテスト。"""

    def test_get_summary(self, client):
        response = client.get("/api/v1/llm-usage/summary?days=30")
        assert response.status_code == 200
        data = response.json()
        assert "total_requests" in data
        assert "total_cost_usd" in data

    def test_get_daily(self, client):
        response = client.get("/api/v1/llm-usage/daily?days=7")
        assert response.status_code == 200
        data = response.json()
        assert "daily" in data
        assert "total_cost_usd" in data
        assert "days" in data

    def test_invalid_days(self, client):
        response = client.get("/api/v1/llm-usage/summary?days=0")
        assert response.status_code == 422
