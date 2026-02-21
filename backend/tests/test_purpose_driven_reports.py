"""目的別レポート出し分けのテスト.

management (経営陣向け) と auditor (監査実務者向け) でスライド数やセクション数が
異なることを検証する。
"""

from unittest.mock import MagicMock, patch

# ============================================================
# Helper: DB mock for report generators
# ============================================================


def _make_mock_db():
    """Return a DuckDBManager mock with canned query results."""
    mock_db = MagicMock()

    def _execute(query, params=None):
        q = query.lower()
        # Monthly trend (check before summary stats - both contain count(*) + sum)
        if "accounting_period" in q and "group by" in q and "order by" in q:
            return [(m, 40 + m, 1_000_000 + m * 100_000, m // 3) for m in range(1, 13)]
        # Summary stats (has count(distinct journal_id))
        if "count(distinct journal_id)" in q:
            return [(500, 100, 50_000_000, "2024-04-01", "2025-03-31", 10, 35.0)]
        # Risk distribution
        if "level" in q and "group by" in q:
            return [
                ("high", 10),
                ("medium", 30),
                ("low", 60),
                ("minimal", 400),
            ]
        # Top findings
        if "rule_name" in q and "rule_violations" in q:
            return [
                ("AMT-001 高額仕訳", 50),
                ("TIM-001 営業時間外", 30),
                ("APR-001 自己承認", 20),
            ]
        # Benford
        if "substr" in q:
            return [(d, 100 + d * 5) for d in range(1, 10)]
        return []

    mock_db.execute = _execute
    return mock_db


# ============================================================
# PPT Report: Slide count tests
# ============================================================


class TestPPTManagementReport:
    """経営陣向けPPTのテスト."""

    def test_slide_count_management(self):
        """経営陣向けPPTのスライド数が7以下であること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="management",
            )
            gen = PPTReportGenerator(config)
            ppt_bytes = gen.generate()

            assert len(ppt_bytes) > 0
            assert len(gen.prs.slides) <= 7

    def test_title_has_audience_label(self):
        """タイトルスライドに対象読者ラベルがあること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="management",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            # Title slide (index 0) should contain "経営陣向け" in one of the text boxes
            title_slide = gen.prs.slides[0]
            texts = [
                shape.text_frame.text
                for shape in title_slide.shapes
                if shape.has_text_frame
            ]
            all_text = " ".join(texts)
            assert "経営陣向け" in all_text

    def test_no_benford_slide(self):
        """経営陣向けPPTにベンフォード分析スライドがないこと."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="management",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            # Check no slide has "ベンフォードの法則分析" as a title
            # (the word may appear in recommendations text, which is OK)
            for slide in gen.prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        assert "ベンフォードの法則分析" not in shape.text_frame.text

    def test_no_appendix_slide(self):
        """経営陣向けPPTに付録スライドがないこと."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="management",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            for slide in gen.prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        assert "付録：検証手法" not in shape.text_frame.text


class TestPPTAuditorReport:
    """監査実務者向けPPTのテスト."""

    def test_slide_count_auditor(self):
        """監査実務者向けPPTのスライド数が10以上であること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            assert len(gen.prs.slides) >= 10

    def test_title_has_auditor_label(self):
        """タイトルスライドに「監査実務者向け」ラベルがあること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            title_slide = gen.prs.slides[0]
            texts = [
                shape.text_frame.text
                for shape in title_slide.shapes
                if shape.has_text_frame
            ]
            all_text = " ".join(texts)
            assert "監査実務者向け" in all_text

    def test_has_benford_slide(self):
        """監査実務者向けPPTにベンフォードスライドがあること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            all_text = ""
            for slide in gen.prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        all_text += shape.text_frame.text + " "
            assert "ベンフォード" in all_text

    def test_has_appendix_slide(self):
        """監査実務者向けPPTに付録スライドがあること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PPTReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PPTReportGenerator(config)
            gen.generate()

            all_text = ""
            for slide in gen.prs.slides:
                for shape in slide.shapes:
                    if shape.has_text_frame:
                        all_text += shape.text_frame.text + " "
            assert "付録" in all_text


# ============================================================
# PDF Report: Section tests
# ============================================================


class TestPDFManagementReport:
    """経営陣向けPDFのテスト."""

    def test_generates_pdf(self):
        """経営陣向けPDFが生成されること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PDFReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="management",
            )
            gen = PDFReportGenerator(config)
            pdf_bytes = gen.generate()

            # PDF should start with %PDF
            assert pdf_bytes[:5] == b"%PDF-"

    def test_management_story_has_no_methodology(self):
        """経営陣向けPDFに検証手法セクションがないこと."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PDFReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="management",
            )
            gen = PDFReportGenerator(config)
            gen._prefetch_data()
            story = gen._build_management_story()

            # Check that no Paragraph in the story contains "検証手法"
            from reportlab.platypus import Paragraph as RL_Paragraph

            texts = [elem.text for elem in story if isinstance(elem, RL_Paragraph)]
            all_text = " ".join(texts)
            assert "検証手法" not in all_text


class TestPDFAuditorReport:
    """監査実務者向けPDFのテスト."""

    def test_generates_pdf(self):
        """監査実務者向けPDFが生成されること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PDFReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PDFReportGenerator(config)
            pdf_bytes = gen.generate()

            assert pdf_bytes[:5] == b"%PDF-"

    def test_auditor_story_has_methodology(self):
        """監査実務者向けPDFに検証手法セクションがあること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PDFReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PDFReportGenerator(config)
            gen._prefetch_data()
            story = gen._build_auditor_story()

            from reportlab.platypus import Paragraph as RL_Paragraph

            texts = [elem.text for elem in story if isinstance(elem, RL_Paragraph)]
            all_text = " ".join(texts)
            assert "検証手法" in all_text

    def test_auditor_story_has_benford(self):
        """監査実務者向けPDFにベンフォードセクションがあること."""
        mock_db = _make_mock_db()

        with patch("app.services.report_generator.DuckDBManager", return_value=mock_db):
            from app.services.report_generator import PDFReportGenerator, ReportConfig

            config = ReportConfig(
                fiscal_year=2024,
                report_purpose="auditor",
            )
            gen = PDFReportGenerator(config)
            gen._prefetch_data()
            story = gen._build_auditor_story()

            from reportlab.platypus import Paragraph as RL_Paragraph

            texts = [elem.text for elem in story if isinstance(elem, RL_Paragraph)]
            all_text = " ".join(texts)
            assert "ベンフォード" in all_text


# ============================================================
# ReportConfig tests
# ============================================================


class TestReportConfig:
    """ReportConfigのテスト."""

    def test_default_purpose_is_auditor(self):
        from app.services.report_generator import ReportConfig

        config = ReportConfig(fiscal_year=2024)
        assert config.report_purpose == "auditor"

    def test_management_purpose(self):
        from app.services.report_generator import ReportConfig

        config = ReportConfig(fiscal_year=2024, report_purpose="management")
        assert config.report_purpose == "management"
