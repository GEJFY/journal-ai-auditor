"""仕訳テスティングツール。

仕訳を手動/自動、標準/非標準に分類し、承認状況やバックデート等を検出する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_journal_entry_testing(fiscal_year: int) -> ToolResult:
    """仕訳の分類テストを実行。"""
    db = duckdb_manager

    query = """
        SELECT
            COUNT(*) as total,
            -- ソース別分類
            COUNT(CASE WHEN source IN ('MANUAL', 'manual') THEN 1 END) as manual_count,
            COUNT(CASE WHEN source IN ('AUTO', 'auto', 'SYSTEM', 'system', 'BATCH', 'batch') THEN 1 END) as auto_count,
            COUNT(CASE WHEN source IS NULL OR source = '' THEN 1 END) as unknown_source,
            -- 承認状況
            COUNT(CASE WHEN approved_by IS NOT NULL AND approved_by != '' THEN 1 END) as approved_count,
            COUNT(CASE WHEN approved_by IS NULL OR approved_by = '' THEN 1 END) as unapproved_count,
            -- 自己承認
            COUNT(CASE WHEN prepared_by = approved_by AND prepared_by IS NOT NULL THEN 1 END) as self_approved,
            -- 摘要
            COUNT(CASE WHEN je_line_description IS NULL OR LENGTH(TRIM(je_line_description)) < 3 THEN 1 END) as no_description,
            -- バックデート（入力日が発効日より30日以上後）
            COUNT(CASE WHEN entry_date > effective_date + INTERVAL '30' DAY THEN 1 END) as backdated,
            -- 金額統計
            SUM(CASE WHEN source IN ('MANUAL', 'manual') THEN ABS(amount) ELSE 0 END) as manual_amount,
            AVG(CASE WHEN source IN ('MANUAL', 'manual') THEN risk_score END) as manual_avg_risk,
            AVG(CASE WHEN source NOT IN ('MANUAL', 'manual') OR source IS NULL THEN risk_score END) as auto_avg_risk,
            -- 期末仕訳
            COUNT(CASE WHEN accounting_period = (SELECT MAX(accounting_period) FROM journal_entries WHERE fiscal_year = je.fiscal_year) THEN 1 END) as period_end_count
        FROM journal_entries je
        WHERE fiscal_year = ?
    """
    result = db.execute_df(query, [fiscal_year])
    if result.is_empty():
        return ToolResult(
            tool_name="journal_entry_testing",
            success=True,
            summary="データが存在しません",
            key_findings=[],
        )

    r = result.to_dicts()[0]
    total = r["total"]
    if total == 0:
        return ToolResult(
            tool_name="journal_entry_testing",
            success=True,
            summary="仕訳データが0件",
            key_findings=[],
        )

    findings = [
        f"総仕訳数: {total:,}件",
        f"手動仕訳: {r['manual_count']:,}件 ({r['manual_count'] / total * 100:.1f}%)、自動仕訳: {r['auto_count']:,}件 ({r['auto_count'] / total * 100:.1f}%)",
        f"未承認仕訳: {r['unapproved_count']:,}件 ({r['unapproved_count'] / total * 100:.1f}%)",
        f"自己承認: {r['self_approved']:,}件 ({r['self_approved'] / total * 100:.1f}%)",
        f"摘要欠損: {r['no_description']:,}件 ({r['no_description'] / total * 100:.1f}%)",
    ]
    if r["backdated"] > 0:
        findings.append(f"バックデート（30日超）: {r['backdated']:,}件")
    if r["manual_avg_risk"] and r["auto_avg_risk"]:
        findings.append(
            f"平均リスク — 手動: {r['manual_avg_risk']:.1f}、自動: {r['auto_avg_risk']:.1f}"
        )

    return ToolResult(
        tool_name="journal_entry_testing",
        success=True,
        summary=f"仕訳テスト: 手動{r['manual_count']:,}件、未承認{r['unapproved_count']:,}件、自己承認{r['self_approved']:,}件。",
        key_findings=findings,
        data={
            "total": total,
            "manual_count": r["manual_count"],
            "auto_count": r["auto_count"],
            "approved_count": r["approved_count"],
            "unapproved_count": r["unapproved_count"],
            "self_approved": r["self_approved"],
            "no_description": r["no_description"],
            "backdated": r["backdated"],
            "manual_amount": r["manual_amount"],
        },
    )


JOURNAL_ENTRY_TESTING_TOOL = ToolDefinition(
    name="journal_entry_testing",
    description="仕訳テスティング（手動/自動分類、承認状況、自己承認、摘要欠損、バックデート検出）",
    category="compliance",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
    },
    execute_fn=execute_journal_entry_testing,
)
