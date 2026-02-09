"""Master data models."""

from typing import Literal

from pydantic import BaseModel, Field


class AccountBase(BaseModel):
    """Base account model (AICPA Chart_of_Accounts compliant)."""

    account_code: str = Field(
        ...,
        max_length=20,
        description="勘定科目コード",
    )
    account_name: str = Field(
        ...,
        max_length=100,
        description="勘定科目名",
    )
    account_name_en: str | None = Field(
        None,
        max_length=100,
        description="勘定科目名（英語）",
    )
    account_category: Literal["BS", "PL"] = Field(
        ...,
        description="財務諸表区分（BS/PL）",
    )
    account_type: Literal["asset", "liability", "equity", "revenue", "expense"] = Field(
        ...,
        description="勘定科目タイプ",
    )
    normal_balance: Literal["debit", "credit"] = Field(
        ...,
        description="正常残高方向",
    )
    level: int = Field(
        ...,
        ge=1,
        le=10,
        description="階層レベル",
    )
    parent_code: str | None = Field(
        None,
        max_length=20,
        description="親科目コード",
    )
    is_posting: bool = Field(
        default=True,
        description="転記可能フラグ",
    )
    is_active: bool = Field(
        default=True,
        description="有効フラグ",
    )


class AccountCreate(AccountBase):
    """Model for creating a new account."""

    pass


class Account(AccountBase):
    """Account model with computed fields."""

    class Config:
        """Pydantic config."""

        from_attributes = True


class Department(BaseModel):
    """Department master model."""

    dept_code: str = Field(
        ...,
        max_length=20,
        description="部門コード",
    )
    dept_name: str = Field(
        ...,
        max_length=100,
        description="部門名",
    )
    dept_name_en: str | None = Field(
        None,
        max_length=100,
        description="部門名（英語）",
    )
    segment: str | None = Field(
        None,
        max_length=20,
        description="セグメントコード",
    )
    parent_dept: str | None = Field(
        None,
        max_length=20,
        description="親部門コード",
    )
    level: int = Field(
        default=1,
        ge=1,
        le=10,
        description="階層レベル",
    )
    cost_center: bool = Field(
        default=True,
        description="コストセンターフラグ",
    )
    is_active: bool = Field(
        default=True,
        description="有効フラグ",
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class Vendor(BaseModel):
    """Vendor/Customer master model."""

    vendor_code: str = Field(
        ...,
        max_length=20,
        description="取引先コード",
    )
    vendor_name: str = Field(
        ...,
        max_length=200,
        description="取引先名",
    )
    vendor_name_en: str | None = Field(
        None,
        max_length=200,
        description="取引先名（英語）",
    )
    vendor_type: Literal["CUSTOMER", "SUPPLIER", "INTERCOMPANY", "BANK", "OTHER"] = Field(
        ...,
        description="取引先区分",
    )
    country: str | None = Field(
        None,
        max_length=2,
        description="国コード (ISO 3166-1 alpha-2)",
    )
    segment: str | None = Field(
        None,
        max_length=20,
        description="セグメント",
    )
    is_related_party: bool = Field(
        default=False,
        description="関連当事者フラグ",
    )
    credit_limit: int | None = Field(
        None,
        ge=0,
        description="与信限度額",
    )
    payment_terms: int | None = Field(
        None,
        ge=0,
        description="支払条件（日数）",
    )
    is_active: bool = Field(
        default=True,
        description="有効フラグ",
    )
    risk_flag: str | None = Field(
        None,
        max_length=50,
        description="リスクフラグ",
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class User(BaseModel):
    """User master model."""

    user_id: str = Field(
        ...,
        max_length=20,
        description="ユーザーID",
    )
    user_name: str = Field(
        ...,
        max_length=100,
        description="ユーザー名",
    )
    user_name_en: str | None = Field(
        None,
        max_length=100,
        description="ユーザー名（英語）",
    )
    dept_code: str | None = Field(
        None,
        max_length=20,
        description="所属部門コード",
    )
    position: str | None = Field(
        None,
        max_length=50,
        description="役職",
    )
    approval_limit: int = Field(
        default=0,
        ge=0,
        description="承認限度額",
    )
    is_active: bool = Field(
        default=True,
        description="有効フラグ",
    )
    can_approve: bool = Field(
        default=False,
        description="承認権限フラグ",
    )
    role: str | None = Field(
        None,
        max_length=20,
        description="ロール",
    )

    class Config:
        """Pydantic config."""

        from_attributes = True


class TrialBalance(BaseModel):
    """Trial balance entry model."""

    fiscal_year: int
    accounting_period: int
    gl_account_number: str
    beginning_balance: float = 0
    period_debit: float = 0
    period_credit: float = 0
    ending_balance: float = 0

    class Config:
        """Pydantic config."""

        from_attributes = True
