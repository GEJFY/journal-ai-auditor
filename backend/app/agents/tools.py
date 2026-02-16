"""Tools for AI agents.

Provides LangChain tools that agents can use to:
- Query journal entries
- Analyze risk scores
- Get aggregated statistics
- Search violations
- Compare patterns
"""

from langchain_core.tools import tool

from app.db import DuckDBManager

# Global DB instance for tools
_db: DuckDBManager | None = None


def get_db() -> DuckDBManager:
    """Get or create DB instance."""
    global _db
    if _db is None:
        _db = DuckDBManager()
    return _db


@tool
def query_journal_entries(
    gl_account_number: str | None = None,
    fiscal_year: int | None = None,
    min_amount: float | None = None,
    max_amount: float | None = None,
    min_risk_score: float | None = None,
    limit: int = 100,
) -> str:
    """Query journal entries with optional filters.

    Args:
        gl_account_number: Filter by account number (prefix match).
        fiscal_year: Filter by fiscal year.
        min_amount: Minimum absolute amount.
        max_amount: Maximum absolute amount.
        min_risk_score: Minimum risk score.
        limit: Maximum entries to return.

    Returns:
        JSON string of matching entries.
    """
    db = get_db()
    conditions = []
    params = []

    if gl_account_number:
        conditions.append("gl_account_number LIKE ?")
        params.append(f"{gl_account_number}%")

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)

    if min_amount:
        conditions.append("ABS(amount) >= ?")
        params.append(min_amount)

    if max_amount:
        conditions.append("ABS(amount) <= ?")
        params.append(max_amount)

    if min_risk_score:
        conditions.append("risk_score >= ?")
        params.append(min_risk_score)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            gl_detail_id,
            journal_id,
            effective_date,
            gl_account_number,
            amount,
            debit_credit_indicator,
            je_line_description,
            prepared_by,
            approved_by,
            risk_score,
            rule_violations
        FROM journal_entries
        WHERE {where_clause}
        ORDER BY risk_score DESC NULLS LAST, ABS(amount) DESC
        LIMIT {limit}
    """

    result = db.execute_df(query, params if params else None)
    return result.write_json()


@tool
def get_high_risk_entries(
    fiscal_year: int | None = None,
    risk_threshold: float = 60.0,
    limit: int = 50,
) -> str:
    """Get journal entries with high risk scores.

    Args:
        fiscal_year: Filter by fiscal year.
        risk_threshold: Minimum risk score (default 60).
        limit: Maximum entries to return.

    Returns:
        JSON string of high-risk entries.
    """
    db = get_db()
    conditions = ["risk_score >= ?"]
    params: list = [risk_threshold]

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)

    where_clause = " AND ".join(conditions)

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
        WHERE {where_clause}
        ORDER BY risk_score DESC
        LIMIT {limit}
    """

    result = db.execute_df(query, params)
    return result.write_json()


@tool
def get_rule_violations(
    rule_id: str | None = None,
    severity: str | None = None,
    fiscal_year: int | None = None,
    limit: int = 100,
) -> str:
    """Get rule violations with optional filters.

    Args:
        rule_id: Filter by specific rule ID.
        severity: Filter by severity (critical, high, medium, low).
        fiscal_year: Filter by fiscal year.
        limit: Maximum violations to return.

    Returns:
        JSON string of violations.
    """
    db = get_db()
    conditions: list[str] = []
    params: list = []

    if rule_id:
        conditions.append("v.rule_id = ?")
        params.append(rule_id)

    if severity:
        conditions.append("v.severity = ?")
        params.append(severity)

    if fiscal_year:
        conditions.append("je.fiscal_year = ?")
        params.append(fiscal_year)

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    query = f"""
        SELECT
            v.rule_id,
            v.severity,
            v.message,
            v.gl_detail_id,
            je.journal_id,
            je.effective_date,
            je.amount,
            je.gl_account_number,
            je.je_line_description
        FROM rule_violations v
        JOIN journal_entries je ON v.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
        ORDER BY
            CASE v.severity
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END,
            ABS(je.amount) DESC
        LIMIT {limit}
    """

    result = db.execute_df(query, params if params else None)
    return result.write_json()


