"""Agent API endpoints.

Provides REST API access to AI agents:
- /agents/ask - Q&A with journal data (cached)
- /agents/ask/stream - Q&A with SSE streaming
- /agents/analyze - Risk analysis
- /agents/investigate - Deep-dive investigation
- /agents/document - Generate documentation
- /agents/review - Review findings
- /agents/workflow - Run multi-agent workflows
- /agents/cache/stats - Cache statistics
"""

import json
import logging
from collections.abc import AsyncGenerator
from typing import Any

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agents import (
    AgentOrchestrator,
    AnalysisAgent,
    DocumentationAgent,
    InvestigationAgent,
    ReviewAgent,
)
from app.core.cache import TTLCache, agent_cache

logger = logging.getLogger(__name__)

router = APIRouter()

# Lazy initialization of orchestrator
_orchestrator: AgentOrchestrator | None = None


def get_orchestrator() -> AgentOrchestrator:
    """Get or create orchestrator instance."""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = AgentOrchestrator()
    return _orchestrator


# Request/Response models
class AskRequest(BaseModel):
    """Request for Q&A endpoint."""

    question: str
    fiscal_year: int | None = None
    context: dict[str, Any] | None = None


class AskResponse(BaseModel):
    """Response from Q&A endpoint."""

    success: bool
    answer: str | None = None
    data: dict[str, Any] | None = None
    error: str | None = None


class AnalyzeRequest(BaseModel):
    """Request for analysis endpoint."""

    fiscal_year: int
    analysis_type: str = (
        "risk_distribution"  # risk_distribution, benford, period_comparison
    )
    account_prefix: str | None = None


class InvestigateRequest(BaseModel):
    """Request for investigation endpoint."""

    target_type: str  # entry, user, rule, journal
    target_id: str
    fiscal_year: int | None = None


class DocumentRequest(BaseModel):
    """Request for documentation endpoint."""

    fiscal_year: int
    doc_type: str = "summary"  # summary, finding, management_letter
    findings: list[dict[str, Any]] | None = None


class ReviewRequest(BaseModel):
    """Request for review endpoint."""

    fiscal_year: int
    review_type: str = "findings"  # findings, prioritize, remediation


class WorkflowRequest(BaseModel):
    """Request for workflow endpoint."""

    workflow_type: str  # full_audit, investigation, documentation
    fiscal_year: int | None = None
    parameters: dict[str, Any] | None = None


class AgentResponse(BaseModel):
    """Generic agent response."""

    success: bool
    workflow_id: str | None = None
    result: dict[str, Any] | None = None
    error: str | None = None


@router.post("/ask", response_model=AskResponse)
async def ask_question(request: AskRequest) -> AskResponse:
    """Ask a question about journal data.

    Uses the QA agent to answer questions about journal entries,
    risk scores, violations, and other audit-related queries.
    Responses are cached to reduce redundant LLM calls.
    """
    try:
        # キャッシュキーを生成
        cache_key = TTLCache._make_key(
            question=request.question,
            fiscal_year=request.fiscal_year,
            context=request.context,
        )

        # キャッシュヒットならそのまま返却
        cached = agent_cache.get(cache_key)
        if cached is not None:
            logger.debug("Cache hit for question: %s", request.question[:50])
            return AskResponse(**cached)

        orchestrator = get_orchestrator()
        context = request.context or {}
        if request.fiscal_year:
            context["fiscal_year"] = request.fiscal_year

        result = await orchestrator.run_qa_session(request.question, context)

        response = AskResponse(
            success=result.success,
            answer=result.final_output,
            data=result.agent_results.get("qa"),
            error=result.error,
        )

        # 成功レスポンスのみキャッシュ
        if response.success:
            agent_cache.set(cache_key, response.model_dump())

        return response
    except Exception as e:
        return AskResponse(
            success=False,
            error=str(e),
        )


