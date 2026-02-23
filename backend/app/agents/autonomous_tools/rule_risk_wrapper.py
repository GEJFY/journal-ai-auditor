"""ルールエンジン結果ラッパーツール。

既存のrule_violations/agg_rule_violationsテーブルを集計し、
ルール別・重篤度別・カテゴリ別の違反サマリを提供する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_rule_risk_summary(
    fiscal_year: int,
    category: str | None = None,
) -> ToolResult:
    """ルール違反のサマリを集計。"""
    db = duckdb_manager

    # カテゴリ別・重篤度別集計
    conditions = ["je.fiscal_year = ?"]
    params: list[object] = [fiscal_year]
    if category:
        conditions.append("rv.category = ?")
        params.append(category)
    where = " AND ".join(conditions)

    query = f"""
        SELECT
            rv.category,
            rv.severity,
            COUNT(*) as violation_count,
            COUNT(DISTINCT rv.gl_detail_id) as affected_entries,
            COUNT(DISTINCT rv.rule_id) as rules_triggered,
            SUM(rv.score_impact) as total_score_impact
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE {where}
        GROUP BY rv.category, rv.severity
        ORDER BY
            CASE rv.severity
                WHEN 'CRITICAL' THEN 1
                WHEN 'HIGH' THEN 2
                WHEN 'MEDIUM' THEN 3
                WHEN 'LOW' THEN 4
                ELSE 5
            END,
            violation_count DESC
    """
    result = db.execute_df(query, params)
    if result.is_empty():
        return ToolResult(
            tool_name="rule_risk_summary",
            success=True,
            summary=f"{fiscal_year}年度のルール違反は0件です",
            key_findings=["ルール違反が検出されていません（バッチ処理未実行の可能性）"],
        )

    rows = result.to_dicts()
    total_violations = sum(r["violation_count"] for r in rows)
    total_affected = sum(r["affected_entries"] for r in rows)

    findings = [
        f"ルール違反合計: {total_violations:,}件、影響仕訳: {total_affected:,}件"
    ]

    # 重篤度別
    by_severity: dict[str, int] = {}
    for r in rows:
        sev = r["severity"]
        by_severity[sev] = by_severity.get(sev, 0) + r["violation_count"]
    for sev in ["CRITICAL", "HIGH", "MEDIUM", "LOW"]:
        if sev in by_severity:
            findings.append(f"{sev}: {by_severity[sev]:,}件")

    # カテゴリ別
    by_cat: dict[str, int] = {}
    for r in rows:
        cat = r["category"]
        by_cat[cat] = by_cat.get(cat, 0) + r["violation_count"]
    for cat, cnt in sorted(by_cat.items(), key=lambda x: -x[1]):
        findings.append(f"カテゴリ {cat}: {cnt:,}件")

    # 上位違反ルール
    top_rules_query = f"""
        SELECT rv.rule_id, rv.rule_name, rv.severity,
               COUNT(*) as cnt
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE {where}
        GROUP BY rv.rule_id, rv.rule_name, rv.severity
        ORDER BY cnt DESC
        LIMIT 10
    """
    top_result = db.execute_df(top_rules_query, params)
    top_rules = top_result.to_dicts() if not top_result.is_empty() else []

    return ToolResult(
        tool_name="rule_risk_summary",
        success=True,
        summary=f"ルール違反{total_violations:,}件。CRITICAL: {by_severity.get('CRITICAL', 0)}、HIGH: {by_severity.get('HIGH', 0)}。",
        key_findings=findings,
        data={
            "by_severity": by_severity,
            "by_category": by_cat,
            "top_rules": top_rules,
        },
    )


RULE_RISK_TOOL = ToolDefinition(
    name="rule_risk_summary",
    description="ルール違反サマリ（重篤度別・カテゴリ別・ルール別の違反件数、影響仕訳数）",
    category="compliance",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "category": {
            "type": "string",
            "description": "ルールカテゴリ（AMOUNT/TIME/APPROVAL等、任意）",
        },
    },
    execute_fn=execute_rule_risk_summary,
)
