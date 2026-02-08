"""Approval-based audit rules.

8 rules for detecting approval control issues:
- APR-001: Self-approval detection
- APR-002: Missing approval
- APR-003: Approval hierarchy violation
- APR-004: Bulk approval pattern
- APR-005: Same user entries
- APR-006: Approval authority exceeded
- APR-007: Sequential approval bypass
- APR-008: Unauthorized approver
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


class SelfApprovalRule(AuditRule):
    """APR-001: Detect self-approved entries."""

    @property
    def rule_id(self) -> str:
        return "APR-001"

    @property
    def rule_name(self) -> str:
        return "自己承認"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "作成者と承認者が同一人物の仕訳を検出します。職務分離違反の可能性があります。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.CRITICAL

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Filter entries with both preparer and approver
        with_approval = df.filter(
            pl.col("prepared_by").is_not_null() &
            pl.col("approved_by").is_not_null()
        )
        result.total_checked = len(with_approval)

        min_amount = self.get_threshold("self_approval_min", 100_000)

        # Find self-approvals
        self_approved = with_approval.filter(
            (pl.col("prepared_by") == pl.col("approved_by")) &
            (pl.col("amount").abs() >= min_amount)
        )

        for row in self_approved.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"自己承認: {row['prepared_by']}, {row['amount']:,.0f}円",
                details={
                    "user": row["prepared_by"],
                    "amount": row["amount"],
                    "account": row.get("gl_account_number"),
                },
                score_impact=25.0,  # Critical
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class MissingApprovalRule(AuditRule):
    """APR-002: Detect entries missing required approval."""

    @property
    def rule_id(self) -> str:
        return "APR-002"

    @property
    def rule_name(self) -> str:
        return "未承認"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "承認が必要な金額であるにもかかわらず、承認者が記録されていない仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        approval_threshold = self.get_threshold("approval_threshold", 1_000_000)

        # High-value entries without approval
        missing = df.filter(
            (pl.col("amount").abs() >= approval_threshold) &
            (pl.col("approved_by").is_null())
        )

        for row in missing.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["gl_detail_id"],
                journal_id=row["journal_id"],
                message=f"承認なし: {row['amount']:,.0f}円",
                details={
                    "amount": row["amount"],
                    "prepared_by": row.get("prepared_by"),
                    "threshold": approval_threshold,
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ApprovalHierarchyRule(AuditRule):
    """APR-003: Detect approval hierarchy violations."""

    @property
    def rule_id(self) -> str:
        return "APR-003"

    @property
    def rule_name(self) -> str:
        return "承認階層違反"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "金額に応じた適切な承認階層を満たしていない仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # Define approval tiers (would be configured per company)
        tiers = self.get_threshold("approval_tiers", [
            {"min": 0, "max": 1_000_000, "level": "staff"},
            {"min": 1_000_000, "max": 10_000_000, "level": "manager"},
            {"min": 10_000_000, "max": 50_000_000, "level": "director"},
            {"min": 50_000_000, "max": float("inf"), "level": "executive"},
        ])

        # Define approver levels (would come from user master)
        # Simplified: check based on approver ID patterns
        executive_prefixes = self.get_threshold("executive_prefixes", ["E", "D", "M"])

        with_approval = df.filter(pl.col("approved_by").is_not_null())
        result.total_checked = len(with_approval)

        # Check high-value entries with low-level approvers
        high_value = with_approval.filter(pl.col("amount").abs() >= 50_000_000)

        for row in high_value.iter_rows(named=True):
            approver = row.get("approved_by", "")
            # Simple check: executive approval should have specific prefix
            if not any(approver.startswith(p) for p in executive_prefixes):
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"承認階層不足: {row['amount']:,.0f}円を{approver}が承認",
                    details={
                        "amount": row["amount"],
                        "approver": approver,
                        "required_level": "executive",
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class BulkApprovalRule(AuditRule):
    """APR-004: Detect bulk approval patterns."""

    @property
    def rule_id(self) -> str:
        return "APR-004"

    @property
    def rule_name(self) -> str:
        return "一括承認"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "短時間に大量の仕訳を承認するパターンを検出します。形骸化した承認の疑いがあります。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_approval = df.filter(
            pl.col("approved_by").is_not_null() &
            pl.col("approved_date").is_not_null()
        )

        # Group by approver and approval date
        grouped = with_approval.group_by([
            "approved_by",
            pl.col("approved_date").cast(pl.Date),
        ]).agg([
            pl.count().alias("approval_count"),
            pl.col("amount").abs().sum().alias("total_amount"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        result.total_checked = len(grouped)

        # Flag bulk approvals
        bulk_threshold = self.get_threshold("bulk_threshold", 50)  # entries per day

        bulk = grouped.filter(pl.col("approval_count") >= bulk_threshold)

        for row in bulk.iter_rows(named=True):
            violation = self._create_violation(
                gl_detail_id=row["sample_id"],
                journal_id=row["sample_journal"],
                message=f"一括承認: {row['approved_by']}が{row['approval_count']}件承認",
                details={
                    "approver": row["approved_by"],
                    "date": str(row["approved_date"]),
                    "count": row["approval_count"],
                    "total_amount": row["total_amount"],
                },
            )
            result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SameUserEntriesRule(AuditRule):
    """APR-005: Detect high volume from single user."""

    @property
    def rule_id(self) -> str:
        return "APR-005"

    @property
    def rule_name(self) -> str:
        return "ユーザー集中"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "特定ユーザーによる異常に多い仕訳入力を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_user = df.filter(pl.col("prepared_by").is_not_null())

        # Calculate user statistics
        user_stats = with_user.group_by("prepared_by").agg([
            pl.count().alias("entry_count"),
            pl.col("amount").abs().sum().alias("total_amount"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        result.total_checked = len(user_stats)

        # Calculate average and find outliers
        avg_count = user_stats["entry_count"].mean()
        std_count = user_stats["entry_count"].std()

        if std_count and std_count > 0:
            threshold = avg_count + 3 * std_count
            concentration_threshold = self.get_threshold(
                "concentration_threshold",
                max(threshold, 1000)
            )

            outliers = user_stats.filter(
                pl.col("entry_count") >= concentration_threshold
            )

            for row in outliers.iter_rows(named=True):
                violation = self._create_violation(
                    gl_detail_id=row["sample_id"],
                    journal_id=row["sample_journal"],
                    message=f"ユーザー集中: {row['prepared_by']}が{row['entry_count']}件入力",
                    details={
                        "user": row["prepared_by"],
                        "entry_count": row["entry_count"],
                        "total_amount": row["total_amount"],
                        "average": avg_count,
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class ApprovalAuthorityRule(AuditRule):
    """APR-006: Detect approval authority exceeded."""

    @property
    def rule_id(self) -> str:
        return "APR-006"

    @property
    def rule_name(self) -> str:
        return "承認権限超過"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "承認者の権限を超える金額の仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_approval = df.filter(pl.col("approved_by").is_not_null())
        result.total_checked = len(with_approval)

        # Define authority limits by approver prefix (simplified)
        authority_limits = self.get_threshold("authority_limits", {
            "S": 1_000_000,      # Staff: 100万
            "M": 10_000_000,     # Manager: 1000万
            "D": 50_000_000,     # Director: 5000万
            "E": float("inf"),   # Executive: unlimited
        })

        for row in with_approval.iter_rows(named=True):
            approver = row.get("approved_by", "")
            amount = abs(row["amount"])

            # Get limit for approver
            limit = float("inf")
            for prefix, auth_limit in authority_limits.items():
                if approver.startswith(prefix):
                    limit = auth_limit
                    break

            if amount > limit:
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"承認権限超過: {row['amount']:,.0f}円 (限度: {limit:,.0f}円)",
                    details={
                        "approver": approver,
                        "amount": row["amount"],
                        "limit": limit,
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SequentialApprovalBypassRule(AuditRule):
    """APR-007: Detect sequential approval bypass."""

    @property
    def rule_id(self) -> str:
        return "APR-007"

    @property
    def rule_name(self) -> str:
        return "承認フロー迂回"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "必要な承認段階を飛ばしている仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        # For this rule, we would need a multi-level approval system
        # Simplified: check if high-value entries skip manager approval
        threshold = self.get_threshold("bypass_threshold", 10_000_000)

        with_approval = df.filter(
            pl.col("approved_by").is_not_null() &
            (pl.col("amount").abs() >= threshold)
        )
        result.total_checked = len(with_approval)

        # Check for entries approved by staff (should require manager)
        staff_prefixes = self.get_threshold("staff_prefixes", ["S", "U"])

        for row in with_approval.iter_rows(named=True):
            approver = row.get("approved_by", "")
            if any(approver.startswith(p) for p in staff_prefixes):
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"承認フロー迂回: {row['amount']:,.0f}円をスタッフが承認",
                    details={
                        "approver": approver,
                        "amount": row["amount"],
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class UnauthorizedApproverRule(AuditRule):
    """APR-008: Detect unauthorized approvers."""

    @property
    def rule_id(self) -> str:
        return "APR-008"

    @property
    def rule_name(self) -> str:
        return "未認可承認者"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.APPROVAL

    @property
    def description(self) -> str:
        return "承認権限を持たないユーザーによる承認を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.CRITICAL

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()

        with_approval = df.filter(pl.col("approved_by").is_not_null())
        result.total_checked = len(with_approval)

        # Define authorized approver patterns (would come from user master)
        authorized_patterns = self.get_threshold(
            "authorized_patterns",
            ["M", "D", "E", "A"]  # Manager, Director, Executive, Admin
        )

        for row in with_approval.iter_rows(named=True):
            approver = row.get("approved_by", "")
            if not any(approver.startswith(p) for p in authorized_patterns):
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"未認可承認者: {approver}",
                    details={
                        "approver": approver,
                        "amount": row["amount"],
                    },
                    score_impact=25.0,
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


def create_approval_rule_set() -> RuleSet:
    """Create the complete approval rule set.

    Returns:
        RuleSet with all 8 approval rules.
    """
    rule_set = RuleSet(
        name="approval_rules",
        description="承認に関する監査ルール (8件)",
    )

    rules = [
        SelfApprovalRule(),
        MissingApprovalRule(),
        ApprovalHierarchyRule(),
        BulkApprovalRule(),
        SameUserEntriesRule(),
        ApprovalAuthorityRule(),
        SequentialApprovalBypassRule(),
        UnauthorizedApproverRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
