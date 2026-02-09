"""Rule engine, scoring, base classes のユニットテスト.

RuleBase (RuleViolation, RuleResult, AuditRule, RuleSet),
RuleEngine, RiskScoringService, RiskPrioritizer をテスト。
DB操作はすべてモック化。
"""

from datetime import datetime
from unittest.mock import MagicMock, patch

import polars as pl
import pytest

from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleSeverity,
    RuleViolation,
)


# =========================================================
# RuleViolation テスト
# =========================================================


class TestRuleViolation:
    """RuleViolation データクラスのテスト"""

    def test_creation(self):
        v = RuleViolation(
            rule_id="AMT-001",
            rule_name="高額取引",
            category=RuleCategory.AMOUNT,
            severity=RuleSeverity.HIGH,
            gl_detail_id="JE001-001",
            journal_id="JE001",
            message="100億円超の取引",
            score_impact=15.0,
        )
        assert v.rule_id == "AMT-001"
        assert v.severity == RuleSeverity.HIGH
        assert v.score_impact == 15.0

    def test_to_dict(self):
        v = RuleViolation(
            rule_id="ACC-001",
            rule_name="勘定異常",
            category=RuleCategory.ACCOUNT,
            severity=RuleSeverity.MEDIUM,
            gl_detail_id="JE002-001",
            journal_id="JE002",
            message="異常な勘定組合せ",
            details={"account": "1131"},
        )
        d = v.to_dict()
        assert d["rule_id"] == "ACC-001"
        assert d["category"] == "account"
        assert d["severity"] == "medium"
        assert d["details"]["account"] == "1131"

    def test_default_score_impact(self):
        v = RuleViolation(
            rule_id="T",
            rule_name="T",
            category=RuleCategory.TIME,
            severity=RuleSeverity.LOW,
            gl_detail_id="X",
            journal_id="X",
            message="msg",
        )
        assert v.score_impact == 0.0  # デフォルト値


# =========================================================
# RuleResult テスト
# =========================================================


class TestRuleResult:
    """RuleResult のテスト"""

    def test_success_property(self):
        r = RuleResult(
            rule_id="AMT-001",
            rule_name="test",
            category=RuleCategory.AMOUNT,
        )
        assert r.success is True

    def test_failure_property(self):
        r = RuleResult(
            rule_id="AMT-001",
            rule_name="test",
            category=RuleCategory.AMOUNT,
            error="テストエラー",
        )
        assert r.success is False

    def test_violation_rate_zero(self):
        r = RuleResult(
            rule_id="T",
            rule_name="T",
            category=RuleCategory.AMOUNT,
            total_checked=0,
            violations_found=0,
        )
        assert r.violation_rate == 0.0

    def test_violation_rate_calculation(self):
        r = RuleResult(
            rule_id="T",
            rule_name="T",
            category=RuleCategory.AMOUNT,
            total_checked=100,
            violations_found=5,
        )
        assert r.violation_rate == 5.0

    def test_to_dict(self):
        r = RuleResult(
            rule_id="ACC-001",
            rule_name="勘定ルール",
            category=RuleCategory.ACCOUNT,
            total_checked=200,
            violations_found=10,
        )
        d = r.to_dict()
        assert d["rule_id"] == "ACC-001"
        assert d["total_checked"] == 200
        assert d["violation_rate"] == 5.0
        assert d["success"] is True


# =========================================================
# AuditRule 基底クラステスト
# =========================================================


class _DummyRule(AuditRule):
    """テスト用の具象ルール"""

    @property
    def rule_id(self):
        return "TEST-001"

    @property
    def rule_name(self):
        return "テストルール"

    @property
    def category(self):
        return RuleCategory.AMOUNT

    @property
    def description(self):
        return "テスト用ルール"

    @property
    def default_severity(self):
        return RuleSeverity.MEDIUM

    def execute(self, df: pl.DataFrame) -> RuleResult:
        result = self._create_result()
        result.total_checked = len(df)
        # 金額100万超を検出
        for i, row in enumerate(df.iter_rows(named=True)):
            if row.get("amount", 0) > 1_000_000:
                v = self._create_violation(
                    gl_detail_id=row.get("gl_detail_id", f"row-{i}"),
                    journal_id=row.get("journal_id", "unknown"),
                    message=f"高額取引: {row.get('amount')}",
                )
                result.violations.append(v)
                result.violations_found += 1
        return result


