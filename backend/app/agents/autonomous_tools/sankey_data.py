"""サンキーチャート用資金フローデータ生成ツール。

勘定科目間の資金フロー（借方→貸方）を集計し、
サンキーチャート向けのノード・リンクデータを生成する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_sankey_flow_data(
    fiscal_year: int,
    min_amount: float = 100000,
    top_n: int = 30,
    accounting_period: int | None = None,
) -> ToolResult:
    """勘定間資金フローをサンキー形式で出力。"""
    db = duckdb_manager
    conditions = ["fiscal_year = ?"]
    params: list[object] = [fiscal_year]
    if accounting_period:
        conditions.append("accounting_period = ?")
        params.append(accounting_period)

    where = " AND ".join(conditions)
    query = f"""
        SELECT
            source_account,
            target_account,
            SUM(flow_amount) as total_flow,
            SUM(transaction_count) as total_count
        FROM agg_account_flow
        WHERE {where}
        GROUP BY source_account, target_account
        HAVING SUM(flow_amount) >= ?
        ORDER BY total_flow DESC
        LIMIT ?
    """
    params.extend([min_amount, top_n])
    result = db.execute_df(query, params)

    if result.is_empty():
        return ToolResult(
            tool_name="sankey_flow_data",
            success=True,
            summary="勘定フローデータが存在しません（agg_account_flowテーブル）",
            key_findings=["資金フローの集計データが未生成です"],
        )

    rows = result.to_dicts()
    # ノード一覧
    accounts = set()
    for r in rows:
        accounts.add(r["source_account"])
        accounts.add(r["target_account"])

    nodes = sorted(accounts)
    links = [
        {
            "source": r["source_account"],
            "target": r["target_account"],
            "value": r["total_flow"],
            "count": r["total_count"],
        }
        for r in rows
    ]
    total_flow = sum(r["total_flow"] for r in rows)

    # 循環取引検出（A→B かつ B→A）
    flow_pairs = {(r["source_account"], r["target_account"]) for r in rows}
    circular = [(a, b) for a, b in flow_pairs if (b, a) in flow_pairs]

    findings = [
        f"資金フロー: {len(links)}経路、{len(nodes)}勘定、合計{total_flow:,.0f}円",
        f"最大フロー: {rows[0]['source_account']}→{rows[0]['target_account']} ({rows[0]['total_flow']:,.0f}円)",
    ]
    if circular:
        findings.append(
            f"循環フロー検出: {len(circular) // 2}ペア（例: {circular[0][0]}⇄{circular[0][1]}）"
        )

    return ToolResult(
        tool_name="sankey_flow_data",
        success=True,
        summary=f"{len(links)}経路の資金フロー。合計{total_flow:,.0f}円。循環{len(circular) // 2}ペア。",
        key_findings=findings,
        data={"nodes": nodes, "links": links, "circular_flows": circular[:10]},
    )


SANKEY_TOOL = ToolDefinition(
    name="sankey_flow_data",
    description="勘定科目間の資金フロー分析（サンキーチャート用ノード・リンク、循環取引検出）",
    category="flow",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "min_amount": {
            "type": "number",
            "description": "最小フロー金額（デフォルト10万円）",
        },
        "top_n": {"type": "integer", "description": "上位N経路（デフォルト30）"},
        "accounting_period": {"type": "integer", "description": "会計期間（任意）"},
    },
    execute_fn=execute_sankey_flow_data,
)
