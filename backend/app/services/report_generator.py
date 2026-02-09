"""Report generation service.

Generates audit reports in various formats:
- PowerPoint presentations
- PDF documents
- Excel workbooks
"""

import io
from dataclasses import dataclass
from datetime import datetime
from typing import Any

from pptx import Presentation
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN
from pptx.util import Inches, Pt
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from app.db import DuckDBManager


@dataclass
class ReportConfig:
    """Report generation configuration."""

    fiscal_year: int
    period_from: int | None = None
    period_to: int | None = None
    company_name: str = "Sample Company"
    report_title: str = "仕訳検証レポート"
    prepared_by: str = "JAIA"
    include_details: bool = True


class PPTReportGenerator:
    """PowerPoint report generator."""

    # Color scheme
    PRIMARY_COLOR = RGBColor(0x1E, 0x40, 0xAF)  # Blue
    SECONDARY_COLOR = RGBColor(0x6B, 0x72, 0x80)  # Gray
    ACCENT_COLOR = RGBColor(0xEF, 0x44, 0x44)  # Red
    SUCCESS_COLOR = RGBColor(0x22, 0xC5, 0x5E)  # Green

    def __init__(self, config: ReportConfig):
        """Initialize PPT generator.

        Args:
            config: Report configuration.
        """
        self.config = config
        self.db = DuckDBManager()
        self.prs = Presentation()
        self.prs.slide_width = Inches(13.333)
        self.prs.slide_height = Inches(7.5)

    def generate(self) -> bytes:
        """Generate PPT report.

        Returns:
            PPT file as bytes.
        """
        # Slide 1: Title
        self._add_title_slide()

        # Slide 2: Executive Summary
        self._add_summary_slide()

        # Slide 3: Key Metrics
        self._add_metrics_slide()

        # Slide 4: Risk Distribution
        self._add_risk_slide()

        # Slide 5: Top Findings
        self._add_findings_slide()

        # Slide 6: Benford Analysis
        self._add_benford_slide()

        # Slide 7: Trend Analysis
        self._add_trend_slide()

        # Slide 8: Recommendations
        self._add_recommendations_slide()

        # Slide 9: Next Steps
        self._add_next_steps_slide()

        # Slide 10: Appendix
        self._add_appendix_slide()

        # Save to bytes
        output = io.BytesIO()
        self.prs.save(output)
        output.seek(0)
        return output.getvalue()

    def _add_title_slide(self) -> None:
        """Add title slide."""
        slide_layout = self.prs.slide_layouts[6]  # Blank
        slide = self.prs.slides.add_slide(slide_layout)

        # Title
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(2.5), Inches(12.333), Inches(1.5)
        )
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = self.config.report_title
        p.font.size = Pt(44)
        p.font.bold = True
        p.font.color.rgb = self.PRIMARY_COLOR
        p.alignment = PP_ALIGN.CENTER

        # Subtitle
        subtitle_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(4), Inches(12.333), Inches(1)
        )
        tf = subtitle_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"{self.config.fiscal_year}年度 {self.config.company_name}"
        p.font.size = Pt(28)
        p.font.color.rgb = self.SECONDARY_COLOR
        p.alignment = PP_ALIGN.CENTER

        # Date
        date_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(5.5), Inches(12.333), Inches(0.5)
        )
        tf = date_box.text_frame
        p = tf.paragraphs[0]
        p.text = f"作成日: {datetime.now().strftime('%Y年%m月%d日')}"
        p.font.size = Pt(14)
        p.font.color.rgb = self.SECONDARY_COLOR
        p.alignment = PP_ALIGN.CENTER

    def _add_summary_slide(self) -> None:
        """Add executive summary slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "エグゼクティブサマリー")

        # Get data
        stats = self._get_summary_stats()

        # Summary text
        summary_text = f"""
検証概要:
• 検証対象仕訳件数: {stats.get("total_entries", 0):,}件
• 総取引金額: ¥{stats.get("total_amount", 0):,.0f}
• 対象期間: {stats.get("date_from", "")} ～ {stats.get("date_to", "")}