async def _sse_ask_generator(
    question: str,
    context: dict[str, Any],
) -> AsyncGenerator[str, None]:
    """SSEイベントを生成するジェネレーター。

    イベント形式:
    - {"type": "start", "agent": "qa"}
    - {"type": "thinking", "content": "..."}
    - {"type": "chunk", "content": "..."}
    - {"type": "complete", "data": {...}}
    - {"type": "error", "message": "..."}
    """

    def sse_event(data: dict[str, Any]) -> str:
        return f"data: {json.dumps(data, ensure_ascii=False)}\n\n"

    try:
        yield sse_event({"type": "start", "agent": "qa"})

        yield sse_event({"type": "thinking", "content": "質問を分析しています..."})

        orchestrator = get_orchestrator()

        yield sse_event(
            {"type": "thinking", "content": "データベースを検索しています..."}
        )

        result = await orchestrator.run_qa_session(question, context)

        # 回答をチャンク分割して送信
        if result.final_output:
            content = result.final_output
            # 段落単位でチャンク化
            paragraphs = content.split("\n\n")
            for para in paragraphs:
                if para.strip():
                    yield sse_event({"type": "chunk", "content": para + "\n\n"})

        yield sse_event(
            {
                "type": "complete",
                "data": {
                    "success": result.success,
                    "answer": result.final_output,
                    "agent_results": result.agent_results.get("qa"),
                },
            }
        )

    except Exception as e:
        logger.error("SSE streaming error: %s", str(e))
        yield sse_event({"type": "error", "message": str(e)})


@router.post("/ask/stream")
async def ask_question_stream(request: AskRequest) -> StreamingResponse:
    """Ask a question with SSE streaming response.

    Returns Server-Sent Events (SSE) stream with progressive updates.
    """
    context = request.context or {}
    if request.fiscal_year:
        context["fiscal_year"] = request.fiscal_year

    return StreamingResponse(
        _sse_ask_generator(request.question, context),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@router.post("/analyze", response_model=AgentResponse)
async def run_analysis(request: AnalyzeRequest) -> AgentResponse:
    """Run risk analysis on journal data.

    Available analysis types:
    - risk_distribution: Analyze risk score distribution
    - benford: Analyze Benford's Law compliance
    - period_comparison: Compare metrics across periods
    """
    try:
        agent = AnalysisAgent()

        if request.analysis_type == "risk_distribution":
            result = await agent.analyze_risk_distribution(request.fiscal_year)
        elif request.analysis_type == "benford":
            result = await agent.analyze_benford_compliance(request.fiscal_year)
        elif request.analysis_type == "period_comparison":
            result = await agent.compare_periods(
                request.fiscal_year,
                request.account_prefix,
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown analysis type: {request.analysis_type}",
            )

        return AgentResponse(
            success=True,
            result=result,
        )
    except HTTPException:
        raise
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e),
        )


@router.post("/investigate", response_model=AgentResponse)
async def run_investigation(request: InvestigateRequest) -> AgentResponse:
    """Run investigation on specific target.

    Target types:
    - entry: Investigate specific journal entry
    - user: Investigate user activity
    - rule: Investigate rule violations
    - journal: Trace transaction flow
    """
    try:
        agent = InvestigationAgent()

        if request.target_type == "entry":
            result = await agent.investigate_entry(request.target_id)
        elif request.target_type == "user":
            result = await agent.investigate_user(
                request.target_id,
                request.fiscal_year,
            )
        elif request.target_type == "rule":
            result = await agent.investigate_rule_violation(
                request.target_id,
                request.fiscal_year,
            )
        elif request.target_type == "journal":
            result = await agent.trace_transaction_flow(request.target_id)
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown target type: {request.target_type}",
            )

        return AgentResponse(
            success=True,
            result=result,
        )
    except HTTPException:
        raise
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e),
        )