class TestAuditRule:
    """AuditRule 基底クラスのテスト"""

    def test_severity_default(self):
        rule = _DummyRule()
        assert rule.severity == RuleSeverity.MEDIUM

    def test_severity_override(self):
        rule = _DummyRule(severity_override=RuleSeverity.CRITICAL)
        assert rule.severity == RuleSeverity.CRITICAL

    def test_threshold_default(self):
        rule = _DummyRule()
        assert rule.get_threshold("amount", 1_000_000) == 1_000_000

    def test_threshold_override(self):
        rule = _DummyRule(threshold_overrides={"amount": 500_000})
        assert rule.get_threshold("amount", 1_000_000) == 500_000

    def test_enabled_default(self):
        rule = _DummyRule()
        assert rule.enabled is True

    def test_disabled(self):
        rule = _DummyRule(enabled=False)
        assert rule.enabled is False

    def test_create_violation_auto_score(self):
        rule = _DummyRule()
        v = rule._create_violation("GL001", "JE001", "テスト")
        # MEDIUM のデフォルトスコアは 10.0
        assert v.score_impact == 10.0

    def test_create_violation_custom_score(self):
        rule = _DummyRule()
        v = rule._create_violation("GL001", "JE001", "テスト", score_impact=25.0)
        assert v.score_impact == 25.0

    def test_repr(self):
        rule = _DummyRule()
        assert "TEST-001" in repr(rule)

    def test_execute_finds_violations(self):
        rule = _DummyRule()
        df = pl.DataFrame({
            "gl_detail_id": ["A", "B", "C"],
            "journal_id": ["J1", "J1", "J2"],
            "amount": [500_000, 2_000_000, 5_000_000],
        })
        result = rule.execute(df)
        assert result.total_checked == 3
        assert result.violations_found == 2

    def test_execute_no_violations(self):
        rule = _DummyRule()
        df = pl.DataFrame({
            "gl_detail_id": ["A"],
            "journal_id": ["J1"],
            "amount": [100],
        })
        result = rule.execute(df)
        assert result.violations_found == 0


# =========================================================
# RuleSet テスト
# =========================================================


class TestRuleSet:
    """RuleSet のテスト"""

    def test_add_and_get_rule(self):
        rs = RuleSet("test_set", "テストセット")
        rule = _DummyRule()
        rs.add_rule(rule)
        assert rs.get_rule("TEST-001") is rule

    def test_get_nonexistent(self):
        rs = RuleSet("test_set")
        assert rs.get_rule("NONE") is None

    def test_get_enabled_rules(self):
        rs = RuleSet("test_set")
        rs.add_rule(_DummyRule())
        enabled = rs.get_enabled_rules()
        assert len(enabled) == 1

    def test_len(self):
        rs = RuleSet("test_set")
        assert len(rs) == 0
        rs.add_rule(_DummyRule())
        assert len(rs) == 1

    def test_iter(self):
        rs = RuleSet("test_set")
        rs.add_rule(_DummyRule())
        rules = list(rs)
        assert len(rules) == 1

    def test_get_rules_by_category(self):
        rs = RuleSet("test_set")
        rs.add_rule(_DummyRule())
        assert len(rs.get_rules_by_category(RuleCategory.AMOUNT)) == 1
        assert len(rs.get_rules_by_category(RuleCategory.TIME)) == 0


# =========================================================
# RuleEngine テスト
# =========================================================


