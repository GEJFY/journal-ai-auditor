"""Batch orchestration service.

Coordinates the execution of:
1. Data import and validation
2. Rule execution (53 rules total)
3. ML anomaly detection (5 methods)
4. Benford's Law analysis (5 checks)
5. Risk scoring
6. Aggregation table updates
7. Report generation triggers

Execution modes:
- Full: Run all rules and analysis
- Incremental: Run on new/modified entries only
- Quick: Run critical rules only
- ML-only: Run ML detection only
"""

import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Optional

import polars as pl

from app.db import DuckDBManager
from app.services.aggregation import AggregationService
from app.services.rules.base import RuleCategory
from app.services.rules.rule_engine import RuleEngine, EngineResult
from app.services.rules.scoring import RiskScoringService, ScoringConfig
from app.services.rules.amount_rules import create_amount_rule_set
from app.services.rules.time_rules import create_time_rule_set
from app.services.rules.account_rules import create_account_rule_set
from app.services.rules.approval_rules import create_approval_rule_set
from app.services.rules.ml_detection import create_ml_rule_set
from app.services.rules.benford import create_benford_rule_set


class BatchMode(str, Enum):
    """Batch execution mode."""

    FULL = "full"           # Run all rules
    INCREMENTAL = "incremental"  # New/modified entries only
    QUICK = "quick"         # Critical rules only
    ML_ONLY = "ml_only"     # ML detection only
    RULES_ONLY = "rules_only"  # Rules without ML


@dataclass
class BatchConfig:
    """Configuration for batch execution."""

    mode: BatchMode = BatchMode.FULL
    fiscal_year: Optional[int] = None
    business_unit_code: Optional[str] = None
    accounting_period: Optional[int] = None
    parallel_execution: bool = True
    max_workers: int = 4
    update_aggregations: bool = True
    store_violations: bool = True
    update_risk_scores: bool = True
    categories: Optional[list[RuleCategory]] = None


@dataclass
class BatchResult:
    """Result of batch execution."""

    batch_id: str
    mode: BatchMode
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: Optional[datetime] = None
    total_entries: int = 0
    rules_executed: int = 0
    rules_failed: int = 0
    total_violations: int = 0
    violations_by_severity: dict[str, int] = field(default_factory=dict)
    violations_by_category: dict[str, int] = field(default_factory=dict)
    scoring_completed: bool = False
    entries_scored: int = 0
    aggregations_updated: int = 0
    execution_time_ms: float = 0.0
    phase_timings: dict[str, float] = field(default_factory=dict)
    errors: list[str] = field(default_factory=list)

    @property
    def success(self) -> bool:
        """Check if batch completed successfully."""
        return len(self.errors) == 0 and self.completed_at is not None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "batch_id": self.batch_id,
            "mode": self.mode.value,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "success": self.success,
            "total_entries": self.total_entries,
            "rules_executed": self.rules_executed,
            "rules_failed": self.rules_failed,
            "total_violations": self.total_violations,
            "violations_by_severity": self.violations_by_severity,
            "violations_by_category": self.violations_by_category,
            "scoring_completed": self.scoring_completed,
            "entries_scored": self.entries_scored,
            "aggregations_updated": self.aggregations_updated,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "phase_timings": {k: round(v, 2) for k, v in self.phase_timings.items()},
            "errors": self.errors,
        }


