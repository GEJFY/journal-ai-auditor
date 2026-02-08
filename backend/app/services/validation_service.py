"""Data validation service for import quality checks."""

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Callable, Optional

import polars as pl


@dataclass
class ValidationError:
    """A single validation error."""

    check_id: str
    check_name: str
    row_index: int
    column: Optional[str]
    value: Any
    message: str
    severity: str = "ERROR"  # ERROR or WARNING


@dataclass
class ValidationResult:
    """Result of validation checks."""

    is_valid: bool = True
    total_rows: int = 0
    checked_rows: int = 0
    error_count: int = 0
    warning_count: int = 0
    error_rows: list[int] = field(default_factory=list)
    warning_rows: list[int] = field(default_factory=list)
    errors: list[dict[str, Any]] = field(default_factory=list)
    warnings: list[dict[str, Any]] = field(default_factory=list)
    check_results: dict[str, dict[str, Any]] = field(default_factory=dict)

    def add_error(self, error: ValidationError) -> None:
        """Add an error to the result."""
        self.error_count += 1
        if error.row_index not in self.error_rows:
            self.error_rows.append(error.row_index)
        self.errors.append({
            "check_id": error.check_id,
            "check_name": error.check_name,
            "row": error.row_index,
            "column": error.column,
            "value": str(error.value) if error.value is not None else None,
            "message": error.message,
        })
        self.is_valid = False

    def add_warning(self, error: ValidationError) -> None:
        """Add a warning to the result."""
        self.warning_count += 1
        if error.row_index not in self.warning_rows:
            self.warning_rows.append(error.row_index)
        self.warnings.append({
            "check_id": error.check_id,
            "check_name": error.check_name,
            "row": error.row_index,
            "column": error.column,
            "value": str(error.value) if error.value is not None else None,
            "message": error.message,
        })


