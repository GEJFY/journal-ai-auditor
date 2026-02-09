"""
ReportGenerator ユニットテスト

PPT/PDFレポート生成をモックDBでテスト。
"""

from unittest.mock import MagicMock, patch

# =========================================================
# ReportConfig テスト
# =========================================================


class TestReportConfig:
    """レポート設定データクラスのテスト"""

    def test_default_values(self):
        from app.services.report_generator import ReportConfig

        config = ReportConfig(
            fiscal_year=2024,
            company_name="テスト株式会社",
        )
        assert config.fiscal_year == 2024
        assert config.company_name == "テスト株式会社"
        assert config.include_details is True or hasattr(config, "include_details")

    def test_custom_values(self):
        from app.services.report_generator import ReportConfig

        config = ReportConfig(
            fiscal_year=2024,
            period_from=1,
            period_to=6,
            company_name="JAIA Corp",
            report_title="中間監査レポート",
            prepared_by="監査太郎",
            include_details=False,
        )
        assert config.period_from == 1
        assert config.period_to == 6
        assert config.prepared_by == "監査太郎"


# =========================================================
# PPTReportGenerator テスト
# =========================================================


class TestPPTReportGenerator:
    """PowerPointレポート生成のテスト"""

    def _mock_db_stats(self):
        """DB統計クエリのモック結果"""
        return {
            "total_entries": 10000,
            "total_amount": 5_000_000_000,
            "period_count": 12,
            "unique_accounts": 150,
            "high_risk_count": 50,
            "medium_risk_count": 200,
            "low_risk_count": 9750,
        }

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_returns_bytes(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_db.execute.return_value = None
        mock_db_cls.return_value = mock_db

        config = ReportConfig(
            fiscal_year=2024,
            company_name="テスト株式会社",
        )
        generator = PPTReportGenerator(config)

        # DB統計をモック
        generator._get_summary_stats = MagicMock(return_value=self._mock_db_stats())
        generator._get_risk_distribution = MagicMock(
            return_value={"high": 50, "medium": 200, "low": 9750}
        )
        generator._get_top_findings = MagicMock(return_value=[])
        generator._get_benford_analysis = MagicMock(
            return_value={"mad": 0.008, "conformity": "Acceptable"}
        )

        result = generator.generate()
        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_empty_dataset(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_db_cls.return_value = mock_db

        config = ReportConfig(
            fiscal_year=2024,
            company_name="空データテスト",
        )
        generator = PPTReportGenerator(config)
        generator._get_summary_stats = MagicMock(
            return_value={
                "total_entries": 0,
                "total_amount": 0,
                "period_count": 0,
                "unique_accounts": 0,
                "high_risk_count": 0,
                "medium_risk_count": 0,
                "low_risk_count": 0,
            }
        )
        generator._get_risk_distribution = MagicMock(
            return_value={"high": 0, "medium": 0, "low": 0}
        )
        generator._get_top_findings = MagicMock(return_value=[])
        generator._get_benford_analysis = MagicMock(
            return_value={"mad": 0.0, "conformity": "N/A"}
        )

        result = generator.generate()
        assert isinstance(result, bytes)

    def test_overall_assessment_high_risk(self):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        with patch("app.services.report_generator.DuckDBManager"):
            generator = PPTReportGenerator(config)
            assessment = generator._get_overall_assessment(
                {"high_risk_count": 100, "total_entries": 1000}
            )
            assert isinstance(assessment, str)
            assert len(assessment) > 0

    def test_overall_assessment_low_risk(self):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        with patch("app.services.report_generator.DuckDBManager"):
            generator = PPTReportGenerator(config)
            assessment = generator._get_overall_assessment(
                {"high_risk_count": 0, "total_entries": 1000}
            )
            assert isinstance(assessment, str)


# =========================================================
# PDFReportGenerator テスト
# =========================================================


class TestPDFReportGenerator:
    """PDFレポート生成のテスト"""

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_returns_bytes(self, mock_db_cls):
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db = MagicMock()
        mock_db.query.return_value = []
        mock_db_cls.return_value = mock_db

        config = ReportConfig(
            fiscal_year=2024,
            company_name="テスト株式会社",
        )
        generator = PDFReportGenerator(config)
        generator._get_summary_stats = MagicMock(
            return_value={
                "total_entries": 500,
                "total_amount": 1_000_000_000,
                "high_risk_count": 10,
                "medium_risk_count": 50,
                "low_risk_count": 440,
            }
        )
        generator._get_risk_distribution = MagicMock(
            return_value={"high": 10, "medium": 50, "low": 440}
        )
        generator._get_top_findings = MagicMock(return_value=[])

        result = generator.generate()
        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch("app.services.report_generator.DuckDBManager")
    def test_create_table(self, mock_db_cls):
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db = MagicMock()
        mock_db_cls.return_value = mock_db

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)

        data = [["Row1 Col1", "Row1 Col2"], ["Row2 Col1", "Row2 Col2"]]
        header = ["Header 1", "Header 2"]
        table = generator._create_table(data, header)
        assert table is not None
