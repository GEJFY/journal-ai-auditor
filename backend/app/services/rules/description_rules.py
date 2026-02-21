"""Description-based audit rules.

6 rules for detecting anomalies in journal entry descriptions:
- DESC-001: 摘要空欄・不備
- DESC-002: 汎用的・曖昧な摘要
- DESC-003: 重複摘要パターン
- DESC-004: 高額取引の摘要不足
- DESC-005: 異常キーワード検出
- DESC-006: 摘要文字数の統計的外れ値
"""

import re

import polars as pl

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleSeverity,
)


class EmptyDescriptionRule(AuditRule):
    """DESC-001: 摘要が空欄または極端に短い仕訳を検出."""

    @property
    def rule_id(self) -> str:
        return "DESC-001"

    @property
    def rule_name(self) -> str:
        return "摘要空欄・不備"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DESCRIPTION

    @property
    def description(self) -> str:
        return "摘要が空欄、または極端に短い（2文字以下）仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        min_length = self.get_threshold("min_description_length", 3)

        empty_desc = df.filter(
            pl.col("je_line_description").is_null()
            | (
                pl.col("je_line_description").str.strip_chars().str.len_chars()
                < min_length
            )
        )

        for row in empty_desc.iter_rows(named=True):
            desc = row.get("je_line_description") or ""
            result.violations.append(
                self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=(
                        f"摘要不備: "
                        f"{'空欄' if not desc.strip() else f'「{desc.strip()}」({len(desc.strip())}文字)'}"
                    ),
                    details={
                        "description": desc,
                        "length": len(desc.strip()) if desc else 0,
                        "min_length": min_length,
                        "amount": row.get("amount"),
                    },
                )
            )

        result.violations_found = len(result.violations)
        return result


