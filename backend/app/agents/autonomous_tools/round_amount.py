"""丸め金額分析ツール。

端数のない丸め金額（1万円単位、10万円単位等）の出現頻度を分析する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_round_amount_analysis(fiscal_year: int) -> ToolResult:
    """丸め金額の出現頻度を分析。"""
    db = duckdb_manager

    query = """
        SELECT
            COUNT(*) as total_count,
            COUNT(CASE WHEN ABS(amount) % 10000 = 0 AND ABS(amount) > 0 THEN 1 END) as round_10k,
            COUNT(CASE WHEN ABS(amount) % 100000 = 0 AND ABS(amount) > 0 THEN 1 END) as round_100k,
            COUNT(CASE WHEN ABS(amount) % 1000000 = 0 AND ABS(amount) > 0 THEN 1 END) as round_1m,
            COUNT(CASE WHEN ABS(amount) % 10000000 = 0 AND ABS(amount) > 0 THEN 1 END) as round_10m,
            SUM(CASE WHEN ABS(amount) % 1000000 = 0 AND ABS(amount) > 0 THEN ABS(amount) ELSE 0 END) as round_1m_amount
        FROM journal_entries
        WHERE fiscal_year = ?
    """
    result = db.execute_df(query, [fiscal_year])
    if result.is_empty():
        return ToolResult(
            tool_name="round_amount_analysis",
            success=True,
            summary="データが存在しません",
            key_findings=[],
        )

    row = result.to_dicts()[0]
    total = row["total_count"]
    if total == 0:
        return ToolResult(
            tool_name="round_amount_analysis",
            success=True,
            summary="仕訳データが0件です",
            key_findings=[],
        )

    findings = [
        f"1万円単位の丸め金額: {row['round_10k']:,}件 ({row['round_10k']/total*100:.1f}%)",
        f"10万円単位の丸め金額: {row['round_100k']:,}件 ({row['round_100k']/total*100:.1f}%)",
        f"100万円単位の丸め金額: {row['round_1m']:,}件 ({row['round_1m']/total*100:.1f}%)",
        f"1000万円単位の丸め金額: {row['round_10m']:,}件 ({row['round_10m']/total*100:.1f}%)",
    ]
    if row["round_1m_amount"] > 0:
        findings.append(f"100万円単位丸め金額の合計: {row['round_1m_amount']:,.0f}円")

    # 上位の丸め金額仕訳
    top_query = """
        SELECT gl_detail_id, journal_id, effective_date, gl_account_number,
               amount, je_line_description, risk_score
        FROM journal_entries
        WHERE fiscal_year = ? AND ABS(amount) % 1000000 = 0 AND ABS(amount) > 0
        ORDER BY ABS(amount) DESC
        LIMIT 10
    """
    top_result = db.execute_df(top_query, [fiscal_year])
    top_entries = top_result.to_dicts() if not top_result.is_empty() else []

    return ToolResult(
        tool_name="round_amount_analysis",
        success=True,
        summary=f"丸め金額分析: 100万円単位{row['round_1m']:,}件、合計{row['round_1m_amount']:,.0f}円。",
        key_findings=findings,
        data={
            "round_10k": row["round_10k"],
            "round_100k": row["round_100k"],
            "round_1m": row["round_1m"],
            "round_10m": row["round_10m"],
            "top_round_entries": top_entries[:10],
        },
        evidence_refs=[
            {"gl_detail_id": e["gl_detail_id"], "amount": e["amount"], "description": e.get("je_line_description", "")}
            for e in top_entries[:5]
        ],
    )


ROUND_AMOUNT_TOOL = ToolDefinition(
    name="round_amount_analysis",
    description="丸め金額（端数なし）の出現頻度分析（1万/10万/100万/1000万円単位別、上位丸め金額仕訳リスト）",
    category="pattern",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
    },
    execute_fn=execute_round_amount_analysis,
)