リスク評価:
• 高リスク仕訳: {stats.get("high_risk_count", 0):,}件 ({stats.get("high_risk_pct", 0):.1f}%)
• 平均リスクスコア: {stats.get("avg_risk_score", 0):.1f}点

総合評価: {self._get_overall_assessment(stats)}
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = summary_text.strip()
        p.font.size = Pt(18)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_metrics_slide(self) -> None:
        """Add key metrics slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "主要指標")

        stats = self._get_summary_stats()

        # Create metric boxes
        metrics = [
            ("仕訳件数", f"{stats.get('total_entries', 0):,}"),
            ("仕訳帳票数", f"{stats.get('total_journals', 0):,}"),
            ("高リスク件数", f"{stats.get('high_risk_count', 0):,}"),
            ("平均リスクスコア", f"{stats.get('avg_risk_score', 0):.1f}"),
        ]

        x_positions = [Inches(0.75), Inches(3.75), Inches(6.75), Inches(9.75)]
        for i, (label, value) in enumerate(metrics):
            box = slide.shapes.add_textbox(
                x_positions[i], Inches(2), Inches(2.5), Inches(2)
            )
            tf = box.text_frame
            tf.word_wrap = True

            # Value
            p = tf.paragraphs[0]
            p.text = value
            p.font.size = Pt(36)
            p.font.bold = True
            p.font.color.rgb = self.PRIMARY_COLOR
            p.alignment = PP_ALIGN.CENTER

            # Label
            p = tf.add_paragraph()
            p.text = label
            p.font.size = Pt(14)
            p.font.color.rgb = self.SECONDARY_COLOR
            p.alignment = PP_ALIGN.CENTER

    def _add_risk_slide(self) -> None:
        """Add risk distribution slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "リスク分布")

        dist = self._get_risk_distribution()

        # Create simple text-based chart
        content = f"""
リスクレベル別仕訳件数:

■ 高リスク (60点以上):   {dist.get("high", 0):,}件
■ 中リスク (40-59点):    {dist.get("medium", 0):,}件
■ 低リスク (20-39点):    {dist.get("low", 0):,}件
■ 最小リスク (20点未満): {dist.get("minimal", 0):,}件

高リスク仕訳には優先的な調査が必要です。
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(20)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_findings_slide(self) -> None:
        """Add top findings slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "主要な発見事項")

        findings = self._get_top_findings()

        content = "検出されたルール違反（上位5件）:\n\n"
        for i, f in enumerate(findings[:5], 1):
            content += f"{i}. {f['rule_name']}: {f['count']:,}件\n"

        if not findings:
            content = "検出された重大な発見事項はありません。"

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(18)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_benford_slide(self) -> None:
        """Add Benford analysis slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "ベンフォードの法則分析")

        benford = self._get_benford_analysis()

        content = f"""
ベンフォードの法則との適合度分析:

• MAD (平均絶対偏差): {benford.get("mad", 0):.4f}
• 適合度評価: {benford.get("conformity_label", "未評価")}

【解釈】
ベンフォードの法則は、自然発生的な数値データの先頭桁分布を示す法則です。
この法則からの大きな乖離は、データ操作の可能性を示唆する場合があります。

適合度基準:
• 0.006以下: 非常に良い適合
• 0.012以下: 許容範囲
• 0.015以下: 境界
• 0.015超: 不適合（要調査）
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(16)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_trend_slide(self) -> None:
        """Add trend analysis slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "トレンド分析")

        content = """
月次推移の主な傾向:

• 期末集中度: 決算期末月に仕訳が集中する傾向の有無を確認
• 金額変動: 月次の取引金額の異常な変動を検出
• 件数変動: 仕訳件数の急激な増減を監視

【注意点】
期末月への仕訳集中は、決算調整の可能性を示唆します。
前年同期比での大きな変動がある場合は、詳細調査を推奨します。
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(18)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_recommendations_slide(self) -> None:
        """Add recommendations slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "推奨事項")

        content = """
検証結果に基づく推奨事項:

1. 高リスク仕訳の詳細調査
   → 担当者へのヒアリングと証憑確認を実施

2. 自己承認仕訳の確認
   → 職務分掌の遵守状況を確認

3. 期末集中仕訳の検証
   → 決算調整の妥当性を検討

