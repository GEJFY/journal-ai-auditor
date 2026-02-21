"""トレンドルール・摘要分析ルールのテスト.

TRD-001〜TRD-006 と DESC-001〜DESC-006 の全12ルールを検証する。
"""

from datetime import date

import polars as pl

from app.services.rules.base import RuleCategory
from app.services.rules.description_rules import (
    DescriptionLengthOutlierRule,
    DuplicateDescriptionRule,
    EmptyDescriptionRule,
    HighValueWeakDescriptionRule,
    SuspiciousKeywordRule,
    VagueDescriptionRule,
    create_description_rule_set,
)
from app.services.rules.trend_rules import (
    ConsecutiveTrendRule,
    MonthOverMonthSpikeRule,
    PeriodEndConcentrationRule,
    PeriodEntryCountAnomalyRule,
    SeasonalDeviationRule,
    YearOverYearDeviationRule,
    create_trend_rule_set,
)

# ============================================================
# テスト用データ
# ============================================================


def _make_df(rows: list[dict]) -> pl.DataFrame:
    """テスト用DataFrameを構築するヘルパー."""
    base = {
        "gl_detail_id": "",
        "journal_id": "",
        "fiscal_year": 2024,
        "accounting_period": 1,
        "gl_account_number": "1111",
        "amount": 100_000,
        "effective_date": date(2024, 4, 1),
        "entry_date": date(2024, 4, 1),
        "je_line_description": "通常仕訳",
        "prepared_by": "U001",
        "approved_by": "U002",
        "risk_score": 0.0,
        "debit_credit_indicator": "D",
        "source": "MANUAL",
    }
    filled = []
    for i, r in enumerate(rows):
        row = {**base, **r}
        if not row["gl_detail_id"]:
            row["gl_detail_id"] = f"GLD-{i:04d}"
        if not row["journal_id"]:
            row["journal_id"] = f"JE-{i:04d}"
        filled.append(row)
    return pl.DataFrame(filled)


def _monthly_data(periods: list[int], amounts: list[float]) -> pl.DataFrame:
    """月別データを生成."""
    rows = []
    for p, a in zip(periods, amounts, strict=True):
        rows.append(
            {
                "accounting_period": p,
                "amount": a,
                "gl_account_number": "4111",
            }
        )
    return _make_df(rows)


# ============================================================
# TRD-001: 月次金額急変動
# ============================================================


class TestMonthOverMonthSpike:
    def test_detects_spike(self):
        """前月比200%以上の変動を検出."""
        df = _monthly_data(
            periods=[1, 2, 3],
            amounts=[100_000, 100_000, 500_000],
        )
        rule = MonthOverMonthSpikeRule()
        result = rule.execute(df)
        assert result.violations_found > 0
        assert any("急変動" in v.message for v in result.violations)

    def test_no_spike_below_threshold(self):
        """閾値以下の変動では検出しない."""
        df = _monthly_data(
            periods=[1, 2, 3],
            amounts=[100_000, 120_000, 140_000],
        )
        rule = MonthOverMonthSpikeRule()
        result = rule.execute(df)
        assert result.violations_found == 0


# ============================================================
# TRD-002: 期末集中取引
# ============================================================


class TestPeriodEndConcentration:
    def test_detects_concentration(self):
        """四半期末月に件数が集中するパターンを検出."""
        rows = []
        for p in range(1, 13):
            count = 50 if p in (3, 6, 9, 12) else 5
            for _j in range(count):
                rows.append(
                    {
                        "accounting_period": p,
                        "amount": 100_000,
                    }
                )
        df = _make_df(rows)
        rule = PeriodEndConcentrationRule()
        result = rule.execute(df)
        assert result.violations_found > 0

    def test_no_concentration(self):
        """均等に分布する場合は検出しない."""
        rows = []
        for p in range(1, 13):
            for _ in range(10):
                rows.append({"accounting_period": p, "amount": 100_000})
        df = _make_df(rows)
        rule = PeriodEndConcentrationRule()
        result = rule.execute(df)
        assert result.violations_found == 0


# ============================================================
# TRD-003: 期間別件数異常
# ============================================================


class TestPeriodEntryCountAnomaly:
    def test_detects_anomaly(self):
        """1つの月が極端に多い場合を検出."""
        rows = []
        for p in range(1, 13):
            count = 100 if p == 6 else 10
            for _ in range(count):
                rows.append({"accounting_period": p, "amount": 100_000})
        df = _make_df(rows)
        rule = PeriodEntryCountAnomalyRule()
        result = rule.execute(df)
        assert result.violations_found > 0


# ============================================================
# TRD-004: 前年同期比重要変動
# ============================================================


class TestYearOverYearDeviation:
    def test_detects_yoy_change(self):
        """前年比150%以上の変動を検出."""
        rows = [
            {"fiscal_year": 2023, "gl_account_number": "4111", "amount": 1_000_000},
            {"fiscal_year": 2024, "gl_account_number": "4111", "amount": 5_000_000},
        ]
        df = _make_df(rows)
        rule = YearOverYearDeviationRule()
        result = rule.execute(df)
        assert result.violations_found > 0


# ============================================================
# TRD-005: 連続増減トレンド
# ============================================================


class TestConsecutiveTrend:
    def test_detects_consecutive_increase(self):
        """4期間以上の連続増加を検出."""
        df = _monthly_data(
            periods=[1, 2, 3, 4, 5, 6],
            amounts=[100_000, 200_000, 300_000, 400_000, 500_000, 600_000],
        )
        rule = ConsecutiveTrendRule()
        result = rule.execute(df)
        assert result.violations_found > 0


