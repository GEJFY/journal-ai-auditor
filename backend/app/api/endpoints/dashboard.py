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

from app.core.cache import TTLCache
from app.db import DuckDBManager
from app.db import get_db as get_global_db

router = APIRouter()

# ダッシュボードクエリキャッシュ（TTL 5分）
_dashboard_cache = TTLCache(max_size=128, ttl_seconds=300)


def get_db() -> DuckDBManager:
    """Get DB instance."""
    return get_global_db()


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
    # Advanced filters
    account_codes: list[str] | None = None
    account_types: list[str] | None = None
    account_classes: list[str] | None = None
    account_groups: list[str] | None = None
    fs_line_items: list[str] | None = None


def build_filter_clause(params: FilterParams) -> tuple[str, list[Any]]:
    """Build SQL WHERE clause and parameters from filter params."""
    clauses = ["je.fiscal_year = ?"]
    args: list[Any] = [params.fiscal_year]

    if params.period_from:
        clauses.append("je.accounting_period >= ?")
        args.append(params.period_from)
    if params.period_to:
        clauses.append("je.accounting_period <= ?")
        args.append(params.period_to)

    # Advanced filters (requires JOIN with chart_of_accounts coa)
    if params.account_codes:
        placeholders = ",".join(["?" for _ in params.account_codes])
        clauses.append(f"je.gl_account_number IN ({placeholders})")
        args.extend(params.account_codes)

    if params.account_types:
        placeholders = ",".join(["?" for _ in params.account_types])
        clauses.append(f"coa.account_type IN ({placeholders})")
        args.extend(params.account_types)

    if params.account_classes:
        placeholders = ",".join(["?" for _ in params.account_classes])
        clauses.append(f"coa.account_class IN ({placeholders})")
        args.extend(params.account_classes)

    if params.account_groups:
        placeholders = ",".join(["?" for _ in params.account_groups])
        clauses.append(f"coa.account_group IN ({placeholders})")
        args.extend(params.account_groups)

    if params.fs_line_items:
        placeholders = ",".join(["?" for _ in params.fs_line_items])
        clauses.append(f"coa.fs_line_item IN ({placeholders})")
        args.extend(params.fs_line_items)

    return " AND ".join(clauses), args


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


class FinancialMetric(BaseModel):
    """Financial metric item."""

    label: str
    amount: float
    ratio: float | None = None
    order: int


class BalanceSheetMetrics(BaseModel):
    """Balance sheet summary."""

    assets: float
    liabilities: float
    equity: float
    imbalance: float


class FinancialMetricsResponse(BaseModel):
    """Financial analysis response."""

    pl_metrics: list[FinancialMetric]
    bs_metrics: BalanceSheetMetrics


