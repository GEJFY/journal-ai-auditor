"""勘定残高分析ツール。

試算表ベースのGL残高分析、異常残高変動検出を行う。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_account_balance_analysis(
    fiscal_year: int,
    accounting_period: int | None = None,
    account_prefix: str | None = None,
) -> ToolResult:
    """試算表から勘定残高を分析。"""
    db = duckdb_manager
    conditions = ["tb.fiscal_year = ?"]
    params: list[object] = [fiscal_year]
    if accounting_period:
        conditions.append("tb.accounting_period = ?")
        params.append(accounting_period)
    if account_prefix:
        conditions.append("tb.gl_account_number LIKE ?")
        params.append(f"{account_prefix}%")

    where = " AND ".join(conditions)
    query = f"""
        SELECT
            tb.gl_account_number,
            COALESCE(ca.account_name, tb.gl_account_number) as account_name,
            COALESCE(ca.account_category, 'N/A') as account_category,
            tb.accounting_period,
            tb.beginning_balance,
            tb.period_debit,
            tb.period_credit,
            tb.ending_balance,
            (tb.period_debit - tb.period_credit) as net_movement
        FROM trial_balance tb
        LEFT JOIN chart_of_accounts ca ON tb.gl_account_number = ca.account_code
        WHERE {where}
        ORDER BY ABS(tb.ending_balance) DESC
        LIMIT 200
    """
    result = db.execute_df(query, params)
    if result.is_empty():
        return ToolResult(
            tool_name="account_balance_analysis",
            success=True,
            summary="試算表データが存在しません",
            key_findings=["試算表データが未登録です"],
        )

    rows = result.to_dicts()
    findings = []

    # BS/PL別集計
    bs_total = sum(r["ending_balance"] for r in rows if r["account_category"] == "BS")
    pl_total = sum(r["ending_balance"] for r in rows if r["account_category"] == "PL")
    findings.append(f"BS勘定残高合計: {bs_total:,.0f}円、PL勘定残高合計: {pl_total:,.0f}円")

    # 大きな残高変動
    large_movements = [r for r in rows if abs(r["net_movement"]) > 0 and r["beginning_balance"] != 0]
    large_movements.sort(key=lambda r: abs(r["net_movement"]), reverse=True)
    for r in large_movements[:5]:
        chg = r["net_movement"] / abs(r["beginning_balance"]) * 100 if r["beginning_balance"] else 0
        findings.append(
            f"{r['account_name']}({r['gl_account_number']}): "
            f"残高{r['ending_balance']:,.0f}円 (変動{chg:+.1f}%)"
        )

    # マイナス残高（異常検出）
    negative_bs = [r for r in rows if r["account_category"] == "BS" and r["ending_balance"] < 0]
    if negative_bs:
        findings.append(f"BS勘定でマイナス残高: {len(negative_bs)}件検出")

    top_accounts = [
        {"account": r["gl_account_number"], "name": r["account_name"], "balance": r["ending_balance"]}
        for r in rows[:20]
    ]

    return ToolResult(
        tool_name="account_balance_analysis",
        success=True,
        summary=f"{fiscal_year}年度の勘定残高分析。{len(rows)}勘定、BS合計{bs_total:,.0f}円。",
        key_findings=findings,
        data={"top_accounts": top_accounts, "bs_total": bs_total, "pl_total": pl_total, "total_accounts": len(rows)},
    )


ACCOUNT_BALANCE_TOOL = ToolDefinition(
    name="account_balance_analysis",
    description="試算表ベースの勘定残高分析（BS/PL別集計、異常残高変動検出、マイナス残高検出）",
    category="account",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "accounting_period": {"type": "integer", "description": "会計期間（任意）"},
        "account_prefix": {"type": "string", "description": "勘定科目プレフィックス（任意）"},
    },
    execute_fn=execute_account_balance_analysis,
)
