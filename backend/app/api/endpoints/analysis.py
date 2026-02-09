"""Analysis API endpoints.

Provides REST API for:
- Rule-based analysis results
- ML anomaly detection results
- Benford analysis
- Risk scoring details
"""

from typing import Any

from fastapi import APIRouter, HTTPException, Query
from pydantic import BaseModel

from app.db import DuckDBManager
from app.services.rules import RiskScoringService

router = APIRouter()


def get_db() -> DuckDBManager:
    """Get DB instance."""
    return DuckDBManager()


class ViolationItem(BaseModel):
    """Single rule violation."""

    gl_detail_id: str
    journal_id: str
    rule_id: str
    rule_name: str
    severity: str
    category: str
    description: str
    amount: float
    date: str


class ViolationsResponse(BaseModel):
    """Rule violations response."""

    violations: list[ViolationItem]
    total_count: int
    by_severity: dict[str, int]
    by_category: dict[str, int]


class MLAnomalyItem(BaseModel):
    """ML anomaly detection result."""

    gl_detail_id: str
    journal_id: str
    anomaly_score: float
    detection_method: str
    is_anomaly: bool
    amount: float
    date: str
    features: dict[str, Any]


class MLAnomaliesResponse(BaseModel):
    """ML anomalies response."""

    anomalies: list[MLAnomalyItem]
    total_count: int
    by_method: dict[str, int]


class RiskDetailItem(BaseModel):
    """Risk score detail."""

    gl_detail_id: str
    journal_id: str
    risk_score: float
    rule_score: float
    ml_score: float
    benford_score: float
    risk_factors: list[str]
    amount: float
    date: str


class RiskDetailsResponse(BaseModel):
    """Risk details response."""

    entries: list[RiskDetailItem]
    total_count: int
    avg_risk_score: float
    distribution: dict[str, int]


class BenfordDigitData(BaseModel):
    """Benford digit distribution data."""

    digit: int
    actual_count: int
    actual_pct: float
    expected_pct: float
    deviation: float
    z_score: float


class BenfordResponse(BaseModel):
    """Benford analysis response."""

    first_digit: list[BenfordDigitData]
    second_digit: list[BenfordDigitData]
    total_count: int
    mad_first: float
    mad_second: float
    conformity: str
    suspicious_accounts: list[dict[str, Any]]


@router.get("/violations", response_model=ViolationsResponse)
async def get_violations(
    fiscal_year: int = Query(...),
    rule_id: str | None = Query(None),
    severity: str | None = Query(None),
    category: str | None = Query(None),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    limit: int = Query(100, le=1000),
    offset: int = Query(0, ge=0),
) -> ViolationsResponse:
    """Get rule violations.

    Args:
        fiscal_year: Fiscal year.
        rule_id: Filter by specific rule.
        severity: Filter by severity level.
        category: Filter by rule category.
        period_from: Start period.
        period_to: End period.
        limit: Maximum results.
        offset: Pagination offset.

    Returns:
        List of violations with statistics.
    """
    db = get_db()

    filters = ["je.fiscal_year = ?"]
    params = [fiscal_year]

    if rule_id:
        filters.append("rv.rule_id = ?")
        params.append(rule_id)
    if severity:
        filters.append("rv.severity = ?")
        params.append(severity)
    if category:
        filters.append("rv.category = ?")
        params.append(category)
    if period_from:
        filters.append("je.accounting_period >= ?")
        params.append(period_from)
    if period_to:
        filters.append("je.accounting_period <= ?")
        params.append(period_to)

    where_clause = " AND ".join(filters)

    # Get violations
    query = f"""
        SELECT
            rv.gl_detail_id,
            rv.journal_id,
            rv.rule_id,
            rv.rule_name,
            rv.severity,
            rv.category,
            rv.violation_description,
            je.amount,
            je.effective_date
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
        ORDER BY rv.created_at DESC
        LIMIT {limit} OFFSET {offset}
    """

    result = db.execute(query, params)

    violations = [
        ViolationItem(
            gl_detail_id=row[0] or "",
            journal_id=row[1] or "",
            rule_id=row[2] or "",
            rule_name=row[3] or "",
            severity=row[4] or "",
            category=row[5] or "",
            description=row[6] or "",
            amount=row[7] or 0,
            date=str(row[8]) if row[8] else "",
        )
        for row in result
    ]

    # Get counts
    count_query = f"""
        SELECT COUNT(*)
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
    """
    total_count = db.execute(count_query, params)[0][0] or 0

    # Get severity distribution
    severity_query = f"""
        SELECT rv.severity, COUNT(*)
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
        GROUP BY rv.severity
    """
    severity_result = db.execute(severity_query, params)
    by_severity = {row[0]: row[1] for row in severity_result}

    # Get category distribution
    category_query = f"""
        SELECT rv.category, COUNT(*)
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
        GROUP BY rv.category
    """
    category_result = db.execute(category_query, params)
    by_category = {row[0]: row[1] for row in category_result}

    return ViolationsResponse(
        violations=violations,
        total_count=total_count,
        by_severity=by_severity,
        by_category=by_category,
    )


