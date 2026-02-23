"""ML異常検知結果ラッパーツール。

既存のml_anomaliesテーブルから手法別異常数、重複分析、上位異常仕訳を提供する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_ml_anomaly_summary(
    fiscal_year: int,
    method: str | None = None,
) -> ToolResult:
    """ML異常検知結果のサマリ。"""
    db = duckdb_manager

    conditions = ["je.fiscal_year = ?"]
    params: list[object] = [fiscal_year]
    if method:
        conditions.append("ma.detection_method = ?")
        params.append(method)
    where = " AND ".join(conditions)

    query = f"""
        SELECT
            ma.detection_method,
            COUNT(*) as total_checked,
            COUNT(CASE WHEN ma.is_anomaly THEN 1 END) as anomaly_count,
            AVG(ma.anomaly_score) as avg_score,
            MAX(ma.anomaly_score) as max_score
        FROM ml_anomalies ma
        JOIN journal_entries je ON ma.gl_detail_id = je.gl_detail_id
        WHERE {where}
        GROUP BY ma.detection_method
        ORDER BY anomaly_count DESC
    """
    result = db.execute_df(query, params)
    if result.is_empty():
        return ToolResult(
            tool_name="ml_anomaly_summary",
            success=True,
            summary="ML異常検知の結果が存在しません",
            key_findings=["ml_anomalies テーブルが空です（バッチ未実行の可能性）"],
        )

    rows = result.to_dicts()
    total_anomalies = sum(r["anomaly_count"] for r in rows)

    findings = [f"ML手法数: {len(rows)}、異常検知合計: {total_anomalies:,}件"]
    for r in rows:
        rate = (
            r["anomaly_count"] / r["total_checked"] * 100 if r["total_checked"] else 0
        )
        findings.append(
            f"{r['detection_method']}: {r['anomaly_count']:,}件/{r['total_checked']:,}件 "
            f"({rate:.1f}%)、平均スコア{r['avg_score']:.2f}"
        )

    # 複数手法で検出された仕訳（高信頼度）
    overlap_query = f"""
        SELECT ma.gl_detail_id, COUNT(DISTINCT ma.detection_method) as method_count,
               MAX(ma.anomaly_score) as max_score
        FROM ml_anomalies ma
        JOIN journal_entries je ON ma.gl_detail_id = je.gl_detail_id
        WHERE {where} AND ma.is_anomaly = true
        GROUP BY ma.gl_detail_id
        HAVING COUNT(DISTINCT ma.detection_method) >= 2
        ORDER BY method_count DESC, max_score DESC
        LIMIT 20
    """
    overlap_result = db.execute_df(overlap_query, params)
    overlaps = overlap_result.to_dicts() if not overlap_result.is_empty() else []
    if overlaps:
        findings.append(f"複数手法で検出（高信頼度）: {len(overlaps)}件")

    return ToolResult(
        tool_name="ml_anomaly_summary",
        success=True,
        summary=f"ML異常検知: {len(rows)}手法で{total_anomalies:,}件検出。複数手法合致{len(overlaps)}件。",
        key_findings=findings,
        data={
            "by_method": rows,
            "overlaps": overlaps,
            "total_anomalies": total_anomalies,
        },
    )


ML_ANOMALY_TOOL = ToolDefinition(
    name="ml_anomaly_summary",
    description="ML異常検知結果サマリ（手法別異常数、検出率、複数手法合致の高信頼度異常）",
    category="anomaly",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "method": {
            "type": "string",
            "description": "検出手法名（任意。isolation_forest/lof/svm/autoencoder/ensemble）",
        },
    },
    execute_fn=execute_ml_anomaly_summary,
)
