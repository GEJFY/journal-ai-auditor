"""Integrated risk scoring service.

Combines rule violations, ML anomaly scores, and Benford analysis
into a unified risk score for each journal entry.

Scoring methodology:
1. Base score starts at 0 (no risk)
2. Each violation adds points based on severity
3. ML anomaly detection adds additional points
4. Benford violations add global risk factor
5. Score is capped at 100

Risk categories:
- Critical (80-100): Immediate investigation required
- High (60-79): Priority review needed
- Medium (40-59): Standard review
- Low (20-39): Minor concerns
- Minimal (0-19): Normal
"""

from dataclasses import dataclass, field
from typing import Any

import polars as pl

from app.db import DuckDBManager
from app.services.rules.base import (
    RuleCategory,
    RuleSeverity,
    RuleViolation,
)


@dataclass
class RiskScore:
    """Risk score for a journal entry."""

    gl_detail_id: str
    journal_id: str
    total_score: float = 0.0
    rule_score: float = 0.0
    ml_score: float = 0.0
    benford_score: float = 0.0
    category_scores: dict[str, float] = field(default_factory=dict)
    violation_count: int = 0
    violations: list[str] = field(default_factory=list)
    severity_level: str = "minimal"
    requires_review: bool = False

    @property
    def risk_category(self) -> str:
        """Get risk category based on score."""
        if self.total_score >= 80:
            return "critical"
        elif self.total_score >= 60:
            return "high"
        elif self.total_score >= 40:
            return "medium"
        elif self.total_score >= 20:
            return "low"
        else:
            return "minimal"

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "gl_detail_id": self.gl_detail_id,
            "journal_id": self.journal_id,
            "total_score": round(self.total_score, 2),
            "rule_score": round(self.rule_score, 2),
            "ml_score": round(self.ml_score, 2),
            "benford_score": round(self.benford_score, 2),
            "category_scores": {
                k: round(v, 2) for k, v in self.category_scores.items()
            },
            "violation_count": self.violation_count,
            "violations": self.violations,
            "severity_level": self.severity_level,
            "risk_category": self.risk_category,
            "requires_review": self.requires_review,
        }


@dataclass
class ScoringConfig:
    """Configuration for risk scoring."""

    # Severity weights
    severity_weights: dict[str, float] = field(
        default_factory=lambda: {
            "critical": 25.0,
            "high": 15.0,
            "medium": 10.0,
            "low": 5.0,
            "info": 0.0,
        }
    )

    # Category weights (multipliers)
    category_weights: dict[str, float] = field(
        default_factory=lambda: {
            "amount": 1.0,
            "time": 1.0,
            "account": 1.0,
            "approval": 1.5,  # Approval violations are more serious
            "description": 0.8,
            "pattern": 1.0,
            "trend": 0.9,
            "ml": 1.2,
        }
    )

    # ML score weight
    ml_weight: float = 1.0

    # Benford global risk factor
    benford_weight: float = 0.5

    # Maximum score cap
    max_score: float = 100.0

    # Review thresholds
    auto_review_threshold: float = 60.0
    critical_threshold: float = 80.0


