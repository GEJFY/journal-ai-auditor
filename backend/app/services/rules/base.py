"""Base classes for audit rules.

Provides abstract base class and common utilities for all audit rules.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import StrEnum
from typing import Any

import polars as pl


class RuleSeverity(StrEnum):
    """Severity level of rule violations."""

    CRITICAL = "critical"  # 重大: 不正の強い疑い
    HIGH = "high"  # 高: 要調査
    MEDIUM = "medium"  # 中: 要確認
    LOW = "low"  # 低: 注意
    INFO = "info"  # 情報: 参考


class RuleCategory(StrEnum):
    """Category of audit rules."""

    AMOUNT = "amount"  # 金額ルール
    TIME = "time"  # 時間ルール
    ACCOUNT = "account"  # 勘定ルール
    APPROVAL = "approval"  # 承認ルール
    DESCRIPTION = "description"  # 摘要ルール
    PATTERN = "pattern"  # パターンルール
    TREND = "trend"  # トレンドルール
    ML = "ml"  # 機械学習ルール


@dataclass
class RuleViolation:
    """Single rule violation record."""

    rule_id: str
    rule_name: str
    category: RuleCategory
    severity: RuleSeverity
    gl_detail_id: str
    journal_id: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)
    score_impact: float = 0.0
    detected_at: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category.value,
            "severity": self.severity.value,
            "gl_detail_id": self.gl_detail_id,
            "journal_id": self.journal_id,
            "message": self.message,
            "details": self.details,
            "score_impact": self.score_impact,
            "detected_at": self.detected_at.isoformat(),
        }


@dataclass
class RuleResult:
    """Result of rule execution."""

    rule_id: str
    rule_name: str
    category: RuleCategory
    executed_at: datetime = field(default_factory=datetime.now)
    total_checked: int = 0
    violations_found: int = 0
    violations: list[RuleViolation] = field(default_factory=list)
    execution_time_ms: float = 0.0
    error: str | None = None

    @property
    def success(self) -> bool:
        """Check if rule executed successfully."""
        return self.error is None

    @property
    def violation_rate(self) -> float:
        """Calculate violation rate as percentage."""
        if self.total_checked == 0:
            return 0.0
        return (self.violations_found / self.total_checked) * 100

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "rule_id": self.rule_id,
            "rule_name": self.rule_name,
            "category": self.category.value,
            "executed_at": self.executed_at.isoformat(),
            "total_checked": self.total_checked,
            "violations_found": self.violations_found,
            "violation_rate": round(self.violation_rate, 2),
            "execution_time_ms": round(self.execution_time_ms, 2),
            "success": self.success,
            "error": self.error,
        }


class AuditRule(ABC):
    """Abstract base class for all audit rules.

    Each rule must implement:
    - rule_id: Unique identifier (e.g., "AMT-001")
    - rule_name: Human-readable name
    - category: Rule category
    - description: Detailed description
    - severity: Default severity level
    - execute(): Main execution logic
    """

    def __init__(
        self,
        enabled: bool = True,
        severity_override: RuleSeverity | None = None,
        threshold_overrides: dict[str, Any] | None = None,
    ) -> None:
        """Initialize rule.

        Args:
            enabled: Whether rule is enabled.
            severity_override: Override default severity.
            threshold_overrides: Override default thresholds.
        """
        self.enabled = enabled
        self._severity_override = severity_override
        self._threshold_overrides = threshold_overrides or {}

    @property
    @abstractmethod
    def rule_id(self) -> str:
        """Unique rule identifier."""
        pass

    @property
    @abstractmethod
    def rule_name(self) -> str:
        """Human-readable rule name."""
        pass

    @property
    @abstractmethod
    def category(self) -> RuleCategory:
        """Rule category."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Rule description."""
        pass

    @property
    @abstractmethod
    def default_severity(self) -> RuleSeverity:
        """Default severity level."""
        pass

    @property
    def severity(self) -> RuleSeverity:
        """Current severity level (with override support)."""
        return self._severity_override or self.default_severity

    def get_threshold(self, name: str, default: Any) -> Any:
        """Get threshold value with override support.

        Args:
            name: Threshold name.
            default: Default value.

        Returns:
            Threshold value (override if set, otherwise default).
        """
        return self._threshold_overrides.get(name, default)

    @abstractmethod
    def execute(self, df: pl.DataFrame) -> RuleResult:
        """Execute the rule against journal entries.

        Args:
            df: Polars DataFrame with journal entries.

        Returns:
            RuleResult with violations found.
        """
        pass

    def _create_result(self) -> RuleResult:
        """Create a new result object for this rule."""
        return RuleResult(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
        )

    def _create_violation(
        self,
        gl_detail_id: str,
        journal_id: str,
        message: str,
        details: dict[str, Any] | None = None,
        score_impact: float | None = None,
    ) -> RuleViolation:
        """Create a violation record.

        Args:
            gl_detail_id: GL detail ID of the violating entry.
            journal_id: Journal ID of the violating entry.
            message: Violation message.
            details: Additional details.
            score_impact: Risk score impact (auto-calculated if not provided).

        Returns:
            RuleViolation instance.
        """
        # Auto-calculate score impact based on severity
        if score_impact is None:
            score_impact = {
                RuleSeverity.CRITICAL: 25.0,
                RuleSeverity.HIGH: 15.0,
                RuleSeverity.MEDIUM: 10.0,
                RuleSeverity.LOW: 5.0,
                RuleSeverity.INFO: 0.0,
            }.get(self.severity, 5.0)

        return RuleViolation(
            rule_id=self.rule_id,
            rule_name=self.rule_name,
            category=self.category,
            severity=self.severity,
            gl_detail_id=gl_detail_id,
            journal_id=journal_id,
            message=message,
            details=details or {},
            score_impact=score_impact,
        )

    def __repr__(self) -> str:
        return f"{self.__class__.__name__}(id={self.rule_id}, enabled={self.enabled})"


class RuleSet:
    """Collection of related rules."""

    def __init__(self, name: str, description: str = "") -> None:
        """Initialize rule set.

        Args:
            name: Rule set name.
            description: Rule set description.
        """
        self.name = name
        self.description = description
        self._rules: dict[str, AuditRule] = {}

    def add_rule(self, rule: AuditRule) -> None:
        """Add a rule to the set.

        Args:
            rule: Rule to add.
        """
        self._rules[rule.rule_id] = rule

    def get_rule(self, rule_id: str) -> AuditRule | None:
        """Get a rule by ID.

        Args:
            rule_id: Rule identifier.

        Returns:
            Rule if found, None otherwise.
        """
        return self._rules.get(rule_id)

    def get_enabled_rules(self) -> list[AuditRule]:
        """Get all enabled rules."""
        return [r for r in self._rules.values() if r.enabled]

    def get_rules_by_category(self, category: RuleCategory) -> list[AuditRule]:
        """Get rules by category.

        Args:
            category: Rule category.

        Returns:
            List of rules in the category.
        """
        return [r for r in self._rules.values() if r.category == category]

    @property
    def rules(self) -> list[AuditRule]:
        """Get all rules."""
        return list(self._rules.values())

    def __len__(self) -> int:
        return len(self._rules)

    def __iter__(self):
        return iter(self._rules.values())
