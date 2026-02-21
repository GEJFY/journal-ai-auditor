"""Trend-based audit rules.

6 rules for detecting anomalous trends and temporal patterns:
- TRD-001: 月次金額急変動（前月比）
- TRD-002: 期末集中取引
- TRD-003: 会計期間間の件数異常
- TRD-004: 前年同期比の重要変動
- TRD-005: 連続増加・減少トレンド
- TRD-006: 季節性逸脱
"""

import polars as pl

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleSeverity,
)


class MonthOverMonthSpikeRule(AuditRule):
    """TRD-001: 前月比で金額が急変動した仕訳を検出."""

    @property
    def rule_id(self) -> str:
        return "TRD-001"

    @property
    def rule_name(self) -> str:
        return "月次金額急変動"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TREND

    @property
    def description(self) -> str:
        return "勘定科目ごとの月次合計が前月比で閾値以上変動した仕訳を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        change_pct_threshold = self.get_threshold("mom_change_pct", 200.0)

        # 勘定科目×会計期間の月次合計を算出
        monthly = (
            df.group_by(["gl_account_number", "accounting_period"])
            .agg(pl.col("amount").abs().sum().alias("period_total"))
            .sort(["gl_account_number", "accounting_period"])
        )

        # 前月比を計算
        monthly = monthly.with_columns(
            pl.col("period_total")
            .shift(1)
            .over("gl_account_number")
            .alias("prior_total")
        )

        # 変動率フィルタ（前月が0でない場合のみ）
        spikes = monthly.filter(
            (pl.col("prior_total") > 0)
            & (
                (
                    (pl.col("period_total") - pl.col("prior_total")).abs()
                    / pl.col("prior_total")
                    * 100
                )
                >= change_pct_threshold
            )
        )

        # 該当期間・科目の仕訳にviolationを発行
        for spike in spikes.iter_rows(named=True):
            acct = spike["gl_account_number"]
            period = spike["accounting_period"]
            change = (
                (spike["period_total"] - spike["prior_total"])
                / spike["prior_total"]
                * 100
            )

            entries = df.filter(
                (pl.col("gl_account_number") == acct)
                & (pl.col("accounting_period") == period)
            )
            for row in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=(
                            f"月次急変動: 科目{acct} 期間{period} 前月比{change:+.1f}%"
                        ),
                        details={
                            "account": acct,
                            "period": period,
                            "current_total": spike["period_total"],
                            "prior_total": spike["prior_total"],
                            "change_pct": round(change, 1),
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class PeriodEndConcentrationRule(AuditRule):
    """TRD-002: 期末（各四半期末）に取引が集中するパターンを検出."""

    @property
    def rule_id(self) -> str:
        return "TRD-002"

    @property
    def rule_name(self) -> str:
        return "期末集中取引"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TREND

    @property
    def description(self) -> str:
        return "四半期末月に取引件数・金額が集中するパターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.HIGH

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        concentration_ratio = self.get_threshold("period_end_ratio", 2.0)

        # 四半期末月: 3, 6, 9, 12
        quarter_end_months = {3, 6, 9, 12}

        monthly_counts = df.group_by("accounting_period").agg(
            pl.len().alias("entry_count"),
            pl.col("amount").abs().sum().alias("total_amount"),
        )

        if len(monthly_counts) == 0:
            return result

        _avg_count = monthly_counts["entry_count"].mean()
        if _avg_count is None or _avg_count == 0:
            return result
        avg_count = float(_avg_count)  # type: ignore[arg-type]

        # 期末月で平均の concentration_ratio 倍以上の月を検出
        concentrated = monthly_counts.filter(
            (pl.col("accounting_period").is_in(list(quarter_end_months)))
            & (pl.col("entry_count") >= avg_count * concentration_ratio)
        )

        for row in concentrated.iter_rows(named=True):
            period = row["accounting_period"]
            ratio = row["entry_count"] / avg_count

            entries = df.filter(pl.col("accounting_period") == period)
            for entry in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=entry["gl_detail_id"],
                        journal_id=entry["journal_id"],
                        message=(
                            f"期末集中: 期間{period} "
                            f"件数{row['entry_count']}件 "
                            f"(平均の{ratio:.1f}倍)"
                        ),
                        details={
                            "period": period,
                            "entry_count": row["entry_count"],
                            "avg_count": round(avg_count, 1),
                            "concentration_ratio": round(ratio, 2),
                            "total_amount": row["total_amount"],
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class PeriodEntryCountAnomalyRule(AuditRule):
    """TRD-003: 会計期間間で仕訳件数が異常に偏るパターンを検出."""

    @property
    def rule_id(self) -> str:
        return "TRD-003"

    @property
    def rule_name(self) -> str:
        return "期間別件数異常"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TREND

    @property
    def description(self) -> str:
        return "特定の会計期間に仕訳件数が統計的に異常な偏りを示す場合を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        std_multiplier = self.get_threshold("count_std_multiplier", 2.0)

        monthly_counts = df.group_by("accounting_period").agg(
            pl.len().alias("entry_count")
        )

        if len(monthly_counts) < 3:
            return result

        _mean_count = monthly_counts["entry_count"].mean()
        _std_count = monthly_counts["entry_count"].std()
        if _mean_count is None or _std_count is None or _std_count == 0:
            return result
        mean_count = float(_mean_count)  # type: ignore[arg-type]
        std_count = float(_std_count)  # type: ignore[arg-type]

        upper_bound = mean_count + std_multiplier * std_count

        anomalous = monthly_counts.filter(pl.col("entry_count") > upper_bound)

        for row in anomalous.iter_rows(named=True):
            period = row["accounting_period"]
            z_score = (row["entry_count"] - mean_count) / std_count

            entries = df.filter(pl.col("accounting_period") == period)
            for entry in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=entry["gl_detail_id"],
                        journal_id=entry["journal_id"],
                        message=(
                            f"件数異常: 期間{period} "
                            f"{row['entry_count']}件 "
                            f"(Z={z_score:.1f})"
                        ),
                        details={
                            "period": period,
                            "entry_count": row["entry_count"],
                            "mean_count": round(mean_count, 1),
                            "std_count": round(std_count, 1),
                            "z_score": round(z_score, 2),
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class YearOverYearDeviationRule(AuditRule):
    """TRD-004: 前年同期比で重要な変動がある仕訳を検出."""

    @property
    def rule_id(self) -> str:
        return "TRD-004"

    @property
    def rule_name(self) -> str:
        return "前年同期比重要変動"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TREND

    @property
    def description(self) -> str:
        return "勘定科目の前年同期比で重要な変動がある場合を検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        yoy_threshold = self.get_threshold("yoy_change_pct", 150.0)

        # 年度ごと勘定科目別合計
        yearly = (
            df.group_by(["fiscal_year", "gl_account_number"])
            .agg(pl.col("amount").abs().sum().alias("yearly_total"))
            .sort(["gl_account_number", "fiscal_year"])
        )

        yearly = yearly.with_columns(
            pl.col("yearly_total")
            .shift(1)
            .over("gl_account_number")
            .alias("prior_year_total")
        )

        deviations = yearly.filter(
            (pl.col("prior_year_total") > 0)
            & (
                (
                    (pl.col("yearly_total") - pl.col("prior_year_total")).abs()
                    / pl.col("prior_year_total")
                    * 100
                )
                >= yoy_threshold
            )
        )

        for dev in deviations.iter_rows(named=True):
            acct = dev["gl_account_number"]
            fy = dev["fiscal_year"]
            change = (
                (dev["yearly_total"] - dev["prior_year_total"])
                / dev["prior_year_total"]
                * 100
            )

            entries = df.filter(
                (pl.col("gl_account_number") == acct) & (pl.col("fiscal_year") == fy)
            )
            for row in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=(f"前年同期比変動: 科目{acct} FY{fy} {change:+.1f}%"),
                        details={
                            "account": acct,
                            "fiscal_year": fy,
                            "current_total": dev["yearly_total"],
                            "prior_year_total": dev["prior_year_total"],
                            "change_pct": round(change, 1),
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class ConsecutiveTrendRule(AuditRule):
    """TRD-005: 勘定科目の金額が連続して増加・減少するトレンドを検出."""

    @property
    def rule_id(self) -> str:
        return "TRD-005"

    @property
    def rule_name(self) -> str:
        return "連続増減トレンド"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TREND

    @property
    def description(self) -> str:
        return (
            "勘定科目の月次合計が連続して増加または減少する異常トレンドを検出します。"
        )

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        min_streak = self.get_threshold("consecutive_months", 4)

        monthly = (
            df.group_by(["gl_account_number", "accounting_period"])
            .agg(pl.col("amount").abs().sum().alias("period_total"))
            .sort(["gl_account_number", "accounting_period"])
        )

        monthly = monthly.with_columns(
            pl.col("period_total")
            .shift(1)
            .over("gl_account_number")
            .alias("prior_total")
        )

        monthly = monthly.with_columns(
            (pl.col("period_total") - pl.col("prior_total")).alias("diff")
        )

        # 勘定科目ごとに連続増加・減少を検出
        flagged: set[tuple[str, int]] = set()

        for acct in monthly["gl_account_number"].unique().to_list():
            acct_data = monthly.filter(pl.col("gl_account_number") == acct).sort(
                "accounting_period"
            )
            diffs = acct_data["diff"].to_list()
            periods = acct_data["accounting_period"].to_list()

            streak = 0
            direction = 0  # 1=増加, -1=減少

            for i, d in enumerate(diffs):
                if d is None:
                    streak = 0
                    direction = 0
                    continue

                if d > 0:
                    if direction == 1:
                        streak += 1
                    else:
                        streak = 1
                        direction = 1
                elif d < 0:
                    if direction == -1:
                        streak += 1
                    else:
                        streak = 1
                        direction = -1
                else:
                    streak = 0
                    direction = 0

                if streak >= min_streak:
                    for p_idx in range(max(0, i - streak + 1), i + 1):
                        flagged.add((acct, periods[p_idx]))

        for acct, period in flagged:
            entries = df.filter(
                (pl.col("gl_account_number") == acct)
                & (pl.col("accounting_period") == period)
            )
            for row in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=row["gl_detail_id"],
                        journal_id=row["journal_id"],
                        message=(
                            f"連続トレンド: 科目{acct} 期間{period} "
                            f"{min_streak}期間以上の連続変動"
                        ),
                        details={
                            "account": acct,
                            "period": period,
                            "min_streak": min_streak,
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


class SeasonalDeviationRule(AuditRule):
    """TRD-006: 季節性パターンから逸脱した取引を検出."""

    @property
    def rule_id(self) -> str:
        return "TRD-006"

    @property
    def rule_name(self) -> str:
        return "季節性逸脱"

    @property
    def category(self) -> RuleCategory:
        return RuleCategory.TREND

    @property
    def description(self) -> str:
        return "過去の季節性パターンから大きく逸脱した仕訳パターンを検出します。"

    @property
    def default_severity(self) -> RuleSeverity:
        return RuleSeverity.LOW

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)

        deviation_threshold = self.get_threshold("seasonal_deviation_pct", 100.0)

        # 月別の平均金額を算出（季節性ベースライン）
        monthly = df.group_by("accounting_period").agg(
            pl.col("amount").abs().sum().alias("period_total")
        )

        if len(monthly) < 6:
            return result

        _overall_mean = monthly["period_total"].mean()
        if _overall_mean is None or _overall_mean == 0:
            return result
        overall_mean = float(_overall_mean)  # type: ignore[arg-type]

        # 各月の平均からの逸脱を検出
        deviating = monthly.filter(
            ((pl.col("period_total") - overall_mean).abs() / overall_mean * 100)
            > deviation_threshold
        )

        for row in deviating.iter_rows(named=True):
            period = row["accounting_period"]
            dev_pct = (row["period_total"] - overall_mean) / overall_mean * 100

            entries = df.filter(pl.col("accounting_period") == period)
            for entry in entries.iter_rows(named=True):
                result.violations.append(
                    self._create_violation(
                        gl_detail_id=entry["gl_detail_id"],
                        journal_id=entry["journal_id"],
                        message=(f"季節性逸脱: 期間{period} 平均比{dev_pct:+.1f}%"),
                        details={
                            "period": period,
                            "period_total": row["period_total"],
                            "overall_mean": round(overall_mean, 0),
                            "deviation_pct": round(dev_pct, 1),
                        },
                    )
                )

        result.violations_found = len(result.violations)
        return result


def create_trend_rule_set() -> RuleSet:
    """トレンド分析ルールセットを作成する."""
    rule_set = RuleSet(
        name="trend_rules",
        description="トレンド分析ルール (6件): TRD-001 to TRD-006",
    )

    rules = [
        MonthOverMonthSpikeRule(),
        PeriodEndConcentrationRule(),
        PeriodEntryCountAnomalyRule(),
        YearOverYearDeviationRule(),
        ConsecutiveTrendRule(),
        SeasonalDeviationRule(),
    ]

    for rule in rules:
        rule_set.add_rule(rule)

    return rule_set