class BatchOrchestrator:
    """Orchestrates batch rule execution and analysis."""

    def __init__(
        self,
        db: Optional[DuckDBManager] = None,
    ) -> None:
        """Initialize batch orchestrator.

        Args:
            db: DuckDB manager instance.
        """
        self.db = db or DuckDBManager()
        self.rule_engine = RuleEngine(db=self.db)
        self.scoring_service = RiskScoringService(db=self.db)
        self.aggregation_service = AggregationService(db=self.db)

        # Register all rule sets
        self._register_rule_sets()

    def _register_rule_sets(self) -> None:
        """Register all rule sets with the engine."""
        self.rule_engine.register_rule_set(create_amount_rule_set())
        self.rule_engine.register_rule_set(create_time_rule_set())
        self.rule_engine.register_rule_set(create_account_rule_set())
        self.rule_engine.register_rule_set(create_approval_rule_set())
        self.rule_engine.register_rule_set(create_ml_rule_set())
        self.rule_engine.register_rule_set(create_benford_rule_set())

    def execute(
        self,
        config: Optional[BatchConfig] = None,
    ) -> BatchResult:
        """Execute batch processing.

        Args:
            config: Batch configuration.

        Returns:
            BatchResult with execution details.
        """
        import uuid
        config = config or BatchConfig()
        result = BatchResult(
            batch_id=str(uuid.uuid4()),
            mode=config.mode,
        )

        start_time = time.perf_counter()

        try:
            # Phase 1: Load data
            phase_start = time.perf_counter()
            df = self._load_data(config)
            result.total_entries = len(df)
            result.phase_timings["load_data"] = (time.perf_counter() - phase_start) * 1000

            if len(df) == 0:
                result.completed_at = datetime.now()
                result.execution_time_ms = (time.perf_counter() - start_time) * 1000
                return result

            # Phase 2: Execute rules
            phase_start = time.perf_counter()
            rules = self._get_rules_for_mode(config)
            engine_result = self.rule_engine.execute_rules(
                df=df,
                rules=rules,
                parallel=config.parallel_execution,
            )
            result.rules_executed = engine_result.rules_executed
            result.rules_failed = engine_result.rules_failed
            result.total_violations = engine_result.total_violations
            result.violations_by_severity = engine_result.violations_by_severity
            result.violations_by_category = engine_result.violations_by_category
            result.phase_timings["rule_execution"] = (time.perf_counter() - phase_start) * 1000

            # Phase 3: Store violations
            if config.store_violations and engine_result.all_violations:
                phase_start = time.perf_counter()
                self.rule_engine.store_violations(engine_result.all_violations)
                result.phase_timings["store_violations"] = (time.perf_counter() - phase_start) * 1000

            # Phase 4: Calculate and update risk scores
            if config.update_risk_scores and engine_result.all_violations:
                phase_start = time.perf_counter()
                scores = self.scoring_service.score_violations(engine_result.all_violations)
                self.scoring_service.update_database_scores(scores)
                result.scoring_completed = True
                result.entries_scored = len(scores)
                result.phase_timings["scoring"] = (time.perf_counter() - phase_start) * 1000

            # Phase 5: Update aggregations
            if config.update_aggregations:
                phase_start = time.perf_counter()
                agg_results = self.aggregation_service.update_all(config.fiscal_year)
                result.aggregations_updated = sum(1 for r in agg_results if r.success)
                result.phase_timings["aggregations"] = (time.perf_counter() - phase_start) * 1000

            result.completed_at = datetime.now()

        except Exception as e:
            result.errors.append(str(e))
            result.completed_at = datetime.now()

        result.execution_time_ms = (time.perf_counter() - start_time) * 1000
        return result

    def _load_data(self, config: BatchConfig) -> pl.DataFrame:
        """Load data for batch processing.

        Args:
            config: Batch configuration.

        Returns:
            DataFrame with journal entries.
        """
        return self.rule_engine.load_journal_entries(
            fiscal_year=config.fiscal_year,
            business_unit_code=config.business_unit_code,
            period=config.accounting_period,
        )

    def _get_rules_for_mode(self, config: BatchConfig):
        """Get rules based on execution mode.

        Args:
            config: Batch configuration.

        Returns:
            List of rules to execute.
        """
        all_rules = self.rule_engine.get_enabled_rules()

        if config.mode == BatchMode.FULL:
            rules = all_rules
        elif config.mode == BatchMode.QUICK:
            # Critical rules only (approval and high-severity)
            rules = [r for r in all_rules if r.category in [
                RuleCategory.APPROVAL,
            ] or r.default_severity.value in ["critical", "high"]]
        elif config.mode == BatchMode.ML_ONLY:
            rules = [r for r in all_rules if r.category == RuleCategory.ML]
        elif config.mode == BatchMode.RULES_ONLY:
            rules = [r for r in all_rules if r.category != RuleCategory.ML]
        else:
            rules = all_rules

        # Filter by categories if specified
        if config.categories:
            rules = [r for r in rules if r.category in config.categories]

        return rules

    def get_status(self, batch_id: str) -> Optional[dict[str, Any]]:
        """Get status of a batch job.

        Args:
            batch_id: Batch ID to check.

        Returns:
            Status dictionary or None if not found.
        """
        # In a full implementation, this would track batch jobs
        # For now, return None as we don't persist batch status
        return None

    def get_rule_summary(self) -> dict[str, Any]:
        """Get summary of registered rules.

        Returns:
            Summary by category.
        """
        rules = self.rule_engine._rules.values()

        by_category = {}
        for rule in rules:
            cat = rule.category.value
            if cat not in by_category:
                by_category[cat] = {"count": 0, "rules": []}
            by_category[cat]["count"] += 1
            by_category[cat]["rules"].append({
                "id": rule.rule_id,
                "name": rule.rule_name,
                "severity": rule.default_severity.value,
                "enabled": rule.enabled,
            })

        return {
            "total_rules": len(rules),
            "enabled_rules": len([r for r in rules if r.enabled]),
            "by_category": by_category,
        }


