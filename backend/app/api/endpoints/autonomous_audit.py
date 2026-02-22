"""自律型監査エージェント API エンドポイント。

- POST /start         — 非同期で分析開始 → session_id 返却
- POST /start/stream  — SSE ストリーミング付き分析開始
- GET  /{session_id}/status     — フェーズ進捗取得
- GET  /{session_id}/hypotheses — 仮説一覧 (HITL 用)
- POST /{session_id}/approve    — 仮説承認 (HITL 再開)
- GET  /{session_id}/insights   — インサイト一覧
- GET  /{session_id}/report     — エグゼクティブサマリー
- GET  /sessions                — セッション履歴
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field

from app.agents.autonomous import AutonomousAuditAgent
from app.agents.autonomous.state import AuditPhase, AutonomousAuditState
from app.agents.autonomous_tools import create_default_registry
from app.db import duckdb_manager

logger = logging.getLogger(__name__)

router = APIRouter()

# 実行中セッション状態のインメモリキャッシュ
_active_sessions: dict[str, AutonomousAuditState] = {}


# ------------------------------------------------------------------
# Request / Response Models
# ------------------------------------------------------------------


class StartRequest(BaseModel):
    fiscal_year: int = Field(..., description="分析対象年度")
    scope: dict[str, Any] = Field(default_factory=dict, description="分析スコープ")
    auto_approve: bool = Field(True, description="仮説を自動承認するか")


class StartResponse(BaseModel):
    session_id: str
    status: str = "started"


class ApproveRequest(BaseModel):
    hypothesis_ids: list[str] | None = Field(None, description="承認する仮説 ID (null=全承認)")
    feedback: str | None = Field(None, description="人間からのフィードバック")


class SessionStatusResponse(BaseModel):
    session_id: str
    fiscal_year: int
    current_phase: str
    status: str
    step_count: int = 0
    hypotheses_count: int = 0
    insights_count: int = 0
    tool_calls_count: int = 0
    started_at: str | None = None
    completed_at: str | None = None
    error: str | None = None


class HypothesisResponse(BaseModel):
    id: str
    title: str
    description: str
    rationale: str
    test_approach: str
    tools_to_use: list[str] = []
    priority: int = 1
    status: str = "pending"
    grounding_score: float = 0.0
    evidence_for: list[str] = []
    evidence_against: list[str] = []


class InsightResponse(BaseModel):
    id: str
    title: str
    description: str
    category: str
    severity: str
    affected_amount: float = 0
    affected_count: int = 0
    recommendations: list[str] = []
    related_hypotheses: list[str] = []
    grounding_score: float = 0.0


class ReportResponse(BaseModel):
    session_id: str
    fiscal_year: int
    executive_summary: str
    insights: list[InsightResponse] = []
    hypotheses: list[HypothesisResponse] = []
    total_tool_calls: int = 0
    started_at: str | None = None
    completed_at: str | None = None


class SessionListItem(BaseModel):
    session_id: str
    fiscal_year: int
    status: str
    current_phase: str
    total_insights: int = 0
    started_at: str | None = None
    completed_at: str | None = None


# ------------------------------------------------------------------
# Helper
# ------------------------------------------------------------------


def _create_agent() -> AutonomousAuditAgent:
    registry = create_default_registry()
    return AutonomousAuditAgent(registry=registry)


def _sse_event(data: dict[str, Any]) -> str:
    return f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"


# ------------------------------------------------------------------
# Endpoints
# ------------------------------------------------------------------


@router.post("/start", response_model=StartResponse)
async def start_audit(request: StartRequest) -> StartResponse:
    """自律型監査を非同期で開始する。"""
    agent = _create_agent()

    try:
        final_state = await agent.run(
            fiscal_year=request.fiscal_year,
            scope=request.scope,
            auto_approve=request.auto_approve,
        )

        session_id = final_state.get("session_id", "unknown")
        _active_sessions[session_id] = final_state

        status = "completed" if final_state.get("current_phase") == AuditPhase.COMPLETE else "error"
        return StartResponse(session_id=session_id, status=status)

    except Exception as e:
        logger.error("Failed to start autonomous audit: %s", str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/start/stream")
async def start_audit_stream(request: StartRequest) -> StreamingResponse:
    """SSE ストリーミング付きで自律型監査を開始する。"""
    agent = _create_agent()

    async def event_generator() -> AsyncGenerator[str, None]:
        yield _sse_event({"type": "start", "fiscal_year": request.fiscal_year})
        try:
            async for event in agent.run_stream(
                fiscal_year=request.fiscal_year,
                scope=request.scope,
                auto_approve=request.auto_approve,
            ):
                yield _sse_event(event)
        except Exception as e:
            logger.error("SSE streaming error: %s", str(e))
            yield _sse_event({"type": "error", "message": str(e)})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{session_id}/status", response_model=SessionStatusResponse)
async def get_session_status(session_id: str) -> SessionStatusResponse:
    """セッションのフェーズ進捗を取得する。"""
    # インメモリから取得
    if session_id in _active_sessions:
        state = _active_sessions[session_id]
        return SessionStatusResponse(
            session_id=session_id,
            fiscal_year=state.get("fiscal_year", 0),
            current_phase=state.get("current_phase", "unknown"),
            status="completed" if state.get("current_phase") == AuditPhase.COMPLETE else "running",
            step_count=state.get("step_count", 0),
            hypotheses_count=len(state.get("hypotheses", [])),
            insights_count=len(state.get("insights", [])),
            tool_calls_count=len(state.get("exploration_log", [])),
            started_at=state.get("started_at"),
            completed_at=state.get("completed_at"),
            error=state.get("error"),
        )

    # DB から取得
    try:
        rows = duckdb_manager.execute(
            """
            SELECT fiscal_year, current_phase, status,
                   total_hypotheses, total_insights, total_tool_calls,
                   started_at, completed_at
            FROM autonomous_audit_sessions
            WHERE session_id = ?
            """,
            [session_id],
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        row = rows[0]
        return SessionStatusResponse(
            session_id=session_id,
            fiscal_year=row[0],
            current_phase=row[1],
            status=row[2],
            hypotheses_count=row[3] or 0,
            insights_count=row[4] or 0,
            tool_calls_count=row[5] or 0,
            started_at=str(row[6]) if row[6] else None,
            completed_at=str(row[7]) if row[7] else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}/hypotheses", response_model=list[HypothesisResponse])
async def get_hypotheses(session_id: str) -> list[HypothesisResponse]:
    """セッションの仮説一覧を取得する。"""
    # インメモリ
    if session_id in _active_sessions:
        return [
            HypothesisResponse(**h)
            for h in _active_sessions[session_id].get("hypotheses", [])
        ]

    # DB
    try:
        rows = duckdb_manager.execute(
            "SELECT hypotheses FROM autonomous_audit_sessions WHERE session_id = ?",
            [session_id],
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        hypotheses = json.loads(rows[0][0]) if rows[0][0] else []
        return [HypothesisResponse(**h) for h in hypotheses]
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.post("/{session_id}/approve", response_model=StartResponse)
async def approve_hypotheses(session_id: str, request: ApproveRequest) -> StartResponse:
    """仮説を承認し、HITL 中断から再開する。"""
    if session_id not in _active_sessions:
        raise HTTPException(status_code=404, detail=f"Active session {session_id} not found")

    state = _active_sessions[session_id]
    if not state.get("awaiting_approval"):
        raise HTTPException(status_code=400, detail="Session is not awaiting approval")

    agent = _create_agent()

    try:
        final_state = await agent.resume_after_approval(
            state=state,
            approved_hypothesis_ids=request.hypothesis_ids,
            feedback=request.feedback,
        )
        _active_sessions[session_id] = final_state

        status = "completed" if final_state.get("current_phase") == AuditPhase.COMPLETE else "error"
        return StartResponse(session_id=session_id, status=status)
    except Exception as e:
        logger.error("Failed to resume session %s: %s", session_id, str(e))
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}/insights", response_model=list[InsightResponse])
async def get_insights(session_id: str) -> list[InsightResponse]:
    """セッションのインサイト一覧を取得する。"""
    # インメモリ
    if session_id in _active_sessions:
        return [
            InsightResponse(**i)
            for i in _active_sessions[session_id].get("insights", [])
        ]

    # DB
    try:
        rows = duckdb_manager.execute(
            """
            SELECT insight_id, title, description, category, severity,
                   grounding_score, affected_amount, affected_count,
                   recommendations
            FROM audit_insights
            WHERE session_id = ?
            ORDER BY severity, grounding_score DESC
            """,
            [session_id],
        )
        return [
            InsightResponse(
                id=r[0],
                title=r[1],
                description=r[2],
                category=r[3],
                severity=r[4],
                grounding_score=r[5] or 0.0,
                affected_amount=r[6] or 0,
                affected_count=r[7] or 0,
                recommendations=json.loads(r[8]) if r[8] else [],
            )
            for r in rows
        ]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/{session_id}/report", response_model=ReportResponse)
async def get_report(session_id: str) -> ReportResponse:
    """セッションの完全レポートを取得する。"""
    # インメモリ
    if session_id in _active_sessions:
        state = _active_sessions[session_id]
        return ReportResponse(
            session_id=session_id,
            fiscal_year=state.get("fiscal_year", 0),
            executive_summary=state.get("executive_summary", ""),
            insights=[InsightResponse(**i) for i in state.get("insights", [])],
            hypotheses=[HypothesisResponse(**h) for h in state.get("hypotheses", [])],
            total_tool_calls=len(state.get("exploration_log", [])),
            started_at=state.get("started_at"),
            completed_at=state.get("completed_at"),
        )

    # DB
    try:
        rows = duckdb_manager.execute(
            """
            SELECT fiscal_year, executive_summary, hypotheses,
                   total_tool_calls, started_at, completed_at
            FROM autonomous_audit_sessions
            WHERE session_id = ?
            """,
            [session_id],
        )
        if not rows:
            raise HTTPException(status_code=404, detail=f"Session {session_id} not found")

        row = rows[0]
        hypotheses = json.loads(row[2]) if row[2] else []

        # インサイトは別テーブルから取得
        insight_rows = duckdb_manager.execute(
            """
            SELECT insight_id, title, description, category, severity,
                   grounding_score, affected_amount, affected_count,
                   recommendations
            FROM audit_insights
            WHERE session_id = ?
            """,
            [session_id],
        )

        insights = [
            InsightResponse(
                id=r[0],
                title=r[1],
                description=r[2],
                category=r[3],
                severity=r[4],
                grounding_score=r[5] or 0.0,
                affected_amount=r[6] or 0,
                affected_count=r[7] or 0,
                recommendations=json.loads(r[8]) if r[8] else [],
            )
            for r in insight_rows
        ]

        return ReportResponse(
            session_id=session_id,
            fiscal_year=row[0],
            executive_summary=row[1] or "",
            insights=insights,
            hypotheses=[HypothesisResponse(**h) for h in hypotheses],
            total_tool_calls=row[3] or 0,
            started_at=str(row[4]) if row[4] else None,
            completed_at=str(row[5]) if row[5] else None,
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e


@router.get("/sessions", response_model=list[SessionListItem])
async def list_sessions(
    fiscal_year: int | None = None,
    limit: int = 20,
) -> list[SessionListItem]:
    """セッション履歴を取得する。"""
    try:
        query = """
            SELECT session_id, fiscal_year, status, current_phase,
                   total_insights, started_at, completed_at
            FROM autonomous_audit_sessions
        """
        params: list[Any] = []
        if fiscal_year:
            query += " WHERE fiscal_year = ?"
            params.append(fiscal_year)
        query += " ORDER BY started_at DESC LIMIT ?"
        params.append(limit)

        rows = duckdb_manager.execute(query, params)
        return [
            SessionListItem(
                session_id=r[0],
                fiscal_year=r[1],
                status=r[2],
                current_phase=r[3],
                total_insights=r[4] or 0,
                started_at=str(r[5]) if r[5] else None,
                completed_at=str(r[6]) if r[6] else None,
            )
            for r in rows
        ]
    except Exception:
        # テーブル未作成の場合は空リストを返す
        return []
