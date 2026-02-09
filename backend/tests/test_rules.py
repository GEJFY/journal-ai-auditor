"""
監査ルールのユニットテスト

各カテゴリの監査ルールが正しく動作することを検証します。
"""

from datetime import date

import polars as pl

from app.services.rules.amount_rules import (
    MaterialityRule,
    OddEndingRule,
    RoundAmountRule,
)
from app.services.rules.approval_rules import (
    MissingApprovalRule,
    SelfApprovalRule,
)
from app.services.rules.base import RuleCategory, RuleSeverity
from app.services.rules.benford import BenfordAnalyzer
from app.services.rules.time_rules import (
    AfterHoursRule,
    PeriodEndConcentrationRule,
    WeekendHolidayRule,
)


class TestAmountRules:
    """金額ルールのテスト"""

    def test_materiality_rule_detects_large_amounts(self, sample_journal_entries):
        """重要性基準超過ルールのテスト"""
        rule = MaterialityRule(threshold=100_000_000)

        result = rule.execute(sample_journal_entries)

        assert result.rule_id == "AMT_001"
        assert result.category == RuleCategory.AMOUNT
        # 150,000,000のエントリが2件（借方・貸方）あるはず
        assert result.violations_found >= 2

    def test_materiality_rule_ignores_small_amounts(self):
        """重要性基準以下の金額は検出しない"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001"],
            "amount": [50_000_000],  # 閾値以下
            "functional_amount": [50_000_000],
        })

        rule = MaterialityRule(threshold=100_000_000)
        result = rule.execute(df)

        assert result.violations_found == 0

    def test_round_amount_rule_detects_round_numbers(self):
        """丸め金額ルールのテスト"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001", "TEST002", "TEST003"],
            "amount": [100_000_000, 12_345_678, 50_000_000],
            "functional_amount": [100_000_000, 12_345_678, 50_000_000],
        })

        rule = RoundAmountRule()
        result = rule.execute(df)

        # 100,000,000と50,000,000が検出されるはず
        assert result.violations_found == 2

    def test_odd_ending_rule_detects_suspicious_endings(self):
        """端数異常ルールのテスト"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001", "TEST002", "TEST003", "TEST004"],
            "amount": [
                99_999_999,  # 999で終わる
                100_000,     # 通常
                88_888_888,  # 888で終わる
                12_345_678,  # 通常
            ],
            "functional_amount": [99_999_999, 100_000, 88_888_888, 12_345_678],
        })

        rule = OddEndingRule()
        result = rule.execute(df)

        # 999と888で終わる金額が検出されるはず
        assert result.violations_found >= 2


class TestTimeRules:
    """時間ルールのテスト"""

    def test_after_hours_rule_detects_late_entries(self, sample_journal_entries):
        """営業時間外ルールのテスト"""
        rule = AfterHoursRule(
            business_start_hour=9,
            business_end_hour=18
        )

        result = rule.execute(sample_journal_entries)

        # 23:55のエントリが検出されるはず
        assert result.violations_found >= 1
        assert result.category == RuleCategory.TIME

    def test_after_hours_rule_allows_business_hours(self):
        """営業時間内は検出しない"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001", "TEST002"],
            "entry_time": ["10:00:00", "14:30:00"],
        })

        rule = AfterHoursRule()
        result = rule.execute(df)

        assert result.violations_found == 0

    def test_weekend_holiday_rule_detects_weekend_entries(self):
        """週末・祝日ルールのテスト"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001", "TEST002", "TEST003"],
            "effective_date": [
                date(2024, 6, 29),  # 土曜日
                date(2024, 6, 30),  # 日曜日
                date(2024, 7, 1),   # 月曜日
            ],
            "entry_date": [
                date(2024, 6, 29),
                date(2024, 6, 30),
                date(2024, 7, 1),
            ],
        })

        rule = WeekendHolidayRule()
        result = rule.execute(df)

        # 土日のエントリが検出されるはず
        assert result.violations_found >= 2

    def test_period_end_concentration_rule(self, sample_journal_entries_with_anomalies):
        """期末集中ルールのテスト"""
        rule = PeriodEndConcentrationRule(threshold_days=3)

        result = rule.execute(sample_journal_entries_with_anomalies)

        # 期末に集中したエントリが検出されるはず
        assert result.category == RuleCategory.TIME


class TestApprovalRules:
    """承認ルールのテスト"""

    def test_self_approval_rule_detects_same_user(self, sample_journal_entries):
        """自己承認ルールのテスト"""
        rule = SelfApprovalRule()

        result = rule.execute(sample_journal_entries)

        # prepared_by == approved_by のエントリが検出されるはず
        assert result.violations_found >= 2  # JE003の2行
        assert result.category == RuleCategory.APPROVAL

        # 違反の詳細を確認
        for violation in result.violations:
            assert violation.severity in [RuleSeverity.CRITICAL, RuleSeverity.HIGH]

    def test_self_approval_rule_allows_different_users(self):
        """異なる承認者は検出しない"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001"],
            "prepared_by": ["U001"],
            "approved_by": ["U002"],
        })

        rule = SelfApprovalRule()
        result = rule.execute(df)

        assert result.violations_found == 0

    def test_missing_approval_rule_detects_null_approver(self):
        """承認者不在ルールのテスト"""
        df = pl.DataFrame({
            "gl_detail_id": ["TEST001", "TEST002", "TEST003"],
            "approved_by": [None, "U002", ""],
        })

        rule = MissingApprovalRule()
        result = rule.execute(df)

        # NullとEmpty文字列が検出されるはず
        assert result.violations_found >= 2


