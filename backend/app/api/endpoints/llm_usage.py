"""LLM Usage API endpoints.

LLMのトークン使用量・コスト追跡を提供するエンドポイント。
"""

from typing import Any

from fastapi import APIRouter, Query

from app.services.llm.cost_tracker import get_daily_costs, get_summary

router = APIRouter()


@router.get("/summary")
async def get_usage_summary(
    days: int = Query(30, ge=1, le=365, description="集計期間（日数）"),
) -> dict[str, Any]:
    """LLM使用状況サマリーを取得する。"""
    return get_summary(days)


@router.get("/daily")
async def get_daily_usage(
    days: int = Query(30, ge=1, le=365, description="集計期間（日数）"),
) -> dict[str, Any]:
    """日別LLMコスト推移を取得する。"""
    data = get_daily_costs(days)
    total_cost = sum(d["cost_usd"] for d in data)
    return {
        "daily": data,
        "total_cost_usd": round(total_cost, 4),
        "days": days,
    }