@tool
def get_account_summary(
    gl_account_number: str,
    fiscal_year: int | None = None,
) -> str:
    """Get summary statistics for an account.

    Args:
        gl_account_number: Account number (prefix match supported).
        fiscal_year: Filter by fiscal year.

    Returns:
        JSON string with account summary.
    """
    db = get_db()
    conditions = ["gl_account_number LIKE ?"]
    params: list = [f"{gl_account_number}%"]

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            gl_account_number,
            COUNT(*) as entry_count,
            SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit_total,
            SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit_total,
            SUM(amount) as net_amount,
            AVG(ABS(amount)) as avg_amount,
            MAX(ABS(amount)) as max_amount,
            COUNT(DISTINCT prepared_by) as unique_users,
            AVG(risk_score) as avg_risk_score,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count
        FROM journal_entries
        WHERE {where_clause}
        GROUP BY gl_account_number
        ORDER BY entry_count DESC
    """

    result = db.execute_df(query, params)
    return result.write_json()


@tool
def get_user_activity(
    user_id: str,
    fiscal_year: int | None = None,
) -> str:
    """Get activity summary for a specific user.

    Args:
        user_id: User ID (prepared_by).
        fiscal_year: Filter by fiscal year.

    Returns:
        JSON string with user activity summary.
    """
    db = get_db()
    conditions = ["prepared_by = ?"]
    params: list = [user_id]

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            prepared_by,
            COUNT(*) as entry_count,
            COUNT(DISTINCT journal_id) as journal_count,
            SUM(ABS(amount)) as total_amount,
            AVG(ABS(amount)) as avg_amount,
            MAX(ABS(amount)) as max_amount,
            AVG(risk_score) as avg_risk_score,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            SUM(CASE WHEN prepared_by = approved_by THEN 1 ELSE 0 END) as self_approval_count,
            COUNT(DISTINCT gl_account_number) as unique_accounts
        FROM journal_entries
        WHERE {where_clause}
        GROUP BY prepared_by
    """

    result = db.execute_df(query, params)
    return result.write_json()


@tool
def get_period_comparison(
    fiscal_year: int,
    gl_account_number: str | None = None,
) -> str:
    """Compare metrics across accounting periods.

    Args:
        fiscal_year: Fiscal year to analyze.
        gl_account_number: Optional account filter.

    Returns:
        JSON string with period comparison data.
    """
    db = get_db()
    conditions = ["fiscal_year = ?"]
    params: list = [fiscal_year]

    if gl_account_number:
        conditions.append("gl_account_number LIKE ?")
        params.append(f"{gl_account_number}%")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            accounting_period,
            COUNT(*) as entry_count,
            SUM(ABS(amount)) as total_amount,
            AVG(ABS(amount)) as avg_amount,
            AVG(risk_score) as avg_risk_score,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count
        FROM journal_entries
        WHERE {where_clause}
        GROUP BY accounting_period
        ORDER BY accounting_period
    """

    result = db.execute_df(query, params)
    return result.write_json()


@tool
def get_anomaly_patterns(
    fiscal_year: int | None = None,
    pattern_type: str | None = None,
) -> str:
    """Get summary of detected anomaly patterns.

    Args:
        fiscal_year: Filter by fiscal year.
        pattern_type: Filter by pattern type (e.g., 'self_approval', 'round_amount').

    Returns:
        JSON string with anomaly pattern summary.
    """
    db = get_db()
    conditions = ["anomaly_flags IS NOT NULL", "anomaly_flags <> ''"]
    params: list = []

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)

    if pattern_type:
        conditions.append("anomaly_flags LIKE ?")
        params.append(f"%{pattern_type}%")

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            CASE
                WHEN anomaly_flags LIKE '%CRITICAL%' THEN 'critical'
                WHEN anomaly_flags LIKE '%HIGH%' THEN 'high'
                WHEN anomaly_flags LIKE '%MEDIUM%' THEN 'medium'
                ELSE 'low'
            END as risk_level,
            COUNT(*) as count,
            SUM(ABS(amount)) as total_amount,
            AVG(risk_score) as avg_risk_score
        FROM journal_entries
        WHERE {where_clause}
        GROUP BY
            CASE
                WHEN anomaly_flags LIKE '%CRITICAL%' THEN 'critical'
                WHEN anomaly_flags LIKE '%HIGH%' THEN 'high'
                WHEN anomaly_flags LIKE '%MEDIUM%' THEN 'medium'
                ELSE 'low'
            END
        ORDER BY
            CASE
                WHEN anomaly_flags LIKE '%CRITICAL%' THEN 1
                WHEN anomaly_flags LIKE '%HIGH%' THEN 2
                WHEN anomaly_flags LIKE '%MEDIUM%' THEN 3
                ELSE 4
            END
    """

    result = db.execute_df(query, params if params else None)
    return result.write_json()


