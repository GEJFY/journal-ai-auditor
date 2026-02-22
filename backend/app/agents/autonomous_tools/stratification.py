"""金額層別（ストラティフィケーション）分析ツール。

仕訳金額を層別に分類し、件数・金額の分布とリスク集中度を分析する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager

DEFAULT_BOUNDARIES = [10000, 100000, 1000000, 10000000, 100000000]
LABELS = ["〜1万円", "1万〜10万円", "10万〜100万円", "100万〜1000万円", "1000万〜1億円", "1億円〜"]


def execute_stratification_analysis(
    fiscal_year: int,
    strata_boundaries: list[float] | None = None,
) -> ToolResult:
    """金額層別分析を実行。"""
    db = duckdb_manager
    bounds = strata_boundaries or DEFAULT_BOUNDARIES

    # CASE文を動的構築
    cases = []
    for i, b in enumerate(bounds):
        if i == 0:
            cases.append(f"WHEN ABS(amount) < {b} THEN {i}")
        else:
            cases.append(f"WHEN ABS(amount) < {b} THEN {i}")
    cases.append(f"ELSE {len(bounds)}")
    case_expr = " ".join(cases)

    query = f"""
        SELECT
            CASE {case_expr} END as stratum,
            COUNT(*) as entry_count,
            SUM(ABS(amount)) as total_amount,
            AVG(ABS(amount)) as avg_amount,
            AVG(risk_score) as avg_risk,
            COUNT(CASE WHEN risk_score >= 60 THEN 1 END) as high_risk_count
        FROM journal_entries
        WHERE fiscal_year = ?
        GROUP BY stratum
        ORDER BY stratum
    """
    result = db.execute_df(query, [fiscal_year])
    if result.is_empty():
        return ToolResult(
            tool_name="stratification_analysis",
            success=True,
            summary="データが存在しません",
            key_findings=[],
        )

    rows = result.to_dicts()
    labels = LABELS if not strata_boundaries else [f"層{i}" for i in range(len(bounds) + 1)]
    grand_total_count = sum(r["entry_count"] for r in rows)
    grand_total_amount = sum(r["total_amount"] for r in rows)

    findings = []
    strata_data = []
    for r in rows:
        idx = r["stratum"]
        label = labels[idx] if idx < len(labels) else f"層{idx}"
        pct_count = r["entry_count"] / grand_total_count * 100 if grand_total_count else 0
        pct_amount = r["total_amount"] / grand_total_amount * 100 if grand_total_amount else 0
        findings.append(
            f"{label}: {r['entry_count']:,}件({pct_count:.1f}%)、"
            f"{r['total_amount']:,.0f}円({pct_amount:.1f}%)、"
            f"高リスク{r['high_risk_count']}件"
        )
        strata_data.append({
            "label": label,
            "count": r["entry_count"],
            "amount": r["total_amount"],
            "pct_count": round(pct_count, 1),
            "pct_amount": round(pct_amount, 1),
            "avg_risk": round(r["avg_risk"] or 0, 1),
            "high_risk_count": r["high_risk_count"],
        })

    return ToolResult(
        tool_name="stratification_analysis",
        success=True,
        summary=f"{fiscal_year}年度の金額層別分析。{len(rows)}層、全{grand_total_count:,}件。",
        key_findings=findings,
        data={"strata": strata_data, "total_count": grand_total_count, "total_amount": grand_total_amount},
    )


STRATIFICATION_TOOL = ToolDefinition(
    name="stratification_analysis",
    description="仕訳金額の層別分析（件数/金額分布、リスク集中度、層別高リスク件数）",
    category="population",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
    },
    execute_fn=execute_stratification_analysis,
)
