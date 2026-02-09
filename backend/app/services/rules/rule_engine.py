"""Rule execution engine.

Orchestrates the execution of audit rules against journal entry data.
"""

import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

import polars as pl

from app.db import DuckDBManager
from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleViolation,
)


@dataclass
class EngineResult:
    """Result of rule engine execution."""

    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    total_entries: int = 0
    total_rules: int = 0
    rules_executed: int = 0
    rules_failed: int = 0
    total_violations: int = 0
    violations_by_category: dict[str, int] = field(default_factory=dict)
    violations_by_severity: dict[str, int] = field(default_factory=dict)
    rule_results: list[RuleResult] = field(default_factory=list)
    all_violations: list[RuleViolation] = field(default_factory=list)
    execution_time_ms: float = 0.0

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
            "total_entries": self.total_entries,
            "total_rules": self.total_rules,
            "rules_executed": self.rules_executed,
            "rules_failed": self.rules_failed,
            "total_violations": self.total_violations,
            "violations_by_category": self.violations_by_category,
            "violations_by_severity": self.violations_by_severity,
            "execution_time_ms": round(self.execution_time_ms, 2),
            "rule_results": [r.to_dict() for r in self.rule_results],
        }


class RuleEngine:
    """Engine for executing audit rules.

    Features:
    - Register and manage audit rules
    - Execute rules in parallel
    - Aggregate and store results
    - Update risk scores
    """

    def __init__(
        self,
        db: DuckDBManager | None = None,
        max_workers: int = 4,
    ) -> None:
        """Initialize rule engine.

        Args:
            db: DuckDB manager instance.
            max_workers: Maximum parallel workers for rule execution.
        """
        self.db = db or DuckDBManager()
        self.max_workers = max_workers
        self._rule_sets: dict[str, RuleSet] = {}
        self._rules: dict[str, AuditRule] = {}

    def register_rule(self, rule: AuditRule) -> None:
        """Register a single rule.

        Args:
            rule: Rule to register.
        """
        self._rules[rule.rule_id] = rule

    def register_rule_set(self, rule_set: RuleSet) -> None:
        """Register a rule set.

        Args:
            rule_set: Rule set to register.
        """
        self._rule_sets[rule_set.name] = rule_set
        for rule in rule_set.rules:
            self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> AuditRule | None:
        """Get a rule by ID.

        Args:
            rule_id: Rule identifier.

        Returns:
            Rule if found, None otherwise.
        """
        return self._rules.get(rule_id)

    def get_rules_by_category(self, category: RuleCategory) -> list[AuditRule]:
        """Get all rules in a category.

        Args:
            category: Rule category.

        Returns:
            List of rules.
        """
        return [r for r in self._rules.values() if r.category == category]

    def get_enabled_rules(self) -> list[AuditRule]:
        """Get all enabled rules."""
        return [r for r in self._rules.values() if r.enabled]

    @property
    def rule_count(self) -> int:
        """Total number of registered rules."""
        return len(self._rules)

    def load_journal_entries(
        self,
        fiscal_year: int | None = None,
        business_unit_code: str | None = None,
        period: int | None = None,
        limit: int | None = None,
    ) -> pl.DataFrame:
        """Load journal entries from database.

        Args:
            fiscal_year: Filter by fiscal year.
            business_unit_code: Filter by business unit.
            period: Filter by accounting period.
            limit: Maximum rows to load.

        Returns:
            Polars DataFrame with journal entries.
        """
        conditions = []
        params = []

        if fiscal_year:
            conditions.append("fiscal_year = ?")
            params.append(fiscal_year)

        if business_unit_code:
            conditions.append("business_unit_code = ?")
            params.append(business_unit_code)

        if period:
            conditions.append("accounting_period = ?")
            params.append(period)

        where_clause = " AND ".join(conditions) if conditions else "1=1"
        limit_clause = f"LIMIT {limit}" if limit else ""

        query = f"""
            SELECT *
            FROM journal_entries
            WHERE {where_clause}
            {limit_clause}
        """

        return self.db.execute_df(query, params if params else None)

    def execute_rule(
        self,
        rule: AuditRule,
        df: pl.DataFrame,
    ) -> RuleResult:
        """Execute a single rule.

        Args:
            rule: Rule to execute.
            df: DataFrame with journal entries.

        Returns:
            Rule execution result.
        """
        start_time = time.perf_counter()

        try:
            result = rule.execute(df)
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return result
        except Exception as e:
            result = RuleResult(
                rule_id=rule.rule_id,
                rule_name=rule.rule_name,
                category=rule.category,
                error=str(e),
            )
            result.execution_time_ms = (time.perf_counter() - start_time) * 1000
            return result

    def execute_rules(
        self,
        df: pl.DataFrame,
        rules: list[AuditRule] | None = None,
        parallel: bool = True,
    ) -> EngineResult:
        """Execute multiple rules against data.

        Args:
            df: DataFrame with journal entries.
            rules: Rules to execute (all enabled if not specified).
            parallel: Execute rules in parallel.

        Returns:
            Engine execution result.
        """
        start_time = time.perf_counter()
        result = EngineResult()
        result.total_entries = len(df)

        # Get rules to execute
        if rules is None:
            rules = self.get_enabled_rules()
        result.total_rules = len(rules)

        # Execute rules
        if parallel and len(rules) > 1:
            rule_results = self._execute_parallel(rules, df)
        else:
            rule_results = [self.execute_rule(r, df) for r in rules]

        # Aggregate results
        for rule_result in rule_results:
            result.rule_results.append(rule_result)
            result.rules_executed += 1

            if rule_result.error:
                result.rules_failed += 1
            else:
                result.total_violations += rule_result.violations_found
                result.all_violations.extend(rule_result.violations)

                # Count by category
                cat = rule_result.category.value
                result.violations_by_category[cat] = (
                    result.violations_by_category.get(cat, 0)
                    + rule_result.violations_found
                )

                # Count by severity
                for v in rule_result.violations:
                    sev = v.severity.value
                    result.violations_by_severity[sev] = (
                        result.violations_by_severity.get(sev, 0) + 1
                    )

        result.completed_at = datetime.now()
        result.execution_time_ms = (time.perf_counter() - start_time) * 1000

        return result

    def _execute_parallel(
        self,
        rules: list[AuditRule],
        df: pl.DataFrame,
    ) -> list[RuleResult]:
        """Execute rules in parallel.

        Args:
            rules: Rules to execute.
            df: DataFrame with journal entries.

        Returns:
            List of rule results.
        """
        results = []

        with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
            futures = {
                executor.submit(self.execute_rule, rule, df): rule for rule in rules
            }

            for future in as_completed(futures):
                results.append(future.result())

        return results

    def execute_all(
        self,
        fiscal_year: int | None = None,
        business_unit_code: str | None = None,
        period: int | None = None,
        categories: list[RuleCategory] | None = None,
    ) -> EngineResult:
        """Execute all rules against database data.

        Args:
            fiscal_year: Filter by fiscal year.
            business_unit_code: Filter by business unit.
            period: Filter by accounting period.
            categories: Filter rules by categories.

        Returns:
            Engine execution result.
        """
        # Load data
        df = self.load_journal_entries(
            fiscal_year=fiscal_year,
            business_unit_code=business_unit_code,
            period=period,
        )

        # Get rules to execute
        rules = self.get_enabled_rules()
        if categories:
            rules = [r for r in rules if r.category in categories]

        # Execute rules
        return self.execute_rules(df, rules)

    def store_violations(
        self, violations: list[RuleViolation], batch_size: int = 50000
    ) -> int:
        """Store violations in database.

        Args:
            violations: List of violations to store.
            batch_size: Number of violations to insert per batch.

        Returns:
            Number of violations stored.
        """
        import json

        if not violations:
            return 0

        total_stored = 0

        # Process in batches for better performance
        for i in range(0, len(violations), batch_size):
            batch = violations[i : i + batch_size]

            # Convert to DataFrame with proper type handling
            records = []
            for v in batch:
                record = {
                    "gl_detail_id": str(v.gl_detail_id),
                    "journal_id": str(v.journal_id),
                    "rule_id": str(v.rule_id),
                    "rule_name": str(v.rule_name),
                    "category": str(v.category.value),
                    "severity": str(v.severity.value),
                    "message": str(v.message)[:500],  # Truncate to fit column
                    "violation_description": str(v.message)[:1000],
                    "details": json.dumps(v.details, ensure_ascii=False, default=str),
                    "score_impact": float(v.score_impact),
                    "created_at": v.detected_at.isoformat(),
                }
                records.append(record)

            df = pl.DataFrame(records)

            # Insert batch into database
            with self.db.connect() as conn:
                conn.register("violations_df", df.to_arrow())
                conn.execute("""
                    INSERT INTO rule_violations
                        (gl_detail_id, journal_id, rule_id, rule_name, category, severity,
                         message, violation_description, details, score_impact, created_at)
                    SELECT
                        gl_detail_id,
                        journal_id,
                        rule_id,
                        rule_name,
                        category,
                        severity,
                        message,
                        violation_description,
                        details,
                        score_impact,
                        created_at::TIMESTAMP
                    FROM violations_df
                """)

            total_stored += len(batch)

        return total_stored

    def update_risk_scores(self, violations: list[RuleViolation]) -> int:
        """Update risk scores for entries with violations.

        Args:
            violations: List of violations.

        Returns:
            Number of entries updated.
        """
        if not violations:
            return 0

        # Group violations by gl_detail_id
        scores: dict[str, float] = {}
        flags: dict[str, list[str]] = {}
        rules: dict[str, list[str]] = {}

        for v in violations:
            gl_id = v.gl_detail_id
            scores[gl_id] = scores.get(gl_id, 0) + v.score_impact
            flags.setdefault(gl_id, []).append(v.severity.value)
            rules.setdefault(gl_id, []).append(v.rule_id)

        # Update in batches
        updated = 0
        with self.db.connect() as conn:
            for gl_id, score in scores.items():
                # Cap score at 100
                capped_score = min(score, 100.0)
                flag_str = ",".join(sorted(set(flags[gl_id])))
                rule_str = ",".join(sorted(set(rules[gl_id])))

                conn.execute(
                    """
                    UPDATE journal_entries
                    SET
                        risk_score = ?,
                        anomaly_flags = ?,
                        rule_violations = ?
                    WHERE gl_detail_id = ?
                    """,
                    [capped_score, flag_str, rule_str, gl_id],
                )
                updated += 1

        return updated

    def get_violation_summary(
        self,
        fiscal_year: int | None = None,
    ) -> dict[str, Any]:
        """Get violation summary from database.

        Args:
            fiscal_year: Filter by fiscal year.

        Returns:
            Summary statistics.
        """
        where_clause = f"WHERE je.fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            SELECT
                v.rule_id,
                v.severity,
                COUNT(*) as count
            FROM rule_violations v
            JOIN journal_entries je ON v.gl_detail_id = je.gl_detail_id
            {where_clause}
            GROUP BY v.rule_id, v.severity
            ORDER BY count DESC
        """

        result = self.db.execute(query)

        by_rule: dict[str, int] = {}
        by_severity: dict[str, int] = {}

        for rule_id, severity, count in result:
            by_rule[rule_id] = by_rule.get(rule_id, 0) + count
            by_severity[severity] = by_severity.get(severity, 0) + count

        return {
            "by_rule": by_rule,
            "by_severity": by_severity,
            "total": sum(by_rule.values()),
        }
