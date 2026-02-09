"""Dashboard API endpoints.

Provides REST API for dashboard data:
- KPIs and summary statistics
- Time series data
- Account analysis
- Risk distribution
- Benford analysis
"""

from datetime import date
from typing import Any

from fastapi import APIRouter, Query
from pydantic import BaseModel

from app.db import DuckDBManager

router = APIRouter()


def get_db() -> DuckDBManager:
    """Get DB instance."""
    return DuckDBManager()


class FilterParams(BaseModel):
    """Common filter parameters for dashboard queries."""

    fiscal_year: int
    period_from: int | None = None
    period_to: int | None = None
    date_from: date | None = None
    date_to: date | None = None
    accounts: list[str] | None = None
    departments: list[str] | None = None
    min_amount: float | None = None
    max_amount: float | None = None


class SummaryResponse(BaseModel):
    """Dashboard summary response."""

    total_entries: int
    total_amount: float
    debit_total: float
    credit_total: float
    unique_accounts: int
    unique_journals: int
    date_range: dict[str, str]
    high_risk_count: int
    anomaly_count: int


class TimeSeriesPoint(BaseModel):
    """Single point in time series data."""

    date: str
    amount: float
    count: int
    debit: float
    credit: float


class TimeSeriesResponse(BaseModel):
    """Time series data response."""

    data: list[TimeSeriesPoint]
    aggregation: str


class AccountSummary(BaseModel):
    """Account summary data."""

    account_code: str
    account_name: str
    debit_total: float
    credit_total: float
    net_amount: float
    entry_count: int


class AccountsResponse(BaseModel):
    """Accounts analysis response."""

    accounts: list[AccountSummary]
    total_accounts: int


class RiskItem(BaseModel):
    """Risk analysis item."""

    journal_id: str
    gl_detail_id: str
    risk_score: float
    risk_factors: list[str]
    amount: float
    date: str
    description: str


class RiskResponse(BaseModel):
    """Risk analysis response."""

    high_risk: list[RiskItem]
    medium_risk: list[RiskItem]
    low_risk: list[RiskItem]
    risk_distribution: dict[str, int]


@router.get("/summary", response_model=SummaryResponse)
async def get_dashboard_summary(
    fiscal_year: int = Query(..., description="Fiscal year"),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
) -> SummaryResponse:
    """Get dashboard summary statistics."""
    db = get_db()

    period_filter = ""
    if period_from:
        period_filter += f" AND accounting_period >= {period_from}"
    if period_to:
        period_filter += f" AND accounting_period <= {period_to}"

    query = f"""
        SELECT
            COUNT(*) as total_entries,
            COALESCE(SUM(ABS(amount)), 0) as total_amount,
            COALESCE(SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END), 0) as debit_total,
            COALESCE(SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END), 0) as credit_total,
            COUNT(DISTINCT gl_account_number) as unique_accounts,
            COUNT(DISTINCT journal_id) as unique_journals,
            MIN(effective_date) as min_date,
            MAX(effective_date) as max_date,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            SUM(CASE WHEN anomaly_flags IS NOT NULL AND anomaly_flags <> '' THEN 1 ELSE 0 END) as anomaly_count
        FROM journal_entries
        WHERE fiscal_year = ? {period_filter}
    """

    result = db.execute(query, [fiscal_year])

    if result:
        row = result[0]
        return SummaryResponse(
            total_entries=row[0] or 0,
            total_amount=row[1] or 0,
            debit_total=row[2] or 0,
            credit_total=row[3] or 0,
            unique_accounts=row[4] or 0,
            unique_journals=row[5] or 0,
            date_range={
                "from": str(row[6]) if row[6] else "",
                "to": str(row[7]) if row[7] else "",
            },
            high_risk_count=row[8] or 0,
            anomaly_count=row[9] or 0,
        )

    return SummaryResponse(
        total_entries=0,
        total_amount=0.0,
        debit_total=0.0,
        credit_total=0.0,
        unique_accounts=0,
        unique_journals=0,
        date_range={"from": "", "to": ""},
        high_risk_count=0,
        anomaly_count=0,
    )


