"""Amount-based audit rules.

15 rules for detecting anomalies in journal entry amounts:
- AMT-001: High value transactions
- AMT-002: Round amount detection
- AMT-003: Just below threshold
- AMT-004: Suspicious amount patterns
- AMT-005: Unusual amount distribution
- AMT-006: Amount outliers (statistical)
- AMT-007: Large adjusting entries
- AMT-008: Significant reversals
- AMT-009: Split transaction detection
- AMT-010: Debit-credit imbalance
- AMT-011: Foreign currency anomalies
- AMT-012: Tax amount irregularities
- AMT-013: Expense ratio anomalies
- AMT-014: Revenue recognition timing
- AMT-015: Unusual write-offs
"""

from typing import Any

import polars as pl

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSeverity,
    RuleSet,
)


class HighValueTransactionRule(AuditRule):
    """AMT-001: Detect high value transactions exceeding threshold."""

    @property
    def rule_id(self) -> str:
        return "AMT-001"

    @property
    def rule_name(self) -> str:
        return "高額取引検出"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "設定された金額閾値を超える取引を検出します。閾値は会社規模に応じて調整可能です。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        threshold = self.get_threshold("high_value_threshold", 100_000_000)  # 1億円

        # Filter high value transactions
        high_value = df.filter(pl.col("amount").abs() >= threshold)

        for row in high_value.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"高額取引: {row['amount']:,.0f}円 (閾値: {threshold:,.0f}円)",
                details={
                    "amount": row["amount"],
                    "threshold": threshold,
                    "account": row.get("gl_account_number"),
                    "description": row.get("je_line_description"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class RoundAmountRule(AuditRule):
    """AMT-002: Detect suspicious round amounts."""

    @property
    def rule_id(self) -> str:
        return "AMT-002"

    @property
    def rule_name(self) -> str:
        return "端数なし金額"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "端数のない切りの良い金額（100万円単位など）を検出します。架空取引の疑いがあります。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        min_amount = self.get_threshold("min_round_amount", 1_000_000)  # 100万円以上

        # Filter large round amounts (divisible by 100万)
        round_amounts = df.filter(
            (pl.col("amount").abs() >= min_amount) &
            (pl.col("amount").abs() % 1_000_000 == 0)
        )

        for row in round_amounts.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"端数なし金額: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "account": row.get("gl_account_number"),
                },
                score_impact=3.0,  # Low impact
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class JustBelowThresholdRule(AuditRule):
    """AMT-003: Detect amounts just below approval thresholds."""

    @property
    def rule_id(self) -> str:
        return "AMT-003"

    @property
    def rule_name(self) -> str:
        return "承認閾値直下取引"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "承認が必要な金額閾値のわずかに下（例：999万円）の取引を検出します。承認回避の疑いがあります。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # Common approval thresholds
        thresholds = self.get_threshold(
            "approval_thresholds",
            [1_000_000, 5_000_000, 10_000_000, 50_000_000, 100_000_000]
        )
        margin_ratio = self.get_threshold("margin_ratio", 0.05)  # 5% below

        for threshold in thresholds:
            lower = threshold * (1 - margin_ratio)
            upper = threshold * 0.999  # Just below

            suspicious = df.filter(
                (pl.col("amount").abs() >= lower) &
                (pl.col("amount").abs() < threshold)
            )

            for row in suspicious.iter_rows(named=True):
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"承認閾値直下: {row['amount']:,.0f}円 (閾値: {threshold:,.0f}円)",
                    details={
                        "amount": row["amount"],
                        "threshold": threshold,
                        "difference": threshold - abs(row["amount"]),
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SuspiciousPatternRule(AuditRule):
    """AMT-004: Detect suspicious amount patterns (repeated digits, sequences)."""

    @property
    def rule_id(self) -> str:
        return "AMT-004"

    @property
    def rule_name(self) -> str:
        return "不審金額パターン"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "不自然な金額パターン（1111111円、1234567円など）を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def _is_suspicious_pattern(self, amount: float) -> tuple[bool, str]:
        """Check if amount has suspicious pattern."""
        amt_str = str(abs(int(amount)))

        # Repeated digits (11111, 33333, etc.)
        if len(amt_str) >= 5 and len(set(amt_str)) == 1:
            return True, "repeated_digits"

        # Sequential digits (12345, 54321)
        if len(amt_str) >= 5:
            digits = [int(d) for d in amt_str]
            diffs = [digits[i+1] - digits[i] for i in range(len(digits)-1)]
            if all(d == 1 for d in diffs) or all(d == -1 for d in diffs):
                return True, "sequential"

        # Palindrome (12321, 45654)
        if len(amt_str) >= 5 and amt_str == amt_str[::-1]:
            return True, "palindrome"

        return False, ""

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        min_amount = self.get_threshold("min_pattern_amount", 100_000)

        filtered = df.filter(pl.col("amount").abs() >= min_amount)

        for row in filtered.iter_rows(named=True):
            is_suspicious, pattern_type = self._is_suspicious_pattern(row["amount"])
            if is_suspicious:
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"不審な金額パターン ({pattern_type}): {row['amount']:,.0f}円",
                    details={
                        "amount": row["amount"],
                        "pattern_type": pattern_type,
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class AmountDistributionRule(AuditRule):
    """AMT-005: Detect unusual amount distribution within a period."""

    @property
    def rule_id(self) -> str:
        return "AMT-005"

    @property
    def rule_name(self) -> str:
        return "金額分布異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "特定期間内で金額分布が通常と異なる取引パターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # Calculate statistics by account
        stats = df.group_by("gl_account_number").agg([
            pl.col("amount").abs().mean().alias("mean"),
            pl.col("amount").abs().std().alias("std"),
            pl.col("amount").abs().quantile(0.99).alias("p99"),
        ])

        # Join back and find anomalies
        df_with_stats = df.join(stats, on="gl_account_number", how="left")

        # Entries beyond 3 standard deviations
        std_threshold = self.get_threshold("std_threshold", 3.0)
        anomalies = df_with_stats.filter(
            (pl.col("std").is_not_null()) &
            (pl.col("std") > 0) &
            ((pl.col("amount").abs() - pl.col("mean")) / pl.col("std") > std_threshold)
        )

        for row in anomalies.iter_rows(named=True):
            z_score = (abs(row["amount"]) - row["mean"]) / row["std"]
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"金額分布異常: Z-score={z_score:.2f}",
                details={
                    "amount": row["amount"],
                    "mean": row["mean"],
                    "std": row["std"],
                    "z_score": z_score,
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class StatisticalOutlierRule(AuditRule):
    """AMT-006: Statistical outlier detection using IQR method."""

    @property
    def rule_id(self) -> str:
        return "AMT-006"

    @property
    def rule_name(self) -> str:
        return "統計的外れ値"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "IQR法による統計的外れ値を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        iqr_multiplier = self.get_threshold("iqr_multiplier", 1.5)

        # Calculate IQR by account
        stats = df.group_by("gl_account_number").agg([
            pl.col("amount").abs().quantile(0.25).alias("q1"),
            pl.col("amount").abs().quantile(0.75).alias("q3"),
        ])
        stats = stats.with_columns([
            (pl.col("q3") - pl.col("q1")).alias("iqr"),
        ])

        df_with_stats = df.join(stats, on="gl_account_number", how="left")

        # Find outliers
        outliers = df_with_stats.filter(
            (pl.col("iqr").is_not_null()) &
            (pl.col("iqr") > 0) &
            (
                (pl.col("amount").abs() < pl.col("q1") - iqr_multiplier * pl.col("iqr")) |
                (pl.col("amount").abs() > pl.col("q3") + iqr_multiplier * pl.col("iqr"))
            )
        )

        for row in outliers.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"統計的外れ値: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "q1": row["q1"],
                    "q3": row["q3"],
                    "iqr": row["iqr"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class LargeAdjustingEntryRule(AuditRule):
    """AMT-007: Detect large adjusting/manual entries."""

    @property
    def rule_id(self) -> str:
        return "AMT-007"

    @property
    def rule_name(self) -> str:
        return "大額修正仕訳"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "大額の修正仕訳や手入力仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        threshold = self.get_threshold("adjusting_threshold", 50_000_000)
        adjustment_sources = self.get_threshold(
            "adjustment_sources",
            ["MANUAL", "ADJUST", "修正", "調整", "振替"]
        )

        # Filter adjusting entries
        adjusting = df.filter(
            (pl.col("amount").abs() >= threshold) &
            (
                pl.col("source").is_in(adjustment_sources) |
                pl.col("je_line_description").str.contains("(?i)修正|調整|振替")
            )
        )

        for row in adjusting.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額修正仕訳: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "source": row.get("source"),
                    "description": row.get("je_line_description"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SignificantReversalRule(AuditRule):
    """AMT-008: Detect significant reversal entries."""

    @property
    def rule_id(self) -> str:
        return "AMT-008"

    @property
    def rule_name(self) -> str:
        return "大額取消仕訳"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "大額の取消（逆仕訳）を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        threshold = self.get_threshold("reversal_threshold", 10_000_000)
        reversal_keywords = ["取消", "戻し", "逆仕訳", "REV", "REVERSE"]

        reversals = df.filter(
            (pl.col("amount").abs() >= threshold) &
            pl.col("je_line_description").str.contains("|".join(reversal_keywords))
        )

        for row in reversals.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額取消仕訳: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "description": row.get("je_line_description"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SplitTransactionRule(AuditRule):
    """AMT-009: Detect split transaction patterns."""

    @property
    def rule_id(self) -> str:
        return "AMT-009"

    @property
    def rule_name(self) -> str:
        return "分割取引検出"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "承認閾値を回避するための取引分割パターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        threshold = self.get_threshold("split_threshold", 10_000_000)
        window_days = self.get_threshold("window_days", 3)

        # Group by user, account, and similar dates
        grouped = df.group_by([
            "prepared_by",
            "gl_account_number",
            pl.col("effective_date").cast(pl.Date),
        ]).agg([
            pl.col("amount").sum().alias("total_amount"),
            pl.col("amount").count().alias("entry_count"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        # Find potential splits
        splits = grouped.filter(
            (pl.col("total_amount").abs() >= threshold) &
            (pl.col("entry_count") >= 3)  # Multiple entries
        )

        for row in splits.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["sample_journal"],
                message=f"分割取引疑い: {row['entry_count']}件で合計{row['total_amount']:,.0f}円",
                details={
                    "total_amount": row["total_amount"],
                    "entry_count": row["entry_count"],
                    "user": row["prepared_by"],
                    "account": row["gl_account_number"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class DebitCreditImbalanceRule(AuditRule):
    """AMT-010: Detect debit-credit imbalances in journal entries."""

    @property
    def rule_id(self) -> str:
        return "AMT-010"

    @property
    def rule_name(self) -> str:
        return "借貸不一致"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "仕訳の借方と貸方が一致しない取引を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.CRITICAL

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        tolerance = self.get_threshold("balance_tolerance", 0.01)  # 1銭

        # Calculate balance by journal
        balance = df.group_by("journal_id").agg([
            pl.when(pl.col("debit_credit_indicator") == "D")
            .then(pl.col("amount"))
            .otherwise(0)
            .sum()
            .alias("total_debit"),
            pl.when(pl.col("debit_credit_indicator") == "C")
            .then(pl.col("amount"))
            .otherwise(0)
            .sum()
            .alias("total_credit"),
            pl.col("gl_detail_id").first().alias("sample_id"),
        ])

        balance = balance.with_columns([
            (pl.col("total_debit") - pl.col("total_credit")).abs().alias("difference"),
        ])

        result.total_checked = len(balance)

        # Find imbalances
        imbalanced = balance.filter(pl.col("difference") > tolerance)

        for row in imbalanced.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["journal_id"],
                message=f"借貸不一致: 差額{row['difference']:,.2f}円",
                details={
                    "total_debit": row["total_debit"],
                    "total_credit": row["total_credit"],
                    "difference": row["difference"],
                },
                score_impact=30.0,  # Critical
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ForeignCurrencyAnomalyRule(AuditRule):
    """AMT-011: Detect foreign currency amount anomalies."""

    @property
    def rule_id(self) -> str:
        return "AMT-011"

    @property
    def rule_name(self) -> str:
        return "外貨金額異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "外貨取引における換算レート異常を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Filter foreign currency entries
        fx_entries = df.filter(
            (pl.col("amount_currency").is_not_null()) &
            (pl.col("amount_currency") != "JPY") &
            (pl.col("functional_amount").is_not_null())
        )

        result.total_checked = len(fx_entries)

        if len(fx_entries) == 0:
            return result

        # Calculate implied rate
        fx_with_rate = fx_entries.with_columns([
            (pl.col("functional_amount") / pl.col("amount")).alias("implied_rate"),
        ])

        # Get statistics by currency
        stats = fx_with_rate.group_by("amount_currency").agg([
            pl.col("implied_rate").mean().alias("avg_rate"),
            pl.col("implied_rate").std().alias("std_rate"),
        ])

        fx_with_stats = fx_with_rate.join(stats, on="amount_currency", how="left")

        # Find rate anomalies (beyond 2 std)
        anomalies = fx_with_stats.filter(
            (pl.col("std_rate").is_not_null()) &
            (pl.col("std_rate") > 0) &
            (((pl.col("implied_rate") - pl.col("avg_rate")).abs() / pl.col("std_rate")) > 2)
        )

        for row in anomalies.iter_rows(named=True):
            deviation = (row["implied_rate"] - row["avg_rate"]) / row["std_rate"]
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"外貨レート異常: {row['amount_currency']} rate={row['implied_rate']:.4f}",
                details={
                    "currency": row["amount_currency"],
                    "amount": row["amount"],
                    "functional_amount": row["functional_amount"],
                    "implied_rate": row["implied_rate"],
                    "avg_rate": row["avg_rate"],
                    "deviation": deviation,
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class TaxIrregularityRule(AuditRule):
    """AMT-012: Detect tax amount irregularities."""

    @property
    def rule_id(self) -> str:
        return "AMT-012"

    @property
    def rule_name(self) -> str:
        return "消費税計算異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "消費税額が期待値と異なる取引を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Tax account patterns
        tax_accounts = self.get_threshold(
            "tax_accounts",
            ["255", "516", "717"]  # 仮払消費税、仮受消費税など
        )
        tax_rate = self.get_threshold("tax_rate", 0.10)  # 10%
        tolerance = self.get_threshold("tax_tolerance", 1.0)  # 1円

        # This is a simplified check - in practice would need linked transactions
        tax_entries = df.filter(
            pl.col("gl_account_number").str.starts_with(tuple(tax_accounts))
        )

        result.total_checked = len(tax_entries)

        # Check for odd tax amounts (not divisible by common factors)
        for row in tax_entries.iter_rows(named=True):
            amount = abs(row["amount"])
            # Check if amount looks like a calculated tax
            # Tax amount should be roughly divisible by tax rate fraction
            expected_base = amount / tax_rate
            if expected_base % 1 > 0.1 and expected_base % 1 < 0.9:
                # Amount doesn't look like standard tax calculation
                if amount >= 10000:  # Only flag significant amounts
                    violation = self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=f"消費税計算異常: {row['amount']:,.0f}円",
                        details={
                            "amount": row["amount"],
                            "implied_base": expected_base,
                        },
                    )
                    result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ExpenseRatioRule(AuditRule):
    """AMT-013: Detect unusual expense ratios."""

    @property
    def rule_id(self) -> str:
        return "AMT-013"

    @property
    def rule_name(self) -> str:
        return "経費比率異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "経費科目の金額比率が通常と異なるパターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        expense_prefix = self.get_threshold("expense_prefix", "7")  # 7xx = 販管費

        expenses = df.filter(
            pl.col("gl_account_number").str.starts_with(expense_prefix)
        )

        result.total_checked = len(expenses)

        # Calculate by account and period
        by_period = expenses.group_by([
            "gl_account_number",
            "accounting_period",
        ]).agg([
            pl.col("amount").sum().alias("period_total"),
        ])

        # Calculate average by account
        avg_by_account = by_period.group_by("gl_account_number").agg([
            pl.col("period_total").mean().alias("avg_total"),
            pl.col("period_total").std().alias("std_total"),
        ])

        by_period = by_period.join(avg_by_account, on="gl_account_number", how="left")

        # Find periods with unusual expense
        anomalies = by_period.filter(
            (pl.col("std_total").is_not_null()) &
            (pl.col("std_total") > 0) &
            (((pl.col("period_total") - pl.col("avg_total")).abs() / pl.col("std_total")) > 2)
        )

        for row in anomalies.iter_rows(named=True):
            deviation = (row["period_total"] - row["avg_total"]) / row["std_total"]
            # Find sample entries for this account/period
            sample = expenses.filter(
                (pl.col("gl_account_number") == row["gl_account_number"]) &
                (pl.col("accounting_period") == row["accounting_period"])
            ).head(1)

            if len(sample) > 0:
                sample_row = sample.row(0, named=True)
                violation = self._create_violation(
                    gl_detail_id=sample_row["gl_detail_id"],
                    journal_id=sample_row["journal_id"],
                    message=f"経費比率異常: {row['gl_account_number']} 期間{row['accounting_period']}",
                    details={
                        "account": row["gl_account_number"],
                        "period": row["accounting_period"],
                        "period_total": row["period_total"],
                        "avg_total": row["avg_total"],
                        "deviation": deviation,
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class RevenueRecognitionRule(AuditRule):
    """AMT-014: Detect unusual revenue recognition patterns."""

    @property
    def rule_id(self) -> str:
        return "AMT-014"

    @property
    def rule_name(self) -> str:
        return "収益認識異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "収益認識タイミングの異常（期末集中など）を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        revenue_prefix = self.get_threshold("revenue_prefix", "5")  # 5xx = 売上

        revenue = df.filter(
            pl.col("gl_account_number").str.starts_with(revenue_prefix)
        )

        result.total_checked = len(revenue)

        # Calculate revenue by period
        by_period = revenue.group_by("accounting_period").agg([
            pl.col("amount").sum().alias("period_total"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        total_revenue = by_period["period_total"].sum()
        if total_revenue == 0:
            return result

        # Calculate concentration in specific periods
        by_period = by_period.with_columns([
            (pl.col("period_total") / total_revenue * 100).alias("pct"),
        ])

        # Flag periods with >25% of annual revenue (unusual concentration)
        concentration_threshold = self.get_threshold("concentration_threshold", 25.0)
        concentrated = by_period.filter(pl.col("pct") > concentration_threshold)

        for row in concentrated.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["sample_journal"],
                message=f"収益集中: 期間{row['accounting_period']}に{row['pct']:.1f}%集中",
                details={
                    "period": row["accounting_period"],
                    "period_total": row["period_total"],
                    "percentage": row["pct"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class UnusualWriteOffRule(AuditRule):
    """AMT-015: Detect unusual write-offs and allowances."""

    @property
    def rule_id(self) -> str:
        return "AMT-015"

    @property
    def rule_name(self) -> str:
        return "異常償却・引当"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.AMOUNT

    @property
    def description(self) -> str:
        return "貸倒償却や引当金計上の異常を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        writeoff_keywords = ["償却", "貸倒", "引当", "損失", "減損"]
        threshold = self.get_threshold("writeoff_threshold", 10_000_000)

        writeoffs = df.filter(
            (pl.col("amount").abs() >= threshold) &
            pl.col("je_line_description").str.contains("|".join(writeoff_keywords))
        )

        result.total_checked = len(writeoffs)

        for row in writeoffs.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"大額償却/引当: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "description": row.get("je_line_description"),
                    "account": row.get("gl_account_number"),
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


def create_amount_rule_set() -> RuleSet:
    """Create the complete amount rule set.

    Returns:
        RuleSet with all 15 amount rules.
    """
    rule_set = RuleSet(
        name="amount_rules",
        description="金額に関する監査ルール (15件)",
    )

    rules = [
        HighValueTransactionRule(),
        RoundAmountRule(),
        JustBelowThresholdRule(),
        SuspiciousPatternRule(),
        AmountDistributionRule(),
        StatisticalOutlierRule(),
        LargeAdjustingEntryRule(),
        SignificantReversalRule(),
        SplitTransactionRule(),
        DebitCreditImbalanceRule(),
        ForeignCurrencyAnomalyRule(),
        TaxIrregularityRule(),
        ExpenseRatioRule(),
        RevenueRecognitionRule(),
        UnusualWriteOffRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
