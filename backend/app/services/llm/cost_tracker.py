"""LLM コスト追跡サービス.

LLM API呼び出しのトークン使用量とコストを記録・集計する。
docs/14_cost_estimation.md のモデル別料金に基づく。
"""

from typing import Any

from app.db.sqlite import sqlite_manager

# 料金テーブル: {provider: {model_prefix: (input_per_1M, output_per_1M)}}
# docs/14_cost_estimation.md ベース (USD)
PRICING: dict[str, dict[str, tuple[float, float]]] = {
    "anthropic": {
        "claude-opus-4": (15.00, 75.00),
        "claude-sonnet-4": (3.00, 15.00),
        "claude-haiku-4": (0.80, 4.00),
    },
    "openai": {
        "gpt-5.2": (15.00, 60.00),
        "gpt-5-mini": (1.50, 6.00),
        "gpt-5-nano": (0.05, 0.20),
        "gpt-5-codex": (15.00, 60.00),
        "gpt-5": (5.00, 30.00),
        "o3-pro": (20.00, 80.00),
        "o3": (10.00, 40.00),
        "o4-mini": (1.10, 4.40),
    },
    "google": {
        "gemini-3-pro": (3.50, 10.50),
        "gemini-3-flash": (0.50, 1.50),
        "gemini-2.5-pro": (2.50, 10.00),
        "gemini-2.5-flash": (0.075, 0.30),
    },
    "bedrock": {
        "anthropic.claude-opus-4": (15.00, 75.00),
        "anthropic.claude-sonnet-4": (3.00, 15.00),
        "anthropic.claude-haiku-4": (0.80, 4.00),
        "amazon.nova-premier": (2.50, 10.00),
        "amazon.nova-pro": (0.80, 3.20),
        "amazon.nova-lite": (0.06, 0.24),
        "amazon.nova-micro": (0.035, 0.14),
        "deepseek.r1": (2.00, 8.00),
    },
    "azure_foundry": {
        "gpt-5.2": (15.00, 60.00),
        "gpt-5-nano": (0.05, 0.20),
        "gpt-5": (5.00, 30.00),
        "claude-opus-4": (15.00, 75.00),
        "claude-sonnet-4": (3.00, 15.00),
        "claude-haiku-4": (0.80, 4.00),
    },
    "vertex_ai": {
        "gemini-3-pro": (3.50, 10.50),
        "gemini-3-flash": (0.50, 1.50),
        "gemini-2.5-pro": (2.50, 10.00),
        "gemini-2.5-flash": (0.075, 0.30),
    },
    "azure": {
        "gpt-4o-mini": (0.15, 0.60),
        "gpt-4o": (2.50, 10.00),
    },
    "ollama": {},
}


def calculate_cost(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
) -> float:
    """トークン使用量からコスト(USD)を算出する。

    Args:
        provider: LLMプロバイダー名
        model: モデルID
        input_tokens: 入力トークン数
        output_tokens: 出力トークン数

    Returns:
        推定コスト (USD)
    """
    if provider == "ollama":
        return 0.0

    provider_pricing = PRICING.get(provider, {})

    # モデルIDの前方一致で料金を検索
    input_rate, output_rate = 0.0, 0.0
    for prefix, (inp, outp) in provider_pricing.items():
        if model.startswith(prefix) or prefix in model:
            input_rate, output_rate = inp, outp
            break

    cost = (input_tokens / 1_000_000) * input_rate + (
        output_tokens / 1_000_000
    ) * output_rate
    return round(cost, 6)


def log_usage(
    provider: str,
    model: str,
    input_tokens: int,
    output_tokens: int,
    latency_ms: float = 0.0,
    request_type: str = "general",
    session_id: str | None = None,
    success: bool = True,
) -> int:
    """LLM使用ログを記録する。

    Args:
        provider: LLMプロバイダー名
        model: モデルID
        input_tokens: 入力トークン数
        output_tokens: 出力トークン数
        latency_ms: レイテンシ (ms)
        request_type: リクエスト種別 (general, analysis, investigation, document)
        session_id: セッションID
        success: 成功フラグ

    Returns:
        挿入されたレコードのID
    """
    cost = calculate_cost(provider, model, input_tokens, output_tokens)

    return sqlite_manager.insert(
        "llm_usage_log",
        {
            "provider": provider,
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "estimated_cost_usd": cost,
            "latency_ms": latency_ms,
            "request_type": request_type,
            "session_id": session_id,
            "success": success,
        },
    )