class TestRuleEngine:
    """RuleEngine のテスト"""

    def _make_engine(self):
        from app.services.rules.rule_engine import RuleEngine
        mock_db = MagicMock()
        return RuleEngine(db=mock_db, max_workers=2)

    def test_register_rule(self):
        engine = self._make_engine()
        rule = _DummyRule()
        engine.register_rule(rule)
        assert engine.get_rule("TEST-001") is rule
        assert engine.rule_count == 1

    def test_register_rule_set(self):
        engine = self._make_engine()
        rs = RuleSet("test_set")
        rs.add_rule(_DummyRule())
        engine.register_rule_set(rs)
        assert engine.rule_count == 1

    def test_get_enabled_rules(self):
        engine = self._make_engine()
        engine.register_rule(_DummyRule())
        assert len(engine.get_enabled_rules()) == 1

    def test_get_rules_by_category(self):
        engine = self._make_engine()
        engine.register_rule(_DummyRule())
        assert len(engine.get_rules_by_category(RuleCategory.AMOUNT)) == 1
        assert len(engine.get_rules_by_category(RuleCategory.TIME)) == 0

    def test_execute_single_rule(self):
        engine = self._make_engine()
        rule = _DummyRule()
        df = pl.DataFrame({
            "gl_detail_id": ["A", "B"],
            "journal_id": ["J1", "J1"],
            "amount": [500_000, 2_000_000],
        })
        result = engine.execute_rule(rule, df)
        assert result.success is True
        assert result.violations_found == 1
        assert result.execution_time_ms >= 0

    def test_execute_rule_handles_exception(self):
        engine = self._make_engine()
        rule = MagicMock(spec=AuditRule)
        rule.rule_id = "ERR-001"
        rule.rule_name = "エラールール"
        rule.category = RuleCategory.AMOUNT
        rule.execute.side_effect = RuntimeError("テストエラー")
        df = pl.DataFrame({"a": [1]})
        result = engine.execute_rule(rule, df)
        assert result.success is False
        assert "テストエラー" in result.error

    def test_execute_rules_sequential(self):
        engine = self._make_engine()
        rule = _DummyRule()
        df = pl.DataFrame({
            "gl_detail_id": ["A", "B", "C"],
            "journal_id": ["J1", "J1", "J2"],
            "amount": [500_000, 2_000_000, 3_000_000],
        })
        result = engine.execute_rules(df, [rule], parallel=False)
        assert result.total_entries == 3
        assert result.rules_executed == 1
        assert result.total_violations == 2

    def test_execute_rules_parallel(self):
        engine = self._make_engine()
        rule = _DummyRule()
        df = pl.DataFrame({
            "gl_detail_id": ["A"],
            "journal_id": ["J1"],
            "amount": [5_000_000],
        })
        # parallel=True でも1ルールなので sequential fallback
        result = engine.execute_rules(df, [rule], parallel=True)
        assert result.rules_executed == 1

    def test_execute_rules_aggregates_by_category(self):
        engine = self._make_engine()
        rule = _DummyRule()
        df = pl.DataFrame({
            "gl_detail_id": ["A"],
            "journal_id": ["J1"],
            "amount": [5_000_000],
        })
        result = engine.execute_rules(df, [rule])
        assert "amount" in result.violations_by_category
        assert result.violations_by_category["amount"] == 1

    def test_execute_rules_with_failed_rule(self):
        engine = self._make_engine()
        bad_rule = MagicMock(spec=AuditRule)
        bad_rule.rule_id = "BAD"
        bad_rule.rule_name = "Bad"
        bad_rule.category = RuleCategory.TIME
        bad_rule.execute.side_effect = Exception("fail")
        df = pl.DataFrame({"a": [1]})
        result = engine.execute_rules(df, [bad_rule], parallel=False)
        assert result.rules_failed == 1

    def test_load_journal_entries(self):
        engine = self._make_engine()
        engine.db.execute_df.return_value = pl.DataFrame({"id": [1, 2]})
        df = engine.load_journal_entries(fiscal_year=2024)
        assert len(df) == 2
        engine.db.execute_df.assert_called_once()

    def test_store_violations_empty(self):
        engine = self._make_engine()
        assert engine.store_violations([]) == 0

    def test_update_risk_scores_empty(self):
        engine = self._make_engine()
        assert engine.update_risk_scores([]) == 0

    def test_update_risk_scores(self):
        engine = self._make_engine()
        mock_conn = MagicMock()
        engine.db.connect.return_value.__enter__ = MagicMock(return_value=mock_conn)
        engine.db.connect.return_value.__exit__ = MagicMock(return_value=False)

        violations = [
            RuleViolation(
                rule_id="AMT-001",
                rule_name="高額",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.HIGH,
                gl_detail_id="GL001",
                journal_id="JE001",
                message="テスト",
                score_impact=15.0,
            ),
            RuleViolation(
                rule_id="AMT-002",
                rule_name="端数",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.MEDIUM,
                gl_detail_id="GL001",
                journal_id="JE001",
                message="テスト2",
                score_impact=10.0,
            ),
        ]
        updated = engine.update_risk_scores(violations)
        assert updated == 1  # 1エントリ（GL001のみ）
        mock_conn.execute.assert_called_once()
        # スコアが25.0（15+10）であること
        call_args = mock_conn.execute.call_args[0]
        assert call_args[1][0] == 25.0  # capped_score

    def test_get_violation_summary(self):
        engine = self._make_engine()
        engine.db.execute.return_value = [
            ("AMT-001", "high", 10),
            ("ACC-001", "medium", 5),
        ]
        summary = engine.get_violation_summary(fiscal_year=2024)
        assert summary["total"] == 15
        assert summary["by_rule"]["AMT-001"] == 10
        assert summary["by_severity"]["high"] == 10


