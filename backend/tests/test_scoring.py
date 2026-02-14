"""リスクスコアリングサービスのユニットテスト"""

from unittest.mock import MagicMock

from app.services.rules.base import RuleCategory, RuleSeverity, RuleViolation
from app.services.rules.scoring import RiskScore, RiskScoringService, ScoringConfig

# ============================================================
# RiskScore データクラステスト
# ============================================================


class TestRiskScore:
    """RiskScoreデータクラスのテスト"""

    def test_default_values(self):
        score = RiskScore(gl_detail_id="JE001-001", journal_id="JE001")
        assert score.total_score == 0.0
        assert score.rule_score == 0.0
        assert score.ml_score == 0.0
        assert score.benford_score == 0.0
        assert score.violation_count == 0
        assert score.severity_level == "minimal"
        assert score.requires_review is False

    def test_risk_category_critical(self):
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=85.0
        )
        assert score.risk_category == "critical"

    def test_risk_category_high(self):
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=65.0
        )
        assert score.risk_category == "high"

    def test_risk_category_medium(self):
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=45.0
        )
        assert score.risk_category == "medium"

    def test_risk_category_low(self):
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=25.0
        )
        assert score.risk_category == "low"

    def test_risk_category_minimal(self):
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=10.0
        )
        assert score.risk_category == "minimal"

    def test_to_dict(self):
        score = RiskScore(
            gl_detail_id="JE001-001",
            journal_id="JE001",
            total_score=75.5,
            rule_score=50.0,
            ml_score=15.0,
            benford_score=10.5,
            violation_count=3,
            violations=["RULE001", "RULE002", "ML001"],
            severity_level="high",
            requires_review=True,
        )
        d = score.to_dict()
        assert d["gl_detail_id"] == "JE001-001"
        assert d["total_score"] == 75.5
        assert d["risk_category"] == "high"
        assert d["requires_review"] is True
        assert len(d["violations"]) == 3

    def test_risk_category_boundary_80(self):
        """80点はcritical"""
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=80.0
        )
        assert score.risk_category == "critical"

    def test_risk_category_boundary_60(self):
        """60点はhigh"""
        score = RiskScore(
            gl_detail_id="JE001-001", journal_id="JE001", total_score=60.0
        )
        assert score.risk_category == "high"

    def test_risk_category_boundary_zero(self):
        """0点はminimal"""
        score = RiskScore(gl_detail_id="JE001-001", journal_id="JE001", total_score=0.0)
        assert score.risk_category == "minimal"


# ============================================================
# ScoringConfig テスト
# ============================================================


class TestScoringConfig:
    """スコアリング設定のテスト"""

    def test_default_severity_weights(self):
        config = ScoringConfig()
        assert config.severity_weights["critical"] == 25.0
        assert config.severity_weights["high"] == 15.0
        assert config.severity_weights["medium"] == 10.0
        assert config.severity_weights["low"] == 5.0
        assert config.severity_weights["info"] == 0.0

    def test_default_category_weights(self):
        config = ScoringConfig()
        assert config.category_weights["approval"] == 1.5  # 承認違反は重い
        assert config.category_weights["ml"] == 1.2

    def test_default_thresholds(self):
        config = ScoringConfig()
        assert config.max_score == 100.0
        assert config.auto_review_threshold == 60.0
        assert config.critical_threshold == 80.0

    def test_custom_config(self):
        config = ScoringConfig(
            max_score=200.0,
            auto_review_threshold=80.0,
            ml_weight=2.0,
        )
        assert config.max_score == 200.0
        assert config.auto_review_threshold == 80.0
        assert config.ml_weight == 2.0


# ============================================================
# RiskScoringService テスト
# ============================================================


def _make_violation(
    rule_id: str = "RULE001",
    gl_detail_id: str = "JE001-001",
    journal_id: str = "JE001",
    severity: RuleSeverity = RuleSeverity.MEDIUM,
    category: RuleCategory = RuleCategory.AMOUNT,
    score_impact: float = 0.0,
) -> RuleViolation:
    """テスト用のRuleViolationを生成"""
    return RuleViolation(
        rule_id=rule_id,
        rule_name=f"Test Rule {rule_id}",
        gl_detail_id=gl_detail_id,
        journal_id=journal_id,
        severity=severity,
        category=category,
        message="Test violation",
        score_impact=score_impact,
    )


