"""Report API endpoints.

Provides REST API for:
- Generating audit reports
- Exporting analysis results
- Creating executive summaries
- Working paper generation
"""

from datetime import datetime
from enum import StrEnum
from typing import Any

from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.db import DuckDBManager

router = APIRouter()


def get_db() -> DuckDBManager:
    """Get DB instance."""
    return DuckDBManager()


class ReportFormat(StrEnum):
    """Report output formats."""

    JSON = "json"
    CSV = "csv"
    EXCEL = "excel"
    PDF = "pdf"


class ReportType(StrEnum):
    """Report types."""

    SUMMARY = "summary"
    DETAILED = "detailed"
    EXECUTIVE = "executive"
    WORKING_PAPER = "working_paper"
    VIOLATIONS = "violations"
    RISK = "risk"
    BENFORD = "benford"


class ReportRequest(BaseModel):
    """Report generation request."""

    report_type: ReportType
    fiscal_year: int
    period_from: int | None = None
    period_to: int | None = None
    accounts: list[str] | None = None
    include_details: bool = True
    format: ReportFormat = ReportFormat.JSON


class ReportMetadata(BaseModel):
    """Report metadata."""

    report_id: str
    report_type: str
    generated_at: str
    fiscal_year: int
    period_range: str
    total_entries: int
    filters_applied: dict[str, Any]


class SummaryReportSection(BaseModel):
    """Summary report section."""

    title: str
    content: dict[str, Any]


class SummaryReport(BaseModel):
    """Summary report response."""

    metadata: ReportMetadata
    executive_summary: str
    key_findings: list[dict[str, Any]]
    statistics: dict[str, Any]
    risk_overview: dict[str, Any]
    recommendations: list[str]


class DetailedReport(BaseModel):
    """Detailed report response."""

    metadata: ReportMetadata
    sections: list[SummaryReportSection]
    violations_by_category: dict[str, list[dict[str, Any]]]
    high_risk_entries: list[dict[str, Any]]
    appendix: dict[str, Any]


@router.post("/generate", response_model=dict[str, Any])
async def generate_report(request: ReportRequest) -> dict[str, Any]:
    """Generate an audit report.

    Args:
        request: Report configuration.

    Returns:
        Generated report data.
    """
    db = get_db()
    report_id = f"RPT-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    # Build period filter
    period_filter = ""
    if request.period_from:
        period_filter += f" AND accounting_period >= {request.period_from}"
    if request.period_to:
        period_filter += f" AND accounting_period <= {request.period_to}"

    account_filter = ""
    if request.accounts:
        accounts_str = ",".join([f"'{a}'" for a in request.accounts])
        account_filter = f" AND gl_account_number IN ({accounts_str})"

    # Get base statistics
    stats_query = f"""
        SELECT
            COUNT(*) as total_entries,
            COUNT(DISTINCT journal_id) as total_journals,
            COALESCE(SUM(ABS(amount)), 0) as total_amount,
            MIN(effective_date) as min_date,
            MAX(effective_date) as max_date,
            COUNT(DISTINCT gl_account_number) as unique_accounts,
            SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
            AVG(CASE WHEN risk_score > 0 THEN risk_score END) as avg_risk_score
        FROM journal_entries
        WHERE fiscal_year = ? {period_filter} {account_filter}
    """
    stats_result = db.execute(stats_query, [request.fiscal_year])
    stats = stats_result[0] if stats_result else [0] * 8

    # Get period range string
    period_range = ""
    if request.period_from and request.period_to:
        period_range = f"期間 {request.period_from} - {request.period_to}"
    elif request.period_from:
        period_range = f"期間 {request.period_from} 以降"
    elif request.period_to:
        period_range = f"期間 {request.period_to} まで"
    else:
        period_range = "全期間"

    metadata = ReportMetadata(
        report_id=report_id,
        report_type=request.report_type.value,
        generated_at=datetime.now().isoformat(),
        fiscal_year=request.fiscal_year,
        period_range=period_range,
        total_entries=stats[0] or 0,
        filters_applied={
            "period_from": request.period_from,
            "period_to": request.period_to,
            "accounts": request.accounts,
        },
    )

    if request.report_type == ReportType.SUMMARY:
        return await _generate_summary_report(db, request, metadata, stats)
    elif request.report_type == ReportType.DETAILED:
        return await _generate_detailed_report(db, request, metadata, stats)
    elif request.report_type == ReportType.EXECUTIVE:
        return await _generate_executive_report(db, request, metadata, stats)
    elif request.report_type == ReportType.VIOLATIONS:
        return await _generate_violations_report(db, request, metadata)
    elif request.report_type == ReportType.RISK:
        return await _generate_risk_report(db, request, metadata, stats)
    elif request.report_type == ReportType.BENFORD:
        return await _generate_benford_report(db, request, metadata)
    else:
        return await _generate_working_paper(db, request, metadata, stats)