@router.get("/ml-anomalies", response_model=MLAnomaliesResponse)
async def get_ml_anomalies(
    fiscal_year: int = Query(...),
    method: str | None = Query(None),
    min_score: float = Query(0.5, ge=0, le=1),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    limit: int = Query(100, le=1000),
) -> MLAnomaliesResponse:
    """Get ML anomaly detection results.

    Args:
        fiscal_year: Fiscal year.
        method: Filter by detection method.
        min_score: Minimum anomaly score.
        period_from: Start period.
        period_to: End period.
        limit: Maximum results.

    Returns:
        List of ML anomalies with statistics.
    """
    db = get_db()

    filters = ["je.fiscal_year = ?", "ma.anomaly_score >= ?"]
    params = [fiscal_year, min_score]

    if method:
        filters.append("ma.detection_method = ?")
        params.append(method)
    if period_from:
        filters.append("je.accounting_period >= ?")
        params.append(period_from)
    if period_to:
        filters.append("je.accounting_period <= ?")
        params.append(period_to)

    where_clause = " AND ".join(filters)

    query = f"""
        SELECT
            ma.gl_detail_id,
            ma.journal_id,
            ma.anomaly_score,
            ma.detection_method,
            ma.is_anomaly,
            je.amount,
            je.effective_date,
            ma.feature_values
        FROM ml_anomalies ma
        JOIN journal_entries je ON ma.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
        ORDER BY ma.anomaly_score DESC
        LIMIT {limit}
    """

    result = db.execute(query, params)

    anomalies = [
        MLAnomalyItem(
            gl_detail_id=row[0] or "",
            journal_id=row[1] or "",
            anomaly_score=row[2] or 0,
            detection_method=row[3] or "",
            is_anomaly=row[4] or False,
            amount=row[5] or 0,
            date=str(row[6]) if row[6] else "",
            features=row[7] if isinstance(row[7], dict) else {},
        )
        for row in result
    ]

    # Get count
    count_query = f"""
        SELECT COUNT(*)
        FROM ml_anomalies ma
        JOIN journal_entries je ON ma.gl_detail_id = je.gl_detail_id
        WHERE {where_clause}
    """
    total_count = db.execute(count_query, params)[0][0] or 0

    # Get method distribution
    method_query = """
        SELECT ma.detection_method, COUNT(*)
        FROM ml_anomalies ma
        JOIN journal_entries je ON ma.gl_detail_id = je.gl_detail_id
        WHERE je.fiscal_year = ? AND ma.is_anomaly = true
        GROUP BY ma.detection_method
    """
    method_result = db.execute(method_query, [fiscal_year])
    by_method = {row[0]: row[1] for row in method_result}

    return MLAnomaliesResponse(
        anomalies=anomalies,
        total_count=total_count,
        by_method=by_method,
    )


