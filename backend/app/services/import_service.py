"""Data import service using Polars for high-performance processing."""

import uuid
from datetime import datetime
from pathlib import Path
from typing import Any, Literal

import polars as pl

from app.db import DuckDBManager
from app.services.validation_service import ValidationResult, ValidationService


class ImportResult:
    """Result of an import operation."""

    def __init__(self) -> None:
        self.success: bool = False
        self.import_id: str = str(uuid.uuid4())
        self.filename: str = ""
        self.file_type: str = ""
        self.total_rows: int = 0
        self.imported_rows: int = 0
        self.error_rows: int = 0
        self.warning_rows: int = 0
        self.errors: list[dict[str, Any]] = []
        self.warnings: list[dict[str, Any]] = []
        self.started_at: datetime = datetime.now()
        self.completed_at: datetime | None = None

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "success": self.success,
            "import_id": self.import_id,
            "filename": self.filename,
            "file_type": self.file_type,
            "total_rows": self.total_rows,
            "imported_rows": self.imported_rows,
            "error_rows": self.error_rows,
            "warning_rows": self.warning_rows,
            "errors": self.errors[:100],  # Limit errors returned
            "warnings": self.warnings[:100],
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat()
            if self.completed_at
            else None,
        }


class ColumnMapping:
    """Column mapping configuration for import."""

    # AICPA GL_Detail standard columns
    STANDARD_COLUMNS = {
        "gl_detail_id": ["gl_detail_id", "id", "line_id", "detail_id"],
        "business_unit_code": [
            "business_unit_code",
            "bu_code",
            "company_code",
            "company",
        ],
        "fiscal_year": ["fiscal_year", "year", "fy"],
        "accounting_period": ["accounting_period", "period", "month"],
        "journal_id": ["journal_id", "je_id", "voucher_no", "slip_no", "伝票番号"],
        "journal_id_line_number": [
            "journal_id_line_number",
            "line_no",
            "line_number",
            "行番号",
        ],
        "effective_date": [
            "effective_date",
            "posting_date",
            "transaction_date",
            "計上日",
            "発効日",
        ],
        "entry_date": ["entry_date", "input_date", "created_date", "入力日"],
        "entry_time": ["entry_time", "input_time", "created_time", "入力時刻"],
        "gl_account_number": [
            "gl_account_number",
            "account_code",
            "account",
            "勘定科目コード",
            "科目",
        ],
        "amount": ["amount", "金額"],
        "amount_currency": ["amount_currency", "currency", "通貨"],
        "functional_amount": ["functional_amount", "local_amount", "円貨金額"],
        "debit_credit_indicator": [
            "debit_credit_indicator",
            "dc_flag",
            "dc",
            "借貸区分",
        ],
        "je_line_description": [
            "je_line_description",
            "description",
            "memo",
            "摘要",
            "適用",
        ],
        "source": ["source", "source_system", "発生源"],
        "vendor_code": ["vendor_code", "customer_code", "取引先コード"],
        "dept_code": ["dept_code", "department_code", "部門コード"],
        "prepared_by": ["prepared_by", "created_by", "入力者", "起票者"],
        "approved_by": ["approved_by", "approver", "承認者"],
        "approved_date": ["approved_date", "approval_date", "承認日"],
    }

    @classmethod
    def auto_detect(cls, columns: list[str]) -> dict[str, str]:
        """Auto-detect column mapping from source columns.

        Args:
            columns: List of column names from source file.

        Returns:
            Dictionary mapping standard columns to source columns.
        """
        mapping: dict[str, str] = {}
        columns_lower = {c.lower(): c for c in columns}

        for standard_col, aliases in cls.STANDARD_COLUMNS.items():
            for alias in aliases:
                if alias.lower() in columns_lower:
                    mapping[standard_col] = columns_lower[alias.lower()]
                    break

        return mapping