@router.get("/timeseries", response_model=TimeSeriesResponse)
async def get_time_series(
    fiscal_year: int = Query(...),
    aggregation: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
) -> TimeSeriesResponse:
    """Get time series data for charts."""
    db = get_db()

    period_filter = ""
    if period_from:
        period_filter += f" AND accounting_period >= {period_from}"
    if period_to:
        period_filter += f" AND accounting_period <= {period_to}"

    if aggregation == "monthly":
        date_expr = "DATE_TRUNC('month', effective_date)"
    elif aggregation == "weekly":
        date_expr = "DATE_TRUNC('week', effective_date)"
    else:
        date_expr = "CAST(effective_date AS DATE)"

    query = f"""
        SELECT
            {date_expr} as date_key,
            COALESCE(SUM(ABS(amount)), 0) as amount,
            COUNT(*) as count,
            COALESCE(SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END), 0) as debit,
            COALESCE(SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END), 0) as credit
        FROM journal_entries
        WHERE fiscal_year = ? {period_filter}
        GROUP BY {date_expr}
        ORDER BY date_key
    """

    result = db.execute(query, [fiscal_year])

    data = [
        TimeSeriesPoint(
            date=str(row[0]),
            amount=row[1] or 0,
            count=row[2] or 0,
            debit=row[3] or 0,
            credit=row[4] or 0,
        )
        for row in result
    ]

    return TimeSeriesResponse(data=data, aggregation=aggregation)


@router.get("/accounts", response_model=AccountsResponse)
async def get_accounts_analysis(
    fiscal_year: int = Query(...),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    limit: int = Query(50, le=500),
) -> AccountsResponse:
    """Get account-level analysis."""
    db = get_db()

    period_filter = ""
    if period_from:
        period_filter += f" AND accounting_period >= {period_from}"
    if period_to:
        period_filter += f" AND accounting_period <= {period_to}"

    query = f"""
        SELECT
            gl_account_number,
            COALESCE(SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END), 0) as debit_total,
            COALESCE(SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END), 0) as credit_total,
            COALESCE(SUM(amount), 0) as net_amount,
            COUNT(*) as entry_count
        FROM journal_entries
        WHERE fiscal_year = ? {period_filter}
        GROUP BY gl_account_number
        ORDER BY ABS(net_amount) DESC
        LIMIT {limit}
    """

    result = db.execute(query, [fiscal_year])

    accounts = [
        AccountSummary(
            account_code=row[0] or "",
            account_name=row[0] or "",  # Would join with chart_of_accounts
            debit_total=row[1] or 0,
            credit_total=row[2] or 0,
            net_amount=row[3] or 0,
            entry_count=row[4] or 0,
        )
        for row in result
    ]

    # Get total count
    count_query = f"""
        SELECT COUNT(DISTINCT gl_account_number)
        FROM journal_entries
        WHERE fiscal_year = ? {period_filter}
    """
    count_result = db.execute(count_query, [fiscal_year])
    total_accounts = count_result[0][0] if count_result else 0

    return AccountsResponse(accounts=accounts, total_accounts=total_accounts)


