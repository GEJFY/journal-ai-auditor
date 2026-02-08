"""Benford's Law analysis for fraud detection.

Benford's Law states that in many naturally occurring collections of numbers,
the leading digit is likely to be small. The probability of the first digit
being d is: P(d) = log10(1 + 1/d)

Expected frequencies:
- 1: 30.1%
- 2: 17.6%
- 3: 12.5%
- 4: 9.7%
- 5: 7.9%
- 6: 6.7%
- 7: 5.8%
- 8: 5.1%
- 9: 4.6%

This module provides:
- BEN-001: First digit analysis (Chi-square test)
- BEN-002: Second digit analysis
- BEN-003: First two digits analysis
- BEN-004: Summation analysis (per-digit deviation)
- BEN-005: Individual transaction flagging
"""

import math
from dataclasses import dataclass, field
from typing import Any, Optional

import numpy as np
import polars as pl
from scipy import stats

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSeverity,
    RuleSet,
    RuleViolation,
)


# Benford's Law expected frequencies
BENFORD_FIRST_DIGIT = {
    1: 0.301,
    2: 0.176,
    3: 0.125,
    4: 0.097,
    5: 0.079,
    6: 0.067,
    7: 0.058,
    8: 0.051,
    9: 0.046,
}

BENFORD_SECOND_DIGIT = {
    0: 0.120,
    1: 0.114,
    2: 0.109,
    3: 0.104,
    4: 0.100,
    5: 0.097,
    6: 0.093,
    7: 0.090,
    8: 0.088,
    9: 0.085,
}


def get_first_digit(amount: float) -> Optional[int]:
    """Extract the first significant digit from an amount.

    Args:
        amount: The amount value.

    Returns:
        First digit (1-9) or None if invalid.
    """
    if amount == 0:
        return None
    amount = abs(amount)
    # Get first digit by string manipulation (more reliable)
    amt_str = f"{amount:.0f}".lstrip("0")
    if not amt_str or not amt_str[0].isdigit():
        return None
    return int(amt_str[0])


def get_second_digit(amount: float) -> Optional[int]:
    """Extract the second significant digit from an amount.

    Args:
        amount: The amount value.

    Returns:
        Second digit (0-9) or None if invalid.
    """
    if amount == 0:
        return None
    amount = abs(amount)
    amt_str = f"{amount:.0f}".lstrip("0")
    if len(amt_str) < 2:
        return None
    return int(amt_str[1])


def get_first_two_digits(amount: float) -> Optional[int]:
    """Extract the first two significant digits from an amount.

    Args:
        amount: The amount value.

    Returns:
        First two digits (10-99) or None if invalid.
    """
    if amount == 0:
        return None
    amount = abs(amount)
    amt_str = f"{amount:.0f}".lstrip("0")
    if len(amt_str) < 2:
        return None
    return int(amt_str[:2])


