"""
ReportGenerator ユニットテスト

PPT/PDFレポート生成をモックDBでテスト。
チャート・グラフ生成を含む改善版テスト。
"""

from unittest.mock import MagicMock, patch

# テスト用共通データ
MOCK_STATS = {
    "total_entries": 10000,
    "total_journals": 500,
    "total_amount": 5_000_000_000,
    "date_from": "2024-04-01",
    "date_to": "2025-03-31",
    "high_risk_count": 50,
    "high_risk_pct": 0.5,
    "avg_risk_score": 25.3,
}

MOCK_STATS_EMPTY = {
    "total_entries": 0,
    "total_journals": 0,
    "total_amount": 0,
    "date_from": "",
    "date_to": "",
    "high_risk_count": 0,
    "high_risk_pct": 0,
    "avg_risk_score": 0,
}

MOCK_RISK_DIST = {"high": 50, "medium": 200, "low": 2000, "minimal": 7750}
MOCK_RISK_DIST_EMPTY = {"high": 0, "medium": 0, "low": 0, "minimal": 0}

MOCK_FINDINGS = [
    {"rule_name": "大口取引チェック", "count": 500},
    {"rule_name": "深夜仕訳チェック", "count": 300},
    {"rule_name": "自己承認チェック", "count": 150},
]

MOCK_BENFORD_DIGITS = [
    {"digit": d, "actual_pct": round(a * 100, 2), "expected_pct": round(e * 100, 2)}
    for d, a, e in [
        (1, 0.305, 0.301),
        (2, 0.172, 0.176),
        (3, 0.128, 0.125),
        (4, 0.095, 0.097),
        (5, 0.081, 0.079),
        (6, 0.068, 0.067),
        (7, 0.055, 0.058),
        (8, 0.050, 0.051),
        (9, 0.046, 0.046),
    ]
]

MOCK_BENFORD_SUMMARY = {
    "mad": 0.008,
    "conformity": "acceptable",
    "conformity_label": "許容範囲",
}

MOCK_MONTHLY_TREND = [
    {
        "period": m,
        "entry_count": 800 + m * 50,
        "total_amount": 400_000_000,
        "high_risk_count": 3 + m,
    }
    for m in range(4, 16)
]