async def _generate_summary_report(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
    stats: tuple,
) -> dict[str, Any]:
    """Generate summary report."""
    total = stats[0] or 1
    high_risk = stats[6] or 0

    # Get top violations
    violations_query = """
        SELECT rule_id, rule_name, severity, COUNT(*) as count
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE je.fiscal_year = ?
        GROUP BY rule_id, rule_name, severity
        ORDER BY count DESC
        LIMIT 10
    """
    violations = db.execute(violations_query, [request.fiscal_year])

    key_findings = [
        {
            "rule_id": row[0],
            "rule_name": row[1],
            "severity": row[2],
            "count": row[3],
        }
        for row in violations
    ]

    # Generate executive summary
    risk_pct = round(high_risk / total * 100, 2)
    executive_summary = f"""
{request.fiscal_year}年度の仕訳検証を実施しました。

【検証概要】
- 検証対象仕訳件数: {stats[0]:,}件
- 仕訳帳票数: {stats[1]:,}件
- 総取引金額: ¥{stats[2]:,.0f}
- 対象期間: {stats[3]} ～ {stats[4]}

【リスク評価】
- 高リスク仕訳: {high_risk:,}件（{risk_pct}%）
- 平均リスクスコア: {stats[7] or 0:.1f}点

【主要な発見事項】
上位{len(key_findings)}件のルール違反を検出しました。詳細は本レポートをご確認ください。
""".strip()

    recommendations = [
        "高リスク仕訳について、担当者へのヒアリングを実施してください",
        "ルール違反の多い勘定科目について、内部統制の見直しを検討してください",
        "自己承認仕訳がある場合、職務分掌の徹底を図ってください",
        "期末集中仕訳について、決算操作の可能性を検討してください",
    ]

    return {
        "metadata": metadata.model_dump(),
        "executive_summary": executive_summary,
        "key_findings": key_findings,
        "statistics": {
            "total_entries": stats[0] or 0,
            "total_journals": stats[1] or 0,
            "total_amount": stats[2] or 0,
            "unique_accounts": stats[5] or 0,
            "high_risk_count": high_risk,
            "high_risk_pct": risk_pct,
            "avg_risk_score": round(stats[7] or 0, 2),
        },
        "risk_overview": {
            "high": high_risk,
            "high_pct": risk_pct,
        },
        "recommendations": recommendations,
    }