4. 異常パターンの追跡
   → ML検出された異常パターンの原因究明

5. 内部統制の改善提案
   → 検出された問題点に対する改善策の策定
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(16)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_next_steps_slide(self) -> None:
        """Add next steps slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "次のステップ")

        content = """
フォローアップ項目:

□ 高リスク仕訳の個別調査（優先度: 高）
  担当: [     ]  期限: [     ]

□ 内部統制の評価・改善提案
  担当: [     ]  期限: [     ]

□ 経営陣への報告
  担当: [     ]  期限: [     ]

□ 是正措置の実施確認
  担当: [     ]  期限: [     ]
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(18)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_appendix_slide(self) -> None:
        """Add appendix slide."""
        slide_layout = self.prs.slide_layouts[6]
        slide = self.prs.slides.add_slide(slide_layout)

        self._add_slide_title(slide, "付録：検証手法")

        content = """
本レポートで使用した検証手法:

【ルールベース検証】
• 58種類の監査ルールを適用
• カテゴリ: 金額、時間、勘定、承認、ML、ベンフォード

【機械学習異常検出】
• Isolation Forest
• Local Outlier Factor
• One-Class SVM
• Autoencoder
• アンサンブル投票

【統計分析】
• ベンフォードの法則（第1桁・第2桁）
• MAD（平均絶対偏差）による適合度評価
"""

        content_box = slide.shapes.add_textbox(
            Inches(0.75), Inches(1.5), Inches(11.833), Inches(5)
        )
        tf = content_box.text_frame
        tf.word_wrap = True
        p = tf.paragraphs[0]
        p.text = content.strip()
        p.font.size = Pt(14)
        p.font.color.rgb = self.SECONDARY_COLOR

    def _add_slide_title(self, slide: Any, title: str) -> None:
        """Add title to slide."""
        title_box = slide.shapes.add_textbox(
            Inches(0.5), Inches(0.3), Inches(12.333), Inches(0.8)
        )
        tf = title_box.text_frame
        p = tf.paragraphs[0]
        p.text = title
        p.font.size = Pt(32)
        p.font.bold = True
        p.font.color.rgb = self.PRIMARY_COLOR

    def _get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        query = """
            SELECT
                COUNT(*) as total_entries,
                COUNT(DISTINCT journal_id) as total_journals,
                COALESCE(SUM(ABS(amount)), 0) as total_amount,
                MIN(effective_date) as date_from,
                MAX(effective_date) as date_to,
                SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
                AVG(CASE WHEN risk_score > 0 THEN risk_score END) as avg_risk_score
            FROM journal_entries
            WHERE fiscal_year = ?
        """
        result = self.db.execute(query, [self.config.fiscal_year])
        if result:
            row = result[0]
            total = row[0] or 1
            return {
                "total_entries": row[0] or 0,
                "total_journals": row[1] or 0,
                "total_amount": row[2] or 0,
                "date_from": str(row[3]) if row[3] else "",
                "date_to": str(row[4]) if row[4] else "",
                "high_risk_count": row[5] or 0,
                "high_risk_pct": (row[5] or 0) / total * 100,
                "avg_risk_score": row[6] or 0,
            }
        return {}

    def _get_risk_distribution(self) -> dict[str, int]:
        """Get risk distribution."""
        query = """
            SELECT
                CASE
                    WHEN risk_score >= 60 THEN 'high'
                    WHEN risk_score >= 40 THEN 'medium'
                    WHEN risk_score >= 20 THEN 'low'
                    ELSE 'minimal'
                END as level,
                COUNT(*) as count
            FROM journal_entries
            WHERE fiscal_year = ?
            GROUP BY level
        """
        result = self.db.execute(query, [self.config.fiscal_year])
        dist = {"high": 0, "medium": 0, "low": 0, "minimal": 0}
        for row in result:
            dist[row[0]] = row[1]
        return dist

    def _get_top_findings(self) -> list[dict[str, Any]]:
        """Get top findings."""
        query = """
            SELECT rule_name, COUNT(*) as count
            FROM rule_violations rv
            JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
            WHERE je.fiscal_year = ?
            GROUP BY rule_name
            ORDER BY count DESC
            LIMIT 5
        """
        result = self.db.execute(query, [self.config.fiscal_year])
        return [{"rule_name": row[0], "count": row[1]} for row in result]

    def _get_benford_analysis(self) -> dict[str, Any]:
        """Get Benford analysis results."""
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
                CAST(SUBSTR(CAST(ABS(CAST(amount AS BIGINT)) AS VARCHAR), 1, 1) AS INTEGER) as digit,
                COUNT(*) as count
            FROM journal_entries
            WHERE fiscal_year = ?
                AND ABS(amount) >= 10
            GROUP BY digit
            HAVING digit BETWEEN 1 AND 9
        """
        result = self.db.execute(query, [self.config.fiscal_year])

        total = sum(row[1] for row in result) or 1
        mad = 0
        for row in result:
            digit, count = row[0], row[1]
            actual = count / total
            exp = expected.get(digit, 0)
            mad += abs(actual - exp)
        mad = mad / 9

        if mad <= 0.006:
            conformity = "close"
            label = "非常に良い適合"
        elif mad <= 0.012:
            conformity = "acceptable"
            label = "許容範囲"
        elif mad <= 0.015:
            conformity = "marginally_acceptable"
            label = "境界"
        else:
            conformity = "nonconforming"
            label = "不適合（要調査）"

        return {
            "mad": mad,
            "conformity": conformity,
            "conformity_label": label,
        }

    def _get_overall_assessment(self, stats: dict[str, Any]) -> str:
        """Get overall assessment text."""
        high_risk_pct = stats.get("high_risk_pct", 0)
        if high_risk_pct > 5:
            return "要注意 - 高リスク仕訳の割合が高く、詳細調査が必要です"
        elif high_risk_pct > 2:
            return "注意 - 一部注意を要する仕訳があります"
        else:
            return "概ね良好 - 重大な問題は検出されていません"


class PDFReportGenerator:
    """PDF report generator."""

    def __init__(self, config: ReportConfig):
        """Initialize PDF generator.

        Args:
            config: Report configuration.
        """
        self.config = config
        self.db = DuckDBManager()
        self.styles = getSampleStyleSheet()
        self._setup_styles()

    def _setup_styles(self) -> None:
        """Setup custom styles."""
        self.styles.add(
            ParagraphStyle(
                name="JapaneseTitle",
                fontSize=24,
                leading=30,
                alignment=1,  # Center
                spaceAfter=20,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="JapaneseHeading",
                fontSize=16,
                leading=20,
                spaceBefore=15,
                spaceAfter=10,
            )
        )
        self.styles.add(
            ParagraphStyle(
                name="JapaneseBody",
                fontSize=10,
                leading=14,
            )
        )

    def generate(self) -> bytes:
        """Generate PDF report.

        Returns:
            PDF file as bytes.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=20 * mm,
            leftMargin=20 * mm,
            topMargin=20 * mm,
            bottomMargin=20 * mm,
        )

        story = []

        # Title
        story.append(Paragraph(self.config.report_title, self.styles["JapaneseTitle"]))
        story.append(
            Paragraph(
                f"{self.config.fiscal_year}年度 {self.config.company_name}",
                self.styles["Normal"],
            )
        )
        story.append(Spacer(1, 30))

        # Executive Summary
        story.append(
            Paragraph("1. エグゼクティブサマリー", self.styles["JapaneseHeading"])
        )
        stats = self._get_summary_stats()
        summary_data = [
            ["検証対象仕訳件数", f"{stats.get('total_entries', 0):,}件"],
            ["総取引金額", f"¥{stats.get('total_amount', 0):,.0f}"],
            ["高リスク仕訳", f"{stats.get('high_risk_count', 0):,}件"],
            ["平均リスクスコア", f"{stats.get('avg_risk_score', 0):.1f}点"],
        ]
        story.append(self._create_table(summary_data))
        story.append(Spacer(1, 20))

        # Risk Distribution
        story.append(Paragraph("2. リスク分布", self.styles["JapaneseHeading"]))
        dist = self._get_risk_distribution()
        dist_data = [
            ["リスクレベル", "件数"],
            ["高リスク (60点以上)", f"{dist.get('high', 0):,}"],
            ["中リスク (40-59点)", f"{dist.get('medium', 0):,}"],
            ["低リスク (20-39点)", f"{dist.get('low', 0):,}"],
            ["最小リスク (20点未満)", f"{dist.get('minimal', 0):,}"],
        ]
        story.append(self._create_table(dist_data, header=True))
        story.append(Spacer(1, 20))

        # Top Findings
        story.append(Paragraph("3. 主要な発見事項", self.styles["JapaneseHeading"]))
        findings = self._get_top_findings()
        if findings:
            findings_data = [["ルール名", "違反件数"]]
            for f in findings[:10]:
                findings_data.append([f["rule_name"], f"{f['count']:,}"])
            story.append(self._create_table(findings_data, header=True))
        else:
            story.append(
                Paragraph(
                    "検出された重大な発見事項はありません。",
                    self.styles["JapaneseBody"],
                )
            )
        story.append(Spacer(1, 20))

        # Recommendations
        story.append(PageBreak())
        story.append(Paragraph("4. 推奨事項", self.styles["JapaneseHeading"]))
        recommendations = [
            "1. 高リスク仕訳の詳細調査を実施してください",
            "2. 自己承認仕訳について職務分掌の遵守状況を確認してください",
            "3. 期末集中仕訳の妥当性を検討してください",
            "4. 検出された異常パターンの原因を究明してください",
            "5. 内部統制の改善提案を策定してください",
        ]
        for rec in recommendations:
            story.append(Paragraph(rec, self.styles["JapaneseBody"]))
            story.append(Spacer(1, 5))

        # Build PDF
        doc.build(story)
        buffer.seek(0)
        return buffer.getvalue()

    def _create_table(self, data: list[list[str]], header: bool = False) -> Table:
        """Create formatted table."""
        table = Table(data, colWidths=[100 * mm, 50 * mm])
        style = [
            ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
            ("FONTSIZE", (0, 0), (-1, -1), 10),
            ("PADDING", (0, 0), (-1, -1), 5),
        ]
        if header:
            style.extend(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.lightgrey),
                    ("FONTSIZE", (0, 0), (-1, 0), 11),
                ]
            )
        table.setStyle(TableStyle(style))
        return table

    def _get_summary_stats(self) -> dict[str, Any]:
        """Get summary statistics."""
        query = """
            SELECT
                COUNT(*) as total_entries,
                COALESCE(SUM(ABS(amount)), 0) as total_amount,
                SUM(CASE WHEN risk_score >= 60 THEN 1 ELSE 0 END) as high_risk_count,
                AVG(CASE WHEN risk_score > 0 THEN risk_score END) as avg_risk_score
            FROM journal_entries
            WHERE fiscal_year = ?
        """
        result = self.db.execute(query, [self.config.fiscal_year])
        if result:
            row = result[0]
            return {
                "total_entries": row[0] or 0,
                "total_amount": row[1] or 0,
                "high_risk_count": row[2] or 0,
                "avg_risk_score": row[3] or 0,
            }
        return {}

    def _get_risk_distribution(self) -> dict[str, int]:
        """Get risk distribution."""
        query = """
            SELECT
                CASE
                    WHEN risk_score >= 60 THEN 'high'
                    WHEN risk_score >= 40 THEN 'medium'
                    WHEN risk_score >= 20 THEN 'low'
                    ELSE 'minimal'
                END as level,
                COUNT(*) as count
            FROM journal_entries
            WHERE fiscal_year = ?
            GROUP BY level
        """
        result = self.db.execute(query, [self.config.fiscal_year])
        dist = {"high": 0, "medium": 0, "low": 0, "minimal": 0}
        for row in result:
            dist[row[0]] = row[1]
        return dist

    def _get_top_findings(self) -> list[dict[str, Any]]:
        """Get top findings."""
        query = """
            SELECT rule_name, COUNT(*) as count
            FROM rule_violations rv
            JOIN journal_entries je ON rv.gl_detail_id = je.gl_detail_id
            WHERE je.fiscal_year = ?
            GROUP BY rule_name
            ORDER BY count DESC
            LIMIT 10
        """
        result = self.db.execute(query, [self.config.fiscal_year])
        return [{"rule_name": row[0], "count": row[1]} for row in result]
