"""勘定間相関分析ツール。

月次集計ベースで勘定科目間の相関を分析し、予期せぬ相関ペアを検出する。
"""

from app.agents.autonomous.tool_registry import ToolDefinition, ToolResult
from app.db import duckdb_manager


def execute_correlation_analysis(
    fiscal_year: int,
    top_accounts: int = 20,
) -> ToolResult:
    """勘定間の月次相関を分析。"""
    db = duckdb_manager

    # 上位勘定の月次金額を取得
    query = """
        SELECT gl_account_number, accounting_period,
               SUM(net_amount) as net_amount
        FROM agg_by_period_account
        WHERE fiscal_year = ?
          AND gl_account_number IN (
              SELECT gl_account_number
              FROM agg_by_period_account
              WHERE fiscal_year = ?
              GROUP BY gl_account_number
              ORDER BY SUM(ABS(net_amount)) DESC
              LIMIT ?
          )
        GROUP BY gl_account_number, accounting_period
        ORDER BY gl_account_number, accounting_period
    """
    result = db.execute_df(query, [fiscal_year, fiscal_year, top_accounts])
    if result.is_empty():
        return ToolResult(
            tool_name="correlation_analysis",
            success=True,
            summary="期間別勘定集計データが不足しています",
            key_findings=["agg_by_period_account テーブルが空です"],
        )

    rows = result.to_dicts()

    # 勘定×期間のマトリクスを構築
    accounts: dict[str, dict[int, float]] = {}
    for r in rows:
        acct = r["gl_account_number"]
        if acct not in accounts:
            accounts[acct] = {}
        accounts[acct][r["accounting_period"]] = r["net_amount"]

    acct_list = sorted(accounts.keys())
    periods = sorted({r["accounting_period"] for r in rows})

    if len(acct_list) < 2 or len(periods) < 3:
        return ToolResult(
            tool_name="correlation_analysis",
            success=True,
            summary="相関分析に十分なデータがありません（勘定2以上、期間3以上必要）",
            key_findings=["データ不足で相関分析を実行できません"],
        )

    # 手動でピアソン相関を計算（numpy不要）
    def pearson(x: list[float], y: list[float]) -> float:
        n = len(x)
        if n < 3:
            return 0.0
        mx = sum(x) / n
        my = sum(y) / n
        num = sum((xi - mx) * (yi - my) for xi, yi in zip(x, y, strict=True))
        dx = sum((xi - mx) ** 2 for xi in x) ** 0.5
        dy = sum((yi - my) ** 2 for yi in y) ** 0.5
        return num / (dx * dy) if dx > 0 and dy > 0 else 0.0

    correlations = []
    for i, a1 in enumerate(acct_list):
        for a2 in acct_list[i + 1 :]:
            x = [accounts[a1].get(p, 0.0) for p in periods]
            y = [accounts[a2].get(p, 0.0) for p in periods]
            corr = pearson(x, y)
            if abs(corr) >= 0.5:
                correlations.append(
                    {"account1": a1, "account2": a2, "correlation": round(corr, 3)}
                )

    correlations.sort(
        key=lambda c: abs(float(c["correlation"])),  # type: ignore[arg-type]
        reverse=True,
    )

    findings = [f"分析対象: {len(acct_list)}勘定 × {len(periods)}期間"]
    strong_pos = [
        c
        for c in correlations
        if float(c["correlation"]) >= 0.8  # type: ignore[arg-type]
    ]
    strong_neg = [
        c
        for c in correlations
        if float(c["correlation"]) <= -0.8  # type: ignore[arg-type]
    ]
    findings.append(f"強い正の相関(≥0.8): {len(strong_pos)}ペア")
    findings.append(f"強い負の相関(≤-0.8): {len(strong_neg)}ペア")

    for c in correlations[:5]:
        findings.append(f"{c['account1']} ⟷ {c['account2']}: r={c['correlation']}")

    return ToolResult(
        tool_name="correlation_analysis",
        success=True,
        summary=f"勘定間相関分析。{len(correlations)}ペアで|r|≥0.5。強相関{len(strong_pos) + len(strong_neg)}ペア。",
        key_findings=findings,
        data={
            "correlations": correlations[:50],
            "accounts_analyzed": len(acct_list),
            "periods": len(periods),
        },
    )


CORRELATION_TOOL = ToolDefinition(
    name="correlation_analysis",
    description="勘定科目間の月次相関分析（ピアソン相関、強い正/負の相関ペア検出）",
    category="pattern",
    parameters={
        "fiscal_year": {"type": "integer", "description": "対象年度"},
        "top_accounts": {
            "type": "integer",
            "description": "分析対象の上位勘定数（デフォルト20）",
        },
    },
    execute_fn=execute_correlation_analysis,
)
