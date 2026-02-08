"""Time-based audit rules.

10 rules for detecting temporal anomalies in journal entries:
- TIM-001: Weekend/holiday entries
- TIM-002: Late night entries
- TIM-003: Period-end concentration
- TIM-004: Backdated entries
- TIM-005: Future-dated entries
- TIM-006: Entry/effective date gap
- TIM-007: Unusual posting patterns
- TIM-008: Fiscal year boundary
- TIM-009: Approval timing anomaly
- TIM-010: Quarterly pattern anomaly
"""

from datetime import datetime, time, timedelta
from typing import Any

import polars as pl

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSeverity,
    RuleSet,
)


class WeekendHolidayRule(AuditRule):
    """TIM-001: Detect entries posted on weekends or holidays."""

    @property
    def rule_id(self) -> str:
        return "TIM-001"

    @property
    def rule_name(self) -> str:
        return "休日入力"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "週末や祝日に入力された仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # Japanese holidays (simplified - should use a proper calendar)
        holiday_threshold = self.get_threshold("high_amount_weekend", 10_000_000)

        # Filter weekend entries (Saturday=6, Sunday=7)
        weekend = df.filter(
            pl.col("entry_date").dt.weekday().is_in([5, 6])  # 0=Mon, 5=Sat, 6=Sun
        )

        # Only flag high-value weekend entries
        high_value_weekend = weekend.filter(
            pl.col("amount").abs() >= holiday_threshold
        )

        for row in high_value_weekend.iter_rows(named=True):
            entry_date = row.get("entry_date")
            weekday_name = ["月", "火", "水", "木", "金", "土", "日"][entry_date.weekday()] if entry_date else "?"

            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"休日入力 ({weekday_name}曜): {row['amount']:,.0f}円",
                details={
                    "entry_date": str(entry_date),
                    "weekday": weekday_name,
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class LateNightEntryRule(AuditRule):
    """TIM-002: Detect entries made during unusual hours."""

    @property
    def rule_id(self) -> str:
        return "TIM-002"

    @property
    def rule_name(self) -> str:
        return "深夜入力"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "通常業務時間外（深夜・早朝）に入力された仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Only check entries with time information
        with_time = df.filter(pl.col("entry_time").is_not_null())
        result.total_checked = len(with_time)

        if len(with_time) == 0:
            return result

        start_hour = self.get_threshold("business_start", 7)  # 7:00
        end_hour = self.get_threshold("business_end", 22)     # 22:00
        min_amount = self.get_threshold("late_night_min", 1_000_000)

        # Filter late night entries
        late_night = with_time.filter(
            (
                (pl.col("entry_time").dt.hour() < start_hour) |
                (pl.col("entry_time").dt.hour() >= end_hour)
            ) &
            (pl.col("amount").abs() >= min_amount)
        )

        for row in late_night.iter_rows(named=True):
            entry_time = row.get("entry_time")
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"深夜入力 ({entry_time.strftime('%H:%M') if entry_time else '?'}): {row['amount']:,.0f}円",
                details={
                    "entry_time": str(entry_time),
                    "hour": entry_time.hour if entry_time else None,
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class PeriodEndConcentrationRule(AuditRule):
    """TIM-003: Detect unusual concentration of entries at period end."""

    @property
    def rule_id(self) -> str:
        return "TIM-003"

    @property
    def rule_name(self) -> str:
        return "期末集中"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "月末・期末に集中する高額仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        last_days = self.get_threshold("period_end_days", 3)
        min_amount = self.get_threshold("period_end_min_amount", 50_000_000)

        # Identify period-end entries (last N days of month)
        period_end = df.filter(
            (pl.col("effective_date").dt.day() >= 28) |
            (
                (pl.col("effective_date").dt.day() <= 3) &
                (pl.col("effective_date").dt.month() != pl.col("effective_date").dt.month().shift(1))
            )
        )

        # High-value period-end entries
        high_value = period_end.filter(pl.col("amount").abs() >= min_amount)

        for row in high_value.iter_rows(named=True):
            eff_date = row.get("effective_date")
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"期末集中: {eff_date.day if eff_date else '?'}日, {row['amount']:,.0f}円",
                details={
                    "effective_date": str(eff_date),
                    "day_of_month": eff_date.day if eff_date else None,
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class BackdatedEntryRule(AuditRule):
    """TIM-004: Detect backdated entries."""

    @property
    def rule_id(self) -> str:
        return "TIM-004"

    @property
    def rule_name(self) -> str:
        return "遡及入力"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "効力発生日より大幅に遅れて入力された仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Need both dates
        with_dates = df.filter(
            pl.col("entry_date").is_not_null() &
            pl.col("effective_date").is_not_null()
        )
        result.total_checked = len(with_dates)

        max_delay_days = self.get_threshold("max_delay_days", 30)
        min_amount = self.get_threshold("backdate_min_amount", 10_000_000)

        # Calculate delay
        with_delay = with_dates.with_columns([
            (pl.col("entry_date") - pl.col("effective_date")).dt.total_days().alias("delay_days")
        ])

        # Find backdated entries
        backdated = with_delay.filter(
            (pl.col("delay_days") > max_delay_days) &
            (pl.col("amount").abs() >= min_amount)
        )

        for row in backdated.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"遡及入力: {row['delay_days']:.0f}日遅延, {row['amount']:,.0f}円",
                details={
                    "entry_date": str(row.get("entry_date")),
                    "effective_date": str(row.get("effective_date")),
                    "delay_days": row["delay_days"],
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class FutureDatedEntryRule(AuditRule):
    """TIM-005: Detect future-dated entries."""

    @property
    def rule_id(self) -> str:
        return "TIM-005"

    @property
    def rule_name(self) -> str:
        return "将来日付"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "入力日より将来の効力発生日を持つ仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_dates = df.filter(
            pl.col("entry_date").is_not_null() &
            pl.col("effective_date").is_not_null()
        )
        result.total_checked = len(with_dates)

        max_future_days = self.get_threshold("max_future_days", 7)

        # Calculate future offset
        with_offset = with_dates.with_columns([
            (pl.col("effective_date") - pl.col("entry_date")).dt.total_days().alias("future_days")
        ])

        # Find future-dated entries
        future_dated = with_offset.filter(pl.col("future_days") > max_future_days)

        for row in future_dated.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"将来日付: 入力日の{row['future_days']:.0f}日後",
                details={
                    "entry_date": str(row.get("entry_date")),
                    "effective_date": str(row.get("effective_date")),
                    "future_days": row["future_days"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class DateGapRule(AuditRule):
    """TIM-006: Detect unusual gaps between entry and effective dates."""

    @property
    def rule_id(self) -> str:
        return "TIM-006"

    @property
    def rule_name(self) -> str:
        return "日付乖離"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "入力日と効力発生日の間に大きな乖離がある仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_dates = df.filter(
            pl.col("entry_date").is_not_null() &
            pl.col("effective_date").is_not_null()
        )
        result.total_checked = len(with_dates)

        max_gap_days = self.get_threshold("max_gap_days", 90)
        min_amount = self.get_threshold("gap_min_amount", 5_000_000)

        # Calculate absolute gap
        with_gap = with_dates.with_columns([
            (pl.col("entry_date") - pl.col("effective_date")).dt.total_days().abs().alias("gap_days")
        ])

        # Find large gaps
        large_gaps = with_gap.filter(
            (pl.col("gap_days") > max_gap_days) &
            (pl.col("amount").abs() >= min_amount)
        )

        for row in large_gaps.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"日付乖離: {row['gap_days']:.0f}日, {row['amount']:,.0f}円",
                details={
                    "entry_date": str(row.get("entry_date")),
                    "effective_date": str(row.get("effective_date")),
                    "gap_days": row["gap_days"],
                    "amount": row["amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class UnusualPostingPatternRule(AuditRule):
    """TIM-007: Detect unusual posting patterns by user."""

    @property
    def rule_id(self) -> str:
        return "TIM-007"

    @property
    def rule_name(self) -> str:
        return "異常入力パターン"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "特定ユーザーの異常な入力パターン（大量入力など）を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_user = df.filter(pl.col("prepared_by").is_not_null())
        result.total_checked = len(with_user)

        # Count entries per user per day
        daily_count = with_user.group_by([
            "prepared_by",
            pl.col("entry_date").cast(pl.Date),
        ]).agg([
            pl.count().alias("entry_count"),
            pl.col("amount").sum().alias("total_amount"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        # Calculate statistics per user
        user_stats = daily_count.group_by("prepared_by").agg([
            pl.col("entry_count").mean().alias("avg_count"),
            pl.col("entry_count").std().alias("std_count"),
        ])

        daily_with_stats = daily_count.join(user_stats, on="prepared_by", how="left")

        # Find unusual days
        unusual = daily_with_stats.filter(
            (pl.col("std_count").is_not_null()) &
            (pl.col("std_count") > 0) &
            ((pl.col("entry_count") - pl.col("avg_count")) / pl.col("std_count") > 3)
        )

        for row in unusual.iter_rows(named=True):
            z_score = (row["entry_count"] - row["avg_count"]) / row["std_count"]
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["sample_journal"],
                message=f"異常入力パターン: {row['prepared_by']}が{row['entry_count']}件入力",
                details={
                    "user": row["prepared_by"],
                    "entry_date": str(row["entry_date"]),
                    "entry_count": row["entry_count"],
                    "avg_count": row["avg_count"],
                    "z_score": z_score,
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class FiscalYearBoundaryRule(AuditRule):
    """TIM-008: Detect entries near fiscal year boundaries."""

    @property
    def rule_id(self) -> str:
        return "TIM-008"

    @property
    def rule_name(self) -> str:
        return "期末境界"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "会計年度末・年度初めに入力された高額仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # Japanese fiscal year end (March) and start (April)
        fy_end_month = self.get_threshold("fy_end_month", 3)
        boundary_days = self.get_threshold("boundary_days", 5)
        min_amount = self.get_threshold("boundary_min_amount", 100_000_000)

        # Filter fiscal year boundary entries
        boundary = df.filter(
            (
                (pl.col("effective_date").dt.month() == fy_end_month) &
                (pl.col("effective_date").dt.day() >= 28)
            ) |
            (
                (pl.col("effective_date").dt.month() == fy_end_month + 1) &
                (pl.col("effective_date").dt.day() <= boundary_days)
            )
        )

        high_value = boundary.filter(pl.col("amount").abs() >= min_amount)

        for row in high_value.iter_rows(named=True):
            eff_date = row.get("effective_date")
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"期末境界: {eff_date.month}/{eff_date.day if eff_date else '?'}, {row['amount']:,.0f}円",
                details={
                    "effective_date": str(eff_date),
                    "amount": row["amount"],
                    "is_year_end": eff_date.month == fy_end_month if eff_date else False,
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ApprovalTimingRule(AuditRule):
    """TIM-009: Detect unusual approval timing patterns."""

    @property
    def rule_id(self) -> str:
        return "TIM-009"

    @property
    def rule_name(self) -> str:
        return "承認タイミング異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "入力から承認までの時間が異常に短い/長い仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_approval = df.filter(
            pl.col("entry_date").is_not_null() &
            pl.col("approved_date").is_not_null()
        )
        result.total_checked = len(with_approval)

        min_hours = self.get_threshold("min_approval_hours", 1)  # Too fast
        max_days = self.get_threshold("max_approval_days", 30)   # Too slow
        min_amount = self.get_threshold("approval_min_amount", 10_000_000)

        # Calculate approval delay
        with_delay = with_approval.with_columns([
            (pl.col("approved_date") - pl.col("entry_date")).dt.total_hours().alias("approval_hours")
        ])

        # Too fast approvals (high value, approved in less than 1 hour)
        too_fast = with_delay.filter(
            (pl.col("approval_hours") < min_hours) &
            (pl.col("amount").abs() >= min_amount)
        )

        for row in too_fast.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"即時承認: {row['approval_hours']:.1f}時間, {row['amount']:,.0f}円",
                details={
                    "entry_date": str(row.get("entry_date")),
                    "approved_date": str(row.get("approved_date")),
                    "approval_hours": row["approval_hours"],
                    "amount": row["amount"],
                },
                score_impact=15.0,
            )
            result.violations.append(violation)

        # Too slow approvals
        too_slow = with_delay.filter(
            pl.col("approval_hours") > max_days * 24
        )

        for row in too_slow.iter_rows(named=True):
            days = row["approval_hours"] / 24
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"遅延承認: {days:.1f}日後",
                details={
                    "entry_date": str(row.get("entry_date")),
                    "approved_date": str(row.get("approved_date")),
                    "approval_days": days,
                },
                score_impact=5.0,
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class QuarterlyPatternRule(AuditRule):
    """TIM-010: Detect unusual quarterly patterns."""

    @property
    def rule_id(self) -> str:
        return "TIM-010"

    @property
    def rule_name(self) -> str:
        return "四半期パターン異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TIME

    @property
    def description(self) -> str:
        return "四半期ごとの取引パターンの異常を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # Assign quarter (Japanese FY: Q1=Apr-Jun, Q2=Jul-Sep, Q3=Oct-Dec, Q4=Jan-Mar)
        with_quarter = df.with_columns([
            pl.when(pl.col("effective_date").dt.month().is_in([4, 5, 6]))
            .then(pl.lit(1))
            .when(pl.col("effective_date").dt.month().is_in([7, 8, 9]))
            .then(pl.lit(2))
            .when(pl.col("effective_date").dt.month().is_in([10, 11, 12]))
            .then(pl.lit(3))
            .otherwise(pl.lit(4))
            .alias("quarter")
        ])

        # Calculate quarterly totals by account
        quarterly = with_quarter.group_by([
            "gl_account_number",
            "fiscal_year",
            "quarter",
        ]).agg([
            pl.col("amount").sum().alias("quarter_total"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        # Calculate average and std per account
        stats = quarterly.group_by("gl_account_number").agg([
            pl.col("quarter_total").mean().alias("avg_total"),
            pl.col("quarter_total").std().alias("std_total"),
        ])

        quarterly_with_stats = quarterly.join(stats, on="gl_account_number", how="left")

        # Find unusual quarters
        unusual = quarterly_with_stats.filter(
            (pl.col("std_total").is_not_null()) &
            (pl.col("std_total") > 0) &
            (((pl.col("quarter_total") - pl.col("avg_total")).abs() / pl.col("std_total")) > 2)
        )

        for row in unusual.iter_rows(named=True):
            z_score = abs(row["quarter_total"] - row["avg_total"]) / row["std_total"]
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["sample_journal"],
                message=f"四半期異常: Q{row['quarter']}, {row['quarter_total']:,.0f}円 (Z={z_score:.2f})",
                details={
                    "account": row["gl_account_number"],
                    "fiscal_year": row["fiscal_year"],
                    "quarter": row["quarter"],
                    "quarter_total": row["quarter_total"],
                    "avg_total": row["avg_total"],
                    "z_score": z_score,
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


def create_time_rule_set() -> RuleSet:
    """Create the complete time rule set.

    Returns:
        RuleSet with all 10 time rules.
    """
    rule_set = RuleSet(
        name="time_rules",
        description="時間に関する監査ルール (10件)",
    )

    rules = [
        WeekendHolidayRule(),
        LateNightEntryRule(),
        PeriodEndConcentrationRule(),
        BackdatedEntryRule(),
        FutureDatedEntryRule(),
        DateGapRule(),
        UnusualPostingPatternRule(),
        FiscalYearBoundaryRule(),
        ApprovalTimingRule(),
        QuarterlyPatternRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