class VagueDescriptionRule(AuditRule):
    """DESC-002: 汎用的・曖昧な摘要を使用した仕訳を検出."""

    @property
    def rule_id(self) -> str:
        return "DESC-002"

    @property
    def rule_name(self) -> str:
        return "汎用的・曖昧な摘要"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DESCRIPTION

    @property
    def description(self) -> str:
        return "「その他」「雑費」「調整」など、汎用的で監査証跡が不十分な摘要を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    # 汎用的とみなすキーワード（完全一致または摘要全体がこのパターン）
    VAGUE_PATTERNS: list[str] = [
        "その他",
        "雑費",
        "雑収入",
        "調整",
        "修正",
        "振替",
        "仮払",
        "仮受",
        "諸口",
        "精算",
        "上記の通り",
        "同上",
        "テスト",
        "確認",
    ]

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        custom_patterns = self.get_threshold("vague_patterns", self.VAGUE_PATTERNS)

        # 摘要が汎用パターンのみ（前後空白除去後に完全一致）
        for row in df.iter_rows(named=True):
            desc = (row.get("je_line_description") or "").strip()
            if not desc:
                continue

            matched = None
            for pattern in custom_patterns:
                if desc == pattern:
                    matched = pattern
                    break

            if matched:
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=f"汎用摘要: 「{desc}」",
                        details={
                            "description": desc,
                            "matched_pattern": matched,
                            "amount": row.get("amount"),
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class DuplicateDescriptionRule(AuditRule):
    """DESC-003: 同一摘要が異常に多く使われるパターンを検出."""

    @property
    def rule_id(self) -> str:
        return "DESC-003"

    @property
    def rule_name(self) -> str:
        return "重複摘要パターン"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DESCRIPTION

    @property
    def description(self) -> str:
        return "同一の摘要文が閾値以上の件数で使い回されているパターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        min_count = self.get_threshold("duplicate_min_count", 20)
        min_ratio = self.get_threshold("duplicate_min_ratio", 5.0)

        total = len(df)
        if total == 0:
            return result

        desc_counts = (
            df.filter(
                pl.col("je_line_description").is_not_null()
                & (pl.col("je_line_description").str.strip_chars().str.len_chars() > 0)
            )
            .group_by("je_line_description")
            .agg(pl.len().alias("usage_count"))
            .filter(pl.col("usage_count") >= min_count)
        )

        # 全体に対する比率も考慮
        desc_counts = desc_counts.with_columns(
            (pl.col("usage_count") / total * 100).alias("usage_ratio")
        )

        frequent = desc_counts.filter(pl.col("usage_ratio") >= min_ratio)

        for freq in frequent.iter_rows(named=True):
            desc_text = freq["je_line_description"]
            count = freq["usage_count"]
            ratio = freq["usage_ratio"]

            entries = df.filter(pl.col("je_line_description") == desc_text)
            for row in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=(
                            f"重複摘要: 「{desc_text[:30]}」({count}件, {ratio:.1f}%)"
                        ),
                        details={
                            "description": desc_text,
                            "usage_count": count,
                            "usage_ratio": round(ratio, 2),
                            "total_entries": total,
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class HighValueWeakDescriptionRule(AuditRule):
    """DESC-004: 高額取引にもかかわらず摘要が不十分な仕訳を検出."""

    @property
    def rule_id(self) -> str:
        return "DESC-004"

    @property
    def rule_name(self) -> str:
        return "高額取引の摘要不足"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DESCRIPTION

    @property
    def description(self) -> str:
        return "高額取引で摘要が短すぎる、または具体性が欠ける仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        amount_threshold = self.get_threshold(
            "high_value_threshold",
            50_000_000,
        )
        min_desc_length = self.get_threshold("min_desc_length_high_value", 10)

        high_value = df.filter(pl.col("amount").abs() >= amount_threshold)

        for row in high_value.iter_rows(named=True):
            desc = (row.get("je_line_description") or "").strip()
            if len(desc) < min_desc_length:
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=(
                            f"高額取引の摘要不足: "
                            f"{row['amount']:,.0f}円に対し"
                            f"摘要{len(desc)}文字"
                        ),
                        details={
                            "amount": row["amount"],
                            "description": desc,
                            "description_length": len(desc),
                            "amount_threshold": amount_threshold,
                            "min_desc_length": min_desc_length,
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class SuspiciousKeywordRule(AuditRule):
    """DESC-005: 不正リスクを示唆するキーワードを含む摘要を検出."""

    @property
    def rule_id(self) -> str:
        return "DESC-005"

    @property
    def rule_name(self) -> str:
        return "異常キーワード検出"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DESCRIPTION

    @property
    def description(self) -> str:
        return "摘要に不正・異常リスクを示唆するキーワードが含まれる仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    # 不正リスクを示唆するキーワードパターン
    SUSPICIOUS_PATTERNS: list[tuple[str, str]] = [
        (r"(架空|カラ|から売)", "架空取引の疑い"),
        (r"(水増|かさ上げ)", "水増し計上の疑い"),
        (r"(簿外|オフバランス)", "簿外取引の疑い"),
        (r"(個人|私用|自宅)", "個人利用の疑い"),
        (r"(現金|キャッシュ).*(引出|払出)", "現金引出"),
        (r"(戻し|取消).*(戻し|取消)", "二重戻し"),
        (r"(至急|緊急|急ぎ)", "緊急処理"),
        (r"(仮|暫定|一時).*(計上|処理)", "仮計上"),
    ]

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        for row in df.iter_rows(named=True):
            desc = row.get("je_line_description") or ""
            if not desc.strip():
                continue

            for pattern, label in self.SUSPICIOUS_PATTERNS:
                if re.search(pattern, desc):
                    result.violations.append(
                        self._create_violation(
                            gl_detail_id=row["gl_detail_id"],
                            journal_id=row["journal_id"],
                            message=f"異常キーワード: {label} 「{desc[:40]}」",
                            details={
                                "description": desc,
                                "pattern": pattern,
                                "keyword_label": label,
                                "amount": row.get("amount"),
                            },
                        )
                    )
                    break  # 1仕訳につき最初のマッチのみ

        result.violations_found = len(result.violations)
        return result


class DescriptionLengthOutlierRule(AuditRule):
    """DESC-006: 摘要文字数が統計的に異常な外れ値を検出."""

    @property
    def rule_id(self) -> str:
        return "DESC-006"

    @property
    def rule_name(self) -> str:
        return "摘要文字数外れ値"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.DESCRIPTION

    @property
    def description(self) -> str:
        return "摘要の文字数が全体の統計分布から大きく外れた仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.INFO

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        std_multiplier = self.get_threshold("desc_length_std_multiplier", 3.0)

        # 摘要文字数を計算
        with_len = df.with_columns(
            pl.col("je_line_description")
            .fill_null("")
            .str.strip_chars()
            .str.len_chars()
            .alias("desc_length")
        )

        # 文字数が0でない行のみ統計
        non_empty = with_len.filter(pl.col("desc_length") > 0)
        if len(non_empty) < 10:
            return result

        mean_len = non_empty["desc_length"].mean()
        std_len = non_empty["desc_length"].std()
        if mean_len is None or std_len is None or std_len == 0:
            return result

        upper_bound = mean_len + std_multiplier * std_len

        outliers = with_len.filter(pl.col("desc_length") > upper_bound)

        for row in outliers.iter_rows(named=True):
            desc = (row.get("je_line_description") or "").strip()
            z_score = (len(desc) - mean_len) / std_len

            result.violations.append(
                self._create_violation(
                    gl_detail_id=row["gl_detail_id"],
                    journal_id=row["journal_id"],
                    message=(
                        f"摘要文字数異常: {len(desc)}文字 "
                        f"(平均{mean_len:.0f}±{std_len:.0f}, "
                        f"Z={z_score:.1f})"
                    ),
                    details={
                        "description": desc[:100],
                        "length": len(desc),
                        "mean_length": round(mean_len, 1),
                        "std_length": round(std_len, 1),
                        "z_score": round(z_score, 2),
                    },
                )
            )

        result.violations_found = len(result.violations)
        return result


def create_description_rule_set() -> RuleSet:
    """摘要分析ルールセットを作成する."""
    rule_set = RuleSet(
        name="description_rules",
        description="摘要分析ルール (6件): DESC-001 to DESC-006",
    )

    rules = [
        EmptyDescriptionRule(),
        VagueDescriptionRule(),
        DuplicateDescriptionRule(),
        HighValueWeakDescriptionRule(),
        SuspiciousKeywordRule(),
        DescriptionLengthOutlierRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
