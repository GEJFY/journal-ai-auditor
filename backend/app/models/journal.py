"""Journal entry models following AICPA GL_Detail standard."""

from datetime import date, datetime, time
from decimal import Decimal
from typing import Literal, Optional

from pydantic import BaseModel, Field, field_validator


class JournalEntryBase(BaseModel):
    """Base journal entry model (AICPA GL_Detail compliant).

    Follows AICPA Audit Data Standards for General Ledger Detail.
    """

    # Identification
    business_unit_code: str = Field(
        ...,
        max_length=20,
        description="事業単位コード",
    )
    fiscal_year: int = Field(
        ...,
        ge=1900,
        le=2100,
        description="会計年度",
    )
    accounting_period: int = Field(
        ...,
        ge=1,
        le=13,
        description="会計期間 (1-12, 13は調整期)",
    )
    journal_id: str = Field(
        ...,
        max_length=50,
        description="仕訳ID",
    )
    journal_id_line_number: int = Field(
        ...,
        ge=1,
        description="仕訳行番号",
    )

    # Dates and Times
    effective_date: date = Field(
        ...,
        description="発効日（仕訳計上日）",
    )
    entry_date: date = Field(
        ...,
        description="入力日",
    )
    entry_time: Optional[time] = Field(
        None,
        description="入力時刻",
    )

    # Account Information
    gl_account_number: str = Field(
        ...,
        max_length=20,
        description="勘定科目コード",
    )

    # Amount
    amount: Decimal = Field(
        ...,
        max_digits=18,
        decimal_places=2,
        description="金額",
    )
    amount_currency: str = Field(
        default="JPY",
        max_length=3,
        description="通貨コード (ISO 4217)",
    )
    functional_amount: Optional[Decimal] = Field(
        None,
        max_digits=18,
        decimal_places=2,
        description="機能通貨換算金額",
    )
    debit_credit_indicator: Literal["D", "C"] = Field(
        ...,
        description="借方(D)/貸方(C)区分",
    )

    # Description
    je_line_description: Optional[str] = Field(
        None,
        max_length=500,
        description="摘要",
    )

    # Source and Classification
    source: Optional[str] = Field(
        None,
        max_length=50,
        description="発生源（MANUAL, SALES, PURCHASE等）",
    )
    vendor_code: Optional[str] = Field(
        None,
        max_length=50,
        description="取引先コード",
    )
    dept_code: Optional[str] = Field(
        None,
        max_length=50,
        description="部門コード",
    )

    # Approval
    prepared_by: Optional[str] = Field(
        None,
        max_length=50,
        description="起票者ID",
    )
    approved_by: Optional[str] = Field(
        None,
        max_length=50,
        description="承認者ID",
    )
    approved_date: Optional[date] = Field(
        None,
        description="承認日",
    )

    # Audit Trail
    last_modified_by: Optional[str] = Field(
        None,
        max_length=50,
        description="最終更新者ID",
    )
    last_modified_date: Optional[datetime] = Field(
        None,
        description="最終更新日時",
    )

    @field_validator("amount")
    @classmethod
    def amount_must_be_positive(cls, v: Decimal) -> Decimal:
        """Ensure amount is positive."""
        if v < 0:
            raise ValueError("金額は0以上である必要があります")
        return v

    @field_validator("effective_date")
    @classmethod
    def validate_effective_date(cls, v: date) -> date:
        """Validate effective date is reasonable."""
        if v.year < 1900 or v.year > 2100:
            raise ValueError("発効日の年が不正です")
        return v


class JournalEntryCreate(JournalEntryBase):
    """Model for creating a new journal entry."""

    pass


class JournalEntry(JournalEntryBase):
    """Journal entry with generated fields."""

    gl_detail_id: str = Field(
        ...,
        description="一意識別子",
    )


class JournalEntryInDB(JournalEntry):
    """Journal entry as stored in database with analysis fields."""

    # Analysis results
    risk_score: Optional[Decimal] = Field(
        None,
        ge=0,
        le=100,
        description="リスクスコア (0-100)",
    )
    anomaly_flags: Optional[str] = Field(
        None,
        max_length=100,
        description="異常フラグ（カンマ区切り）",
    )
    rule_violations: Optional[str] = Field(
        None,
        max_length=200,
        description="ルール違反（カンマ区切り）",
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class JournalHeader(BaseModel):
    """Journal header (group of entries with same journal_id)."""

    journal_id: str
    fiscal_year: int
    accounting_period: int
    effective_date: date
    entry_date: date
    source: Optional[str]
    prepared_by: Optional[str]
    approved_by: Optional[str]
    approved_date: Optional[date]
    line_count: int
    total_debit: Decimal
    total_credit: Decimal
    is_balanced: bool
    description: Optional[str]


class JournalSearchParams(BaseModel):
    """Parameters for journal entry search."""

    fiscal_year: Optional[int] = None
    period_from: Optional[int] = Field(None, ge=1, le=13)
    period_to: Optional[int] = Field(None, ge=1, le=13)
    date_from: Optional[date] = None
    date_to: Optional[date] = None
    accounts: Optional[list[str]] = None
    departments: Optional[list[str]] = None
    vendors: Optional[list[str]] = None
    prepared_by: Optional[list[str]] = None
    approved_by: Optional[list[str]] = None
    min_amount: Optional[Decimal] = None
    max_amount: Optional[Decimal] = None
    description_contains: Optional[str] = None
    source: Optional[list[str]] = None
    risk_score_min: Optional[Decimal] = None
    has_anomaly: Optional[bool] = None
    has_violation: Optional[bool] = None
    limit: int = Field(default=100, le=10000)
    offset: int = Field(default=0, ge=0)