@router.get("/financial-metrics", response_model=FinancialMetricsResponse)
async def get_financial_metrics(fiscal_year: int) -> FinancialMetricsResponse:
    """Get financial statement metrics."""
    db = get_db()

    # Aggregate by account classifications
    query = """
        SELECT
            coa.account_category,
            coa.account_type,
            coa.account_class,
            coa.account_group,
            SUM(CASE WHEN je.debit_credit_indicator = 'D' THEN je.amount ELSE -je.amount END) as net_debit,
            SUM(CASE WHEN je.debit_credit_indicator = 'C' THEN je.amount ELSE -je.amount END) as net_credit
        FROM journal_entries je
        LEFT JOIN chart_of_accounts coa ON je.gl_account_number = coa.account_code
        WHERE je.fiscal_year = ?
        GROUP BY coa.account_category, coa.account_type, coa.account_class, coa.account_group
    """

    result = db.execute(query, [fiscal_year])

    total_assets = 0.0
    total_liabilities = 0.0
    total_equity = 0.0

    total_revenue = 0.0
    total_cost_of_sales = 0.0
    total_expenses = 0.0
    total_other_income = 0.0
    total_other_expense = 0.0

    for row in result:
        cat = (row[0] or "").upper()
        atype = (row[1] or "").upper()
        aclass = (row[2] or "").upper()
        agroup = (row[3] or "").upper()

        net_dr = float(row[4] or 0.0)
        net_cr = float(row[5] or 0.0)

        # BS logic
        is_bs = (
            cat == "BS" or "ASSET" in atype or "LIABILITY" in atype or "EQUITY" in atype
        )
        if is_bs:
            if "ASSET" in atype or "ASSET" in aclass:
                total_assets += net_dr
            elif "LIABILITY" in atype or "LIABILITY" in aclass:
                total_liabilities += net_cr
            elif "EQUITY" in atype or "CAPITAL" in atype:
                total_equity += net_cr
            else:
                if net_cr > 0:
                    total_liabilities += net_cr
                else:
                    total_assets += net_dr
        # PL logic
        else:
            if "REVENUE" in atype or "SALES" in atype or "INCOME" in atype:
                if "NON-OPERATING" in aclass or "OTHER" in aclass or "OTHER" in agroup:
                    total_other_income += net_cr
                else:
                    total_revenue += net_cr
            elif "EXPENSE" in atype or "COST" in atype:
                if "COST" in atype or "COST" in aclass or "COGS" in atype:
                    total_cost_of_sales += net_dr
                elif "NON-OPERATING" in aclass or "OTHER" in aclass or "TAX" in atype:
                    total_other_expense += net_dr
                else:
                    total_expenses += net_dr
            else:
                if net_cr > 0:
                    total_revenue += net_cr
                else:
                    total_expenses += net_dr

    gross_profit = total_revenue - total_cost_of_sales
    operating_income = gross_profit - total_expenses
    ordinary_income = operating_income + total_other_income - total_other_expense
    net_income = ordinary_income

    base = total_revenue if total_revenue != 0 else 1.0

    pl_metrics = [
        FinancialMetric(label="Net Sales", amount=total_revenue, ratio=100.0, order=1),
        FinancialMetric(
            label="Cost of Sales",
            amount=total_cost_of_sales,
            ratio=round(total_cost_of_sales / base * 100, 1),
            order=2,
        ),
        FinancialMetric(
            label="Gross Profit",
            amount=gross_profit,
            ratio=round(gross_profit / base * 100, 1),
            order=3,
        ),
        FinancialMetric(
            label="Operating Expenses",
            amount=total_expenses,
            ratio=round(total_expenses / base * 100, 1),
            order=4,
        ),
        FinancialMetric(
            label="Operating Income",
            amount=operating_income,
            ratio=round(operating_income / base * 100, 1),
            order=5,
        ),
        FinancialMetric(
            label="Ordinary Income",
            amount=ordinary_income,
            ratio=round(ordinary_income / base * 100, 1),
            order=6,
        ),
        FinancialMetric(
            label="Net Income",
            amount=net_income,
            ratio=round(net_income / base * 100, 1),
            order=7,
        ),
    ]

    bs_metrics = BalanceSheetMetrics(
        assets=round(total_assets, 2),
        liabilities=round(total_liabilities, 2),
        equity=round(total_equity, 2),
        imbalance=round(total_assets - (total_liabilities + total_equity), 2),
    )

    return FinancialMetricsResponse(pl_metrics=pl_metrics, bs_metrics=bs_metrics)


@router.get("/fiscal-years")
async def get_fiscal_years() -> dict[str, Any]:
    """Get list of fiscal years that have journal data."""
    db = get_db()
    try:
        result = db.execute(
            "SELECT DISTINCT fiscal_year FROM journal_entries ORDER BY fiscal_year DESC"
        )
        years = [row[0] for row in result if row[0] is not None]
    except Exception:
        years = []
    return {"fiscal_years": years}