@tool
def get_benford_analysis(fiscal_year: int | None = None) -> str:
    """Get Benford's Law distribution analysis.

    Args:
        fiscal_year: Filter by fiscal year.

    Returns:
        JSON string with Benford distribution data.
    """
    db = get_db()
    params: list = []

    if fiscal_year:
        where_clause = "WHERE fiscal_year = ?"
        params.append(fiscal_year)
    else:
        where_clause = ""

    query = f"""
        SELECT
            first_digit,
            actual_count,
            actual_pct,
            expected_pct,
            actual_pct - expected_pct as deviation
        FROM agg_benford_distribution
        {where_clause}
        ORDER BY first_digit
    """

    try:
        result = db.execute_df(query, params if params else None)
        return result.write_json()
    except Exception:
        return '{"error": "Benford analysis data not available"}'


@tool
def get_dashboard_kpi(fiscal_year: int | None = None) -> str:
    """Get key performance indicators for dashboard.

    Args:
        fiscal_year: Filter by fiscal year.

    Returns:
        JSON string with KPI data.
    """
    db = get_db()
    params: list = []

    if fiscal_year:
        where_clause = "WHERE fiscal_year = ?"
        params.append(fiscal_year)
    else:
        where_clause = ""

    query = f"""
        SELECT
            fiscal_year,
            total_entries,
            total_journals,
            total_amount,
            unique_users,
            unique_accounts,
            high_risk_count,
            high_risk_pct,
            avg_risk_score,
            self_approval_count
        FROM agg_dashboard_kpi
        {where_clause}
    """

    try:
        result = db.execute_df(query, params if params else None)
        return result.write_json()
    except Exception:
        return '{"error": "Dashboard KPI data not available"}'


@tool
def search_journal_description(
    search_term: str,
    fiscal_year: int | None = None,
    limit: int = 50,
) -> str:
    """Search journal entries by description.

    Args:
        search_term: Text to search for in description.
        fiscal_year: Filter by fiscal year.
        limit: Maximum entries to return.

    Returns:
        JSON string of matching entries.
    """
    db = get_db()
    conditions = ["je_line_description LIKE ?"]
    params: list = [f"%{search_term}%"]

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)

    where_clause = " AND ".join(conditions)

    query = f"""
        SELECT
            gl_detail_id,
            journal_id,
            effective_date,
            gl_account_number,
            amount,
            je_line_description,
            prepared_by,
            risk_score
        FROM journal_entries
        WHERE {where_clause}
        ORDER BY ABS(amount) DESC
        LIMIT {limit}
    """

    result = db.execute_df(query, params)
    return result.write_json()