async def _generate_detailed_report(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
    stats: tuple,
) -> dict[str, Any]:
    """Generate detailed report with all sections."""
    # Get violations by category
    cat_query = """
        SELECT
            rv.category,
            rv.rule_id,
            rv.rule_name,
            rv.severity,
            COUNT(*) as count,
            SUM(je.amount) as total_amount
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE je.fiscal_year = ?
        GROUP BY rv.category, rv.rule_id, rv.rule_name, rv.severity
        ORDER BY rv.category, count DESC
    """
    cat_result = db.execute(cat_query, [request.fiscal_year])

    violations_by_category: dict[str, list] = {}
    for row in cat_result:
        cat = row[0]
        if cat not in violations_by_category:
            violations_by_category[cat] = []
        violations_by_category[cat].append(
            {
                "rule_id": row[1],
                "rule_name": row[2],
                "severity": row[3],
                "count": row[4],
                "total_amount": row[5] or 0,
            }
        )

    # Get high risk entries
    high_risk_query = """
        SELECT
            gl_detail_id,
            journal_id,
            effective_date,
            gl_account_number,
            amount,
            risk_score,
            rule_violations,
            je_line_description
        FROM journal_entries
        WHERE fiscal_year = ? AND risk_score >= 60
        ORDER BY risk_score DESC
        LIMIT 50
    """
    high_risk_result = db.execute(high_risk_query, [request.fiscal_year])

    high_risk_entries = [
        {
            "gl_detail_id": row[0],
            "journal_id": row[1],
            "date": str(row[2]),
            "account": row[3],
            "amount": row[4],
            "risk_score": row[5],
            "violations": row[6],
            "description": row[7],
        }
        for row in high_risk_result
    ]

    sections = [
        SummaryReportSection(
            title="1. 検証概要",
            content={
                "objective": "仕訳データの網羅的検証による不正・誤謬の検出",
                "scope": f"{request.fiscal_year}年度 {metadata.period_range}",
                "method": "ルールベース検証、機械学習異常検出、ベンフォード分析",
            },
        ),
        SummaryReportSection(
            title="2. 検証結果サマリー",
            content={
                "total_entries": stats[0],
                "violations_detected": sum(
                    sum(v["count"] for v in vlist)
                    for vlist in violations_by_category.values()
                ),
                "high_risk_entries": len(high_risk_entries),
            },
        ),
        SummaryReportSection(
            title="3. カテゴリ別分析",
            content=violations_by_category,
        ),
    ]

    return {
        "metadata": metadata.model_dump(),
        "sections": [s.model_dump() for s in sections],
        "violations_by_category": violations_by_category,
        "high_risk_entries": high_risk_entries,
        "appendix": {
            "rule_definitions": "別紙参照",
            "methodology": "別紙参照",
        },
    }


async def _generate_executive_report(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
    stats: tuple,
) -> dict[str, Any]:
    """Generate executive summary report."""
    total = stats[0] or 1
    high_risk = stats[6] or 0
    risk_pct = round(high_risk / total * 100, 2)

    # Risk assessment
    if risk_pct > 5:
        overall_assessment = "要注意"
        assessment_detail = (
            "高リスク仕訳の割合が5%を超えています。詳細な調査が必要です。"
        )
    elif risk_pct > 2:
        overall_assessment = "注意"
        assessment_detail = (
            "一部注意を要する仕訳があります。優先順位を付けて確認してください。"
        )
    else:
        overall_assessment = "概ね良好"
        assessment_detail = (
            "重大な問題は検出されていませんが、高リスク仕訳の確認を推奨します。"
        )

    return {
        "metadata": metadata.model_dump(),
        "title": f"{request.fiscal_year}年度 仕訳検証 エグゼクティブサマリー",
        "overall_assessment": overall_assessment,
        "assessment_detail": assessment_detail,
        "key_metrics": {
            "total_entries_reviewed": stats[0] or 0,
            "total_amount": stats[2] or 0,
            "high_risk_count": high_risk,
            "high_risk_percentage": risk_pct,
            "average_risk_score": round(stats[7] or 0, 1),
        },
        "action_items": [
            {
                "priority": "高",
                "item": "高リスク仕訳の個別調査",
                "deadline": "2週間以内",
            },
            {
                "priority": "中",
                "item": "ルール違反パターンの分析",
                "deadline": "1ヶ月以内",
            },
            {
                "priority": "低",
                "item": "内部統制改善提案の作成",
                "deadline": "四半期内",
            },
        ],
        "generated_for": "経営陣向け",
    }


