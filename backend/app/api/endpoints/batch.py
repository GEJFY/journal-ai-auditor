"""Batch processing API endpoints.

Provides REST API for:
- Starting batch analysis jobs
- Monitoring job status
- Retrieving batch results
"""

from typing import Any

from fastapi import APIRouter, BackgroundTasks, HTTPException
from pydantic import BaseModel

from app.services.batch import (
    BatchConfig,
    BatchMode,
    BatchOrchestrator,
    BatchScheduler,
)

router = APIRouter()

# Global scheduler instance
_scheduler: BatchScheduler | None = None


def get_scheduler() -> BatchScheduler:
    """Get or create scheduler instance."""
    global _scheduler
    if _scheduler is None:
        _scheduler = BatchScheduler()
    return _scheduler


class BatchJobRequest(BaseModel):
    """Request to start a batch job."""

    mode: str = "full"  # full, quick, ml_only, rules_only
    fiscal_year: int | None = None
    business_unit_code: str | None = None
    accounting_period: int | None = None
    update_aggregations: bool = True


class BatchJobResponse(BaseModel):
    """Response with batch job information."""

    job_id: str
    status: str
    message: str


class BatchStatusResponse(BaseModel):
    """Response with batch job status."""

    job_id: str
    status: str
    mode: str
    started_at: str
    completed_at: str | None = None
    total_entries: int = 0
    rules_executed: int = 0
    total_violations: int = 0
    execution_time_ms: float = 0.0
    success: bool = False
    errors: list[str] = []


class RuleSummaryResponse(BaseModel):
    """Response with rule summary."""

    total_rules: int
    enabled_rules: int
    by_category: dict[str, Any]


@router.post("/start", response_model=BatchJobResponse)
async def start_batch_job(
    request: BatchJobRequest,
    background_tasks: BackgroundTasks,
) -> BatchJobResponse:
    """Start a new batch analysis job.

    Batch modes:
    - full: Run all rules and ML detection
    - quick: Run critical rules only
    - ml_only: Run ML anomaly detection only
    - rules_only: Run rule-based detection only

    Args:
        request: Batch job configuration.

    Returns:
        Job ID and status.
    """
    scheduler = get_scheduler()

    try:
        mode = BatchMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}. Valid modes: full, quick, ml_only, rules_only",
        )

    if not request.fiscal_year:
        raise HTTPException(
            status_code=400,
            detail="fiscal_year is required",
        )

    # Start job based on mode
    if mode == BatchMode.FULL:
        job_id = scheduler.schedule_full_analysis(request.fiscal_year)
    elif mode == BatchMode.QUICK:
        job_id = scheduler.schedule_quick_check(
            request.fiscal_year,
            request.accounting_period,
        )
    elif mode == BatchMode.ML_ONLY:
        job_id = scheduler.schedule_ml_analysis(request.fiscal_year)
    else:
        # Run custom configuration
        orchestrator = scheduler.orchestrator
        config = BatchConfig(
            mode=mode,
            fiscal_year=request.fiscal_year,
            business_unit_code=request.business_unit_code,
            accounting_period=request.accounting_period,
            update_aggregations=request.update_aggregations,
        )
        result = orchestrator.execute(config)
        scheduler._jobs[result.batch_id] = result
        job_id = result.batch_id

    return BatchJobResponse(
        job_id=job_id,
        status="started",
        message=f"Batch job started with mode: {request.mode}",
    )


@router.get("/status/{job_id}", response_model=BatchStatusResponse)
async def get_job_status(job_id: str) -> BatchStatusResponse:
    """Get status of a batch job.

    Args:
        job_id: Batch job ID.

    Returns:
        Job status and statistics.
    """
    scheduler = get_scheduler()
    result = scheduler.get_job_result(job_id)

    if not result:
        raise HTTPException(
            status_code=404,
            detail=f"Job not found: {job_id}",
        )

    return BatchStatusResponse(
        job_id=result.batch_id,
        status="completed" if result.completed_at else "running",
        mode=result.mode.value,
        started_at=result.started_at.isoformat(),
        completed_at=result.completed_at.isoformat() if result.completed_at else None,
        total_entries=result.total_entries,
        rules_executed=result.rules_executed,
        total_violations=result.total_violations,
        execution_time_ms=result.execution_time_ms,
        success=result.success,
        errors=result.errors,
    )


@router.get("/jobs", response_model=list[dict[str, Any]])
async def list_recent_jobs(limit: int = 10) -> list[dict[str, Any]]:
    """List recent batch jobs.

    Args:
        limit: Maximum jobs to return.

    Returns:
        List of recent job summaries.
    """
    scheduler = get_scheduler()
    return scheduler.get_recent_jobs(limit)


@router.get("/rules", response_model=RuleSummaryResponse)
async def get_rule_summary() -> RuleSummaryResponse:
    """Get summary of registered rules.

    Returns:
        Rule counts by category.
    """
    scheduler = get_scheduler()
    summary = scheduler.orchestrator.get_rule_summary()

    return RuleSummaryResponse(
        total_rules=summary["total_rules"],
        enabled_rules=summary["enabled_rules"],
        by_category=summary["by_category"],
    )


@router.post("/run-sync")
async def run_batch_sync(request: BatchJobRequest) -> dict[str, Any]:
    """Run batch job synchronously and return results.

    Warning: This may take a long time for large datasets.
    Consider using /start for async execution.

    Args:
        request: Batch job configuration.

    Returns:
        Complete batch results.
    """
    if not request.fiscal_year:
        raise HTTPException(
            status_code=400,
            detail="fiscal_year is required",
        )

    try:
        mode = BatchMode(request.mode)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid mode: {request.mode}",
        )

    orchestrator = BatchOrchestrator()
    config = BatchConfig(
        mode=mode,
        fiscal_year=request.fiscal_year,
        business_unit_code=request.business_unit_code,
        accounting_period=request.accounting_period,
        update_aggregations=request.update_aggregations,
    )

    result = orchestrator.execute(config)
    return result.to_dict()
