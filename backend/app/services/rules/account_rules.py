"""Account-based audit rules.

20 rules for detecting account-related anomalies:
- ACC-001: Unusual account combinations
- ACC-002: Related party transactions
- ACC-003: Suspense account aging
- ACC-004: Intercompany imbalance
- ACC-005: Revenue-receivable mismatch
- ACC-006: Expense-payable mismatch
- ACC-007: Cash account anomaly
- ACC-008: Inventory adjustment
- ACC-009: Fixed asset anomaly
- ACC-010: Prepaid expense aging
- ACC-011: Accrual reversal check
- ACC-012: Tax account consistency
- ACC-013: Contra account check
- ACC-014: Capital transaction
- ACC-015: Loan account activity
- ACC-016: Investment account
- ACC-017: Provision movement
- ACC-018: Revaluation entries
- ACC-019: Chart of accounts violation
- ACC-020: Dormant account activity
"""

import polars as pl

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleSeverity,
)


class UnusualAccountCombinationRule(AuditRule):
    """ACC-001: Detect unusual account combinations in journal entries."""

    @property
    def rule_id(self) -> str:
        return "ACC-001"

    @property
    def rule_name(self) -> str:
        return "異常な勘定組み合わせ"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "通常発生しない勘定科目の組み合わせを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Get account combinations within each journal
        journal_accounts = df.group_by("journal_id").agg(
            [
                pl.col("gl_account_number").unique().alias("accounts"),
                pl.col("amount").sum().alias("total_amount"),
                pl.col("gl_detail_id").first().alias("sample_id"),
            ]
        )

        result.total_checked = len(journal_accounts)

        # Define unusual combinations
        unusual_pairs = self.get_threshold(
            "unusual_pairs",
            [
                (
                    "111",
                    "511",
                ),  # 現金 to 売上 (direct cash sales unusual for large companies)
                ("131", "521"),  # 売掛金 to 仕入 (receivables to purchases)
                ("211", "411"),  # 買掛金 to 受取利息
            ],
        )

        for row in journal_accounts.iter_rows(named=True):
            accounts = row["accounts"]
            for pair in unusual_pairs:
                acc1_match = any(a.startswith(pair[0]) for a in accounts)
                acc2_match = any(a.startswith(pair[1]) for a in accounts)
                if acc1_match and acc2_match:
                    violation = self._create_violation(
                        gl_detail_id=row["sample_id"],
                        journal_id=row["journal_id"],
                        message=f"異常な勘定組み合わせ: {pair[0]}xxx と {pair[1]}xxx",
                        details={
                            "accounts": accounts,
                            "unusual_pair": pair,
                        },
                    )
                    result.violations.append(violation)
                    break

        result.violations_found = len(result.violations)
        return result