@router.get("/risk-details", response_model=RiskDetailsResponse)
async def get_risk_details(
    fiscal_year: int = Query(...),
    min_score: float = Query(0, ge=0, le=100),
    max_score: float = Query(100, ge=0, le=100),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    limit: int = Query(100, le=1000),
) -> RiskDetailsResponse:
    """Get detailed risk score breakdown.

    Args:
        fiscal_year: Fiscal year.
        min_score: Minimum risk score.
        max_score: Maximum risk score.
        period_from: Start period.
        period_to: End period.
        limit: Maximum results.

    Returns:
        Risk score details with breakdown.
    """
    db = get_db()

    filters = [
        "fiscal_year = ?",
        "risk_score >= ?",
        "risk_score <= ?",
    ]
    params = [fiscal_year, min_score, max_score]

    if period_from:
        filters.append("accounting_period >= ?")
        params.append(period_from)
    if period_to:
        filters.append("accounting_period <= ?")
        params.append(period_to)

    where_clause = " AND ".join(filters)

    query = f"""
        SELECT
            gl_detail_id,
            journal_id,
            risk_score,
            rule_violations,
            anomaly_flags,
            amount,
            effective_date
        FROM journal_entries
        WHERE {where_clause}
        ORDER BY risk_score DESC
        LIMIT {limit}
    """

    result = db.execute(query, params)

    entries = []
    for row in result:
        # Parse risk factors from violations and flags
        violations = (row[3] or "").split(",") if row[3] else []
        flags = (row[4] or "").split(",") if row[4] else []
        risk_factors = [v.strip() for v in violations + flags if v.strip()]

        entries.append(
            RiskDetailItem(
                gl_detail_id=row[0] or "",
                journal_id=row[1] or "",
                risk_score=row[2] or 0,
                rule_score=0,  # Would be calculated from violations
                ml_score=0,  # Would be from ml_anomalies
                benford_score=0,  # Would be from benford analysis
                risk_factors=risk_factors,
                amount=row[5] or 0,
                date=str(row[6]) if row[6] else "",
            )
        )

    # Get statistics
    stats_query = f"""
        SELECT
            COUNT(*),
            AVG(risk_score)
        FROM journal_entries
        WHERE {where_clause}
    """
    stats = db.execute(stats_query, params)
    total_count = stats[0][0] or 0
    avg_risk = stats[0][1] or 0

    # Get distribution
    dist_query = """
        SELECT
            CASE
                WHEN risk_score >= 60 THEN 'high'
                WHEN risk_score >= 40 THEN 'medium'
                WHEN risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END as level,
            COUNT(*)
        FROM journal_entries
        WHERE fiscal_year = ?
        GROUP BY
            CASE
                WHEN risk_score >= 60 THEN 'high'
                WHEN risk_score >= 40 THEN 'medium'
                WHEN risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END
    """
    dist_result = db.execute(dist_query, [fiscal_year])
    distribution = {row[0]: row[1] for row in dist_result}

    return RiskDetailsResponse(
        entries=entries,
        total_count=total_count,
        avg_risk_score=round(avg_risk, 2),
        distribution=distribution,
    )


@router.get("/benford-detail", response_model=BenfordResponse)
async def get_benford_detail(
    fiscal_year: int = Query(...),
    account: str | None = Query(None),
) -> BenfordResponse:
    """Get detailed Benford's Law analysis.

    Args:
        fiscal_year: Fiscal year.
        account: Optional account filter.

    Returns:
        Detailed Benford analysis with digit distributions.
    """
    db = get_db()

    account_filter = ""
    params = [fiscal_year]
    if account:
        account_filter = "AND gl_account_number = ?"
        params.append(account)

    # Expected Benford distributions
    expected_first = {
        1: 0.301,
        2: 0.176,
        3: 0.125,
        4: 0.097,
        5: 0.079,
        6: 0.067,
        7: 0.058,
        8: 0.051,
        9: 0.046,
    }
    expected_second = {
        0: 0.120,
        1: 0.114,
        2: 0.109,
        3: 0.104,
        4: 0.100,
        5: 0.097,
        6: 0.093,
        7: 0.090,
        8: 0.088,
        9: 0.085,
    }

    # First digit distribution
    first_query = f"""
        SELECT
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) as digit,
            COUNT(*) as count
        FROM journal_entries
        WHERE fiscal_year = ?
            AND ABS(amount) >= 10
            {account_filter}
        GROUP BY
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER)
        HAVING digit BETWEEN 1 AND 9
        ORDER BY digit
    """
    first_result = db.execute(first_query, params)

    total_first = sum(row[1] for row in first_result) or 1
    first_digit_data = []
    for row in first_result:
        digit, count = row[0], row[1]
        actual_pct = count / total_first
        expected_pct = expected_first.get(digit, 0)
        deviation = actual_pct - expected_pct
        # Z-score approximation
        z_score = (
            deviation / (expected_pct * (1 - expected_pct) / total_first) ** 0.5
            if total_first > 0
            else 0
        )

        first_digit_data.append(
            BenfordDigitData(
                digit=digit,
                actual_count=count,
                actual_pct=round(actual_pct, 4),
                expected_pct=expected_pct,
                deviation=round(deviation, 4),
                z_score=round(z_score, 2),
            )
        )

    # Second digit distribution
    second_query = f"""
        SELECT
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 2, 1) AS INTEGER) as digit,
            COUNT(*) as count
        FROM journal_entries
        WHERE fiscal_year = ?
            AND ABS(amount) >= 100
            {account_filter}
        GROUP BY
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 2, 1) AS INTEGER)
        HAVING digit BETWEEN 0 AND 9
        ORDER BY digit
    """
    second_result = db.execute(second_query, params)

    total_second = sum(row[1] for row in second_result) or 1
    second_digit_data = []
    for row in second_result:
        digit, count = row[0], row[1]
        actual_pct = count / total_second
        expected_pct = expected_second.get(digit, 0)
        deviation = actual_pct - expected_pct
        z_score = (
            deviation / (expected_pct * (1 - expected_pct) / total_second) ** 0.5
            if total_second > 0
            else 0
        )

        second_digit_data.append(
            BenfordDigitData(
                digit=digit,
                actual_count=count,
                actual_pct=round(actual_pct, 4),
                expected_pct=expected_pct,
                deviation=round(deviation, 4),
                z_score=round(z_score, 2),
            )
        )

    # Calculate MAD
    mad_first = (
        sum(abs(d.deviation) for d in first_digit_data) / 9 if first_digit_data else 0
    )
    mad_second = (
        sum(abs(d.deviation) for d in second_digit_data) / 10
        if second_digit_data
        else 0
    )

    # Determine conformity
    if mad_first <= 0.006:
        conformity = "close"
    elif mad_first <= 0.012:
        conformity = "acceptable"
    elif mad_first <= 0.015:
        conformity = "marginally_acceptable"
    else:
        conformity = "nonconforming"

    # Find suspicious accounts (high deviation)
    suspicious_query = """
        WITH account_benford AS (
            SELECT
                gl_account_number,
                CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) as first_digit,
                COUNT(*) as count
            FROM journal_entries
            WHERE fiscal_year = ?
                AND ABS(amount) >= 10
            GROUP BY gl_account_number, first_digit
            HAVING first_digit BETWEEN 1 AND 9
        )
        SELECT
            gl_account_number,
            SUM(count) as total_count,
            SUM(CASE WHEN first_digit = 1 THEN count ELSE 0 END) as digit_1_count
        FROM account_benford
        GROUP BY gl_account_number
        HAVING total_count >= 100
        ORDER BY
            ABS(CAST(digit_1_count AS FLOAT) / total_count - 0.301) DESC
        LIMIT 10
    """
    suspicious_result = db.execute(suspicious_query, [fiscal_year])

    suspicious_accounts = [
        {
            "account": row[0],
            "total_count": row[1],
            "digit_1_pct": round(row[2] / row[1], 4) if row[1] > 0 else 0,
            "expected_pct": 0.301,
            "deviation": round(row[2] / row[1] - 0.301, 4) if row[1] > 0 else 0,
        }
        for row in suspicious_result
    ]

    return BenfordResponse(
        first_digit=first_digit_data,
        second_digit=second_digit_data,
        total_count=total_first,
        mad_first=round(mad_first, 4),
        mad_second=round(mad_second, 4),
        conformity=conformity,
        suspicious_accounts=suspicious_accounts,
    )


