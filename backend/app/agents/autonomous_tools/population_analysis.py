"""母集団統計分析ツール。

仕訳データ全体の統計的特性を分析する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_population_statistics(
    fiscal_year: int, account_prefix: str | None = None
) -> ToolResult:
    """母集団の統計情報を算出。"""
    db = duckdb_manager
    where = "WHERE fiscal_year = ?"
    params: list[object] = [fiscal_year]
    if account_prefix:
        where += " AND gl_account_number LIKE ?"
        params.append(f"{account_prefix}%")

    query = f"""
        SELECT
            COUNT(*) as total_count,
            COUNT(DISTINCT journal_id) as unique_journals,
            COUNT(DISTINCT gl_account_number) as unique_accounts,
            COUNT(DISTINCT prepared_by) as unique_preparers,
            COUNT(DISTINCT approved_by) as unique_approvers,
            SUM(CASE WHEN debit_credit_indicator='D' THEN amount ELSE 0 END) as total_debit,
            SUM(CASE WHEN debit_credit_indicator='C' THEN amount ELSE 0 END) as total_credit,
            AVG(ABS(amount)) as avg_amount,
            MEDIAN(ABS(amount)) as median_amount,
            STDDEV(ABS(amount)) as stddev_amount,
            MIN(ABS(amount)) as min_amount,
            MAX(ABS(amount)) as max_amount,
            QUANTILE_CONT(ABS(amount), 0.25) as p25,
            QUANTILE_CONT(ABS(amount), 0.75) as p75,
            QUANTILE_CONT(ABS(amount), 0.90) as p90,
            QUANTILE_CONT(ABS(amount), 0.95) as p95,
            QUANTILE_CONT(ABS(amount), 0.99) as p99,
            MIN(effective_date) as date_from,
            MAX(effective_date) as date_to,
            COUNT(DISTINCT accounting_period) as periods_count,
            AVG(risk_score) as avg_risk_score,
            COUNT(CASE WHEN risk_score >= 60 THEN 1 END) as high_risk_count,
            COUNT(CASE WHEN risk_score >= 80 THEN 1 END) as critical_risk_count
        FROM journal_entries
        {where}
    """
    result = db.execute_df(query, params)
    if result.is_empty():
        return ToolResult(
            tool_name="population_statistics",
            success=False,
            summary="データが存在しません",
            error=f"fiscal_year={fiscal_year} のデータが見つかりません",
        )

    row = result.to_dicts()[0]
    findings = []
    total = row["total_count"]
    if total > 0:
        findings.append(
            f"仕訳件数: {total:,}件、仕訳番号: {row['unique_journals']:,}件"
        )
        findings.append(
            f"金額範囲: {row['min_amount']:,.0f}〜{row['max_amount']:,.0f}円 (平均{row['avg_amount']:,.0f}円、中央値{row['median_amount']:,.0f}円)"
        )
        findings.append(
            f"借方合計: {row['total_debit']:,.0f}円、貸方合計: {row['total_credit']:,.0f}円"
        )
        if row["high_risk_count"] > 0:
            findings.append(
                f"高リスク仕訳: {row['high_risk_count']:,}件 ({row['high_risk_count'] / total * 100:.1f}%)"
            )
        if row["critical_risk_count"] > 0:
            findings.append(f"重要リスク仕訳: {row['critical_risk_count']:,}件")

    return ToolResult(
        tool_name="population_statistics",
        success=True,
        summary=f"{fiscal_year}年度の仕訳{total:,}件を分析。平均金額{row['avg_amount']:,.0f}円、高リスク{row['high_risk_count']:,}件。",
        key_findings=findings,
        data={
            k: (float(v) if v is not None and not isinstance(v, str) else v)
            for k, v in row.items()
        },
    )


POPULATION_TOOL = ToolDefinition(
    name="population_statistics",
    description="仕訳データの母集団統計（件数、金額分布、パーセンタイル、リスク分布）を算出",
    category="population",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "account_prefix": {
            "type": "string",
            "description": "勘定科目プレフィックス（任意）",
        },
    },
    execute_fn=execute_population_statistics,
)