@router.get("/risk", response_model=RiskResponse)
async def get_risk_analysis(
    fiscal_year: int = Query(...),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    limit: int = Query(100, le=1000),
) -> RiskResponse:
    """Get risk analysis results."""
    db = get_db()

    period_filter = ""
    if period_from:
        period_filter += f" AND accounting_period >= {period_from}"
    if period_to:
        period_filter += f" AND accounting_period <= {period_to}"

    def get_risk_items(min_score: float, max_score: float) -> list[RiskItem]:
        query = f"""
            SELECT
                journal_id,
                gl_detail_id,
                risk_score,
                rule_violations,
                amount,
                effective_date,
                je_line_description
            FROM journal_entries
            WHERE fiscal_year = ?
                AND risk_score >= {min_score}
                AND risk_score < {max_score}
                {period_filter}
            ORDER BY risk_score DESC
            LIMIT {limit // 3}
        """
        result = db.execute(query, [fiscal_year])

        return [
            RiskItem(
                journal_id=row[0] or "",
                gl_detail_id=row[1] or "",
                risk_score=row[2] or 0,
                risk_factors=(row[3] or "").split(",") if row[3] else [],
                amount=row[4] or 0,
                date=str(row[5]) if row[5] else "",
                description=row[6] or "",
            )
            for row in result
        ]

    high_risk = get_risk_items(60, 101)
    medium_risk = get_risk_items(40, 60)
    low_risk = get_risk_items(20, 40)

    # Get distribution
    dist_query = f"""
        SELECT
            CASE
                WHEN risk_score >= 60 THEN 'high'
                WHEN risk_score >= 40 THEN 'medium'
                WHEN risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END as level,
            COUNT(*) as count
        FROM journal_entries
        WHERE fiscal_year = ? {period_filter}
        GROUP BY
            CASE
                WHEN risk_score >= 60 THEN 'high'
                WHEN risk_score >= 40 THEN 'medium'
                WHEN risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END
    """
    dist_result = db.execute(dist_query, [fiscal_year])

    distribution = {"high": 0, "medium": 0, "low": 0, "minimal": 0}
    for row in dist_result:
        distribution[row[0]] = row[1]

    return RiskResponse(
        high_risk=high_risk,
        medium_risk=medium_risk,
        low_risk=low_risk,
        risk_distribution=distribution,
    )


@router.get("/kpi")
async def get_kpi(fiscal_year: int) -> dict[str, Any]:
    """Get key performance indicators."""
    db = get_db()

    query = """
        SELECT
            COUNT(*) as total_entries,
            COUNT(DISTINCT journal_id) as total_journals,
            SUM(ABS(amount)) as total_amount,
            COUNT(DISTINCT prepared_by) as unique_users,
            COUNT(DISTINCT gl_account_number) as unique_accounts,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            AVG(CASE WHEN risk_score > 0 THEN risk_score END) as avg_risk_score,
            SUM(CASE WHEN prepared_by = approved_by AND prepared_by IS NOT NULL THEN 1 ELSE 0 END) as self_approval_count
        FROM journal_entries
        WHERE fiscal_year = ?
    """

    result = db.execute(query, [fiscal_year])

    if result:
        row = result[0]
        total = row[0] or 1
        return {
            "fiscal_year": fiscal_year,
            "total_entries": row[0] or 0,
            "total_journals": row[1] or 0,
            "total_amount": row[2] or 0,
            "unique_users": row[3] or 0,
            "unique_accounts": row[4] or 0,
            "high_risk_count": row[5] or 0,
            "high_risk_pct": round((row[5] or 0) / total * 100, 2),
            "avg_risk_score": round(row[6] or 0, 2),
            "self_approval_count": row[7] or 0,
        }

    return {"fiscal_year": fiscal_year}


@router.get("/benford")
async def get_benford_distribution(fiscal_year: int) -> dict[str, Any]:
    """Get Benford's Law distribution analysis."""
    db = get_db()

    expected = {
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

    query = """
        SELECT
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) as first_digit,
            COUNT(*) as count
        FROM journal_entries
        WHERE fiscal_year = ?
            AND ABS(amount) >= 10
        GROUP BY
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER)
        HAVING
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) BETWEEN 1 AND 9
        ORDER BY first_digit
    """

    result = db.execute(query, [fiscal_year])

    total = sum(row[1] for row in result)
    distribution = []

    for row in result:
        digit, count = row[0], row[1]
        actual_pct = count / total if total > 0 else 0
        expected_pct = expected.get(digit, 0)
        distribution.append(
            {
                "digit": digit,
                "count": count,
                "actual_pct": round(actual_pct, 4),
                "expected_pct": expected_pct,
                "deviation": round(actual_pct - expected_pct, 4),
            }
        )

    mad = sum(abs(d["deviation"]) for d in distribution) / 9 if distribution else 0

    return {
        "distribution": distribution,
        "total_count": total,
        "mad": round(mad, 4),
        "conformity": (
            "close"
            if mad <= 0.006
            else "acceptable"
            if mad <= 0.012
            else "marginally_acceptable"
            if mad <= 0.015
            else "nonconforming"
        ),
    }