class RiskScoringService:
    """Service for calculating integrated risk scores."""

    def __init__(
        self,
        db: DuckDBManager | None = None,
        config: ScoringConfig | None = None,
    ) -> None:
        """Initialize scoring service.

        Args:
            db: DuckDB manager instance.
            config: Scoring configuration.
        """
        self.db = db or DuckDBManager()
        self.config = config or ScoringConfig()

    def calculate_score(
        self,
        violations: list[RuleViolation],
        ml_score: float = 0.0,
        benford_risk: float = 0.0,
    ) -> float:
        """Calculate total risk score from violations.

        Args:
            violations: List of violations for an entry.
            ml_score: ML anomaly score (0-1 range).
            benford_risk: Benford violation risk (0-1 range).

        Returns:
            Total risk score (0-100).
        """
        total = 0.0

        # Sum up violation scores
        for v in violations:
            base_score = self.config.severity_weights.get(
                v.severity.value, self.config.severity_weights.get("medium", 10.0)
            )

            # Apply category weight
            category_weight = self.config.category_weights.get(v.category.value, 1.0)

            # Use custom score impact if provided
            if v.score_impact > 0:
                total += v.score_impact * category_weight
            else:
                total += base_score * category_weight

        # Add ML score contribution
        total += ml_score * 20.0 * self.config.ml_weight

        # Add Benford risk contribution
        total += benford_risk * 10.0 * self.config.benford_weight

        # Cap at maximum
        return min(total, self.config.max_score)

    def score_violations(
        self,
        violations: list[RuleViolation],
    ) -> dict[str, RiskScore]:
        """Calculate risk scores for all entries with violations.

        Args:
            violations: List of all violations.

        Returns:
            Dictionary mapping gl_detail_id to RiskScore.
        """
        scores: dict[str, RiskScore] = {}

        # Group violations by entry
        for v in violations:
            if v.gl_detail_id not in scores:
                scores[v.gl_detail_id] = RiskScore(
                    gl_detail_id=v.gl_detail_id,
                    journal_id=v.journal_id,
                )

            score = scores[v.gl_detail_id]
            score.violations.append(v.rule_id)
            score.violation_count += 1

            # Track category scores
            cat = v.category.value
            if cat not in score.category_scores:
                score.category_scores[cat] = 0.0

            # Calculate contribution
            base_score = self.config.severity_weights.get(v.severity.value, 10.0)
            category_weight = self.config.category_weights.get(cat, 1.0)

            contribution = (
                v.score_impact if v.score_impact > 0 else base_score
            ) * category_weight
            score.category_scores[cat] += contribution

            # Track specific score types
            if v.category == RuleCategory.ML:
                score.ml_score += contribution
            elif v.category == RuleCategory.PATTERN:
                score.benford_score += contribution
            else:
                score.rule_score += contribution

            # Update severity level
            if v.severity == RuleSeverity.CRITICAL:
                score.severity_level = "critical"
            elif v.severity == RuleSeverity.HIGH and score.severity_level not in [
                "critical"
            ]:
                score.severity_level = "high"
            elif v.severity == RuleSeverity.MEDIUM and score.severity_level not in [
                "critical",
                "high",
            ]:
                score.severity_level = "medium"

        # Calculate total scores
        for score in scores.values():
            score.total_score = min(
                sum(score.category_scores.values()), self.config.max_score
            )
            score.requires_review = (
                score.total_score >= self.config.auto_review_threshold
            )

        return scores

    def update_database_scores(
        self,
        scores: dict[str, RiskScore],
    ) -> int:
        """Update risk scores in the database.

        Args:
            scores: Dictionary of risk scores.

        Returns:
            Number of entries updated.
        """
        if not scores:
            return 0

        updated = 0
        with self.db.connect() as conn:
            for score in scores.values():
                # Build flags string
                flags = []
                if score.severity_level == "critical":
                    flags.append("CRITICAL")
                elif score.severity_level == "high":
                    flags.append("HIGH")
                elif score.severity_level == "medium":
                    flags.append("MEDIUM")

                if score.ml_score > 10:
                    flags.append("ML_ANOMALY")

                # Build violations string
                rules_str = ",".join(sorted(set(score.violations)))[:200]

                conn.execute(
                    """
                    UPDATE journal_entries
                    SET
                        risk_score = ?,
                        anomaly_flags = ?,
                        rule_violations = ?
                    WHERE gl_detail_id = ?
                    """,
                    [
                        round(score.total_score, 2),
                        ",".join(flags),
                        rules_str,
                        score.gl_detail_id,
                    ],
                )
                updated += 1

        return updated

    def get_high_risk_entries(
        self,
        threshold: float = 60.0,
        limit: int = 100,
    ) -> pl.DataFrame:
        """Get journal entries with high risk scores.

        Args:
            threshold: Minimum risk score.
            limit: Maximum entries to return.

        Returns:
            DataFrame of high-risk entries.
        """
        query = f"""
            SELECT
                gl_detail_id,
                journal_id,
                effective_date,
                gl_account_number,
                amount,
                je_line_description,
                prepared_by,
                approved_by,
                risk_score,
                anomaly_flags,
                rule_violations
            FROM journal_entries
            WHERE risk_score >= {threshold}
            ORDER BY risk_score DESC
            LIMIT {limit}
        """
        return self.db.execute_df(query)

    def get_risk_distribution(self) -> dict[str, int]:
        """Get distribution of risk scores.

        Returns:
            Dictionary with count by risk category.
        """
        query = """
            SELECT
                CASE
                    WHEN risk_score >= 80 THEN 'critical'
                    WHEN risk_score >= 60 THEN 'high'
                    WHEN risk_score >= 40 THEN 'medium'
                    WHEN risk_score >= 20 THEN 'low'
                    ELSE 'minimal'
                END as category,
                COUNT(*) as count
            FROM journal_entries
            GROUP BY category
            ORDER BY
                CASE category
                    WHEN 'critical' THEN 1
                    WHEN 'high' THEN 2
                    WHEN 'medium' THEN 3
                    WHEN 'low' THEN 4
                    ELSE 5
                END
        """
        result = self.db.execute(query)
        return {row[0]: row[1] for row in result}

    def get_scoring_summary(
        self,
        fiscal_year: int | None = None,
    ) -> dict[str, Any]:
        """Get summary of risk scoring results.

        Args:
            fiscal_year: Filter by fiscal year.

        Returns:
            Summary statistics.
        """
        where_clause = f"WHERE fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            SELECT
                COUNT(*) as total_entries,
                SUM(CASE WHEN risk_score > 0 THEN 1 ELSE 0 END) as flagged_entries,
                SUM(CASE WHEN risk_score >= 80 THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN risk_score >= 60 AND risk_score < 80 THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN risk_score >= 40 AND risk_score < 60 THEN 1 ELSE 0 END) as medium_count,
                AVG(CASE WHEN risk_score > 0 THEN risk_score END) as avg_risk_score,
                MAX(risk_score) as max_risk_score
            FROM journal_entries
            {where_clause}
        """
        result = self.db.execute(query)

        if result:
            row = result[0]
            return {
                "total_entries": row[0] or 0,
                "flagged_entries": row[1] or 0,
                "flagged_percentage": round(
                    (row[1] or 0) / max(row[0] or 1, 1) * 100, 2
                ),
                "critical_count": row[2] or 0,
                "high_count": row[3] or 0,
                "medium_count": row[4] or 0,
                "avg_risk_score": round(row[5] or 0, 2),
                "max_risk_score": round(row[6] or 0, 2),
            }

        return {}


class RiskPrioritizer:
    """Prioritize entries for audit review."""

    def __init__(
        self,
        db: DuckDBManager | None = None,
    ) -> None:
        self.db = db or DuckDBManager()

    def get_review_queue(
        self,
        max_entries: int = 100,
        fiscal_year: int | None = None,
    ) -> pl.DataFrame:
        """Get prioritized queue of entries for review.

        Prioritization factors:
        1. Risk score (highest first)
        2. Amount (larger amounts priority)
        3. Critical vs non-critical flags
        4. Number of distinct rule violations

        Args:
            max_entries: Maximum entries in queue.
            fiscal_year: Filter by fiscal year.

        Returns:
            DataFrame with prioritized entries.
        """
        where_clause = f"WHERE fiscal_year = {fiscal_year}" if fiscal_year else ""
        if where_clause:
            where_clause += " AND risk_score > 0"
        else:
            where_clause = "WHERE risk_score > 0"

        query = f"""
            SELECT
                gl_detail_id,
                journal_id,
                effective_date,
                gl_account_number,
                amount,
                je_line_description,
                prepared_by,
                approved_by,
                risk_score,
                anomaly_flags,
                rule_violations,
                -- Priority score calculation
                risk_score * 2 +
                LOG10(ABS(amount) + 1) * 5 +
                CASE WHEN anomaly_flags LIKE '%CRITICAL%' THEN 50 ELSE 0 END +
                LENGTH(rule_violations) - LENGTH(REPLACE(rule_violations, ',', ''))
                AS priority_score
            FROM journal_entries
            {where_clause}
            ORDER BY priority_score DESC, risk_score DESC
            LIMIT {max_entries}
        """
        return self.db.execute_df(query)

    def get_sample_by_risk_level(
        self,
        sample_sizes: dict[str, int] | None = None,
    ) -> pl.DataFrame:
        """Get stratified sample by risk level.

        Args:
            sample_sizes: Sample size per risk category.

        Returns:
            DataFrame with sampled entries.
        """
        if sample_sizes is None:
            sample_sizes = {
                "critical": 50,
                "high": 30,
                "medium": 15,
                "low": 5,
            }

        samples = []

        for category, size in sample_sizes.items():
            if category == "critical":
                score_range = "risk_score >= 80"
            elif category == "high":
                score_range = "risk_score >= 60 AND risk_score < 80"
            elif category == "medium":
                score_range = "risk_score >= 40 AND risk_score < 60"
            else:
                score_range = "risk_score >= 20 AND risk_score < 40"

            query = f"""
                SELECT *
                FROM journal_entries
                WHERE {score_range}
                ORDER BY RANDOM()
                LIMIT {size}
            """
            samples.append(self.db.execute_df(query))

        if samples:
            return pl.concat(samples)
        return pl.DataFrame()