class ImportService:
    """Service for importing journal entry data."""

    def __init__(self, db: DuckDBManager | None = None) -> None:
        """Initialize import service.

        Args:
            db: DuckDB manager instance.
        """
        self.db = db or DuckDBManager()
        self.validator = ValidationService()

    def read_file(
        self,
        file_path: Path,
        file_type: Literal["csv", "excel"] | None = None,
    ) -> pl.DataFrame:
        """Read a file into a Polars DataFrame.

        Args:
            file_path: Path to the file.
            file_type: Type of file (csv or excel). Auto-detected if not provided.

        Returns:
            Polars DataFrame with file contents.

        Raises:
            ValueError: If file type is unsupported.
        """
        if file_type is None:
            suffix = file_path.suffix.lower()
            if suffix == ".csv":
                file_type = "csv"
            elif suffix in [".xlsx", ".xls"]:
                file_type = "excel"
            else:
                raise ValueError(f"Unsupported file type: {suffix}")

        if file_type == "csv":
            return pl.read_csv(
                file_path,
                try_parse_dates=True,
                ignore_errors=True,
                encoding="utf-8",
            )
        elif file_type == "excel":
            try:
                return pl.read_excel(file_path)
            except ImportError:
                # fastexcel (calamine) が無い場合 openpyxl にフォールバック
                return pl.read_excel(file_path, engine="openpyxl")
        else:
            raise ValueError(f"Unsupported file type: {file_type}")

    def preview_file(
        self,
        file_path: Path,
        rows: int = 100,
    ) -> dict[str, Any]:
        """Preview a file without full import.

        Args:
            file_path: Path to the file.
            rows: Number of rows to preview.

        Returns:
            Preview data including columns, sample rows, and suggested mapping.
        """
        df = self.read_file(file_path)

        columns = df.columns
        suggested_mapping = ColumnMapping.auto_detect(columns)

        # Get sample data
        sample_df = df.head(rows)

        return {
            "filename": file_path.name,
            "total_rows": len(df),
            "columns": columns,
            "column_count": len(columns),
            "suggested_mapping": suggested_mapping,
            "unmapped_columns": [
                c for c in columns if c not in suggested_mapping.values()
            ],
            "missing_required": [
                c
                for c in [
                    "journal_id",
                    "effective_date",
                    "gl_account_number",
                    "amount",
                    "debit_credit_indicator",
                ]
                if c not in suggested_mapping
            ],
            "sample_data": sample_df.to_dicts()[:10],
            "dtypes": {
                col: str(dtype)
                for col, dtype in zip(df.columns, df.dtypes, strict=False)
            },
        }

    def validate_file(
        self,
        file_path: Path,
        column_mapping: dict[str, str] | None = None,
    ) -> ValidationResult:
        """Validate a file before import.

        Args:
            file_path: Path to the file.
            column_mapping: Column mapping (auto-detected if not provided).

        Returns:
            Validation result with errors and warnings.
        """
        df = self.read_file(file_path)

        if column_mapping is None:
            column_mapping = ColumnMapping.auto_detect(df.columns)

        # Apply column mapping
        df = self._apply_mapping(df, column_mapping)

        # Run validation
        return self.validator.validate_dataframe(df)

    def import_file(
        self,
        file_path: Path,
        column_mapping: dict[str, str] | None = None,
        skip_validation: bool = False,
        skip_errors: bool = False,
        business_unit_code: str = "DEFAULT",
        fiscal_year: int | None = None,
    ) -> ImportResult:
        """Import a file into the database.

        Args:
            file_path: Path to the file.
            column_mapping: Column mapping.
            skip_validation: Skip validation step.
            skip_errors: Skip rows with errors.
            business_unit_code: Default business unit code.
            fiscal_year: Default fiscal year.

        Returns:
            Import result with statistics.
        """
        result = ImportResult()
        result.filename = file_path.name
        result.file_type = file_path.suffix[1:]

        try:
            # Read file
            df = self.read_file(file_path)
            result.total_rows = len(df)

            # Apply column mapping
            if column_mapping is None:
                column_mapping = ColumnMapping.auto_detect(df.columns)
            df = self._apply_mapping(df, column_mapping)

            # Validate
            if not skip_validation:
                validation = self.validator.validate_dataframe(df)
                result.errors = validation.errors
                result.warnings = validation.warnings
                result.error_rows = len(validation.error_rows)
                result.warning_rows = len(validation.warning_rows)

                if not validation.is_valid and not skip_errors:
                    result.success = False
                    result.completed_at = datetime.now()
                    return result

                # Remove error rows if skip_errors
                if skip_errors and validation.error_rows:
                    df = df.filter(~pl.arange(0, len(df)).is_in(validation.error_rows))

            # Add default values
            df = self._add_defaults(df, business_unit_code, fiscal_year)

            # Generate IDs
            df = self._generate_ids(df)

            # Insert into database
            self.db.insert_df("journal_entries", df)

            result.imported_rows = len(df)
            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(
                {
                    "type": "system",
                    "message": str(e),
                }
            )

        result.completed_at = datetime.now()
        return result

    def _apply_mapping(
        self,
        df: pl.DataFrame,
        mapping: dict[str, str],
    ) -> pl.DataFrame:
        """Apply column mapping to DataFrame.

        Args:
            df: Source DataFrame.
            mapping: Column mapping (standard -> source).

        Returns:
            DataFrame with renamed columns.
        """
        # Rename columns according to mapping
        rename_dict = {v: k for k, v in mapping.items()}
        df = df.rename(rename_dict)

        # Keep only mapped columns plus any extras
        return df

    def _add_defaults(
        self,
        df: pl.DataFrame,
        business_unit_code: str,
        fiscal_year: int | None,
    ) -> pl.DataFrame:
        """Add default values for missing columns.

        Args:
            df: DataFrame to process.
            business_unit_code: Default business unit.
            fiscal_year: Default fiscal year.

        Returns:
            DataFrame with defaults added.
        """
        # Add business_unit_code if missing
        if "business_unit_code" not in df.columns:
            df = df.with_columns(pl.lit(business_unit_code).alias("business_unit_code"))

        # Add fiscal_year if missing
        if "fiscal_year" not in df.columns:
            if fiscal_year:
                df = df.with_columns(pl.lit(fiscal_year).alias("fiscal_year"))
            elif "effective_date" in df.columns:
                # Derive from effective_date (April start fiscal year)
                df = df.with_columns(
                    pl.when(pl.col("effective_date").dt.month() >= 4)
                    .then(pl.col("effective_date").dt.year())
                    .otherwise(pl.col("effective_date").dt.year() - 1)
                    .alias("fiscal_year")
                )

        # Add accounting_period if missing
        if "accounting_period" not in df.columns and "effective_date" in df.columns:
            df = df.with_columns(
                pl.col("effective_date").dt.month().alias("accounting_period")
            )

        # Add entry_date if missing
        if "entry_date" not in df.columns:
            if "effective_date" in df.columns:
                df = df.with_columns(pl.col("effective_date").alias("entry_date"))
            else:
                df = df.with_columns(pl.lit(datetime.now().date()).alias("entry_date"))

        # Add currency if missing
        if "amount_currency" not in df.columns:
            df = df.with_columns(pl.lit("JPY").alias("amount_currency"))

        # Add functional_amount if missing
        if "functional_amount" not in df.columns and "amount" in df.columns:
            df = df.with_columns(pl.col("amount").alias("functional_amount"))

        return df

    def _generate_ids(self, df: pl.DataFrame) -> pl.DataFrame:
        """Generate unique IDs for journal entries.

        Args:
            df: DataFrame to process.

        Returns:
            DataFrame with generated IDs.
        """
        # Generate gl_detail_id if missing
        if "gl_detail_id" not in df.columns:
            # Create ID from journal_id and line_number
            if "journal_id" in df.columns and "journal_id_line_number" in df.columns:
                df = df.with_columns(
                    (
                        pl.col("journal_id")
                        + "-"
                        + pl.col("journal_id_line_number").cast(pl.Utf8).str.zfill(3)
                    ).alias("gl_detail_id")
                )
            else:
                # Generate UUID for each row
                ids = [str(uuid.uuid4()) for _ in range(len(df))]
                df = df.with_columns(pl.Series("gl_detail_id", ids))

        return df

    def import_master_data(
        self,
        file_path: Path,
        master_type: Literal["accounts", "departments", "vendors", "users"],
    ) -> ImportResult:
        """Import master data file.

        Args:
            file_path: Path to master data file.
            master_type: Type of master data.

        Returns:
            Import result.
        """
        result = ImportResult()
        result.filename = file_path.name
        result.file_type = file_path.suffix[1:]

        try:
            df = self.read_file(file_path)
            result.total_rows = len(df)

            table_name = {
                "accounts": "chart_of_accounts",
                "departments": "departments",
                "vendors": "vendors",
                "users": "users",
            }[master_type]

            self.db.insert_df(table_name, df)

            result.imported_rows = len(df)
            result.success = True

        except Exception as e:
            result.success = False
            result.errors.append(
                {
                    "type": "system",
                    "message": str(e),
                }
            )

        result.completed_at = datetime.now()
        return result