@dataclass
class BenfordResult:
    """Result of Benford's Law analysis."""

    analysis_type: str  # "first_digit", "second_digit", "first_two"
    total_count: int = 0
    observed_freq: dict[int, float] = field(default_factory=dict)
    expected_freq: dict[int, float] = field(default_factory=dict)
    chi_square: float = 0.0
    p_value: float = 1.0
    mad: float = 0.0  # Mean Absolute Deviation
    conformity: str = "unknown"  # "close", "acceptable", "marginally acceptable", "nonconforming"
    digit_deviations: dict[int, float] = field(default_factory=dict)

    @property
    def is_suspicious(self) -> bool:
        """Check if the distribution is suspicious."""
        return self.conformity in ["marginally acceptable", "nonconforming"]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary."""
        return {
            "analysis_type": self.analysis_type,
            "total_count": self.total_count,
            "observed_freq": self.observed_freq,
            "expected_freq": self.expected_freq,
            "chi_square": self.chi_square,
            "p_value": self.p_value,
            "mad": self.mad,
            "conformity": self.conformity,
            "digit_deviations": self.digit_deviations,
        }


class BenfordAnalyzer:
    """Analyzer for Benford's Law conformity."""

    # MAD thresholds for conformity (Nigrini, 2012)
    MAD_THRESHOLDS_FIRST = {
        "close": 0.006,
        "acceptable": 0.012,
        "marginally_acceptable": 0.015,
    }

    MAD_THRESHOLDS_SECOND = {
        "close": 0.008,
        "acceptable": 0.010,
        "marginally_acceptable": 0.012,
    }

    def analyze_first_digit(
        self,
        amounts: list[float],
        min_samples: int = 100,
    ) -> BenfordResult:
        """Analyze first digit distribution.

        Args:
            amounts: List of amount values.
            min_samples: Minimum samples required.

        Returns:
            BenfordResult with analysis.
        """
        result = BenfordResult(analysis_type="first_digit")

        # Extract first digits
        digits = [get_first_digit(a) for a in amounts]
        digits = [d for d in digits if d is not None]

        result.total_count = len(digits)
        if result.total_count < min_samples:
            result.conformity = "insufficient_data"
            return result

        # Count observed frequencies
        counts = {d: 0 for d in range(1, 10)}
        for d in digits:
            counts[d] += 1

        result.observed_freq = {d: c / result.total_count for d, c in counts.items()}
        result.expected_freq = BENFORD_FIRST_DIGIT.copy()

        # Calculate deviations
        result.digit_deviations = {
            d: result.observed_freq[d] - BENFORD_FIRST_DIGIT[d]
            for d in range(1, 10)
        }

        # Calculate MAD
        result.mad = sum(abs(v) for v in result.digit_deviations.values()) / 9

        # Chi-square test
        observed = [counts[d] for d in range(1, 10)]
        expected = [BENFORD_FIRST_DIGIT[d] * result.total_count for d in range(1, 10)]
        chi2, p_value = stats.chisquare(observed, expected)

        result.chi_square = chi2
        result.p_value = p_value

        # Determine conformity based on MAD
        if result.mad <= self.MAD_THRESHOLDS_FIRST["close"]:
            result.conformity = "close"
        elif result.mad <= self.MAD_THRESHOLDS_FIRST["acceptable"]:
            result.conformity = "acceptable"
        elif result.mad <= self.MAD_THRESHOLDS_FIRST["marginally_acceptable"]:
            result.conformity = "marginally_acceptable"
        else:
            result.conformity = "nonconforming"

        return result

    def analyze_second_digit(
        self,
        amounts: list[float],
        min_samples: int = 100,
    ) -> BenfordResult:
        """Analyze second digit distribution.

        Args:
            amounts: List of amount values.
            min_samples: Minimum samples required.

        Returns:
            BenfordResult with analysis.
        """
        result = BenfordResult(analysis_type="second_digit")

        digits = [get_second_digit(a) for a in amounts]
        digits = [d for d in digits if d is not None]

        result.total_count = len(digits)
        if result.total_count < min_samples:
            result.conformity = "insufficient_data"
            return result

        counts = {d: 0 for d in range(0, 10)}
        for d in digits:
            counts[d] += 1

        result.observed_freq = {d: c / result.total_count for d, c in counts.items()}
        result.expected_freq = BENFORD_SECOND_DIGIT.copy()

        result.digit_deviations = {
            d: result.observed_freq[d] - BENFORD_SECOND_DIGIT[d]
            for d in range(0, 10)
        }

        result.mad = sum(abs(v) for v in result.digit_deviations.values()) / 10

        observed = [counts[d] for d in range(0, 10)]
        expected = [BENFORD_SECOND_DIGIT[d] * result.total_count for d in range(0, 10)]
        chi2, p_value = stats.chisquare(observed, expected)

        result.chi_square = chi2
        result.p_value = p_value

        if result.mad <= self.MAD_THRESHOLDS_SECOND["close"]:
            result.conformity = "close"
        elif result.mad <= self.MAD_THRESHOLDS_SECOND["acceptable"]:
            result.conformity = "acceptable"
        elif result.mad <= self.MAD_THRESHOLDS_SECOND["marginally_acceptable"]:
            result.conformity = "marginally_acceptable"
        else:
            result.conformity = "nonconforming"

        return result