async def _generate_violations_report(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
) -> dict[str, Any]:
    """Generate violations detail report."""
    query = """
        SELECT
            rv.gl_detail_id,
            rv.journal_id,
            rv.rule_id,
            rv.rule_name,
            rv.category,
            rv.severity,
            rv.violation_description,
            je.effective_date,
            je.gl_account_number,
            je.amount,
            je.prepared_by,
            je.je_line_description
        FROM rule_violations rv
        JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
        WHERE je.fiscal_year = ?
        ORDER BY
            CASE rv.severity
                WHEN 'critical' THEN 1
                WHEN 'high' THEN 2
                WHEN 'medium' THEN 3
                ELSE 4
            END,
            je.effective_date DESC
        LIMIT 500
    """
    result = db.execute(query, [request.fiscal_year])

    violations = [
        {
            "gl_detail_id": row[0],
            "journal_id": row[1],
            "rule_id": row[2],
            "rule_name": row[3],
            "category": row[4],
            "severity": row[5],
            "description": row[6],
            "date": str(row[7]),
            "account": row[8],
            "amount": row[9],
            "prepared_by": row[10],
            "line_description": row[11],
        }
        for row in result
    ]

    # Summary by severity
    severity_summary = {}
    for v in violations:
        sev = v["severity"]
        if sev not in severity_summary:
            severity_summary[sev] = 0
        severity_summary[sev] += 1

    return {
        "metadata": metadata.model_dump(),
        "total_violations": len(violations),
        "severity_summary": severity_summary,
        "violations": violations,
    }


async def _generate_risk_report(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
    stats: tuple,
) -> dict[str, Any]:
    """Generate risk analysis report."""
    # Risk distribution
    dist_query = """
        SELECT
            CASE
                WHEN risk_score >= 80 THEN 'critical'
                WHEN risk_score >= 60 THEN 'high'
                WHEN risk_score >= 40 THEN 'medium'
                WHEN risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END as level,
            COUNT(*) as count,
            AVG(risk_score) as avg_score,
            SUM(ABS(amount)) as total_amount
        FROM journal_entries
        WHERE fiscal_year = ?
        GROUP BY
            CASE
                WHEN risk_score >= 80 THEN 'critical'
                WHEN risk_score >= 60 THEN 'high'
                WHEN risk_score >= 40 THEN 'medium'
                WHEN risk_score >= 20 THEN 'low'
                ELSE 'minimal'
            END
        ORDER BY avg_score DESC
    """
    dist_result = db.execute(dist_query, [request.fiscal_year])

    distribution = [
        {
            "level": row[0],
            "count": row[1],
            "avg_score": round(row[2] or 0, 2),
            "total_amount": row[3] or 0,
        }
        for row in dist_result
    ]

    # Top risk entries
    top_risk_query = """
        SELECT
            gl_detail_id,
            journal_id,
            effective_date,
            gl_account_number,
            amount,
            risk_score,
            rule_violations,
            anomaly_flags
        FROM journal_entries
        WHERE fiscal_year = ?
        ORDER BY risk_score DESC
        LIMIT 20
    """
    top_result = db.execute(top_risk_query, [request.fiscal_year])

    top_risk_entries = [
        {
            "gl_detail_id": row[0],
            "journal_id": row[1],
            "date": str(row[2]),
            "account": row[3],
            "amount": row[4],
            "risk_score": row[5],
            "violations": row[6],
            "anomaly_flags": row[7],
        }
        for row in top_result
    ]

    return {
        "metadata": metadata.model_dump(),
        "overall_risk_score": round(stats[7] or 0, 2),
        "distribution": distribution,
        "top_risk_entries": top_risk_entries,
        "risk_factors": {
            "rule_violations": "ルール違反による加点",
            "ml_anomalies": "機械学習異常検出による加点",
            "benford_deviation": "ベンフォード分析偏差による加点",
        },
    }