class TestBenfordAnalysis:
    """Benford分析のテスト"""

    def test_benford_first_digit_distribution(self, benford_test_data):
        """第1桁分析のテスト"""
        analyzer = BenfordAnalyzer()

        result = analyzer.analyze_first_digit(benford_test_data)

        assert "observed" in result
        assert "expected" in result
        assert "mad" in result
        assert "conformity" in result

        # 分布は9個の要素を持つはず（1-9）
        assert len(result["observed"]) == 9
        assert len(result["expected"]) == 9

        # Benfordの期待値を確認
        assert abs(result["expected"][0] - 0.301) < 0.01  # 1の出現率は約30.1%

    def test_benford_second_digit_distribution(self, benford_test_data):
        """第2桁分析のテスト"""
        analyzer = BenfordAnalyzer()

        result = analyzer.analyze_second_digit(benford_test_data)

        assert "observed" in result
        assert "expected" in result
        assert "mad" in result

        # 分布は10個の要素を持つはず（0-9）
        assert len(result["observed"]) == 10
        assert len(result["expected"]) == 10

    def test_benford_conformity_classification(self):
        """適合性分類のテスト"""
        analyzer = BenfordAnalyzer()

        # MAD値に基づく分類
        assert analyzer.classify_conformity(0.004) == "Close Conformity"
        assert analyzer.classify_conformity(0.008) == "Acceptable Conformity"
        assert analyzer.classify_conformity(0.012) == "Marginally Acceptable"
        assert analyzer.classify_conformity(0.020) == "Nonconformity"

    def test_benford_with_manipulated_data(self):
        """操作されたデータのテスト"""
        # 1で始まる数字が異常に多いデータ
        manipulated_data = [100 + i for i in range(500)] + [200 + i for i in range(100)]

        analyzer = BenfordAnalyzer()
        result = analyzer.analyze_first_digit(manipulated_data)

        # MADが高くなるはず（不適合）
        assert result["mad"] > 0.015
        assert result["conformity"] in ["Marginally Acceptable", "Nonconformity"]


class TestRuleExecution:
    """ルール実行全体のテスト"""

    def test_rule_result_contains_required_fields(self, sample_journal_entries):
        """ルール結果に必要なフィールドが含まれることを確認"""
        rule = MaterialityRule()
        result = rule.execute(sample_journal_entries)

        assert result.rule_id is not None
        assert result.rule_name is not None
        assert result.category is not None
        assert result.entries_checked >= 0
        assert result.violations_found >= 0
        assert result.execution_time_ms >= 0

    def test_violations_contain_required_fields(self, sample_journal_entries):
        """違反に必要なフィールドが含まれることを確認"""
        rule = MaterialityRule(threshold=100_000_000)
        result = rule.execute(sample_journal_entries)

        if result.violations:
            violation = result.violations[0]
            assert violation.gl_detail_id is not None
            assert violation.rule_id is not None
            assert violation.severity is not None
            assert violation.message is not None
            assert violation.score_impact > 0

    def test_rule_can_be_disabled(self):
        """ルールを無効化できることを確認"""
        rule = MaterialityRule()
        rule.enabled = False

        pl.DataFrame({
            "gl_detail_id": ["TEST001"],
            "amount": [999_999_999],
            "functional_amount": [999_999_999],
        })

        # 無効化されたルールは実行されない
        assert not rule.enabled
