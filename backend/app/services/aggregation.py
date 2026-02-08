"""Aggregation table update service.

Maintains pre-aggregated tables for fast dashboard queries.
Updates are run after data import and rule execution.

Aggregation tables (17 total):
1. agg_by_period_account - Period x Account totals
2. agg_by_date - Daily totals
3. agg_by_user - User activity summary
4. agg_by_department - Department totals
5. agg_by_vendor - Vendor transaction summary
6. agg_high_risk - High risk entry summary
7. agg_rule_violations - Violation counts by rule
8. agg_trend_mom - Month-over-month trends
9. agg_trend_yoy - Year-over-year comparisons
10. agg_benford_distribution - Benford's Law distribution
11. agg_amount_distribution - Amount distribution buckets
12. agg_time_distribution - Time-based distribution
13. agg_approval_patterns - Approval pattern summary
14. agg_account_activity - Account activity metrics
15. agg_anomaly_summary - Anomaly detection summary
16. agg_ml_scores - ML score distribution
17. agg_dashboard_kpi - Dashboard KPI summary
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Any, Optional

from app.db import DuckDBManager


@dataclass
class AggregationResult:
    """Result of aggregation update."""

    table_name: str
    rows_affected: int
    execution_time_ms: float
    success: bool
    error: Optional[str] = None


class AggregationService:
    """Service for updating aggregation tables."""

    def __init__(self, db: Optional[DuckDBManager] = None) -> None:
        """Initialize aggregation service.

        Args:
            db: DuckDB manager instance.
        """
        self.db = db or DuckDBManager()

    def update_all(self, fiscal_year: Optional[int] = None) -> list[AggregationResult]:
        """Update all aggregation tables.

        Args:
            fiscal_year: Filter by fiscal year (updates all if not specified).

        Returns:
            List of aggregation results.
        """
        results = []

        # Core aggregations
        results.append(self._update_period_account(fiscal_year))
        results.append(self._update_daily(fiscal_year))
        results.append(self._update_by_user(fiscal_year))
        results.append(self._update_by_department(fiscal_year))
        results.append(self._update_by_vendor(fiscal_year))

        # Risk aggregations
        results.append(self._update_high_risk(fiscal_year))
        results.append(self._update_rule_violations(fiscal_year))
        results.append(self._update_anomaly_summary(fiscal_year))

        # Trend aggregations
        results.append(self._update_trend_mom(fiscal_year))
        results.append(self._update_trend_yoy(fiscal_year))

        # Distribution aggregations
        results.append(self._update_benford_distribution(fiscal_year))
        results.append(self._update_amount_distribution(fiscal_year))
        results.append(self._update_time_distribution(fiscal_year))

        # Pattern aggregations
        results.append(self._update_approval_patterns(fiscal_year))
        results.append(self._update_account_activity(fiscal_year))

        # Summary aggregations
        results.append(self._update_ml_scores(fiscal_year))
        results.append(self._update_dashboard_kpi(fiscal_year))

        return results

    def _execute_aggregation(
        self,
        table_name: str,
        query: str,
    ) -> AggregationResult:
        """Execute an aggregation query.

        Args:
            table_name: Target table name.
            query: Aggregation SQL query.

        Returns:
            AggregationResult with execution details.
        """
        import time
        start = time.perf_counter()

        try:
            with self.db.connect() as conn:
                # Clear existing data
                conn.execute(f"DELETE FROM {table_name}")
                # Insert aggregated data
                conn.execute(query)
                count = conn.execute(f"SELECT COUNT(*) FROM {table_name}").fetchone()[0]

            return AggregationResult(
                table_name=table_name,
                rows_affected=count,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                success=True,
            )
        except Exception as e:
            return AggregationResult(
                table_name=table_name,
                rows_affected=0,
                execution_time_ms=(time.perf_counter() - start) * 1000,
                success=False,
                error=str(e),
            )

    def _update_period_account(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update period x account aggregation."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_by_period_account
            SELECT
                fiscal_year,
                accounting_period,
                gl_account_number,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit_total,
                SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit_total,
                SUM(amount) as net_amount,
                COUNT(*) as entry_count,
                COUNT(DISTINCT journal_id) as journal_count,
                AVG(risk_score) as avg_risk_score,
                MAX(risk_score) as max_risk_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY fiscal_year, accounting_period, gl_account_number
        """
        return self._execute_aggregation("agg_by_period_account", query)

    def _update_daily(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update daily aggregation."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_by_date
            SELECT
                CAST(effective_date AS DATE) as date,
                fiscal_year,
                accounting_period,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit_total,
                SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit_total,
                COUNT(*) as entry_count,
                COUNT(DISTINCT journal_id) as journal_count,
                COUNT(DISTINCT prepared_by) as unique_users,
                AVG(risk_score) as avg_risk_score,
                SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY CAST(effective_date AS DATE), fiscal_year, accounting_period
        """
        return self._execute_aggregation("agg_by_date", query)

    def _update_by_user(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update user activity aggregation."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_by_user
            SELECT
                prepared_by as user_id,
                fiscal_year,
                COUNT(*) as entry_count,
                COUNT(DISTINCT journal_id) as journal_count,
                SUM(ABS(amount)) as total_amount,
                AVG(ABS(amount)) as avg_amount,
                MAX(ABS(amount)) as max_amount,
                AVG(risk_score) as avg_risk_score,
                SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
                COUNT(DISTINCT gl_account_number) as unique_accounts,
                SUM(CASE WHEN prepared_by = approved_by THEN 1 ELSE 0 END) as self_approval_count,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE prepared_by IS NOT NULL {fy_filter}
            GROUP BY prepared_by, fiscal_year
        """
        return self._execute_aggregation("agg_by_user", query)

    def _update_by_department(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update department aggregation."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_by_department
            SELECT
                dept_code,
                fiscal_year,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit_total,
                SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit_total,
                COUNT(*) as entry_count,
                COUNT(DISTINCT prepared_by) as unique_users,
                AVG(risk_score) as avg_risk_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE dept_code IS NOT NULL {fy_filter}
            GROUP BY dept_code, fiscal_year
        """
        return self._execute_aggregation("agg_by_department", query)

    def _update_by_vendor(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update vendor aggregation."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_by_vendor
            SELECT
                vendor_code,
                fiscal_year,
                SUM(amount) as total_amount,
                COUNT(*) as transaction_count,
                COUNT(DISTINCT journal_id) as journal_count,
                AVG(risk_score) as avg_risk_score,
                MAX(risk_score) as max_risk_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE vendor_code IS NOT NULL {fy_filter}
            GROUP BY vendor_code, fiscal_year
        """
        return self._execute_aggregation("agg_by_vendor", query)

    def _update_high_risk(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update high risk summary."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_high_risk
            SELECT
                fiscal_year,
                accounting_period,
                CASE
                    WHEN risk_score >= 80 THEN 'critical'
                    WHEN risk_score >= 60 THEN 'high'
                    WHEN risk_score >= 40 THEN 'medium'
                    ELSE 'low'
                END as risk_category,
                COUNT(*) as entry_count,
                SUM(ABS(amount)) as total_amount,
                AVG(risk_score) as avg_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE risk_score >= 20 {fy_filter}
            GROUP BY fiscal_year, accounting_period,
                CASE
                    WHEN risk_score >= 80 THEN 'critical'
                    WHEN risk_score >= 60 THEN 'high'
                    WHEN risk_score >= 40 THEN 'medium'
                    ELSE 'low'
                END
        """
        return self._execute_aggregation("agg_high_risk", query)

    def _update_rule_violations(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update rule violation counts."""
        fy_filter = f"AND je.fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_rule_violations
            SELECT
                v.rule_id,
                je.fiscal_year,
                COUNT(*) as violation_count,
                COUNT(DISTINCT je.journal_id) as affected_journals,
                SUM(ABS(je.amount)) as total_amount,
                v.severity,
                CURRENT_TIMESTAMP as updated_at
            FROM rule_violations v
            JOIN journal_entries je ON v.gl_detail_id = je.gl_detail_id
            WHERE 1=1 {fy_filter}
            GROUP BY v.rule_id, je.fiscal_year, v.severity
        """
        return self._execute_aggregation("agg_rule_violations", query)

    def _update_trend_mom(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update month-over-month trend."""
        fy_filter = f"WHERE fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_trend_mom
            SELECT
                fiscal_year,
                accounting_period,
                gl_account_number,
                SUM(amount) as current_amount,
                LAG(SUM(amount)) OVER (
                    PARTITION BY gl_account_number
                    ORDER BY fiscal_year, accounting_period
                ) as prior_amount,
                SUM(amount) - LAG(SUM(amount)) OVER (
                    PARTITION BY gl_account_number
                    ORDER BY fiscal_year, accounting_period
                ) as change_amount,
                CASE
                    WHEN LAG(SUM(amount)) OVER (
                        PARTITION BY gl_account_number
                        ORDER BY fiscal_year, accounting_period
                    ) <> 0
                    THEN (SUM(amount) - LAG(SUM(amount)) OVER (
                        PARTITION BY gl_account_number
                        ORDER BY fiscal_year, accounting_period
                    )) / ABS(LAG(SUM(amount)) OVER (
                        PARTITION BY gl_account_number
                        ORDER BY fiscal_year, accounting_period
                    )) * 100
                    ELSE 0
                END as change_pct,
                COUNT(*) as entry_count,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            {fy_filter}
            GROUP BY fiscal_year, accounting_period, gl_account_number
        """
        return self._execute_aggregation("agg_trend_mom", query)

    def _update_trend_yoy(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update year-over-year trend."""
        query = """
            INSERT INTO agg_trend_yoy
            SELECT
                fiscal_year,
                gl_account_number,
                SUM(amount) as current_amount,
                LAG(SUM(amount)) OVER (
                    PARTITION BY gl_account_number
                    ORDER BY fiscal_year
                ) as prior_year_amount,
                SUM(amount) - LAG(SUM(amount)) OVER (
                    PARTITION BY gl_account_number
                    ORDER BY fiscal_year
                ) as change_amount,
                CASE
                    WHEN LAG(SUM(amount)) OVER (
                        PARTITION BY gl_account_number
                        ORDER BY fiscal_year
                    ) <> 0
                    THEN (SUM(amount) - LAG(SUM(amount)) OVER (
                        PARTITION BY gl_account_number
                        ORDER BY fiscal_year
                    )) / ABS(LAG(SUM(amount)) OVER (
                        PARTITION BY gl_account_number
                        ORDER BY fiscal_year
                    )) * 100
                    ELSE 0
                END as change_pct,
                COUNT(*) as entry_count,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            GROUP BY fiscal_year, gl_account_number
        """
        return self._execute_aggregation("agg_trend_yoy", query)

    def _update_benford_distribution(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update Benford's Law distribution."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_benford_distribution
            SELECT
                fiscal_year,
                CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) as first_digit,
                COUNT(*) as actual_count,
                COUNT(*) * 1.0 / SUM(COUNT(*)) OVER (PARTITION BY fiscal_year) as actual_pct,
                -- Expected Benford percentages
                CASE CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER)
                    WHEN 1 THEN 0.301
                    WHEN 2 THEN 0.176
                    WHEN 3 THEN 0.125
                    WHEN 4 THEN 0.097
                    WHEN 5 THEN 0.079
                    WHEN 6 THEN 0.067
                    WHEN 7 THEN 0.058
                    WHEN 8 THEN 0.051
                    WHEN 9 THEN 0.046
                    ELSE 0
                END as expected_pct,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE ABS(amount) >= 10 {fy_filter}
            GROUP BY
                fiscal_year,
                CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER)
            HAVING CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) BETWEEN 1 AND 9
        """
        return self._execute_aggregation("agg_benford_distribution", query)

    def _update_amount_distribution(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update amount distribution buckets."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_amount_distribution
            SELECT
                fiscal_year,
                CASE
                    WHEN ABS(amount) < 10000 THEN '0-10K'
                    WHEN ABS(amount) < 100000 THEN '10K-100K'
                    WHEN ABS(amount) < 1000000 THEN '100K-1M'
                    WHEN ABS(amount) < 10000000 THEN '1M-10M'
                    WHEN ABS(amount) < 100000000 THEN '10M-100M'
                    ELSE '100M+'
                END as amount_bucket,
                COUNT(*) as entry_count,
                SUM(ABS(amount)) as total_amount,
                AVG(risk_score) as avg_risk_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY
                fiscal_year,
                CASE
                    WHEN ABS(amount) < 10000 THEN '0-10K'
                    WHEN ABS(amount) < 100000 THEN '10K-100K'
                    WHEN ABS(amount) < 1000000 THEN '100K-1M'
                    WHEN ABS(amount) < 10000000 THEN '1M-10M'
                    WHEN ABS(amount) < 100000000 THEN '10M-100M'
                    ELSE '100M+'
                END
        """
        return self._execute_aggregation("agg_amount_distribution", query)

    def _update_time_distribution(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update time-based distribution."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_time_distribution
            SELECT
                fiscal_year,
                EXTRACT(DOW FROM effective_date) as day_of_week,
                EXTRACT(DAY FROM effective_date) as day_of_month,
                COUNT(*) as entry_count,
                SUM(ABS(amount)) as total_amount,
                AVG(risk_score) as avg_risk_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY
                fiscal_year,
                EXTRACT(DOW FROM effective_date),
                EXTRACT(DAY FROM effective_date)
        """
        return self._execute_aggregation("agg_time_distribution", query)

    def _update_approval_patterns(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update approval pattern summary."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_approval_patterns
            SELECT
                fiscal_year,
                prepared_by,
                approved_by,
                COUNT(*) as pair_count,
                SUM(ABS(amount)) as total_amount,
                AVG(risk_score) as avg_risk_score,
                CASE WHEN prepared_by = approved_by THEN 1 ELSE 0 END as is_self_approval,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE prepared_by IS NOT NULL
                AND approved_by IS NOT NULL
                {fy_filter}
            GROUP BY
                fiscal_year,
                prepared_by,
                approved_by,
                CASE WHEN prepared_by = approved_by THEN 1 ELSE 0 END
        """
        return self._execute_aggregation("agg_approval_patterns", query)

    def _update_account_activity(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update account activity metrics."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_account_activity
            SELECT
                gl_account_number,
                fiscal_year,
                COUNT(*) as total_entries,
                COUNT(DISTINCT journal_id) as unique_journals,
                COUNT(DISTINCT prepared_by) as unique_users,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit_total,
                SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit_total,
                AVG(ABS(amount)) as avg_amount,
                MAX(ABS(amount)) as max_amount,
                MIN(effective_date) as first_activity,
                MAX(effective_date) as last_activity,
                AVG(risk_score) as avg_risk_score,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY gl_account_number, fiscal_year
        """
        return self._execute_aggregation("agg_account_activity", query)

    def _update_anomaly_summary(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update anomaly detection summary."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_anomaly_summary
            SELECT
                fiscal_year,
                accounting_period,
                SUM(CASE WHEN risk_score >= 80 THEN 1 ELSE 0 END) as critical_count,
                SUM(CASE WHEN risk_score >= 60 AND risk_score < 80 THEN 1 ELSE 0 END) as high_count,
                SUM(CASE WHEN risk_score >= 40 AND risk_score < 60 THEN 1 ELSE 0 END) as medium_count,
                SUM(CASE WHEN risk_score >= 20 AND risk_score < 40 THEN 1 ELSE 0 END) as low_count,
                SUM(CASE WHEN anomaly_flags LIKE '%ML_ANOMALY%' THEN 1 ELSE 0 END) as ml_anomaly_count,
                SUM(CASE WHEN rule_violations IS NOT NULL AND rule_violations <> '' THEN 1 ELSE 0 END) as rule_violation_count,
                COUNT(*) as total_entries,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY fiscal_year, accounting_period
        """
        return self._execute_aggregation("agg_anomaly_summary", query)

    def _update_ml_scores(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update ML score distribution."""
        fy_filter = f"AND fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_ml_scores
            SELECT
                fiscal_year,
                CASE
                    WHEN risk_score >= 80 THEN '80-100'
                    WHEN risk_score >= 60 THEN '60-79'
                    WHEN risk_score >= 40 THEN '40-59'
                    WHEN risk_score >= 20 THEN '20-39'
                    WHEN risk_score > 0 THEN '1-19'
                    ELSE '0'
                END as score_bucket,
                COUNT(*) as entry_count,
                SUM(ABS(amount)) as total_amount,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            WHERE 1=1 {fy_filter}
            GROUP BY
                fiscal_year,
                CASE
                    WHEN risk_score >= 80 THEN '80-100'
                    WHEN risk_score >= 60 THEN '60-79'
                    WHEN risk_score >= 40 THEN '40-59'
                    WHEN risk_score >= 20 THEN '20-39'
                    WHEN risk_score > 0 THEN '1-19'
                    ELSE '0'
                END
        """
        return self._execute_aggregation("agg_ml_scores", query)

    def _update_dashboard_kpi(self, fiscal_year: Optional[int]) -> AggregationResult:
        """Update dashboard KPI summary."""
        fy_filter = f"WHERE fiscal_year = {fiscal_year}" if fiscal_year else ""

        query = f"""
            INSERT INTO agg_dashboard_kpi
            SELECT
                fiscal_year,
                COUNT(*) as total_entries,
                COUNT(DISTINCT journal_id) as total_journals,
                SUM(ABS(amount)) as total_amount,
                COUNT(DISTINCT prepared_by) as unique_users,
                COUNT(DISTINCT gl_account_number) as unique_accounts,
                SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
                SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) * 100.0 / NULLIF(COUNT(*), 0) as high_risk_pct,
                AVG(CASE WHEN risk_score > 0 THEN risk_score END) as avg_risk_score,
                SUM(CASE WHEN prepared_by = approved_by AND prepared_by IS NOT NULL THEN 1 ELSE 0 END) as self_approval_count,
                CURRENT_TIMESTAMP as updated_at
            FROM journal_entries
            {fy_filter}
            GROUP BY fiscal_year
        """
        return self._execute_aggregation("agg_dashboard_kpi", query)