def get_summary(days: int = 30) -> dict[str, Any]:
    """指定期間のLLM使用状況サマリーを取得する。

    Args:
        days: 集計期間 (日数)

    Returns:
        使用状況サマリー
    """
    rows = sqlite_manager.execute(
        """
        SELECT
            COUNT(*) as total_requests,
            COALESCE(SUM(input_tokens), 0) as total_input_tokens,
            COALESCE(SUM(output_tokens), 0) as total_output_tokens,
            COALESCE(SUM(estimated_cost_usd), 0) as total_cost_usd,
            COALESCE(AVG(latency_ms), 0) as avg_latency_ms,
            SUM(CASE WHEN success = 1 THEN 1 ELSE 0 END) as success_count
        FROM llm_usage_log
        WHERE timestamp >= datetime('now', ?)
        """,
        (f"-{days} days",),
    )

    if not rows or rows[0]["total_requests"] == 0:
        return {
            "total_requests": 0,
            "total_input_tokens": 0,
            "total_output_tokens": 0,
            "total_cost_usd": 0.0,
            "avg_latency_ms": 0.0,
            "success_rate": 0.0,
            "by_provider": {},
            "by_request_type": {},
        }

    row = rows[0]
    total = row["total_requests"]

    # プロバイダー別集計
    provider_rows = sqlite_manager.execute(
        """
        SELECT
            provider,
            COUNT(*) as requests,
            SUM(input_tokens) as input_tokens,
            SUM(output_tokens) as output_tokens,
            SUM(estimated_cost_usd) as cost_usd
        FROM llm_usage_log
        WHERE timestamp >= datetime('now', ?)
        GROUP BY provider
        """,
        (f"-{days} days",),
    )

    by_provider = {
        r["provider"]: {
            "requests": r["requests"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cost_usd": round(r["cost_usd"], 4),
        }
        for r in provider_rows
    }

    # リクエスト種別集計
    type_rows = sqlite_manager.execute(
        """
        SELECT
            request_type,
            COUNT(*) as requests,
            SUM(estimated_cost_usd) as cost_usd
        FROM llm_usage_log
        WHERE timestamp >= datetime('now', ?)
        GROUP BY request_type
        """,
        (f"-{days} days",),
    )

    by_request_type = {
        r["request_type"]: {
            "requests": r["requests"],
            "cost_usd": round(r["cost_usd"], 4),
        }
        for r in type_rows
    }

    return {
        "total_requests": total,
        "total_input_tokens": row["total_input_tokens"],
        "total_output_tokens": row["total_output_tokens"],
        "total_cost_usd": round(row["total_cost_usd"], 4),
        "avg_latency_ms": round(row["avg_latency_ms"], 1),
        "success_rate": round(row["success_count"] / total * 100, 1) if total else 0.0,
        "by_provider": by_provider,
        "by_request_type": by_request_type,
    }


def get_daily_costs(days: int = 30) -> list[dict[str, Any]]:
    """日別LLMコスト推移を取得する。

    Args:
        days: 集計期間 (日数)

    Returns:
        日別コストリスト
    """
    rows = sqlite_manager.execute(
        """
        SELECT
            DATE(timestamp) as date,
            COUNT(*) as requests,
            SUM(input_tokens) as input_tokens,
            SUM(output_tokens) as output_tokens,
            SUM(estimated_cost_usd) as cost_usd
        FROM llm_usage_log
        WHERE timestamp >= datetime('now', ?)
        GROUP BY DATE(timestamp)
        ORDER BY date
        """,
        (f"-{days} days",),
    )

    return [
        {
            "date": r["date"],
            "requests": r["requests"],
            "input_tokens": r["input_tokens"],
            "output_tokens": r["output_tokens"],
            "cost_usd": round(r["cost_usd"], 4),
        }
        for r in rows
    ]
