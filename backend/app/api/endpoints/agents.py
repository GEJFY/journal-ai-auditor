"""Agent API endpoints.

Provides REST API access to AI agents:
- /agents/ask - Q&A with journal data
- /agents/analyze - Risk analysis
- /agents/investigate - Deep-dive investigation
- /agents/document - Generate documentation
- /agents/review - Review findings
- /agents/workflow - Run multi-agent workflows
"""

from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.agents import (
    AgentOrchestrator,
    AnalysisAgent,
    DocumentationAgent,
    InvestigationAgent,
    ReviewAgent,
)

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
    analysis_type: str = "risk_distribution"  # risk_distribution, benford, period_comparison
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
    """
    try:
        orchestrator = get_orchestrator()
        context = request.context or {}
        if request.fiscal_year:
            context["fiscal_year"] = request.fiscal_year

        result = await orchestrator.run_qa_session(request.question, context)

        return AskResponse(
            success=result.success,
            answer=result.final_output,
            data=result.agent_results.get("qa"),
            error=result.error,
        )
    except Exception as e:
        return AskResponse(
            success=False,
            error=str(e),
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