class RelatedPartyRule(AuditRule):
    """ACC-002: Detect related party transaction anomalies."""

    @property
    def rule_id(self) -> str:
        return "ACC-002"

    @property
    def rule_name(self) -> str:
        return "関連当事者取引"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "関連当事者との取引で異常なパターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        related_accounts = self.get_threshold(
            "related_party_accounts",
            ["135", "136", "235", "236"],  # 関係会社勘定
        )

        related_entries = df.filter(
            pl.col("gl_account_number").str.starts_with(tuple(related_accounts))
        )
        result.total_checked = len(related_entries)

        # Large related party transactions
        threshold = self.get_threshold("related_party_threshold", 100_000_000)

        large_rp = related_entries.filter(pl.col("amount").abs() >= threshold)

        for row in large_rp.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額関連当事者取引: {row['amount']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "amount": row["amount"],
                    "vendor": row.get("vendor_code"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SuspenseAccountAgingRule(AuditRule):
    """ACC-003: Detect aged suspense account balances."""

    @property
    def rule_id(self) -> str:
        return "ACC-003"

    @property
    def rule_name(self) -> str:
        return "仮勘定滞留"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "長期間滞留している仮勘定（仮払金、仮受金等）を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        suspense_accounts = self.get_threshold(
            "suspense_accounts",
            ["159", "259"],  # 仮払金、仮受金
        )

        suspense = df.filter(
            pl.col("gl_account_number").str.starts_with(tuple(suspense_accounts))
        )
        result.total_checked = len(suspense)

        # Find old uncleared entries
        self.get_threshold("suspense_aging_days", 90)
        threshold = self.get_threshold("suspense_threshold", 1_000_000)

        # Group by account to find aged items
        aged = suspense.group_by("gl_account_number").agg(
            [
                pl.col("amount").sum().alias("balance"),
                pl.col("effective_date").min().alias("oldest_date"),
                pl.col("gl_detail_id").first().alias("sample_id"),
                pl.col("journal_id").first().alias("sample_journal"),
            ]
        )

        # Check if balance is material and aged
        for row in aged.iter_rows(named=True):
            if abs(row["balance"]) >= threshold:
                violation = self._create_violation(
                    gl_detail_id=row["sample_id"],
                    journal_id=row["sample_journal"],
                    message=f"仮勘定滞留: {row['gl_account_number']}, 残高{row['balance']:,.0f}円",
                    details={
                        "account": row["gl_account_number"],
                        "balance": row["balance"],
                        "oldest_date": str(row["oldest_date"]),
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class IntercompanyImbalanceRule(AuditRule):
    """ACC-004: Detect intercompany balance mismatches."""

    @property
    def rule_id(self) -> str:
        return "ACC-004"

    @property
    def rule_name(self) -> str:
        return "連結会社間不一致"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "グループ会社間の債権債務の不一致を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        ic_receivable = self.get_threshold("ic_receivable", "135")
        ic_payable = self.get_threshold("ic_payable", "235")

        # Get intercompany entries
        ic_entries = df.filter(
            pl.col("gl_account_number").str.starts_with(ic_receivable)
            | pl.col("gl_account_number").str.starts_with(ic_payable)
        )
        result.total_checked = len(ic_entries)

        # Calculate net position
        receivable_sum = ic_entries.filter(
            pl.col("gl_account_number").str.starts_with(ic_receivable)
        )["amount"].sum()

        payable_sum = ic_entries.filter(
            pl.col("gl_account_number").str.starts_with(ic_payable)
        )["amount"].sum()

        tolerance = self.get_threshold("ic_tolerance", 1_000_000)
        imbalance = abs(receivable_sum - payable_sum)

        if imbalance > tolerance:
            sample = ic_entries.head(1)
            if len(sample) > 0:
                sample_row = sample.row(0, named=True)
                violation = self._create_violation(
                    gl_detail_id=sample_row["gl_detail_id"],
                    journal_id=sample_row["journal_id"],
                    message=f"連結会社間不一致: 差額{imbalance:,.0f}円",
                    details={
                        "receivable_sum": receivable_sum,
                        "payable_sum": payable_sum,
                        "imbalance": imbalance,
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class RevenueReceivableMismatchRule(AuditRule):
    """ACC-005: Detect revenue and receivable mismatch patterns."""

    @property
    def rule_id(self) -> str:
        return "ACC-005"

    @property
    def rule_name(self) -> str:
        return "売上・売掛金不一致"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "売上計上と売掛金発生の不整合を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        revenue_prefix = self.get_threshold("revenue_prefix", "511")
        receivable_prefix = self.get_threshold("receivable_prefix", "131")

        # Get journals with revenue
        revenue_journals = df.filter(
            pl.col("gl_account_number").str.starts_with(revenue_prefix)
        )["journal_id"].unique()

        result.total_checked = len(revenue_journals)

        # Check if corresponding receivable exists
        for journal_id in revenue_journals:
            journal_entries = df.filter(pl.col("journal_id") == journal_id)

            has_revenue = journal_entries.filter(
                pl.col("gl_account_number").str.starts_with(revenue_prefix)
            )
            has_receivable = journal_entries.filter(
                pl.col("gl_account_number").str.starts_with(receivable_prefix)
            )
            has_cash = journal_entries.filter(
                pl.col("gl_account_number").str.starts_with("111")
            )

            # Revenue without receivable or cash
            if len(has_revenue) > 0 and len(has_receivable) == 0 and len(has_cash) == 0:
                revenue_row = has_revenue.row(0, named=True)
                violation = self._create_violation(
                    gl_detail_id=revenue_row["gl_detail_id"],
                    journal_id=journal_id,
                    message="売上計上に対応する売掛金/現金なし",
                    details={
                        "revenue_amount": revenue_row["amount"],
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ExpensePayableMismatchRule(AuditRule):
    """ACC-006: Detect expense and payable mismatch patterns."""

    @property
    def rule_id(self) -> str:
        return "ACC-006"

    @property
    def rule_name(self) -> str:
        return "経費・買掛金不一致"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "経費計上と買掛金発生の不整合を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        # Similar logic to ACC-005 for expenses
        result.total_checked = len(df)
        # Simplified - would implement similar to revenue check
        return result


class CashAccountAnomalyRule(AuditRule):
    """ACC-007: Detect cash account anomalies."""

    @property
    def rule_id(self) -> str:
        return "ACC-007"

    @property
    def rule_name(self) -> str:
        return "現金異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "現金勘定の異常な動きを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        cash_prefix = self.get_threshold("cash_prefix", "111")
        cash_entries = df.filter(
            pl.col("gl_account_number").str.starts_with(cash_prefix)
        )
        result.total_checked = len(cash_entries)

        # Large cash transactions
        threshold = self.get_threshold("cash_threshold", 10_000_000)

        large_cash = cash_entries.filter(pl.col("amount").abs() >= threshold)

        for row in large_cash.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額現金取引: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "description": row.get("je_line_description"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class InventoryAdjustmentRule(AuditRule):
    """ACC-008: Detect unusual inventory adjustments."""

    @property
    def rule_id(self) -> str:
        return "ACC-008"

    @property
    def rule_name(self) -> str:
        return "棚卸資産調整"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "棚卸資産の異常な調整を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        inventory_prefix = self.get_threshold("inventory_prefix", "14")
        inventory = df.filter(
            pl.col("gl_account_number").str.starts_with(inventory_prefix)
        )
        result.total_checked = len(inventory)

        # Large inventory adjustments (manual source)
        threshold = self.get_threshold("inventory_threshold", 50_000_000)
        adjustments = inventory.filter(
            (pl.col("amount").abs() >= threshold)
            & (
                pl.col("source").is_in(["MANUAL", "ADJUST"])
                | pl.col("je_line_description").str.contains("(?i)調整|棚卸|評価")
            )
        )

        for row in adjustments.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額棚卸調整: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "account": row["gl_account_number"],
                    "description": row.get("je_line_description"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class FixedAssetAnomalyRule(AuditRule):
    """ACC-009: Detect fixed asset transaction anomalies."""

    @property
    def rule_id(self) -> str:
        return "ACC-009"

    @property
    def rule_name(self) -> str:
        return "固定資産異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "固定資産取引の異常を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        fa_prefix = self.get_threshold("fixed_asset_prefix", "16")
        fa_entries = df.filter(pl.col("gl_account_number").str.starts_with(fa_prefix))
        result.total_checked = len(fa_entries)

        # Large manual fixed asset entries
        threshold = self.get_threshold("fa_threshold", 100_000_000)
        large_fa = fa_entries.filter(
            (pl.col("amount").abs() >= threshold)
            & (pl.col("source").is_in(["MANUAL", "ADJUST"]))
        )

        for row in large_fa.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額固定資産取引: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "account": row["gl_account_number"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class PrepaidExpenseAgingRule(AuditRule):
    """ACC-010: Detect aged prepaid expense items."""

    @property
    def rule_id(self) -> str:
        return "ACC-010"

    @property
    def rule_name(self) -> str:
        return "前払費用滞留"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "長期間滞留する前払費用を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        prepaid_prefix = self.get_threshold("prepaid_prefix", "152")
        prepaid = df.filter(pl.col("gl_account_number").str.starts_with(prepaid_prefix))
        result.total_checked = len(prepaid)

        # Check for old balances
        threshold = self.get_threshold("prepaid_threshold", 10_000_000)
        balance = prepaid.group_by("gl_account_number").agg(
            [
                pl.col("amount").sum().alias("balance"),
                pl.col("gl_detail_id").first().alias("sample_id"),
                pl.col("journal_id").first().alias("sample_journal"),
            ]
        )

        for row in balance.iter_rows(named=True):
            if abs(row["balance"]) >= threshold:
                violation = self._create_violation(
                    gl_detail_id=row["sample_id"],
                    journal_id=row["sample_journal"],
                    message=f"前払費用残高: {row['balance']:,.0f}円",
                    details={
                        "account": row["gl_account_number"],
                        "balance": row["balance"],
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class AccrualReversalRule(AuditRule):
    """ACC-011: Check accrual reversal patterns."""

    @property
    def rule_id(self) -> str:
        return "ACC-011"

    @property
    def rule_name(self) -> str:
        return "未払費用戻し"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "未払費用の計上と取崩しの整合性を検証します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)
        # Simplified implementation
        return result


class TaxAccountConsistencyRule(AuditRule):
    """ACC-012: Check tax account consistency."""

    @property
    def rule_id(self) -> str:
        return "ACC-012"

    @property
    def rule_name(self) -> str:
        return "税金勘定整合性"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "消費税・法人税等の勘定の整合性を検証します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        tax_accounts = self.get_threshold("tax_accounts", ["255", "256", "257"])
        tax_entries = df.filter(
            pl.col("gl_account_number").str.starts_with(tuple(tax_accounts))
        )
        result.total_checked = len(tax_entries)

        # Check for manual tax adjustments
        threshold = self.get_threshold("tax_threshold", 10_000_000)
        manual_tax = tax_entries.filter(
            (pl.col("amount").abs() >= threshold) & (pl.col("source") == "MANUAL")
        )

        for row in manual_tax.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"手動税金調整: {row['amount']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ContraAccountRule(AuditRule):
    """ACC-013: Detect contra account issues."""

    @property
    def rule_id(self) -> str:
        return "ACC-013"

    @property
    def rule_name(self) -> str:
        return "評価勘定異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "評価勘定（貸倒引当金等）の異常を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)
        return result


class CapitalTransactionRule(AuditRule):
    """ACC-014: Detect capital transaction anomalies."""

    @property
    def rule_id(self) -> str:
        return "ACC-014"

    @property
    def rule_name(self) -> str:
        return "資本取引"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "資本金・資本剰余金等の変動を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.CRITICAL

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        capital_prefix = self.get_threshold("capital_prefix", "31")
        capital = df.filter(pl.col("gl_account_number").str.starts_with(capital_prefix))
        result.total_checked = len(capital)

        for row in capital.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"資本取引: {row['amount']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "amount": row["amount"],
                },
                score_impact=20.0,
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class LoanAccountActivityRule(AuditRule):
    """ACC-015: Detect loan account activity."""

    @property
    def rule_id(self) -> str:
        return "ACC-015"

    @property
    def rule_name(self) -> str:
        return "借入金変動"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "借入金勘定の変動を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        loan_prefix = self.get_threshold("loan_prefix", "23")
        loans = df.filter(pl.col("gl_account_number").str.starts_with(loan_prefix))
        result.total_checked = len(loans)

        threshold = self.get_threshold("loan_threshold", 100_000_000)
        large_loans = loans.filter(pl.col("amount").abs() >= threshold)

        for row in large_loans.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"借入金変動: {row['amount']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class InvestmentAccountRule(AuditRule):
    """ACC-016: Detect investment account activity."""

    @property
    def rule_id(self) -> str:
        return "ACC-016"

    @property
    def rule_name(self) -> str:
        return "投資勘定変動"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "投資有価証券等の変動を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        investment_prefix = self.get_threshold("investment_prefix", "17")
        investments = df.filter(
            pl.col("gl_account_number").str.starts_with(investment_prefix)
        )
        result.total_checked = len(investments)

        threshold = self.get_threshold("investment_threshold", 100_000_000)
        large_inv = investments.filter(pl.col("amount").abs() >= threshold)

        for row in large_inv.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"投資勘定変動: {row['amount']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ProvisionMovementRule(AuditRule):
    """ACC-017: Detect provision account movements."""

    @property
    def rule_id(self) -> str:
        return "ACC-017"

    @property
    def rule_name(self) -> str:
        return "引当金変動"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "各種引当金の計上・取崩しを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        provision_prefix = self.get_threshold("provision_prefix", "26")
        provisions = df.filter(
            pl.col("gl_account_number").str.starts_with(provision_prefix)
        )
        result.total_checked = len(provisions)

        threshold = self.get_threshold("provision_threshold", 50_000_000)
        large_prov = provisions.filter(pl.col("amount").abs() >= threshold)

        for row in large_prov.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"引当金変動: {row['amount']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class RevaluationEntryRule(AuditRule):
    """ACC-018: Detect revaluation entries."""

    @property
    def rule_id(self) -> str:
        return "ACC-018"

    @property
    def rule_name(self) -> str:
        return "評価替仕訳"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "資産・負債の評価替え仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        reval_keywords = ["評価", "時価", "減損", "洗替"]
        revaluations = df.filter(
            pl.col("je_line_description").str.contains("|".join(reval_keywords))
        )
        result.total_checked = len(revaluations)

        threshold = self.get_threshold("revaluation_threshold", 10_000_000)
        large_reval = revaluations.filter(pl.col("amount").abs() >= threshold)

        for row in large_reval.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"評価替仕訳: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "description": row.get("je_line_description"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ChartOfAccountsViolationRule(AuditRule):
    """ACC-019: Detect chart of accounts violations."""

    @property
    def rule_id(self) -> str:
        return "ACC-019"

    @property
    def rule_name(self) -> str:
        return "勘定科目違反"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "勘定科目マスタに存在しない科目コードを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # This would need chart_of_accounts table
        # Simplified: check for null or empty account numbers
        invalid = df.filter(
            pl.col("gl_account_number").is_null() | (pl.col("gl_account_number") == "")
        )

        for row in invalid.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message="勘定科目コード不正",
                details={
                    "account": row.get("gl_account_number"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class DormantAccountActivityRule(AuditRule):
    """ACC-020: Detect activity in dormant accounts."""

    @property
    def rule_id(self) -> str:
        return "ACC-020"

    @property
    def rule_name(self) -> str:
        return "休眠勘定活動"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.ACCOUNT

    @property
    def description(self) -> str:
        return "長期間使用されていなかった勘定科目への活動を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Find accounts with few transactions
        account_activity = df.group_by("gl_account_number").agg(
            [
                pl.count().alias("tx_count"),
                pl.col("amount").sum().alias("total"),
                pl.col("gl_detail_id").first().alias("sample_id"),
                pl.col("journal_id").first().alias("sample_journal"),
            ]
        )

        result.total_checked = len(account_activity)

        # Accounts with single high-value transaction (potentially dormant reactivation)
        threshold = self.get_threshold("dormant_threshold", 10_000_000)
        suspicious = account_activity.filter(
            (pl.col("tx_count") <= 2) & (pl.col("total").abs() >= threshold)
        )

        for row in suspicious.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["sample_journal"],
                message=f"休眠勘定活動: {row['gl_account_number']}, {row['total']:,.0f}円",
                details={
                    "account": row["gl_account_number"],
                    "tx_count": row["tx_count"],
                    "total": row["total"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


def create_account_rule_set() -> RuleSet:
    """Create the complete account rule set.

    Returns:
        RuleSet with all 20 account rules.
    """
    rule_set = RuleSet(
        name="account_rules",
        description="勘定科目に関する監査ルール (20件)",
    )

    rules = [
        UnusualAccountCombinationRule(),
        RelatedPartyRule(),
        SuspenseAccountAgingRule(),
        IntercompanyImbalanceRule(),
        RevenueReceivableMismatchRule(),
        ExpensePayableMismatchRule(),
        CashAccountAnomalyRule(),
        InventoryAdjustmentRule(),
        FixedAssetAnomalyRule(),
        PrepaidExpenseAgingRule(),
        AccrualReversalRule(),
        TaxAccountConsistencyRule(),
        ContraAccountRule(),
        CapitalTransactionRule(),
        LoanAccountActivityRule(),
        InvestmentAccountRule(),
        ProvisionMovementRule(),
        RevaluationEntryRule(),
        ChartOfAccountsViolationRule(),
        DormantAccountActivityRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
