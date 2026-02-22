"""時系列トレンド分析ツール。

仕訳データの時系列パターン（月末集中、異常期間、季節性）を分析する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_time_series_trend(
    fiscal_year: int,
    metric: str = "amount",
    granularity: str = "monthly",
) -> ToolResult:
    """時系列トレンドを分析。"""
    db = duckdb_manager

    if granularity == "daily":
        query = """
            SELECT
                effective_date as period_key,
                entry_count,
                debit_total,
                credit_total,
                (debit_total + credit_total) as total_amount,
                day_of_week,
                is_weekend
            FROM agg_by_date
            WHERE fiscal_year = ?
            ORDER BY effective_date
        """
        result = db.execute_df(query, [fiscal_year])
    else:
        query = """
            SELECT
                accounting_period as period_key,
                SUM(entry_count) as entry_count,
                SUM(debit_total) as debit_total,
                SUM(credit_total) as credit_total,
                SUM(debit_total + credit_total) as total_amount,
                SUM(journal_count) as journal_count
            FROM agg_by_period_account
            WHERE fiscal_year = ?
            GROUP BY accounting_period
            ORDER BY accounting_period
        """
        result = db.execute_df(query, [fiscal_year])

    if result.is_empty():
        return ToolResult(
            tool_name="time_series_trend",
            success=True,
            summary="時系列集計データが存在しません",
            key_findings=["agg_by_date / agg_by_period_account テーブルが空です"],
        )

    rows = result.to_dicts()
    findings = []

    if metric == "amount":
        values = [r["total_amount"] for r in rows]
    else:
        values = [r["entry_count"] for r in rows]

    avg_val = sum(values) / len(values) if values else 0
    max_val = max(values) if values else 0
    min_val = min(values) if values else 0
    max_idx = values.index(max_val) if values else 0
    min_idx = values.index(min_val) if values else 0

    findings.append(f"期間数: {len(rows)}、平均: {avg_val:,.0f}、最大: {max_val:,.0f}、最小: {min_val:,.0f}")
    findings.append(f"ピーク期間: {rows[max_idx]['period_key']} ({max_val:,.0f})")
    findings.append(f"最少期間: {rows[min_idx]['period_key']} ({min_val:,.0f})")

    # 変動率（前期比）
    if len(values) >= 2:
        changes = []
        for i in range(1, len(values)):
            if values[i - 1] > 0:
                chg = (values[i] - values[i - 1]) / values[i - 1] * 100
                changes.append((rows[i]["period_key"], chg))
        # 最大変動
        if changes:
            changes.sort(key=lambda x: abs(x[1]), reverse=True)
            findings.append(f"最大変動: 期間{changes[0][0]}で{changes[0][1]:+.1f}%")

    # 日次の場合：週末比率
    if granularity == "daily":
        weekend_rows = [r for r in rows if r.get("is_weekend")]
        if weekend_rows and rows:
            weekend_ratio = len(weekend_rows) / len(rows) * 100
            weekend_amount = sum(r["total_amount"] for r in weekend_rows)
            total_amount = sum(r["total_amount"] for r in rows)
            weekend_amount_ratio = weekend_amount / total_amount * 100 if total_amount else 0
            findings.append(f"週末入力: {len(weekend_rows)}日 ({weekend_ratio:.1f}%)、金額比率{weekend_amount_ratio:.1f}%")

    trend_data = [{"period": str(r["period_key"]), "value": values[i]} for i, r in enumerate(rows)]

    return ToolResult(
        tool_name="time_series_trend",
        success=True,
        summary=f"{fiscal_year}年度の{granularity}時系列。{len(rows)}期間。ピーク{rows[max_idx]['period_key']}。",
        key_findings=findings,
        data={"trend": trend_data, "avg": avg_val, "max": max_val, "min": min_val},
    )


TIME_SERIES_TOOL = ToolDefinition(
    name="time_series_trend",
    description="仕訳データの時系列トレンド分析（月末集中、異常期間検出、前期比変動、週末入力比率）",
    category="trend",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "metric": {"type": "string", "description": "分析指標（amount/count）", "enum": ["amount", "count"]},
        "granularity": {"type": "string", "description": "粒度（daily/monthly）", "enum": ["daily", "monthly"]},
    },
    execute_fn=execute_time_series_trend,
)
