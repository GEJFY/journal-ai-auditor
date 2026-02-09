"""Audit rule engine package.

This package provides:
- Base rule classes and interfaces
- Rule execution engine
- Specific rule implementations (Amount, Time, Account, Approval)
- ML-based anomaly detection
- Benford's Law analysis
- Integrated risk scoring

Rule categories (58 total rules):
- Amount rules (15): AMT-001 to AMT-015
- Time rules (10): TIM-001 to TIM-010
- Account rules (20): ACC-001 to ACC-020
- Approval rules (8): APR-001 to APR-008
- ML detection (5): ML-001 to ML-005
- Benford analysis (5): BEN-001 to BEN-005
"""

from app.services.rules.account_rules import create_account_rule_set
from app.services.rules.amount_rules import create_amount_rule_set
from app.services.rules.approval_rules import create_approval_rule_set
from app.services.rules.base import (
    AuditRule,
    RuleCategory,
    RuleResult,
    RuleSet,
    RuleSeverity,
    RuleViolation,
)
from app.services.rules.benford import BenfordAnalyzer, create_benford_rule_set
from app.services.rules.ml_detection import create_ml_rule_set
from app.services.rules.rule_engine import EngineResult, RuleEngine
from app.services.rules.scoring import RiskScore, RiskScoringService, ScoringConfig
from app.services.rules.time_rules import create_time_rule_set

__all__ = [
    # Base classes
    "AuditRule",
    "RuleResult",
    "RuleSeverity",
    "RuleCategory",
    "RuleViolation",
    "RuleSet",
    # Engine
    "RuleEngine",
    "EngineResult",
    # Rule set factories
    "create_amount_rule_set",
    "create_time_rule_set",
    "create_account_rule_set",
    "create_approval_rule_set",
    "create_ml_rule_set",
    "create_benford_rule_set",
    # Benford
    "BenfordAnalyzer",
    # Scoring
    "RiskScoringService",
    "RiskScore",
    "ScoringConfig",
]
