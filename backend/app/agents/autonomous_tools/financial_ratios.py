"""財務指標分析ツール。

試算表データからBS/PLを集計し、主要財務指標を算出する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_financial_ratio_analysis(
    fiscal_year: int,
    comparison_year: int | None = None,
) -> ToolResult:
    """主要財務指標を算出し前年比較を行う。"""
    db = duckdb_manager

    # 最終期間の残高を集計（BSは期末残高、PLは期間累計）
    query = """
        SELECT
            ca.account_type,
            ca.account_category,
            SUM(tb.ending_balance) as total_balance
        FROM trial_balance tb
        JOIN chart_of_accounts ca ON tb.gl_account_number = ca.account_code
        WHERE tb.fiscal_year = ?
          AND tb.accounting_period = (
              SELECT MAX(accounting_period)
              FROM trial_balance
              WHERE fiscal_year = ?
          )
        GROUP BY ca.account_type, ca.account_category
    """
    result = db.execute_df(query, [fiscal_year, fiscal_year])
    if result.is_empty():
        return ToolResult(
            tool_name="financial_ratio_analysis",
            success=True,
            summary="試算表・勘定科目マスタデータが不足しています",
            key_findings=["財務指標算出に必要なデータが不足"],
        )

    rows = result.to_dicts()
    balances = {r["account_type"]: r["total_balance"] for r in rows}

    # 主要指標算出
    ratios: dict[str, float | None] = {}
    current_assets = balances.get("current_asset", 0) or 0
    current_liab = balances.get("current_liability", 0) or 0
    total_assets = current_assets + (balances.get("fixed_asset", 0) or 0)
    total_liab = (current_liab + (balances.get("fixed_liability", 0) or 0))
    equity = balances.get("equity", 0) or 0
    revenue = abs(balances.get("revenue", 0) or 0)
    expenses = abs(balances.get("expense", 0) or 0)

    ratios["current_ratio"] = (current_assets / current_liab * 100) if current_liab else None
    ratios["debt_to_equity"] = (total_liab / equity * 100) if equity else None
    ratios["expense_ratio"] = (expenses / revenue * 100) if revenue else None
    ratios["net_income"] = revenue - expenses

    findings = []
    findings.append(f"総資産: {total_assets:,.0f}円、総負債: {total_liab:,.0f}円、純資産: {equity:,.0f}円")
    findings.append(f"売上高: {revenue:,.0f}円、費用: {expenses:,.0f}円、純利益: {ratios['net_income']:,.0f}円")
    if ratios["current_ratio"] is not None:
        findings.append(f"流動比率: {ratios['current_ratio']:.1f}%")
    if ratios["debt_to_equity"] is not None:
        findings.append(f"負債比率: {ratios['debt_to_equity']:.1f}%")
    if ratios["expense_ratio"] is not None:
        findings.append(f"費用率: {ratios['expense_ratio']:.1f}%")

    # 前年比較
    if comparison_year:
        prev_result = db.execute_df(query, [comparison_year, comparison_year])
        if not prev_result.is_empty():
            prev_rows = prev_result.to_dicts()
            prev_balances = {r["account_type"]: r["total_balance"] for r in prev_rows}
            prev_revenue = abs(prev_balances.get("revenue", 0) or 0)
            if prev_revenue > 0:
                revenue_chg = (revenue - prev_revenue) / prev_revenue * 100
                findings.append(f"売上高前年比: {revenue_chg:+.1f}%")

    return ToolResult(
        tool_name="financial_ratio_analysis",
        success=True,
        summary=f"{fiscal_year}年度の財務指標。売上{revenue:,.0f}円、純利益{ratios['net_income']:,.0f}円。",
        key_findings=findings,
        data={"ratios": {k: v for k, v in ratios.items() if v is not None}, "balances": balances},
    )


FINANCIAL_RATIOS_TOOL = ToolDefinition(
    name="financial_ratio_analysis",
    description="主要財務指標（流動比率、負債比率、費用率、純利益）を算出し前年比較を行う",
    category="account",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "comparison_year": {"type": "integer", "description": "比較年度（任意）"},
    },
    execute_fn=execute_financial_ratio_analysis,
)
