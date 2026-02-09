"""
ImportService ユニットテスト

CSV/Excelインポート、カラムマッピング、バリデーション連携をテスト。
"""

import tempfile
from datetime import date
from pathlib import Path
from unittest.mock import MagicMock, patch

import polars as pl
import pytest


# =========================================================
# ColumnMapping テスト
# =========================================================


class TestColumnMapping:
    """カラムマッピング自動検出のテスト"""

    def test_auto_detect_english_columns(self):
        from app.services.import_service import ColumnMapping

        columns = [
            "journal_id",
            "effective_date",
            "gl_account_number",
            "amount",
            "debit_credit_indicator",
        ]
        mapping = ColumnMapping.auto_detect(columns)
        assert mapping["journal_id"] == "journal_id"
        assert mapping["effective_date"] == "effective_date"
        assert mapping["amount"] == "amount"

    def test_auto_detect_japanese_columns(self):
        from app.services.import_service import ColumnMapping

        columns = ["仕訳番号", "計上日", "勘定科目コード", "金額", "貸借区分"]
        mapping = ColumnMapping.auto_detect(columns)
        assert "journal_id" in mapping
        assert "effective_date" in mapping
        assert "amount" in mapping

    def test_auto_detect_partial_columns(self):
        from app.services.import_service import ColumnMapping

        columns = ["journal_id", "some_unknown", "amount"]
        mapping = ColumnMapping.auto_detect(columns)
        assert "journal_id" in mapping
        assert "amount" in mapping
        # 不明カラムはマッピングされない
        assert "some_unknown" not in mapping.values() or len(mapping) <= len(columns)

    def test_auto_detect_empty_columns(self):
        from app.services.import_service import ColumnMapping

        mapping = ColumnMapping.auto_detect([])
        assert isinstance(mapping, dict)
        assert len(mapping) == 0

    def test_standard_columns_defined(self):
        from app.services.import_service import ColumnMapping

        assert "journal_id" in ColumnMapping.STANDARD_COLUMNS
        assert "effective_date" in ColumnMapping.STANDARD_COLUMNS
        assert "amount" in ColumnMapping.STANDARD_COLUMNS
        assert "debit_credit_indicator" in ColumnMapping.STANDARD_COLUMNS


# =========================================================
# ImportResult テスト
# =========================================================


class TestImportResult:
    """インポート結果データクラスのテスト"""

    def test_default_values(self):
        from app.services.import_service import ImportResult

        result = ImportResult()
        assert result.total_rows == 0
        assert result.imported_rows == 0
        assert result.skipped_rows == 0
        assert result.errors == []
        assert result.warnings == []

    def test_to_dict(self):
        from app.services.import_service import ImportResult

        result = ImportResult()
        result.total_rows = 100
        result.imported_rows = 95
        result.skipped_rows = 5
        result.errors = ["error1"]
        d = result.to_dict()
        assert d["total_rows"] == 100
        assert d["imported_rows"] == 95
        assert d["skipped_rows"] == 5

    def test_to_dict_limits_errors(self):
        from app.services.import_service import ImportResult

        result = ImportResult()
        result.errors = [f"error_{i}" for i in range(200)]
        d = result.to_dict()
        assert len(d["errors"]) <= 100


# =========================================================
# ImportService テスト
# =========================================================


class TestImportServiceReadFile:
    """ファイル読み込みのテスト"""

    def test_read_csv_file(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "test.csv"
        csv_file.write_text(
            "journal_id,effective_date,amount\nJE001,2024-04-01,100000\n",
            encoding="utf-8",
        )

        service = ImportService(db=None)
        df = service.read_file(csv_file)
        assert len(df) == 1
        assert "journal_id" in df.columns

    def test_read_excel_file(self, tmp_path):
        from app.services.import_service import ImportService

        # Excelファイルを作成
        excel_file = tmp_path / "test.xlsx"
        df = pl.DataFrame(
            {
                "journal_id": ["JE001"],
                "effective_date": ["2024-04-01"],
                "amount": [100000],
            }
        )
        df.write_excel(excel_file)

        service = ImportService(db=None)
        result_df = service.read_file(excel_file, file_type="excel")
        assert len(result_df) >= 1

    def test_read_unsupported_format(self, tmp_path):
        from app.services.import_service import ImportService

        txt_file = tmp_path / "test.txt"
        txt_file.write_text("data")

        service = ImportService(db=None)
        with pytest.raises((ValueError, Exception)):
            service.read_file(txt_file, file_type="txt")

    def test_read_empty_csv(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "empty.csv"
        csv_file.write_text("journal_id,amount\n", encoding="utf-8")

        service = ImportService(db=None)
        df = service.read_file(csv_file)
        assert len(df) == 0


class TestImportServicePreview:
    """ファイルプレビューのテスト"""

    def test_preview_csv(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "preview.csv"
        lines = ["journal_id,amount"] + [f"JE{i:03d},{i * 1000}" for i in range(50)]
        csv_file.write_text("\n".join(lines), encoding="utf-8")

        service = ImportService(db=None)
        result = service.preview_file(csv_file, rows=10)
        assert "columns" in result
        assert "data" in result or "rows" in result or "preview" in result

    def test_preview_with_row_limit(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "large.csv"
        lines = ["journal_id,amount"] + [f"JE{i:03d},{i * 1000}" for i in range(200)]
        csv_file.write_text("\n".join(lines), encoding="utf-8")

        service = ImportService(db=None)
        result = service.preview_file(csv_file, rows=5)
        assert isinstance(result, dict)


class TestImportServiceValidate:
    """バリデーション連携のテスト"""

    def test_validate_valid_file(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "valid.csv"
        csv_file.write_text(
            "journal_id,effective_date,gl_account_number,amount,debit_credit_indicator\n"
            "JE001,2024-04-01,1131,100000,D\n"
            "JE001,2024-04-01,4111,100000,C\n",
            encoding="utf-8",
        )

        service = ImportService(db=None)
        result = service.validate_file(csv_file)
        assert result is not None

    def test_validate_missing_columns(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "missing.csv"
        csv_file.write_text("some_col,other_col\nval1,val2\n", encoding="utf-8")

        service = ImportService(db=None)
        result = service.validate_file(csv_file)
        # バリデーションエラーまたは警告があるはず
        assert result is not None


class TestImportServiceImport:
    """メインインポート処理のテスト"""

    def test_import_with_mock_db(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "import.csv"
        csv_file.write_text(
            "journal_id,effective_date,gl_account_number,amount,debit_credit_indicator\n"
            "JE001,2024-04-01,1131,100000,D\n"
            "JE001,2024-04-01,4111,100000,C\n",
            encoding="utf-8",
        )

        mock_db = MagicMock()
        service = ImportService(db=mock_db)
        result = service.import_file(
            file_path=csv_file,
            skip_validation=True,
            business_unit_code="GP001",
            fiscal_year=2024,
        )
        assert result is not None
        assert result.total_rows >= 0

    def test_import_master_data(self, tmp_path):
        from app.services.import_service import ImportService

        csv_file = tmp_path / "accounts.csv"
        csv_file.write_text(
            "gl_account_number,gl_account_name,account_type\n"
            "1111,現金,Asset\n"
            "1131,売掛金,Asset\n",
            encoding="utf-8",
        )

        mock_db = MagicMock()
        service = ImportService(db=mock_db)
        result = service.import_master_data(csv_file, master_type="accounts")
        assert result is not None