class TestEngineResult:
    """EngineResult のテスト"""

    def test_to_dict(self):
        from app.services.rules.rule_engine import EngineResult
        result = EngineResult(
            total_entries=100,
            total_rules=5,
            rules_executed=5,
            total_violations=10,
        )
        d = result.to_dict()
        assert d["total_entries"] == 100
        assert d["total_rules"] == 5
        assert d["total_violations"] == 10


# =========================================================
# RiskScoringService テスト
# =========================================================


class TestRiskScore:
    """RiskScore データクラスのテスト"""

    def test_risk_category_critical(self):
        from app.services.rules.scoring import RiskScore
        s = RiskScore(gl_detail_id="A", journal_id="J", total_score=85)
        assert s.risk_category == "critical"

    def test_risk_category_high(self):
        from app.services.rules.scoring import RiskScore
        s = RiskScore(gl_detail_id="A", journal_id="J", total_score=65)
        assert s.risk_category == "high"

    def test_risk_category_medium(self):
        from app.services.rules.scoring import RiskScore
        s = RiskScore(gl_detail_id="A", journal_id="J", total_score=45)
        assert s.risk_category == "medium"

    def test_risk_category_low(self):
        from app.services.rules.scoring import RiskScore
        s = RiskScore(gl_detail_id="A", journal_id="J", total_score=25)
        assert s.risk_category == "low"

    def test_risk_category_minimal(self):
        from app.services.rules.scoring import RiskScore
        s = RiskScore(gl_detail_id="A", journal_id="J", total_score=10)
        assert s.risk_category == "minimal"

    def test_to_dict(self):
        from app.services.rules.scoring import RiskScore
        s = RiskScore(
            gl_detail_id="A",
            journal_id="J",
            total_score=75.555,
            rule_score=50.0,
            ml_score=15.0,
            benford_score=10.555,
        )
        d = s.to_dict()
        assert d["total_score"] == 75.56
        assert d["benford_score"] == 10.56
        assert d["risk_category"] == "high"


class TestScoringConfig:
    """ScoringConfig のテスト"""

    def test_defaults(self):
        from app.services.rules.scoring import ScoringConfig
        config = ScoringConfig()
        assert config.severity_weights["critical"] == 25.0
        assert config.category_weights["approval"] == 1.5
        assert config.max_score == 100.0
        assert config.auto_review_threshold == 60.0