async def _generate_benford_report(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
) -> dict[str, Any]:
    """Generate Benford's Law analysis report."""
    expected = {
        1: 0.301,
        2: 0.176,
        3: 0.125,
        4: 0.097,
        5: 0.079,
        6: 0.067,
        7: 0.058,
        8: 0.051,
        9: 0.046,
    }

    query = """
        SELECT
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) as first_digit,
            COUNT(*) as count
        FROM journal_entries
        WHERE fiscal_year = ?
            AND ABS(amount) >= 10
        GROUP BY
            CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER)
        HAVING first_digit BETWEEN 1 AND 9
        ORDER BY first_digit
    """
    result = db.execute(query, [request.fiscal_year])

    total = sum(row[1] for row in result) or 1
    distribution = []
    for row in result:
        digit, count = row[0], row[1]
        actual = count / total
        exp = expected.get(digit, 0)
        distribution.append(
            {
                "digit": digit,
                "count": count,
                "actual_pct": round(actual * 100, 2),
                "expected_pct": round(exp * 100, 2),
                "deviation": round((actual - exp) * 100, 2),
            }
        )

    mad = sum(abs(d["deviation"]) for d in distribution) / 900 if distribution else 0

    if mad <= 0.6:
        conformity = "close"
        interpretation = "ベンフォードの法則に非常によく適合しています"
    elif mad <= 1.2:
        conformity = "acceptable"
        interpretation = "ベンフォードの法則に適合しています"
    elif mad <= 1.5:
        conformity = "marginally_acceptable"
        interpretation = "ベンフォードの法則からやや乖離があります"
    else:
        conformity = "nonconforming"
        interpretation = (
            "ベンフォードの法則から大きく乖離しています。詳細な調査を推奨します"
        )

    return {
        "metadata": metadata.model_dump(),
        "total_analyzed": total,
        "distribution": distribution,
        "mad": round(mad, 4),
        "conformity": conformity,
        "interpretation": interpretation,
        "methodology": "ベンフォードの法則は、自然発生的な数値データの先頭桁が1である確率が約30%であることを示す法則です。会計データがこの法則から大きく乖離している場合、データ操作の可能性を示唆します。",
    }


async def _generate_working_paper(
    db: DuckDBManager,
    request: ReportRequest,
    metadata: ReportMetadata,
    stats: tuple,
) -> dict[str, Any]:
    """Generate audit working paper."""
    return {
        "metadata": metadata.model_dump(),
        "working_paper": {
            "reference": f"WP-JE-{request.fiscal_year}",
            "prepared_by": "[監査担当者名]",
            "reviewed_by": "[レビュー担当者名]",
            "date": datetime.now().strftime("%Y-%m-%d"),
        },
        "objective": "仕訳データの網羅的検証による不正・誤謬リスクの評価",
        "scope": {
            "fiscal_year": request.fiscal_year,
            "period": metadata.period_range,
            "entries_tested": stats[0] or 0,
            "coverage": "100%（全件検証）",
        },
        "procedures_performed": [
            "1. ルールベース検証（58ルール適用）",
            "2. 機械学習による異常検出（5手法）",
            "3. ベンフォードの法則による分析",
            "4. 統合リスクスコアリング",
        ],
        "results_summary": {
            "high_risk_identified": stats[6] or 0,
            "average_risk_score": round(stats[7] or 0, 2),
        },
        "conclusion": "[結論を記載]",
        "follow_up_required": "[フォローアップ事項]",
    }