@tool
def save_audit_finding(
    workflow_id: str,
    agent_type: str,
    fiscal_year: int,
    finding_title: str,
    finding_description: str,
    severity: str = "MEDIUM",
    category: str = "",
    affected_amount: float = 0.0,
    affected_count: int = 0,
    recommendation: str = "",
) -> str:
    """Save an audit finding to the database for persistence.

    Args:
        workflow_id: ID of the workflow that produced this finding.
        agent_type: Type of agent (analysis, investigation, review).
        fiscal_year: Fiscal year of the finding.
        finding_title: Short title of the finding.
        finding_description: Detailed description.
        severity: Severity level (LOW, MEDIUM, HIGH, CRITICAL).
        category: Finding category.
        affected_amount: Financial amount affected.
        affected_count: Number of entries affected.
        recommendation: Recommended action.

    Returns:
        JSON string with the saved finding ID.
    """
    import json
    import uuid

    db = get_db()
    finding_id = f"AF-{uuid.uuid4().hex[:8].upper()}"

    try:
        db.execute(
            """INSERT INTO audit_findings
               (finding_id, workflow_id, agent_type, fiscal_year,
                finding_title, finding_description, severity, category,
                affected_amount, affected_count, recommendation)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            [
                finding_id,
                workflow_id,
                agent_type,
                fiscal_year,
                finding_title,
                finding_description,
                severity.upper(),
                category,
                affected_amount,
                affected_count,
                recommendation,
            ],
        )
        return json.dumps({"finding_id": finding_id, "status": "saved"})
    except Exception as e:
        return json.dumps({"error": str(e)})


@tool
def get_saved_findings(
    fiscal_year: int | None = None,
    workflow_id: str | None = None,
    severity: str | None = None,
) -> str:
    """Get previously saved audit findings from the database.

    Args:
        fiscal_year: Filter by fiscal year.
        workflow_id: Filter by workflow ID.
        severity: Filter by severity (LOW, MEDIUM, HIGH, CRITICAL).

    Returns:
        JSON string of saved findings.
    """
    db = get_db()
    conditions: list[str] = []
    params: list = []

    if fiscal_year:
        conditions.append("fiscal_year = ?")
        params.append(fiscal_year)
    if workflow_id:
        conditions.append("workflow_id = ?")
        params.append(workflow_id)
    if severity:
        conditions.append("severity = ?")
        params.append(severity.upper())

    where_clause = " AND ".join(conditions) if conditions else "1=1"

    try:
        query = f"""
            SELECT finding_id, workflow_id, agent_type, fiscal_year,
                   finding_title, finding_description, severity, category,
                   affected_amount, affected_count, recommendation, status,
                   created_at
            FROM audit_findings
            WHERE {where_clause}
            ORDER BY
                CASE severity
                    WHEN 'CRITICAL' THEN 1 WHEN 'HIGH' THEN 2
                    WHEN 'MEDIUM' THEN 3 ELSE 4
                END,
                created_at DESC
        """
        result = db.execute_df(query, params if params else None)
        return result.write_json()
    except Exception:
        return '{"findings": [], "note": "audit_findings table not yet initialized"}'


# Tool collections for different agent types
ANALYSIS_TOOLS = [
    query_journal_entries,
    get_high_risk_entries,
    get_account_summary,
    get_period_comparison,
    get_anomaly_patterns,
    get_benford_analysis,
    get_dashboard_kpi,
    save_audit_finding,
]

INVESTIGATION_TOOLS = [
    query_journal_entries,
    get_high_risk_entries,
    get_rule_violations,
    get_user_activity,
    get_account_summary,
    search_journal_description,
    save_audit_finding,
    get_saved_findings,
]

QA_TOOLS = [
    query_journal_entries,
    get_account_summary,
    get_user_activity,
    get_period_comparison,
    get_dashboard_kpi,
    search_journal_description,
    get_saved_findings,
]

REVIEW_TOOLS = [
    get_high_risk_entries,
    get_rule_violations,
    get_anomaly_patterns,
    get_dashboard_kpi,
    save_audit_finding,
    get_saved_findings,
]

DOCUMENTATION_TOOLS = [
    query_journal_entries,
    get_high_risk_entries,
    get_account_summary,
    get_period_comparison,
    get_anomaly_patterns,
    get_benford_analysis,
    get_dashboard_kpi,
    get_rule_violations,
    get_saved_findings,
]