class FirstDigitBenfordRule(AuditRule):
    """BEN-001: Benford's Law first digit analysis."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.analyzer = BenfordAnalyzer()

    @property
    def rule_id(self) -> str:
        return "BEN-001"

    @property
    def rule_name(self) -> str:
        return "ベンフォード第1桁分析"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PATTERN

    @property
    def description(self) -> str:
        return "ベンフォードの法則に基づく第1桁の分布分析を実行し、全体の分布異常を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        amounts = df["amount"].abs().to_list()
        benford_result = self.analyzer.analyze_first_digit(amounts)

        if benford_result.conformity == "insufficient_data":
            return result

        if benford_result.is_suspicious:
            # Create a single violation for the overall distribution
            sample = df.head(1)
            if len(sample) > 0:
                sample_row = sample.row(0, named=True)
                violation = self._create_violation(
                    gl_detail_id=sample_row["gl_detail_id"],
                    journal_id=sample_row["journal_id"],
                    message=f"ベンフォード分析: {benford_result.conformity} (MAD={benford_result.mad:.4f})",
                    details={
                        "analysis_type": "first_digit",
                        "conformity": benford_result.conformity,
                        "mad": benford_result.mad,
                        "chi_square": benford_result.chi_square,
                        "p_value": benford_result.p_value,
                        "digit_deviations": benford_result.digit_deviations,
                        "total_entries": result.total_checked,
                    },
                    score_impact=15.0 if benford_result.conformity == "nonconforming" else 10.0,
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SecondDigitBenfordRule(AuditRule):
    """BEN-002: Benford's Law second digit analysis."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.analyzer = BenfordAnalyzer()

    @property
    def rule_id(self) -> str:
        return "BEN-002"

    @property
    def rule_name(self) -> str:
        return "ベンフォード第2桁分析"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PATTERN

    @property
    def description(self) -> str:
        return "ベンフォードの法則に基づく第2桁の分布分析を実行します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        amounts = df["amount"].abs().to_list()
        benford_result = self.analyzer.analyze_second_digit(amounts)

        if benford_result.conformity == "insufficient_data":
            return result

        if benford_result.is_suspicious:
            sample = df.head(1)
            if len(sample) > 0:
                sample_row = sample.row(0, named=True)
                violation = self._create_violation(
                    gl_detail_id=sample_row["gl_detail_id"],
                    journal_id=sample_row["journal_id"],
                    message=f"ベンフォード第2桁: {benford_result.conformity}",
                    details={
                        "analysis_type": "second_digit",
                        "conformity": benford_result.conformity,
                        "mad": benford_result.mad,
                        "p_value": benford_result.p_value,
                    },
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class DigitDeviationBenfordRule(AuditRule):
    """BEN-003: Detect individual digits with large deviations."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.analyzer = BenfordAnalyzer()

    @property
    def rule_id(self) -> str:
        return "BEN-003"

    @property
    def rule_name(self) -> str:
        return "桁別偏差分析"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PATTERN

    @property
    def description(self) -> str:
        return "特定の第1桁で期待値から大きく乖離している場合を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        amounts = df["amount"].abs().to_list()
        benford_result = self.analyzer.analyze_first_digit(amounts)

        if benford_result.conformity == "insufficient_data":
            return result

        # Find digits with large deviation
        threshold = self.get_threshold("digit_deviation_threshold", 0.03)

        for digit, deviation in benford_result.digit_deviations.items():
            if abs(deviation) > threshold:
                # Find sample entries with this digit
                digit_entries = df.filter(
                    (pl.col("amount").abs().cast(pl.Utf8).str.lstrip("0").str.slice(0, 1) == str(digit))
                )
                if len(digit_entries) > 0:
                    sample_row = digit_entries.row(0, named=True)
                    direction = "過多" if deviation > 0 else "過少"
                    violation = self._create_violation(
                        gl_detail_id=sample_row["gl_detail_id"],
                        journal_id=sample_row["journal_id"],
                        message=f"桁{digit}が{direction}: 偏差{deviation:+.3f}",
                        details={
                            "digit": digit,
                            "observed": benford_result.observed_freq[digit],
                            "expected": BENFORD_FIRST_DIGIT[digit],
                            "deviation": deviation,
                            "count": len(digit_entries),
                        },
                    )
                    result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class SummationBenfordRule(AuditRule):
    """BEN-004: Summation analysis - detect concentrated amounts."""

    @property
    def rule_id(self) -> str:
        return "BEN-004"

    @property
    def rule_name(self) -> str:
        return "金額合計分析"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PATTERN

    @property
    def description(self) -> str:
        return "特定の第1桁に金額が集中しているかを分析します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        # Calculate sum by first digit
        df_with_digit = df.with_columns([
            pl.col("amount").abs().cast(pl.Utf8).str.lstrip("0").str.slice(0, 1).alias("first_digit")
        ])

        summation = df_with_digit.group_by("first_digit").agg([
            pl.col("amount").abs().sum().alias("digit_sum"),
            pl.count().alias("count"),
            pl.col("gl_detail_id").first().alias("sample_id"),
            pl.col("journal_id").first().alias("sample_journal"),
        ])

        total_sum = df["amount"].abs().sum()
        if total_sum == 0:
            return result

        # Check for concentration
        concentration_threshold = self.get_threshold("summation_threshold", 0.40)

        for row in summation.iter_rows(named=True):
            digit = row["first_digit"]
            pct = row["digit_sum"] / total_sum

            # Expected summation follows modified Benford
            if digit.isdigit() and int(digit) >= 1:
                expected_pct = 0.11  # Roughly equal for summation

                if pct > concentration_threshold:
                    violation = self._create_violation(
                        gl_detail_id=row["sample_id"],
                        journal_id=row["sample_journal"],
                        message=f"金額集中: 桁{digit}に{pct*100:.1f}%集中",
                        details={
                            "digit": digit,
                            "sum": row["digit_sum"],
                            "percentage": pct,
                            "count": row["count"],
                        },
                    )
                    result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


class IndividualBenfordViolationRule(AuditRule):
    """BEN-005: Flag individual transactions that contribute to Benford violations."""

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        self.analyzer = BenfordAnalyzer()

    @property
    def rule_id(self) -> str:
        return "BEN-005"

    @property
    def rule_name(self) -> str:
        return "個別ベンフォード違反"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.PATTERN

    @property
    def description(self) -> str:
        return "ベンフォード分布から乖離している第1桁を持つ高額取引を個別にフラグします。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        amounts = df["amount"].abs().to_list()
        benford_result = self.analyzer.analyze_first_digit(amounts)

        if benford_result.conformity == "insufficient_data":
            return result

        # Only flag if overall distribution is suspicious
        if not benford_result.is_suspicious:
            return result

        # Find the most anomalous digit
        max_deviation_digit = max(
            benford_result.digit_deviations.items(),
            key=lambda x: abs(x[1])
        )[0]

        # If this digit is over-represented, flag high-value entries with it
        if benford_result.digit_deviations[max_deviation_digit] > 0:
            threshold = self.get_threshold("individual_threshold", 10_000_000)

            df_with_digit = df.with_columns([
                pl.col("amount").abs().cast(pl.Utf8).str.lstrip("0").str.slice(0, 1).alias("first_digit")
            ])

            flagged = df_with_digit.filter(
                (pl.col("first_digit") == str(max_deviation_digit)) &
                (pl.col("amount").abs() >= threshold)
            )

            # Limit to top entries
            max_flags = self.get_threshold("max_individual_flags", 100)
            flagged = flagged.head(max_flags)

            for row in flagged.iter_rows(named=True):
                violation = self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=f"ベンフォード異常桁: {row['amount']:,.0f}円 (桁{max_deviation_digit})",
                    details={
                        "amount": row["amount"],
                        "first_digit": max_deviation_digit,
                        "digit_deviation": benford_result.digit_deviations[max_deviation_digit],
                    },
                    score_impact=5.0,
                )
                result.violations.append(violation)

        result.violations_found = len(result.violations)
        return result


def create_benford_rule_set() -> RuleSet:
    """Create the complete Benford's Law rule set.

    Returns:
        RuleSet with all 5 Benford rules.
    """
    rule_set = RuleSet(
        name="benford_rules",
        description="ベンフォードの法則による異常検知ルール (5件)",
    )

    rules = [
        FirstDigitBenfordRule(),
        SecondDigitBenfordRule(),
        DigitDeviationBenfordRule(),
        SummationBenfordRule(),
        IndividualBenfordViolationRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