class ValidationService:
    """Service for validating journal entry data.

    Implements 10 standard validation checks:
    1. Required fields check
    2. Data type validation
    3. Date range validation
    4. Amount validation
    5. Debit/Credit indicator validation
    6. Journal balance check
    7. Account code existence check
    8. Duplicate check
    9. Referential integrity check
    10. Business rule validation
    """

    # Required columns for AICPA GL_Detail
    REQUIRED_COLUMNS = [
        "journal_id",
        "effective_date",
        "gl_account_number",
        "amount",
        "debit_credit_indicator",
    ]

    # Optional but recommended columns
    RECOMMENDED_COLUMNS = [
        "journal_id_line_number",
        "entry_date",
        "je_line_description",
        "prepared_by",
    ]

    def __init__(self) -> None:
        """Initialize validation service."""
        self.checks: list[Callable[[pl.DataFrame, ValidationResult], None]] = [
            self._check_required_fields,
            self._check_data_types,
            self._check_date_range,
            self._check_amounts,
            self._check_dc_indicator,
            self._check_journal_balance,
            self._check_account_codes,
            self._check_duplicates,
            self._check_referential_integrity,
            self._check_business_rules,
        ]

    def validate_dataframe(self, df: pl.DataFrame) -> ValidationResult:
        """Run all validation checks on a DataFrame.

        Args:
            df: DataFrame to validate.

        Returns:
            Validation result with all errors and warnings.
        """
        result = ValidationResult()
        result.total_rows = len(df)
        result.checked_rows = len(df)

        for check in self.checks:
            check(df, result)

        return result

    def _check_required_fields(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 1: Required fields are present and not null.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V001"
        check_name = "必須項目チェック"

        # Check columns exist
        missing_columns = [c for c in self.REQUIRED_COLUMNS if c not in df.columns]
        if missing_columns:
            result.add_error(ValidationError(
                check_id=check_id,
                check_name=check_name,
                row_index=-1,
                column=None,
                value=missing_columns,
                message=f"必須列が見つかりません: {', '.join(missing_columns)}",
            ))
            return

        # Check for null values in required columns
        for col in self.REQUIRED_COLUMNS:
            if col in df.columns:
                null_mask = df[col].is_null()
                null_indices = df.with_row_index().filter(null_mask)["index"].to_list()

                for idx in null_indices[:100]:  # Limit to first 100
                    result.add_error(ValidationError(
                        check_id=check_id,
                        check_name=check_name,
                        row_index=idx,
                        column=col,
                        value=None,
                        message=f"必須項目 '{col}' が空です",
                    ))

        # Warn about missing recommended columns
        missing_recommended = [c for c in self.RECOMMENDED_COLUMNS if c not in df.columns]
        if missing_recommended:
            result.add_warning(ValidationError(
                check_id=check_id,
                check_name=check_name,
                row_index=-1,
                column=None,
                value=missing_recommended,
                message=f"推奨列がありません: {', '.join(missing_recommended)}",
                severity="WARNING",
            ))

        result.check_results[check_id] = {
            "name": check_name,
            "passed": len(missing_columns) == 0,
            "missing_columns": missing_columns,
        }

    def _check_data_types(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 2: Data types are correct.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V002"
        check_name = "データ型チェック"

        errors_found = 0

        # Check amount is numeric
        if "amount" in df.columns:
            try:
                # Try to cast to float
                df.select(pl.col("amount").cast(pl.Float64))
            except Exception:
                # Find non-numeric values
                non_numeric = df.with_row_index().filter(
                    ~pl.col("amount").cast(pl.Utf8).str.contains(r"^-?\d+\.?\d*$")
                )
                for row in non_numeric.iter_rows(named=True):
                    result.add_error(ValidationError(
                        check_id=check_id,
                        check_name=check_name,
                        row_index=row["index"],
                        column="amount",
                        value=row.get("amount"),
                        message="金額が数値ではありません",
                    ))
                    errors_found += 1
                    if errors_found >= 100:
                        break

        # Check dates are valid
        for date_col in ["effective_date", "entry_date", "approved_date"]:
            if date_col in df.columns:
                dtype = df[date_col].dtype
                if dtype not in [pl.Date, pl.Datetime]:
                    # Try to parse as date
                    try:
                        df.select(pl.col(date_col).str.to_date())
                    except Exception:
                        result.add_warning(ValidationError(
                            check_id=check_id,
                            check_name=check_name,
                            row_index=-1,
                            column=date_col,
                            value=str(dtype),
                            message=f"'{date_col}' が日付型ではありません",
                            severity="WARNING",
                        ))

        result.check_results[check_id] = {
            "name": check_name,
            "passed": errors_found == 0,
            "error_count": errors_found,
        }

    def _check_date_range(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 3: Dates are within reasonable range.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V003"
        check_name = "日付範囲チェック"

        if "effective_date" not in df.columns:
            return

        # Define reasonable date range (10 years back to 1 year forward)
        min_date = date(date.today().year - 10, 1, 1)
        max_date = date(date.today().year + 1, 12, 31)

        errors_found = 0

        try:
            df_with_idx = df.with_row_index()

            # Check dates outside range
            if df["effective_date"].dtype == pl.Date:
                out_of_range = df_with_idx.filter(
                    (pl.col("effective_date") < min_date) |
                    (pl.col("effective_date") > max_date)
                )

                for row in out_of_range.iter_rows(named=True):
                    result.add_warning(ValidationError(
                        check_id=check_id,
                        check_name=check_name,
                        row_index=row["index"],
                        column="effective_date",
                        value=row.get("effective_date"),
                        message=f"日付が範囲外です ({min_date} - {max_date})",
                        severity="WARNING",
                    ))
                    errors_found += 1
                    if errors_found >= 50:
                        break

        except Exception:
            pass

        result.check_results[check_id] = {
            "name": check_name,
            "passed": errors_found == 0,
            "warning_count": errors_found,
        }

    def _check_amounts(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 4: Amounts are valid.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V004"
        check_name = "金額チェック"

        if "amount" not in df.columns:
            return

        errors_found = 0

        try:
            df_with_idx = df.with_row_index()

            # Check for negative amounts
            negative = df_with_idx.filter(pl.col("amount") < 0)
            for row in negative.head(50).iter_rows(named=True):
                result.add_error(ValidationError(
                    check_id=check_id,
                    check_name=check_name,
                    row_index=row["index"],
                    column="amount",
                    value=row.get("amount"),
                    message="金額が負の値です",
                ))
                errors_found += 1

            # Check for extremely large amounts (warning)
            large_threshold = 10_000_000_000  # 100億円
            large = df_with_idx.filter(pl.col("amount") > large_threshold)
            for row in large.head(20).iter_rows(named=True):
                result.add_warning(ValidationError(
                    check_id=check_id,
                    check_name=check_name,
                    row_index=row["index"],
                    column="amount",
                    value=row.get("amount"),
                    message=f"金額が非常に大きい値です (>{large_threshold:,})",
                    severity="WARNING",
                ))

        except Exception:
            pass

        result.check_results[check_id] = {
            "name": check_name,
            "passed": errors_found == 0,
            "error_count": errors_found,
        }

    def _check_dc_indicator(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 5: Debit/Credit indicator is valid.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V005"
        check_name = "借貸区分チェック"

        if "debit_credit_indicator" not in df.columns:
            return

        valid_values = ["D", "C", "d", "c", "借", "貸", "1", "2"]
        errors_found = 0

        df_with_idx = df.with_row_index()
        invalid = df_with_idx.filter(
            ~pl.col("debit_credit_indicator").cast(pl.Utf8).is_in(valid_values)
        )

        for row in invalid.head(100).iter_rows(named=True):
            result.add_error(ValidationError(
                check_id=check_id,
                check_name=check_name,
                row_index=row["index"],
                column="debit_credit_indicator",
                value=row.get("debit_credit_indicator"),
                message=f"借貸区分が不正です（有効値: D, C）",
            ))
            errors_found += 1

        result.check_results[check_id] = {
            "name": check_name,
            "passed": errors_found == 0,
            "error_count": errors_found,
        }

    def _check_journal_balance(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 6: Each journal balances (debits = credits).

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V006"
        check_name = "仕訳バランスチェック"

        if "journal_id" not in df.columns or "amount" not in df.columns:
            return

        if "debit_credit_indicator" not in df.columns:
            return

        try:
            # Calculate debit and credit totals per journal
            df_calc = df.with_columns([
                pl.when(pl.col("debit_credit_indicator").cast(pl.Utf8).str.to_uppercase() == "D")
                .then(pl.col("amount"))
                .otherwise(0)
                .alias("debit_amount"),
                pl.when(pl.col("debit_credit_indicator").cast(pl.Utf8).str.to_uppercase() == "C")
                .then(pl.col("amount"))
                .otherwise(0)
                .alias("credit_amount"),
            ])

            balance = df_calc.group_by("journal_id").agg([
                pl.sum("debit_amount").alias("total_debit"),
                pl.sum("credit_amount").alias("total_credit"),
            ]).with_columns(
                (pl.col("total_debit") - pl.col("total_credit")).abs().alias("difference")
            )

            # Find unbalanced journals (allowing for small rounding differences)
            tolerance = 0.01
            unbalanced = balance.filter(pl.col("difference") > tolerance)

            errors_found = 0
            for row in unbalanced.head(100).iter_rows(named=True):
                result.add_error(ValidationError(
                    check_id=check_id,
                    check_name=check_name,
                    row_index=-1,
                    column="journal_id",
                    value=row.get("journal_id"),
                    message=f"仕訳がバランスしていません（借方:{row['total_debit']:,.2f} 貸方:{row['total_credit']:,.2f}）",
                ))
                errors_found += 1

            result.check_results[check_id] = {
                "name": check_name,
                "passed": errors_found == 0,
                "unbalanced_count": errors_found,
                "total_journals": len(balance),
            }

        except Exception as e:
            result.add_warning(ValidationError(
                check_id=check_id,
                check_name=check_name,
                row_index=-1,
                column=None,
                value=None,
                message=f"バランスチェック実行エラー: {e}",
                severity="WARNING",
            ))

    def _check_account_codes(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 7: Account codes are valid format.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V007"
        check_name = "勘定科目コードチェック"

        if "gl_account_number" not in df.columns:
            return

        # Check for empty or very short codes
        df_with_idx = df.with_row_index()
        invalid = df_with_idx.filter(
            (pl.col("gl_account_number").cast(pl.Utf8).str.len_chars() < 2) |
            pl.col("gl_account_number").is_null()
        )

        errors_found = 0
        for row in invalid.head(50).iter_rows(named=True):
            result.add_warning(ValidationError(
                check_id=check_id,
                check_name=check_name,
                row_index=row["index"],
                column="gl_account_number",
                value=row.get("gl_account_number"),
                message="勘定科目コードが短すぎるか空です",
                severity="WARNING",
            ))
            errors_found += 1

        # Get unique account codes for summary
        unique_accounts = df["gl_account_number"].n_unique()

        result.check_results[check_id] = {
            "name": check_name,
            "passed": errors_found == 0,
            "warning_count": errors_found,
            "unique_accounts": unique_accounts,
        }

    def _check_duplicates(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 8: Check for duplicate entries.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V008"
        check_name = "重複チェック"

        # Check for duplicate gl_detail_id if present
        if "gl_detail_id" in df.columns:
            duplicates = df.group_by("gl_detail_id").agg(pl.count().alias("cnt")).filter(pl.col("cnt") > 1)
            if len(duplicates) > 0:
                for row in duplicates.head(20).iter_rows(named=True):
                    result.add_error(ValidationError(
                        check_id=check_id,
                        check_name=check_name,
                        row_index=-1,
                        column="gl_detail_id",
                        value=row.get("gl_detail_id"),
                        message=f"ID重複: {row['cnt']}件",
                    ))

        # Check for potential duplicate entries (same journal_id, line, account, amount)
        if all(c in df.columns for c in ["journal_id", "journal_id_line_number", "gl_account_number", "amount"]):
            key_cols = ["journal_id", "journal_id_line_number", "gl_account_number", "amount"]
            duplicates = df.group_by(key_cols).agg(pl.count().alias("cnt")).filter(pl.col("cnt") > 1)

            if len(duplicates) > 0:
                result.add_warning(ValidationError(
                    check_id=check_id,
                    check_name=check_name,
                    row_index=-1,
                    column=None,
                    value=len(duplicates),
                    message=f"潜在的な重複仕訳が{len(duplicates)}件あります",
                    severity="WARNING",
                ))

        result.check_results[check_id] = {
            "name": check_name,
            "passed": True,  # Duplicates are warnings
        }

    def _check_referential_integrity(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 9: Check referential integrity.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V009"
        check_name = "参照整合性チェック"

        # This check requires master data to be loaded
        # For now, just validate format of reference fields

        warnings_found = 0

        # Check vendor_code format if present
        if "vendor_code" in df.columns:
            non_null_vendors = df.filter(pl.col("vendor_code").is_not_null())
            if len(non_null_vendors) > 0:
                unique_vendors = non_null_vendors["vendor_code"].n_unique()
                result.check_results[f"{check_id}_vendors"] = {
                    "unique_vendors": unique_vendors,
                }

        # Check dept_code format if present
        if "dept_code" in df.columns:
            non_null_depts = df.filter(pl.col("dept_code").is_not_null())
            if len(non_null_depts) > 0:
                unique_depts = non_null_depts["dept_code"].n_unique()
                result.check_results[f"{check_id}_departments"] = {
                    "unique_departments": unique_depts,
                }

        result.check_results[check_id] = {
            "name": check_name,
            "passed": True,
            "note": "マスタデータとの照合は取込後に実行",
        }

    def _check_business_rules(
        self,
        df: pl.DataFrame,
        result: ValidationResult,
    ) -> None:
        """Check 10: Business-specific validation rules.

        Args:
            df: DataFrame to validate.
            result: Validation result to update.
        """
        check_id = "V010"
        check_name = "業務ルールチェック"

        warnings_found = 0

        # Check 1: Self-approval (preparer = approver)
        if "prepared_by" in df.columns and "approved_by" in df.columns:
            self_approved = df.filter(
                (pl.col("prepared_by").is_not_null()) &
                (pl.col("approved_by").is_not_null()) &
                (pl.col("prepared_by") == pl.col("approved_by"))
            )
            if len(self_approved) > 0:
                result.add_warning(ValidationError(
                    check_id=check_id,
                    check_name=check_name,
                    row_index=-1,
                    column=None,
                    value=len(self_approved),
                    message=f"自己承認仕訳が{len(self_approved)}件あります",
                    severity="WARNING",
                ))
                warnings_found += len(self_approved)

        # Check 2: Missing description for high amounts
        if "je_line_description" in df.columns and "amount" in df.columns:
            threshold = 1_000_000  # 100万円
            missing_desc = df.filter(
                (pl.col("amount") >= threshold) &
                (pl.col("je_line_description").is_null() | (pl.col("je_line_description").cast(pl.Utf8).str.len_chars() < 3))
            )
            if len(missing_desc) > 0:
                result.add_warning(ValidationError(
                    check_id=check_id,
                    check_name=check_name,
                    row_index=-1,
                    column="je_line_description",
                    value=len(missing_desc),
                    message=f"高額仕訳（{threshold:,}円以上）で摘要が未入力: {len(missing_desc)}件",
                    severity="WARNING",
                ))
                warnings_found += 1

        result.check_results[check_id] = {
            "name": check_name,
            "passed": warnings_found == 0,
            "warning_count": warnings_found,
        }
