"""重複仕訳検出ツール。

同一金額・日付・勘定科目の組み合わせで重複候補を検出する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_duplicate_detection(
    fiscal_year: int,
    amount_tolerance: float = 0.0,  # noqa: ARG001
) -> ToolResult:
    """重複仕訳候補を検出。"""
    db = duckdb_manager

    query = """
        SELECT
            effective_date,
            gl_account_number,
            amount,
            debit_credit_indicator,
            COUNT(*) as dup_count,
            LIST(gl_detail_id ORDER BY gl_detail_id) as detail_ids,
            LIST(journal_id ORDER BY journal_id) as journal_ids,
            LIST(je_line_description ORDER BY gl_detail_id) as descriptions
        FROM journal_entries
        WHERE fiscal_year = ?
        GROUP BY effective_date, gl_account_number, amount, debit_credit_indicator
        HAVING COUNT(*) >= 2
        ORDER BY COUNT(*) DESC, ABS(amount) DESC
        LIMIT 100
    """
    result = db.execute_df(query, [fiscal_year])

    if result.is_empty():
        return ToolResult(
            tool_name="duplicate_detection",
            success=True,
            summary=f"{fiscal_year}年度で重複仕訳は検出されませんでした",
            key_findings=["完全一致の重複仕訳は検出されませんでした"],
        )

    rows = result.to_dicts()
    total_dup_entries = sum(r["dup_count"] for r in rows)
    total_dup_amount = sum(abs(r["amount"]) * (r["dup_count"] - 1) for r in rows)

    findings = [
        f"重複候補: {len(rows)}グループ、{total_dup_entries:,}件",
        f"重複による超過金額（推定）: {total_dup_amount:,.0f}円",
    ]
    for r in rows[:5]:
        findings.append(
            f"{r['effective_date']} / {r['gl_account_number']} / "
            f"{r['amount']:,.0f}円 - {r['dup_count']}回出現"
        )

    clusters = [
        {
            "date": str(r["effective_date"]),
            "account": r["gl_account_number"],
            "amount": r["amount"],
            "count": r["dup_count"],
            "detail_ids": r["detail_ids"][:10],
        }
        for r in rows[:50]
    ]

    return ToolResult(
        tool_name="duplicate_detection",
        success=True,
        summary=f"重複候補{len(rows)}グループ検出。超過金額推定{total_dup_amount:,.0f}円。",
        key_findings=findings,
        data={
            "clusters": clusters,
            "total_groups": len(rows),
            "total_excess_amount": total_dup_amount,
        },
    )


DUPLICATE_TOOL = ToolDefinition(
    name="duplicate_detection",
    description="重複仕訳検出（同一日付・勘定・金額の組み合わせで完全一致する仕訳候補を検出）",
    category="anomaly",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "amount_tolerance": {
            "type": "number",
            "description": "金額許容誤差（デフォルト0=完全一致）",
        },
    },
    execute_fn=execute_duplicate_detection,
)