class TestRiskScoringService:
    """RiskScoringService のテスト"""

    def _make_service(self):
        from app.services.rules.scoring import RiskScoringService
        mock_db = MagicMock()
        return RiskScoringService(db=mock_db)

    def test_calculate_score_basic(self):
        service = self._make_service()
        violations = [
            RuleViolation(
                rule_id="AMT-001",
                rule_name="高額",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.HIGH,
                gl_detail_id="A",
                journal_id="J",
                message="msg",
                score_impact=15.0,
            ),
        ]
        score = service.calculate_score(violations)
        # score_impact(15.0) * category_weight(1.0) = 15.0
        assert score == 15.0

    def test_calculate_score_with_ml_and_benford(self):
        service = self._make_service()
        score = service.calculate_score([], ml_score=0.8, benford_risk=0.5)
        # ml: 0.8 * 20.0 * 1.0 = 16.0
        # benford: 0.5 * 10.0 * 0.5 = 2.5
        assert score == pytest.approx(18.5, abs=0.1)

    def test_calculate_score_capped_at_100(self):
        service = self._make_service()
        violations = [
            RuleViolation(
                rule_id=f"R-{i}",
                rule_name="r",
                category=RuleCategory.APPROVAL,
                severity=RuleSeverity.CRITICAL,
                gl_detail_id="A",
                journal_id="J",
                message="m",
                score_impact=30.0,
            )
            for i in range(10)
        ]
        score = service.calculate_score(violations)
        assert score == 100.0

    def test_score_violations_groups_by_entry(self):
        service = self._make_service()
        violations = [
            RuleViolation(
                rule_id="AMT-001",
                rule_name="高額",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.HIGH,
                gl_detail_id="GL001",
                journal_id="JE001",
                message="msg1",
                score_impact=15.0,
            ),
            RuleViolation(
                rule_id="ACC-001",
                rule_name="勘定",
                category=RuleCategory.ACCOUNT,
                severity=RuleSeverity.MEDIUM,
                gl_detail_id="GL001",
                journal_id="JE001",
                message="msg2",
                score_impact=10.0,
            ),
            RuleViolation(
                rule_id="AMT-001",
                rule_name="高額",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.HIGH,
                gl_detail_id="GL002",
                journal_id="JE002",
                message="msg3",
                score_impact=15.0,
            ),
        ]
        scores = service.score_violations(violations)
        assert len(scores) == 2
        assert scores["GL001"].violation_count == 2
        assert scores["GL002"].violation_count == 1
        # GL001: amount(15) + account(10) = 25, requires_review = False (< 60)
        assert scores["GL001"].requires_review is False

    def test_score_violations_requires_review(self):
        service = self._make_service()
        violations = [
            RuleViolation(
                rule_id=f"R-{i}",
                rule_name="r",
                category=RuleCategory.APPROVAL,
                severity=RuleSeverity.CRITICAL,
                gl_detail_id="GL001",
                journal_id="JE001",
                message="m",
                score_impact=25.0,
            )
            for i in range(3)
        ]
        scores = service.score_violations(violations)
        # 25 * 1.5(approval weight) * 3 = 112.5 -> capped at 100
        assert scores["GL001"].total_score == 100.0
        assert scores["GL001"].requires_review is True

    def test_score_violations_severity_escalation(self):
        service = self._make_service()
        violations = [
            RuleViolation(
                rule_id="R-1",
                rule_name="r",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.LOW,
                gl_detail_id="A",
                journal_id="J",
                message="m",
                score_impact=5.0,
            ),
            RuleViolation(
                rule_id="R-2",
                rule_name="r",
                category=RuleCategory.AMOUNT,
                severity=RuleSeverity.CRITICAL,
                gl_detail_id="A",
                journal_id="J",
                message="m",
                score_impact=25.0,
            ),
        ]
        scores = service.score_violations(violations)
        assert scores["A"].severity_level == "critical"

    def test_update_database_scores_empty(self):
        service = self._make_service()
        assert service.update_database_scores({}) == 0

    def test_get_high_risk_entries(self):
        service = self._make_service()
        service.db.execute_df.return_value = pl.DataFrame({"id": [1, 2]})
        df = service.get_high_risk_entries(threshold=60.0, limit=50)
        assert len(df) == 2

    def test_get_risk_distribution(self):
        service = self._make_service()
        service.db.execute.return_value = [
            ("critical", 5),
            ("high", 10),
            ("medium", 20),
        ]
        dist = service.get_risk_distribution()
        assert dist["critical"] == 5
        assert dist["high"] == 10

    def test_get_scoring_summary(self):
        service = self._make_service()
        service.db.execute.return_value = [
            (1000, 50, 5, 10, 15, 35.5, 95.0),
        ]
        summary = service.get_scoring_summary(fiscal_year=2024)
        assert summary["total_entries"] == 1000
        assert summary["flagged_entries"] == 50
        assert summary["critical_count"] == 5
        assert summary["max_risk_score"] == 95.0

    def test_get_scoring_summary_empty(self):
        service = self._make_service()
        service.db.execute.return_value = []
        summary = service.get_scoring_summary()
        assert summary == {}


class TestRiskPrioritizer:
    """RiskPrioritizer のテスト"""

    def test_get_review_queue(self):
        from app.services.rules.scoring import RiskPrioritizer
        mock_db = MagicMock()
        mock_db.execute_df.return_value = pl.DataFrame({"id": [1, 2, 3]})
        prioritizer = RiskPrioritizer(db=mock_db)
        df = prioritizer.get_review_queue(max_entries=10, fiscal_year=2024)
        assert len(df) == 3

    def test_get_sample_by_risk_level_default(self):
        from app.services.rules.scoring import RiskPrioritizer
        mock_db = MagicMock()
        mock_db.execute_df.return_value = pl.DataFrame({"id": [1]})
        prioritizer = RiskPrioritizer(db=mock_db)
        df = prioritizer.get_sample_by_risk_level()
        # 4カテゴリ * 1行 = 4行
        assert len(df) == 4

    def test_get_sample_by_risk_level_custom(self):
        from app.services.rules.scoring import RiskPrioritizer
        mock_db = MagicMock()
        mock_db.execute_df.return_value = pl.DataFrame({"id": [1, 2]})
        prioritizer = RiskPrioritizer(db=mock_db)
        df = prioritizer.get_sample_by_risk_level({"critical": 10, "high": 5})
        # 2カテゴリ * 2行 = 4行
        assert len(df) == 4