@router.get("/summary", response_model=SummaryResponse)
async def get_dashboard_summary(
    fiscal_year: int = Query(..., description="Fiscal year"),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    # Advanced filters
    account_codes: list[str] | None = Query(None),
    account_types: list[str] | None = Query(None),
    account_classes: list[str] | None = Query(None),
    account_groups: list[str] | None = Query(None),
    fs_line_items: list[str] | None = Query(None),
) -> SummaryResponse:
    """Get dashboard summary statistics."""
    cache_key = _dashboard_cache._make_key(
        "summary", fiscal_year, period_from, period_to
    )
    cached = _dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

    db = get_db()

    filters = FilterParams(
        fiscal_year=fiscal_year,
        period_from=period_from,
        period_to=period_to,
        account_codes=account_codes,
        account_types=account_types,
        account_classes=account_classes,
        account_groups=account_groups,
        fs_line_items=fs_line_items,
    )
    where_clause, query_args = build_filter_clause(filters)

    # Need to join coa if any account-related filters are present,
    # but for simplicity/performance in summary, we might want to restrict advanced filters here?
    # Or just support them. Let's support them.

    join_clause = """
        LEFT JOIN chart_of_accounts coa ON je.gl_account_number = coa.account_code
    """

    query = f"""
        SELECT
            COUNT(*) as total_entries,
            COALESCE(SUM(ABS(je.amount)), 0) as total_amount,
            COALESCE(SUM(CASE WHEN je.debit_credit_indicator = 'D' THEN je.amount ELSE 0 END), 0) as debit_total,
            COALESCE(SUM(CASE WHEN je.debit_credit_indicator = 'C' THEN je.amount ELSE 0 END), 0) as credit_total,
            COUNT(DISTINCT je.gl_account_number) as unique_accounts,
            COUNT(DISTINCT je.journal_id) as unique_journals,
            MIN(je.effective_date) as min_date,
            MAX(je.effective_date) as max_date,
            SUM(CASE WHEN je.risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            SUM(CASE WHEN je.anomaly_flags IS NOT NULL AND je.anomaly_flags <> '' THEN 1 ELSE 0 END) as anomaly_count
        FROM journal_entries je
        {join_clause}
        WHERE {where_clause}
    """

    result = db.execute(query, query_args)

    if result:
        row = result[0]
        response = SummaryResponse(
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
    else:
        response = SummaryResponse(
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

    _dashboard_cache.set(cache_key, response)
    return response


@router.get("/timeseries", response_model=TimeSeriesResponse)
async def get_time_series(
    fiscal_year: int = Query(...),
    aggregation: str = Query("daily", regex="^(daily|weekly|monthly)$"),
    period_from: int | None = Query(None, ge=1, le=12),
    period_to: int | None = Query(None, ge=1, le=12),
    # Advanced filters
    account_codes: list[str] | None = Query(None),
    account_types: list[str] | None = Query(None),
    account_classes: list[str] | None = Query(None),
    account_groups: list[str] | None = Query(None),
    fs_line_items: list[str] | None = Query(None),
) -> TimeSeriesResponse:
    """Get time series data for charts."""
    db = get_db()

    filters = FilterParams(
        fiscal_year=fiscal_year,
        period_from=period_from,
        period_to=period_to,
        account_codes=account_codes,
        account_types=account_types,
        account_classes=account_classes,
        account_groups=account_groups,
        fs_line_items=fs_line_items,
    )
    where_clause, query_args = build_filter_clause(filters)

    if aggregation == "monthly":
        date_expr = "DATE_TRUNC('month', je.effective_date)"
    elif aggregation == "weekly":
        date_expr = "DATE_TRUNC('week', je.effective_date)"
    else:
        date_expr = "CAST(je.effective_date AS DATE)"

    query = f"""
        SELECT
            {date_expr} as date_key,
            COALESCE(SUM(ABS(je.amount)), 0) as amount,
            COUNT(*) as count,
            COALESCE(SUM(CASE WHEN je.debit_credit_indicator = 'D' THEN je.amount ELSE 0 END), 0) as debit,
            COALESCE(SUM(CASE WHEN je.debit_credit_indicator = 'C' THEN je.amount ELSE 0 END), 0) as credit
        FROM journal_entries je
        LEFT JOIN chart_of_accounts coa ON je.gl_account_number = coa.account_code
        WHERE {where_clause}
        GROUP BY {date_expr}
        ORDER BY date_key
    """

    result = db.execute(query, query_args)

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
            je.gl_account_number,
            COALESCE(SUM(CASE WHEN je.debit_credit_indicator = 'D' THEN je.amount ELSE 0 END), 0) as debit_total,
            COALESCE(SUM(CASE WHEN je.debit_credit_indicator = 'C' THEN je.amount ELSE 0 END), 0) as credit_total,
            COALESCE(SUM(je.amount), 0) as net_amount,
            COUNT(*) as entry_count,
            MAX(coa.account_name) as account_name
        FROM journal_entries je
        LEFT JOIN chart_of_accounts coa
            ON je.gl_account_number = coa.account_code
        WHERE je.fiscal_year = ? {period_filter.replace("accounting_period", "je.accounting_period")}
        GROUP BY je.gl_account_number
        ORDER BY ABS(COALESCE(SUM(je.amount), 0)) DESC
        LIMIT {limit}
    """

    result = db.execute(query, [fiscal_year])

    accounts = [
        AccountSummary(
            account_code=row[0] or "",
            account_name=row[5] or row[0] or "",
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
    # Advanced filters
    account_codes: list[str] | None = Query(None),
    account_types: list[str] | None = Query(None),
    account_classes: list[str] | None = Query(None),
    account_groups: list[str] | None = Query(None),
    fs_line_items: list[str] | None = Query(None),
) -> RiskResponse:
    """Get risk analysis results."""
    db = get_db()

    filters = FilterParams(
        fiscal_year=fiscal_year,
        period_from=period_from,
        period_to=period_to,
        account_codes=account_codes,
        account_types=account_types,
        account_classes=account_classes,
        account_groups=account_groups,
        fs_line_items=fs_line_items,
    )
    where_clause, query_args = build_filter_clause(filters)

    # 1クエリでhigh/medium/lowを一括取得
    items_query = f"""
        SELECT
            je.journal_id,
            je.gl_detail_id,
            je.risk_score,
            je.rule_violations,
            je.amount,
            je.effective_date,
            je.je_line_description,
            CASE
                WHEN je.risk_score >= 60 THEN 'high'
                WHEN je.risk_score >= 40 THEN 'medium'
                ELSE 'low'
            END as risk_level
        FROM journal_entries je
        LEFT JOIN chart_of_accounts coa ON je.gl_account_number = coa.account_code
        WHERE {where_clause}
            AND je.risk_score >= 20
        ORDER BY je.risk_score DESC
        LIMIT {limit}
    """
    items_result = db.execute(items_query, query_args)

    high_risk: list[RiskItem] = []
    medium_risk: list[RiskItem] = []
    low_risk: list[RiskItem] = []
    per_level_limit = limit // 3

    for row in items_result:
        item = RiskItem(
            journal_id=row[0] or "",
            gl_detail_id=row[1] or "",
            risk_score=row[2] or 0,
            risk_factors=(row[3] or "").split(",") if row[3] else [],
            amount=row[4] or 0,
            date=str(row[5]) if row[5] else "",
            description=row[6] or "",
        )
        level = row[7]
        if level == "high" and len(high_risk) < per_level_limit:
            high_risk.append(item)
        elif level == "medium" and len(medium_risk) < per_level_limit:
            medium_risk.append(item)
        elif level == "low" and len(low_risk) < per_level_limit:
            low_risk.append(item)

    # リスク分布（集計のみ、軽量）
    dist_query = f"""
        SELECT
            CASE
                WHEN je.risk_score >= 60 THEN 'high'
                WHEN je.risk_score >= 40 THEN 'medium'
                WHEN je.risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END as level,
            COUNT(*) as count
        FROM journal_entries je
        LEFT JOIN chart_of_accounts coa ON je.gl_account_number = coa.account_code
        WHERE {where_clause}
        GROUP BY
            CASE
                WHEN je.risk_score >= 60 THEN 'high'
                WHEN je.risk_score >= 40 THEN 'medium'
                WHEN je.risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END
    """
    dist_result = db.execute(dist_query, query_args)

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
    cache_key = _dashboard_cache._make_key("kpi", fiscal_year)
    cached = _dashboard_cache.get(cache_key)
    if cached is not None:
        return cached

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
        response = {
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
    else:
        response = {"fiscal_year": fiscal_year}

    _dashboard_cache.set(cache_key, response)
    return response


class PeriodComparisonItem(BaseModel):
    """期間比較データ項目。"""

    account_code: str
    account_name: str
    current_amount: float
    previous_amount: float
    change_amount: float
    change_percent: float | None


class PeriodComparisonResponse(BaseModel):
    """期間比較レスポンス。"""

    items: list[PeriodComparisonItem]
    comparison_type: str
    current_period: str
    previous_period: str
    total_current: float
    total_previous: float


@router.get("/period-comparison", response_model=PeriodComparisonResponse)
async def get_period_comparison(
    fiscal_year: int = Query(...),
    period: int = Query(..., ge=1, le=12, description="比較対象の会計期間"),
    comparison_type: str = Query(
        "mom", regex="^(mom|yoy)$", description="mom=前月比, yoy=前年同月比"
    ),
    limit: int = Query(20, le=100),
) -> PeriodComparisonResponse:
    """勘定科目別の期間比較データを取得する。"""
    db = get_db()

    if comparison_type == "mom":
        # 前月比: 同一年度内で前月と比較
        current_period = period
        previous_period = period - 1
        current_year = fiscal_year
        previous_year = fiscal_year
        current_label = f"{fiscal_year}年 第{current_period}期"
        previous_label = f"{fiscal_year}年 第{previous_period}期"

        if previous_period < 1:
            return PeriodComparisonResponse(
                items=[],
                comparison_type=comparison_type,
                current_period=current_label,
                previous_period="N/A",
                total_current=0,
                total_previous=0,
            )
    else:
        # 前年同月比
        current_period = period
        previous_period = period
        current_year = fiscal_year
        previous_year = fiscal_year - 1
        current_label = f"{current_year}年 第{current_period}期"
        previous_label = f"{previous_year}年 第{previous_period}期"

    query = f"""
        WITH current_data AS (
            SELECT
                gl_account_number,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE -amount END) as net_amount
            FROM journal_entries
            WHERE fiscal_year = ? AND accounting_period = ?
            GROUP BY gl_account_number
        ),
        previous_data AS (
            SELECT
                gl_account_number,
                SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE -amount END) as net_amount
            FROM journal_entries
            WHERE fiscal_year = ? AND accounting_period = ?
            GROUP BY gl_account_number
        )
        SELECT
            COALESCE(c.gl_account_number, p.gl_account_number) as account_code,
            COALESCE(coa.account_name, COALESCE(c.gl_account_number, p.gl_account_number)) as account_name,
            COALESCE(c.net_amount, 0) as current_amount,
            COALESCE(p.net_amount, 0) as previous_amount
        FROM current_data c
        FULL OUTER JOIN previous_data p
            ON c.gl_account_number = p.gl_account_number
        LEFT JOIN chart_of_accounts coa
            ON COALESCE(c.gl_account_number, p.gl_account_number) = coa.account_code
        ORDER BY ABS(COALESCE(c.net_amount, 0) - COALESCE(p.net_amount, 0)) DESC
        LIMIT {limit}
    """

    result = db.execute(
        query, [current_year, current_period, previous_year, previous_period]
    )

    items = []
    total_current = 0.0
    total_previous = 0.0

    for row in result:
        current_amt = row[2] or 0.0
        previous_amt = row[3] or 0.0
        change = current_amt - previous_amt
        pct = (change / previous_amt * 100) if previous_amt != 0 else None

        items.append(
            PeriodComparisonItem(
                account_code=row[0] or "",
                account_name=row[1] or "",
                current_amount=current_amt,
                previous_amount=previous_amt,
                change_amount=change,
                change_percent=round(pct, 2) if pct is not None else None,
            )
        )
        total_current += abs(current_amt)
        total_previous += abs(previous_amt)

    return PeriodComparisonResponse(
        items=items,
        comparison_type=comparison_type,
        current_period=current_label,
        previous_period=previous_label,
        total_current=total_current,
        total_previous=total_previous,
    )


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


class FilterOptionsResponse(BaseModel):
    """Filter options response."""

    account_codes: list[dict[str, str]]  # code, name
    account_types: list[str]
    account_classes: list[str]
    account_groups: list[str]
    fs_line_items: list[str]
    users: list[str]


@router.get("/filter-options", response_model=FilterOptionsResponse)
async def get_filter_options() -> FilterOptionsResponse:
    """Get available filter options from chart of accounts."""
    db = get_db()

    # Get all options in one go if possible, or multiple queries
    # DuckDB is fast, multiple queries are fine.

    # 1. Accounts
    accounts_res = db.execute(
        "SELECT account_code, account_name FROM chart_of_accounts ORDER BY account_code"
    )
    accounts = [{"code": row[0], "name": row[1]} for row in accounts_res]

    # 2. Account Types
    types_res = db.execute(
        "SELECT DISTINCT account_type FROM chart_of_accounts WHERE account_type IS NOT NULL ORDER BY account_type"
    )
    types = [row[0] for row in types_res]

    # 3. Account Classes
    classes_res = db.execute(
        "SELECT DISTINCT account_class FROM chart_of_accounts WHERE account_class IS NOT NULL ORDER BY account_class"
    )
    classes = [row[0] for row in classes_res]

    # 4. Account Groups
    groups_res = db.execute(
        "SELECT DISTINCT account_group FROM chart_of_accounts WHERE account_group IS NOT NULL ORDER BY account_group"
    )
    groups = [row[0] for row in groups_res]

    # 5. FS Line Items
    fs_items_res = db.execute(
        "SELECT DISTINCT fs_line_item FROM chart_of_accounts WHERE fs_line_item IS NOT NULL ORDER BY fs_line_item"
    )
    fs_items = [row[0] for row in fs_items_res]

    # 6. Users (Prepared By)
    # This might be slow if the table is large, but acceptable for this use case
    users_res = db.execute(
        "SELECT DISTINCT prepared_by FROM journal_entries WHERE prepared_by IS NOT NULL ORDER BY prepared_by"
    )
    users = [row[0] for row in users_res]

    return FilterOptionsResponse(
        account_codes=accounts,
        account_types=types,
        account_classes=classes,
        account_groups=groups,
        fs_line_items=fs_items,
        users=users,
    )


# ============================================================
# 部門分析・取引先分析・勘定科目フロー
# ============================================================


@router.get("/departments")
async def get_department_analysis(
    fiscal_year: int = Query(..., description="Fiscal year"),
    limit: int = Query(50, le=200),
) -> dict[str, Any]:
    """Get department-level analytics.

    Returns department breakdown with entry counts, amounts,
    risk scores, and self-approval rates.
    """
    db = get_db()

    query = """
        SELECT
            dept_code,
            COUNT(*) as entry_count,
            COUNT(DISTINCT journal_id) as journal_count,
            SUM(CASE WHEN debit_credit_indicator = 'D' THEN amount ELSE 0 END) as debit_total,
            SUM(CASE WHEN debit_credit_indicator = 'C' THEN amount ELSE 0 END) as credit_total,
            AVG(ABS(amount)) as avg_amount,
            COUNT(DISTINCT prepared_by) as unique_users,
            AVG(risk_score) as avg_risk_score,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            SUM(CASE WHEN prepared_by = approved_by THEN 1 ELSE 0 END) as self_approval_count
        FROM journal_entries
        WHERE fiscal_year = ?
          AND dept_code IS NOT NULL
          AND dept_code <> ''
        GROUP BY dept_code
        ORDER BY entry_count DESC
        LIMIT ?
    """

    try:
        rows = db.execute(query, [fiscal_year, limit])
        departments = [
            {
                "dept_code": r[0],
                "entry_count": r[1],
                "journal_count": r[2],
                "debit_total": float(r[3] or 0),
                "credit_total": float(r[4] or 0),
                "avg_amount": float(r[5] or 0),
                "unique_users": r[6],
                "avg_risk_score": round(float(r[7] or 0), 2),
                "high_risk_count": r[8],
                "self_approval_count": r[9],
                "self_approval_rate": round(r[9] / r[1] * 100, 1) if r[1] else 0,
            }
            for r in rows
        ]
        return {"departments": departments, "total": len(departments)}
    except Exception:
        return {"departments": [], "total": 0}


@router.get("/vendors")
async def get_vendor_analysis(
    fiscal_year: int = Query(..., description="Fiscal year"),
    limit: int = Query(50, le=200),
) -> dict[str, Any]:
    """Get vendor concentration analysis.

    Returns top vendors ranked by transaction volume with risk indicators.
    """
    db = get_db()

    query = """
        SELECT
            vendor_code,
            COUNT(*) as transaction_count,
            COUNT(DISTINCT journal_id) as journal_count,
            SUM(ABS(amount)) as total_amount,
            AVG(ABS(amount)) as avg_amount,
            MAX(ABS(amount)) as max_amount,
            AVG(risk_score) as avg_risk_score,
            MAX(risk_score) as max_risk_score,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            MIN(effective_date) as first_transaction,
            MAX(effective_date) as last_transaction
        FROM journal_entries
        WHERE fiscal_year = ?
          AND vendor_code IS NOT NULL
          AND vendor_code <> ''
        GROUP BY vendor_code
        ORDER BY total_amount DESC
        LIMIT ?
    """

    try:
        rows = db.execute(query, [fiscal_year, limit])
        vendors = [
            {
                "vendor_code": r[0],
                "transaction_count": r[1],
                "journal_count": r[2],
                "total_amount": float(r[3] or 0),
                "avg_amount": float(r[4] or 0),
                "max_amount": float(r[5] or 0),
                "avg_risk_score": round(float(r[6] or 0), 2),
                "max_risk_score": round(float(r[7] or 0), 2),
                "high_risk_count": r[8],
                "first_transaction": str(r[9]) if r[9] else None,
                "last_transaction": str(r[10]) if r[10] else None,
            }
            for r in rows
        ]
        return {"vendors": vendors, "total": len(vendors)}
    except Exception:
        return {"vendors": [], "total": 0}


@router.get("/account-flow")
async def get_account_flow(
    fiscal_year: int = Query(..., description="Fiscal year"),
    min_amount: float = Query(0, description="Minimum flow amount"),
    limit: int = Query(50, le=200),
) -> dict[str, Any]:
    """Get account-to-account fund flow analysis.

    Analyzes debit-credit pairs within the same journal to map
    fund movement between accounts.
    """
    db = get_db()
    params: list = [fiscal_year, fiscal_year]
    having = ""
    if min_amount > 0:
        having = "HAVING SUM(d.amount) >= ?"
        params.append(min_amount)
    params.append(limit)

    query = f"""
        SELECT
            d.gl_account_number as source_account,
            c.gl_account_number as target_account,
            COUNT(DISTINCT d.journal_id) as transaction_count,
            SUM(d.amount) as flow_amount,
            AVG(d.amount) as avg_amount
        FROM journal_entries d
        JOIN journal_entries c
            ON d.journal_id = c.journal_id
            AND d.debit_credit_indicator = 'D'
            AND c.debit_credit_indicator = 'C'
            AND d.gl_detail_id <> c.gl_detail_id
        WHERE d.fiscal_year = ?
          AND c.fiscal_year = ?
        GROUP BY d.gl_account_number, c.gl_account_number
        {having}
        ORDER BY flow_amount DESC
        LIMIT ?
    """

    try:
        rows = db.execute(query, params)
        flows = [
            {
                "source_account": r[0],
                "target_account": r[1],
                "transaction_count": r[2],
                "flow_amount": float(r[3] or 0),
                "avg_amount": float(r[4] or 0),
            }
            for r in rows
        ]
        return {"flows": flows, "total": len(flows)}
    except Exception:
        return {"flows": [], "total": 0}