def _apply_mock_data(
    generator,
    stats=None,
    risk_dist=None,
    findings=None,
    benford_digits=None,
    benford_summary=None,
    trend=None,
):
    """テスト用にジェネレータのキャッシュデータを直接設定。"""
    generator._stats = stats or MOCK_STATS
    generator._risk_dist = risk_dist or MOCK_RISK_DIST
    generator._findings = findings if findings is not None else MOCK_FINDINGS
    generator._benford_digits = benford_digits or MOCK_BENFORD_DIGITS
    generator._benford_summary = benford_summary or MOCK_BENFORD_SUMMARY
    generator._monthly_trend = trend or MOCK_MONTHLY_TREND
    # _prefetch_dataをスキップ
    generator._prefetch_data = MagicMock()


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
        assert config.include_details is True

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
    """PowerPointレポート生成のテスト（チャート付き）"""

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_returns_bytes(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="テスト株式会社")
        generator = PPTReportGenerator(config)
        _apply_mock_data(generator)

        result = generator.generate()
        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_empty_dataset(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="空データテスト")
        generator = PPTReportGenerator(config)
        _apply_mock_data(
            generator,
            stats=MOCK_STATS_EMPTY,
            risk_dist=MOCK_RISK_DIST_EMPTY,
            findings=[],
            benford_digits=[],
            benford_summary={
                "mad": 0.0,
                "conformity": "close",
                "conformity_label": "N/A",
            },
            trend=[],
        )

        result = generator.generate()
        assert isinstance(result, bytes)

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_has_pptx_signature(self, mock_db_cls):
        """PPTXファイルの先頭バイトがZIP形式であることを確認"""
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PPTReportGenerator(config)
        _apply_mock_data(generator)

        result = generator.generate()
        # PPTX is a ZIP file - starts with PK signature
        assert result[:2] == b"PK"

    @patch("app.services.report_generator.DuckDBManager")
    def test_assessment_high_risk(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()
        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PPTReportGenerator(config)

        generator._stats = {**MOCK_STATS, "high_risk_pct": 8.0}
        label, detail, color = generator._get_assessment()
        assert label == "要注意"

    @patch("app.services.report_generator.DuckDBManager")
    def test_assessment_medium_risk(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()
        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PPTReportGenerator(config)

        generator._stats = {**MOCK_STATS, "high_risk_pct": 3.0}
        label, detail, color = generator._get_assessment()
        assert label == "注意"

    @patch("app.services.report_generator.DuckDBManager")
    def test_assessment_low_risk(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()
        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PPTReportGenerator(config)

        generator._stats = {**MOCK_STATS, "high_risk_pct": 0.5}
        label, detail, color = generator._get_assessment()
        assert label == "概ね良好"

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_recommendations(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()
        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PPTReportGenerator(config)
        _apply_mock_data(generator)

        recs = generator._generate_recommendations()
        assert isinstance(recs, list)
        assert len(recs) >= 2
        for rec in recs:
            assert "title" in rec
            assert "detail" in rec

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_next_steps(self, mock_db_cls):
        from app.services.report_generator import PPTReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()
        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PPTReportGenerator(config)
        _apply_mock_data(generator)

        steps = generator._generate_next_steps()
        assert isinstance(steps, list)
        assert len(steps) >= 3
        for step in steps:
            assert "priority" in step
            assert "task" in step
            assert "deadline" in step


# =========================================================
# PDFReportGenerator テスト
# =========================================================


class TestPDFReportGenerator:
    """PDFレポート生成のテスト（チャート付き）"""

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_returns_bytes(self, mock_db_cls):
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="テスト株式会社")
        generator = PDFReportGenerator(config)
        _apply_mock_data(generator)

        result = generator.generate()
        assert isinstance(result, bytes)
        assert len(result) > 0

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_has_pdf_signature(self, mock_db_cls):
        """PDFファイルの先頭がPDFヘッダであることを確認"""
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        _apply_mock_data(generator)

        result = generator.generate()
        assert result[:5] == b"%PDF-"

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_empty_dataset(self, mock_db_cls):
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="空データテスト")
        generator = PDFReportGenerator(config)
        _apply_mock_data(
            generator,
            stats=MOCK_STATS_EMPTY,
            risk_dist=MOCK_RISK_DIST_EMPTY,
            findings=[],
            benford_digits=[],
            benford_summary={
                "mad": 0.0,
                "conformity": "close",
                "conformity_label": "N/A",
            },
            trend=[],
        )

        result = generator.generate()
        assert isinstance(result, bytes)

    @patch("app.services.report_generator.DuckDBManager")
    def test_create_table(self, mock_db_cls):
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        generator._risk_dist = MOCK_RISK_DIST

        data = [["Header 1", "Header 2"], ["Row1 Col1", "Row1 Col2"]]
        table = generator._create_table(data, header=True)
        assert table is not None

    @patch("app.services.report_generator.DuckDBManager")
    def test_create_risk_pie_chart(self, mock_db_cls):
        """リスク分布円グラフが生成されることを確認"""
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        generator._risk_dist = MOCK_RISK_DIST

        result = generator._create_risk_pie_chart()
        assert result is not None
        # PNG形式の確認
        result.seek(0)
        assert result.read(4) == b"\x89PNG"

    @patch("app.services.report_generator.DuckDBManager")
    def test_create_risk_pie_chart_empty(self, mock_db_cls):
        """空データでNoneを返すことを確認"""
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        generator._risk_dist = MOCK_RISK_DIST_EMPTY

        result = generator._create_risk_pie_chart()
        assert result is None

    @patch("app.services.report_generator.DuckDBManager")
    def test_create_benford_bar_chart(self, mock_db_cls):
        """ベンフォードチャートが生成されることを確認"""
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        generator._benford_digits = MOCK_BENFORD_DIGITS

        result = generator._create_benford_bar_chart()
        assert result is not None
        result.seek(0)
        assert result.read(4) == b"\x89PNG"

    @patch("app.services.report_generator.DuckDBManager")
    def test_create_trend_line_chart(self, mock_db_cls):
        """月次トレンドチャートが生成されることを確認"""
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        generator._monthly_trend = MOCK_MONTHLY_TREND

        result = generator._create_trend_line_chart()
        assert result is not None
        result.seek(0)
        assert result.read(4) == b"\x89PNG"

    @patch("app.services.report_generator.DuckDBManager")
    def test_generate_recommendations(self, mock_db_cls):
        from app.services.report_generator import PDFReportGenerator, ReportConfig

        mock_db_cls.return_value = MagicMock()

        config = ReportConfig(fiscal_year=2024, company_name="Test")
        generator = PDFReportGenerator(config)
        _apply_mock_data(generator)

        recs = generator._generate_recommendations()
        assert isinstance(recs, list)
        assert len(recs) >= 2
        for rec in recs:
            assert isinstance(rec, str)