class BatchScheduler:
    """Schedule and manage batch jobs."""

    def __init__(
        self,
        orchestrator: Optional[BatchOrchestrator] = None,
    ) -> None:
        """Initialize batch scheduler.

        Args:
            orchestrator: Batch orchestrator instance.
        """
        self.orchestrator = orchestrator or BatchOrchestrator()
        self._jobs: dict[str, BatchResult] = {}

    def schedule_full_analysis(
        self,
        fiscal_year: int,
    ) -> str:
        """Schedule a full analysis job.

        Args:
            fiscal_year: Fiscal year to analyze.

        Returns:
            Batch job ID.
        """
        config = BatchConfig(
            mode=BatchMode.FULL,
            fiscal_year=fiscal_year,
        )
        result = self.orchestrator.execute(config)
        self._jobs[result.batch_id] = result
        return result.batch_id

    def schedule_quick_check(
        self,
        fiscal_year: int,
        period: Optional[int] = None,
    ) -> str:
        """Schedule a quick check job.

        Args:
            fiscal_year: Fiscal year.
            period: Accounting period (optional).

        Returns:
            Batch job ID.
        """
        config = BatchConfig(
            mode=BatchMode.QUICK,
            fiscal_year=fiscal_year,
            accounting_period=period,
            update_aggregations=False,
        )
        result = self.orchestrator.execute(config)
        self._jobs[result.batch_id] = result
        return result.batch_id

    def schedule_ml_analysis(
        self,
        fiscal_year: int,
    ) -> str:
        """Schedule ML-only analysis.

        Args:
            fiscal_year: Fiscal year.

        Returns:
            Batch job ID.
        """
        config = BatchConfig(
            mode=BatchMode.ML_ONLY,
            fiscal_year=fiscal_year,
        )
        result = self.orchestrator.execute(config)
        self._jobs[result.batch_id] = result
        return result.batch_id

    def get_job_result(self, job_id: str) -> Optional[BatchResult]:
        """Get result of a scheduled job.

        Args:
            job_id: Job ID.

        Returns:
            BatchResult or None if not found.
        """
        return self._jobs.get(job_id)

    def get_recent_jobs(self, limit: int = 10) -> list[dict[str, Any]]:
        """Get recent job results.

        Args:
            limit: Maximum jobs to return.

        Returns:
            List of job summaries.
        """
        sorted_jobs = sorted(
            self._jobs.values(),
            key=lambda x: x.started_at,
            reverse=True,
        )
        return [job.to_dict() for job in sorted_jobs[:limit]]