class TestRiskScoringService:
    """リスクスコアリングサービスのテスト"""

    def test_calculate_score_no_violations(self):
        service = RiskScoringService(db=MagicMock())
        score = service.calculate_score([])
        assert score == 0.0

    def test_calculate_score_single_medium(self):
        service = RiskScoringService(db=MagicMock())
        violations = [_make_violation(severity=RuleSeverity.MEDIUM)]
        score = service.calculate_score(violations)
        # medium = 10.0, amount weight = 1.0
        assert score == 10.0

    def test_calculate_score_single_critical(self):
        service = RiskScoringService(db=MagicMock())
        violations = [_make_violation(severity=RuleSeverity.CRITICAL)]
        score = service.calculate_score(violations)
        # critical = 25.0, amount weight = 1.0
        assert score == 25.0

    def test_calculate_score_approval_weight(self):
        """承認カテゴリは1.5倍"""
        service = RiskScoringService(db=MagicMock())
        violations = [
            _make_violation(severity=RuleSeverity.HIGH, category=RuleCategory.APPROVAL)
        ]
        score = service.calculate_score(violations)
        # high = 15.0, approval weight = 1.5
        assert score == 22.5

    def test_calculate_score_capped_at_100(self):
        """スコアは100を超えない"""
        service = RiskScoringService(db=MagicMock())
        violations = [
            _make_violation(severity=RuleSeverity.CRITICAL) for _ in range(10)
        ]
        score = service.calculate_score(violations)
        assert score == 100.0

    def test_calculate_score_with_ml_score(self):
        """MLスコアの加算"""
        service = RiskScoringService(db=MagicMock())
        score = service.calculate_score([], ml_score=0.5)
        # ml_score * 20.0 * 1.0 = 10.0
        assert score == 10.0

    def test_calculate_score_with_benford_risk(self):
        """ベンフォードリスクの加算"""
        service = RiskScoringService(db=MagicMock())
        score = service.calculate_score([], benford_risk=0.8)
        # benford * 10.0 * 0.5 = 4.0
        assert score == 4.0

    def test_calculate_score_custom_score_impact(self):
        """カスタムscore_impactが使用される"""
        service = RiskScoringService(db=MagicMock())
        violations = [_make_violation(score_impact=30.0)]
        score = service.calculate_score(violations)
        # score_impact 30.0 * amount weight 1.0 = 30.0
        assert score == 30.0

    def test_score_violations_groups_by_entry(self):
        """エントリごとにグループ化"""
        service = RiskScoringService(db=MagicMock())
        violations = [
            _make_violation(gl_detail_id="A", journal_id="J1"),
            _make_violation(rule_id="RULE002", gl_detail_id="A", journal_id="J1"),
            _make_violation(gl_detail_id="B", journal_id="J2"),
        ]
        scores = service.score_violations(violations)
        assert "A" in scores
        assert "B" in scores
        assert scores["A"].violation_count == 2
        assert scores["B"].violation_count == 1

    def test_score_violations_requires_review(self):
        """60点以上でレビュー必要"""
        service = RiskScoringService(db=MagicMock())
        # critical (25) x 3 = 75 > 60
        violations = [
            _make_violation(
                rule_id=f"R{i}",
                severity=RuleSeverity.CRITICAL,
            )
            for i in range(3)
        ]
        scores = service.score_violations(violations)
        assert scores["JE001-001"].requires_review is True

    def test_score_violations_severity_escalation(self):
        """最も重い重要度が設定される"""
        service = RiskScoringService(db=MagicMock())
        violations = [
            _make_violation(rule_id="R1", severity=RuleSeverity.LOW),
            _make_violation(rule_id="R2", severity=RuleSeverity.CRITICAL),
        ]
        scores = service.score_violations(violations)
        assert scores["JE001-001"].severity_level == "critical"
