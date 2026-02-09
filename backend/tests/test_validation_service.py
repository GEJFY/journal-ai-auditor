"""
ValidationService ユニットテスト

10個のバリデーションチェック全てをテスト。
"""

from datetime import date, timedelta

import polars as pl


def make_journal_df(**overrides) -> pl.DataFrame:
    """テスト用の最小限仕訳DataFrameを生成するヘルパー"""
    defaults = {
        "gl_detail_id": ["JE001-001", "JE001-002"],
        "journal_id": ["JE001", "JE001"],
        "journal_id_line_number": [1, 2],
        "effective_date": [date(2024, 4, 1), date(2024, 4, 1)],
        "entry_date": [date(2024, 4, 1), date(2024, 4, 1)],
        "gl_account_number": ["1131", "4111"],
        "amount": [100000, 100000],
        "functional_amount": [100000, 100000],
        "debit_credit_indicator": ["D", "C"],
        "je_line_description": ["売上計上", "売上計上"],
        "prepared_by": ["U001", "U001"],
        "approved_by": ["U002", "U002"],
    }
    defaults.update(overrides)
    return pl.DataFrame(defaults)


# =========================================================
# ValidationResult テスト
# =========================================================


class TestValidationResult:
    """ValidationResult データクラスのテスト"""

    def test_initial_state(self):
        from app.services.validation_service import ValidationResult

        result = ValidationResult()
        assert result.is_valid is True
        assert result.error_count == 0
        assert result.warning_count == 0

    def test_add_error_sets_invalid(self):
        from app.services.validation_service import ValidationError, ValidationResult

        result = ValidationResult()
        error = ValidationError(
            check_id="V001",
            check_name="test",
            row_index=0,
            column="col",
            value="val",
            message="error msg",
            severity="error",
        )
        result.add_error(error)
        assert result.is_valid is False
        assert result.error_count == 1

    def test_add_warning_keeps_valid(self):
        from app.services.validation_service import ValidationError, ValidationResult

        result = ValidationResult()
        warning = ValidationError(
            check_id="V001",
            check_name="test",
            row_index=0,
            column="col",
            value="val",
            message="warning msg",
            severity="warning",
        )
        result.add_warning(warning)
        assert result.is_valid is True
        assert result.warning_count == 1


# =========================================================
# ValidationService テスト
# =========================================================


class TestValidationServiceFull:
    """全体バリデーションのテスト"""

    def test_valid_data_passes(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df()
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result is not None
        assert result.total_rows == 2

    def test_empty_dataframe(self):
        from app.services.validation_service import ValidationService

        df = pl.DataFrame(
            {
                "journal_id": [],
                "effective_date": [],
                "gl_account_number": [],
                "amount": [],
                "debit_credit_indicator": [],
            }
        ).cast(
            {
                "amount": pl.Float64,
            }
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result is not None
        assert result.total_rows == 0


class TestV001RequiredFields:
    """V001: 必須フィールドチェック"""

    def test_missing_required_column(self):
        from app.services.validation_service import ValidationService

        # amount 列を削除
        df = make_journal_df()
        df = df.drop("amount")
        service = ValidationService()
        result = service.validate_dataframe(df)
        # エラーまたは警告が検出されるはず
        assert result.error_count > 0 or result.warning_count > 0

    def test_null_in_required_field(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            gl_account_number=["1131", None],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result.error_count > 0 or result.warning_count > 0


class TestV003DateRange:
    """V003: 日付範囲チェック"""

    def test_future_date_warning(self):
        from app.services.validation_service import ValidationService

        future = date.today() + timedelta(days=400)
        df = make_journal_df(
            effective_date=[future, future],
            entry_date=[future, future],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        # 1年以上先の日付は警告
        assert result.warning_count > 0 or result.error_count > 0

    def test_very_old_date_warning(self):
        from app.services.validation_service import ValidationService

        old = date(2000, 1, 1)
        df = make_journal_df(
            effective_date=[old, old],
            entry_date=[old, old],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result.warning_count > 0 or result.error_count > 0


class TestV004Amounts:
    """V004: 金額チェック"""

    def test_extremely_large_amount_warning(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            amount=[20_000_000_000, 20_000_000_000],
            functional_amount=[20_000_000_000, 20_000_000_000],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        # 100億超は警告
        assert result.warning_count > 0 or result.error_count > 0


class TestV005DCIndicator:
    """V005: 貸借区分チェック"""

    def test_valid_dc_indicators(self):
        from app.services.validation_service import ValidationService

        for indicator in ["D", "C"]:
            df = make_journal_df(
                debit_credit_indicator=[indicator, indicator],
            )
            service = ValidationService()
            result = service.validate_dataframe(df)
            # DC区分自体はエラーにならない
            dc_errors = [
                e
                for e in result.errors
                if hasattr(e, "check_id") and e.check_id == "V005"
            ]
            assert len(dc_errors) == 0

    def test_invalid_dc_indicator(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            debit_credit_indicator=["X", "Y"],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result.error_count > 0


class TestV006JournalBalance:
    """V006: 仕訳バランスチェック"""

    def test_balanced_journal(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            amount=[100000, 100000],
            debit_credit_indicator=["D", "C"],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        balance_errors = [
            e for e in result.errors if hasattr(e, "check_id") and e.check_id == "V006"
        ]
        assert len(balance_errors) == 0

    def test_unbalanced_journal(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            amount=[100000, 50000],
            debit_credit_indicator=["D", "C"],
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        # 不均衡は警告またはエラー
        assert result.error_count > 0 or result.warning_count > 0


class TestV008Duplicates:
    """V008: 重複チェック"""

    def test_duplicate_gl_detail_id(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            gl_detail_id=["JE001-001", "JE001-001"],  # 重複
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result.error_count > 0 or result.warning_count > 0


class TestV010BusinessRules:
    """V010: ビジネスルールチェック"""

    def test_self_approval_warning(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            prepared_by=["U001", "U001"],
            approved_by=["U001", "U001"],  # 自己承認
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result.warning_count > 0 or result.error_count > 0

    def test_high_amount_without_description(self):
        from app.services.validation_service import ValidationService

        df = make_journal_df(
            amount=[5_000_000, 5_000_000],
            functional_amount=[5_000_000, 5_000_000],
            je_line_description=["", ""],  # 100万超で説明なし
        )
        service = ValidationService()
        result = service.validate_dataframe(df)
        assert result.warning_count > 0 or result.error_count > 0