@router.get("/templates")
async def get_report_templates() -> dict[str, Any]:
    """Get available report templates.

    Returns:
        List of available templates.
    """
    return {
        "templates": [
            {
                "id": "summary",
                "name": "サマリーレポート",
                "description": "検証結果の概要と主要な発見事項",
            },
            {
                "id": "detailed",
                "name": "詳細レポート",
                "description": "カテゴリ別の詳細な分析結果",
            },
            {
                "id": "executive",
                "name": "エグゼクティブサマリー",
                "description": "経営陣向けの要約レポート",
            },
            {
                "id": "violations",
                "name": "違反一覧レポート",
                "description": "検出されたルール違反の詳細リスト",
            },
            {
                "id": "risk",
                "name": "リスク分析レポート",
                "description": "リスクスコア分布と高リスク仕訳の分析",
            },
            {
                "id": "benford",
                "name": "ベンフォード分析レポート",
                "description": "ベンフォードの法則による数値分析",
            },
            {
                "id": "working_paper",
                "name": "監査調書",
                "description": "監査手続と結果の記録用調書",
            },
        ],
    }


@router.get("/history")
async def get_report_history(
    fiscal_year: int | None = Query(None),
    limit: int = Query(20, le=100),
) -> dict[str, Any]:
    """Get report generation history.

    Args:
        fiscal_year: Filter by fiscal year.
        limit: Maximum results.

    Returns:
        List of previously generated reports.
    """
    # In a real implementation, this would query a reports table
    # For now, return empty history
    return {
        "reports": [],
        "total_count": 0,
    }


@router.get("/export/ppt")
async def export_ppt_report(
    fiscal_year: int = Query(..., description="Fiscal year"),
    company_name: str = Query("Sample Company", description="Company name"),
) -> StreamingResponse:
    """Export report as PowerPoint presentation.

    Generates a 10-slide presentation with:
    - Title slide
    - Executive summary
    - Key metrics
    - Risk distribution
    - Top findings
    - Benford analysis
    - Trend analysis
    - Recommendations
    - Next steps
    - Appendix

    Args:
        fiscal_year: Fiscal year for the report.
        company_name: Company name for the report.

    Returns:
        PowerPoint file as streaming response.
    """
    try:
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        config = ReportConfig(
            fiscal_year=fiscal_year,
            company_name=company_name,
            report_title="仕訳検証レポート",
        )
        generator = PPTReportGenerator(config)
        ppt_bytes = generator.generate()

        filename = f"JAIA_Report_{fiscal_year}_{datetime.now().strftime('%Y%m%d')}.pptx"

        return StreamingResponse(
            iter([ppt_bytes]),
            media_type="application/vnd.openxmlformats-officedocument.presentationml.presentation",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(ppt_bytes)),
            },
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"PPT generation requires python-pptx package: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PPT report: {str(e)}",
        )


@router.get("/export/pdf")
async def export_pdf_report(
    fiscal_year: int = Query(..., description="Fiscal year"),
    company_name: str = Query("Sample Company", description="Company name"),
) -> StreamingResponse:
    """Export report as PDF document.

    Generates a comprehensive PDF report with:
    - Executive summary
    - Risk distribution tables
    - Top findings
    - Recommendations

    Args:
        fiscal_year: Fiscal year for the report.
        company_name: Company name for the report.

    Returns:
        PDF file as streaming response.
    """
    try:
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        config = ReportConfig(
            fiscal_year=fiscal_year,
            company_name=company_name,
            report_title="仕訳検証レポート",
        )
        generator = PDFReportGenerator(config)
        pdf_bytes = generator.generate()

        filename = f"JAIA_Report_{fiscal_year}_{datetime.now().strftime('%Y%m%d')}.pdf"

        return StreamingResponse(
            iter([pdf_bytes]),
            media_type="application/pdf",
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "Content-Length": str(len(pdf_bytes)),
            },
        )
    except ImportError as e:
        raise HTTPException(
            status_code=500,
            detail=f"PDF generation requires reportlab package: {str(e)}",
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to generate PDF report: {str(e)}",
        )
