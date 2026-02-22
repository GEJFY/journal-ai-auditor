"""T勘定分析ツール。

特定勘定科目の借方/貸方フローを分析し、相手先勘定のTOPを特定する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_t_account_analysis(fiscal_year: int, gl_account_number: str) -> ToolResult:
    """T勘定（借方/貸方フロー）を分析。"""
    db = duckdb_manager

    # 期間別借方/貸方集計
    query = """
        SELECT
            accounting_period,
            SUM(CASE WHEN debit_credit_indicator='D' THEN amount ELSE 0 END) as total_debit,
            SUM(CASE WHEN debit_credit_indicator='C' THEN amount ELSE 0 END) as total_credit,
            COUNT(*) as entry_count
        FROM journal_entries
        WHERE fiscal_year = ? AND gl_account_number = ?
        GROUP BY accounting_period
        ORDER BY accounting_period
    """
    period_result = db.execute_df(query, [fiscal_year, gl_account_number])

    # 相手先勘定TOP10（同一仕訳内の別勘定）
    counter_query = """
        SELECT
            je2.gl_account_number as counter_account,
            COALESCE(ca.account_name, je2.gl_account_number) as counter_name,
            COUNT(*) as pair_count,
            SUM(ABS(je2.amount)) as pair_amount
        FROM journal_entries je1
        JOIN journal_entries je2
            ON je1.journal_id = je2.journal_id
            AND je1.gl_detail_id != je2.gl_detail_id
        LEFT JOIN chart_of_accounts ca ON je2.gl_account_number = ca.account_code
        WHERE je1.fiscal_year = ?
          AND je1.gl_account_number = ?
        GROUP BY je2.gl_account_number, ca.account_name
        ORDER BY pair_amount DESC
        LIMIT 10
    """
    counter_result = db.execute_df(counter_query, [fiscal_year, gl_account_number])

    if period_result.is_empty():
        return ToolResult(
            tool_name="t_account_analysis",
            success=True,
            summary=f"勘定{gl_account_number}のデータが{fiscal_year}年度に存在しません",
            key_findings=[],
        )

    periods = period_result.to_dicts()
    total_debit = sum(p["total_debit"] for p in periods)
    total_credit = sum(p["total_credit"] for p in periods)
    total_entries = sum(p["entry_count"] for p in periods)

    findings = [
        f"勘定{gl_account_number}: 借方合計{total_debit:,.0f}円、貸方合計{total_credit:,.0f}円",
        f"仕訳件数: {total_entries:,}件 ({len(periods)}期間)",
        f"純額: {total_debit - total_credit:,.0f}円",
    ]

    counters = counter_result.to_dicts() if not counter_result.is_empty() else []
    for c in counters[:5]:
        findings.append(f"相手先: {c['counter_name']}({c['counter_account']}) - {c['pair_count']}件、{c['pair_amount']:,.0f}円")

    return ToolResult(
        tool_name="t_account_analysis",
        success=True,
        summary=f"勘定{gl_account_number}のT勘定分析。借方{total_debit:,.0f}円、貸方{total_credit:,.0f}円。",
        key_findings=findings,
        data={
            "periods": periods,
            "counter_accounts": counters,
            "total_debit": total_debit,
            "total_credit": total_credit,
        },
    )


T_ACCOUNT_TOOL = ToolDefinition(
    name="t_account_analysis",
    description="特定勘定科目のT勘定分析（期間別借方/貸方フロー、相手先勘定TOP10）",
    category="account",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "gl_account_number": {"type": "string", "description": "勘定科目コード"},
    },
    required_params=["fiscal_year", "gl_account_number"],
    execute_fn=execute_t_account_analysis,
)