@router.post("/document", response_model=AgentResponse)
async def generate_documentation(request: DocumentRequest) -> AgentResponse:
    """Generate audit documentation.

    Document types:
    - summary: Summary report of all findings
    - finding: Detailed finding report
    - management_letter: Draft management letter
    """
    try:
        agent = DocumentationAgent()

        if request.doc_type == "summary":
            result = await agent.generate_summary_report(request.fiscal_year)
        elif request.doc_type == "finding":
            result = await agent.generate_finding_report(request.fiscal_year)
        elif request.doc_type == "management_letter":
            result = await agent.draft_management_letter(
                request.fiscal_year,
                request.findings or [],
            )
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown document type: {request.doc_type}",
            )

        return AgentResponse(
            success=True,
            result=result,
        )
    except HTTPException:
        raise
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e),
        )


@router.post("/review", response_model=AgentResponse)
async def run_review(request: ReviewRequest) -> AgentResponse:
    """Review audit findings.

    Review types:
    - findings: Review all findings
    - prioritize: Prioritize findings
    - remediation: Suggest remediation actions
    """
    try:
        agent = ReviewAgent()

        if request.review_type == "findings":
            result = await agent.review_findings(request.fiscal_year)
        elif request.review_type == "prioritize":
            result = await agent.prioritize_findings(request.fiscal_year)
        elif request.review_type == "remediation":
            result = await agent.suggest_remediation("high_risk")
        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown review type: {request.review_type}",
            )

        return AgentResponse(
            success=True,
            result=result,
        )
    except HTTPException:
        raise
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e),
        )


@router.post("/workflow", response_model=AgentResponse)
async def run_workflow(request: WorkflowRequest) -> AgentResponse:
    """Run a multi-agent workflow.

    Workflow types:
    - full_audit: Complete audit workflow
    - investigation: Investigation workflow
    - documentation: Documentation workflow
    """
    try:
        orchestrator = get_orchestrator()
        params = request.parameters or {}

        if request.workflow_type == "full_audit":
            if not request.fiscal_year:
                raise HTTPException(
                    status_code=400,
                    detail="fiscal_year is required for full_audit workflow",
                )
            result = await orchestrator.run_full_audit_workflow(request.fiscal_year)

        elif request.workflow_type == "investigation":
            if "target_type" not in params or "target_id" not in params:
                raise HTTPException(
                    status_code=400,
                    detail="target_type and target_id are required for investigation workflow",
                )
            result = await orchestrator.run_investigation_workflow(
                params["target_type"],
                params["target_id"],
                request.fiscal_year,
            )

        elif request.workflow_type == "documentation":
            if not request.fiscal_year:
                raise HTTPException(
                    status_code=400,
                    detail="fiscal_year is required for documentation workflow",
                )
            result = await orchestrator.run_documentation_workflow(
                request.fiscal_year,
                params.get("doc_type", "summary"),
                params.get("findings"),
            )

        else:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown workflow type: {request.workflow_type}",
            )

        return AgentResponse(
            success=result.success,
            workflow_id=result.workflow_id,
            result=result.to_dict(),
            error=result.error,
        )
    except HTTPException:
        raise
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e),
        )


@router.get("/workflows")
async def list_workflows() -> list[dict[str, str]]:
    """List available workflows."""
    orchestrator = get_orchestrator()
    return orchestrator.get_available_workflows()


@router.post("/route")
async def route_request(request: AskRequest) -> AgentResponse:
    """Automatically route a request to the appropriate agent.

    The orchestrator analyzes the request and routes it to the
    most suitable agent based on the content.
    """
    try:
        orchestrator = get_orchestrator()
        context = request.context or {}
        if request.fiscal_year:
            context["fiscal_year"] = request.fiscal_year

        result = await orchestrator.route_request(request.question, context)

        return AgentResponse(
            success=result.success,
            workflow_id=result.workflow_id,
            result=result.to_dict(),
            error=result.error,
        )
    except Exception as e:
        return AgentResponse(
            success=False,
            error=str(e),
        )


@router.get("/cache/stats")
async def cache_stats() -> dict[str, int]:
    """Return agent response cache statistics."""
    return agent_cache.stats


@router.post("/cache/clear")
async def cache_clear() -> dict[str, str]:
    """Clear agent response cache."""
    agent_cache.clear()
    return {"status": "cleared"}