@router.get("/rules-summary")
async def get_rules_summary(fiscal_year: int = Query(...)) -> dict[str, Any]:
    """Get summary of rule violations by rule.

    Args:
        fiscal_year: Fiscal year.

    Returns:
        Summary statistics by rule.
    """
    db = get_db()

    query = """
        SELECT
            rv.rule_id,
            rv.rule_name,
            rv.category,
            rv.severity,
            COUNT(*) as violation_count,
            SUM(je.amount) as total_amount
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE je.fiscal_year = ?
        GROUP BY rv.rule_id, rv.rule_name, rv.category, rv.severity
        ORDER BY violation_count DESC
    """

    result = db.execute(query, [fiscal_year])

    rules = [
        {
            "rule_id": row[0],
            "rule_name": row[1],
            "category": row[2],
            "severity": row[3],
            "violation_count": row[4],
            "total_amount": row[5] or 0,
        }
        for row in result
    ]

    # Aggregate by category
    by_category = {}
    for rule in rules:
        cat = rule["category"]
        if cat not in by_category:
            by_category[cat] = {"count": 0, "rules": 0}
        by_category[cat]["count"] += rule["violation_count"]
        by_category[cat]["rules"] += 1

    # Aggregate by severity
    by_severity = {}
    for rule in rules:
        sev = rule["severity"]
        if sev not in by_severity:
            by_severity[sev] = 0
        by_severity[sev] += rule["violation_count"]

    return {
        "rules": rules,
        "total_rules_triggered": len(rules),
        "total_violations": sum(r["violation_count"] for r in rules),
        "by_category": by_category,
        "by_severity": by_severity,
    }


@router.post("/recalculate-scores")
async def recalculate_risk_scores(
    fiscal_year: int = Query(...),
    period: int | None = Query(None, ge=1, le=12),
) -> dict[str, Any]:
    """Recalculate risk scores for entries.

    Args:
        fiscal_year: Fiscal year.
        period: Optional specific period.

    Returns:
        Recalculation statistics.
    """
    try:
        scoring_service = RiskScoringService()

        if period:
            result = scoring_service.score_period(fiscal_year, period)
        else:
            result = scoring_service.score_fiscal_year(fiscal_year)

        return {
            "success": True,
            "fiscal_year": fiscal_year,
            "period": period,
            "entries_scored": result.get("entries_scored", 0),
            "avg_score": result.get("avg_score", 0),
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to recalculate scores: {str(e)}",
        )