# ============================================================
# TRD-006: 季節性逸脱
# ============================================================


class TestSeasonalDeviation:
    def test_detects_deviation(self):
        """平均から大きく逸脱した月を検出."""
        amounts = [100_000] * 11 + [1_000_000]
        df = _monthly_data(
            periods=list(range(1, 13)),
            amounts=amounts,
        )
        rule = SeasonalDeviationRule()
        result = rule.execute(df)
        assert result.violations_found > 0


# ============================================================
# DESC-001: 摘要空欄・不備
# ============================================================


class TestEmptyDescription:
    def test_detects_empty(self):
        """空欄摘要を検出."""
        df = _make_df(
            [
                {"je_line_description": ""},
                {"je_line_description": None},
                {"je_line_description": "OK仕訳"},
            ]
        )
        rule = EmptyDescriptionRule()
        result = rule.execute(df)
        assert result.violations_found == 2

    def test_detects_short(self):
        """2文字以下の短い摘要を検出."""
        df = _make_df(
            [
                {"je_line_description": "ab"},
                {"je_line_description": "正常な摘要です"},
            ]
        )
        rule = EmptyDescriptionRule()
        result = rule.execute(df)
        assert result.violations_found == 1


# ============================================================
# DESC-002: 汎用的・曖昧な摘要
# ============================================================


class TestVagueDescription:
    def test_detects_vague(self):
        """汎用キーワードのみの摘要を検出."""
        df = _make_df(
            [
                {"je_line_description": "その他"},
                {"je_line_description": "調整"},
                {"je_line_description": "売上計上 顧客A"},
            ]
        )
        rule = VagueDescriptionRule()
        result = rule.execute(df)
        assert result.violations_found == 2


# ============================================================
# DESC-003: 重複摘要パターン
# ============================================================


class TestDuplicateDescription:
    def test_detects_high_frequency(self):
        """同一摘要の大量使用を検出."""
        rows = []
        for _i in range(100):
            rows.append({"je_line_description": "売上計上"})
        for i in range(10):  # noqa: B007
            rows.append({"je_line_description": f"個別摘要{i}"})
        df = _make_df(rows)
        rule = DuplicateDescriptionRule(
            threshold_overrides={"duplicate_min_count": 10, "duplicate_min_ratio": 5.0}
        )
        result = rule.execute(df)
        assert result.violations_found > 0


# ============================================================
# DESC-004: 高額取引の摘要不足
# ============================================================


class TestHighValueWeakDescription:
    def test_detects_weak_desc_on_high_value(self):
        """高額取引で摘要が短い場合を検出."""
        df = _make_df(
            [
                {"amount": 100_000_000, "je_line_description": "調整"},
                {
                    "amount": 100_000_000,
                    "je_line_description": "期末決算調整 顧客A向け売上計上",
                },
                {"amount": 1_000, "je_line_description": "x"},
            ]
        )
        rule = HighValueWeakDescriptionRule()
        result = rule.execute(df)
        assert result.violations_found == 1
        assert "高額取引の摘要不足" in result.violations[0].message


# ============================================================
# DESC-005: 異常キーワード検出
# ============================================================


class TestSuspiciousKeyword:
    def test_detects_suspicious(self):
        """不正リスクキーワードを検出."""
        df = _make_df(
            [
                {"je_line_description": "架空売上の計上"},
                {"je_line_description": "水増し請求"},
                {"je_line_description": "通常の売上計上"},
            ]
        )
        rule = SuspiciousKeywordRule()
        result = rule.execute(df)
        assert result.violations_found == 2

    def test_no_false_positive(self):
        """通常の摘要では検出しない."""
        df = _make_df(
            [
                {"je_line_description": "売上計上 顧客A"},
                {"je_line_description": "仕入計上 取引先B"},
            ]
        )
        rule = SuspiciousKeywordRule()
        result = rule.execute(df)
        assert result.violations_found == 0


# ============================================================
# DESC-006: 摘要文字数外れ値
# ============================================================


class TestDescriptionLengthOutlier:
    def test_detects_outlier(self):
        """異常に長い摘要を検出."""
        rows = []
        for i in range(50):
            rows.append({"je_line_description": f"通常摘要{i}"})
        rows.append({"je_line_description": "x" * 500})
        df = _make_df(rows)
        rule = DescriptionLengthOutlierRule()
        result = rule.execute(df)
        assert result.violations_found > 0


# ============================================================
# ルールセットファクトリ
# ============================================================


class TestRuleSetFactories:
    def test_trend_rule_set(self):
        """トレンドルールセットが6件作成されること."""
        rs = create_trend_rule_set()
        assert rs.name == "trend_rules"
        rules = rs.get_enabled_rules()
        assert len(rules) == 6
        assert all(r.category == RuleCategory.TREND for r in rules)

    def test_description_rule_set(self):
        """摘要ルールセットが6件作成されること."""
        rs = create_description_rule_set()
        assert rs.name == "description_rules"
        rules = rs.get_enabled_rules()
        assert len(rules) == 6
        assert all(r.category == RuleCategory.DESCRIPTION for r in rules)

    def test_rule_ids_unique(self):
        """全ルールIDがユニークであること."""
        trend = create_trend_rule_set()
        desc = create_description_rule_set()
        all_ids = [r.rule_id for r in trend.get_enabled_rules()]
        all_ids += [r.rule_id for r in desc.get_enabled_rules()]
        assert len(all_ids) == len(set(all_ids))
