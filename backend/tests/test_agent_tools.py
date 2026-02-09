"""Agent tools unit tests.

Tests for all LangChain tool functions used by agents.
Uses a temporary DuckDB database with test data.
"""

import json
from unittest.mock import patch

import pytest

from app.db.duckdb import DuckDBManager


@pytest.fixture
def temp_db(tmp_path):
    """Create a temporary DuckDB with test schema and data."""
    db_path = tmp_path / "test_tools.duckdb"
    db = DuckDBManager(db_path=db_path)

    with db.connect() as conn:
        # journal_entries テーブル作成
        conn.execute("""
            CREATE TABLE journal_entries (
                gl_detail_id VARCHAR PRIMARY KEY,
                journal_id VARCHAR,
                fiscal_year INTEGER,
                accounting_period INTEGER,
                effective_date DATE,
                gl_account_number VARCHAR,
                amount DOUBLE,
                debit_credit_indicator VARCHAR,
                je_line_description VARCHAR,
                prepared_by VARCHAR,
                approved_by VARCHAR,
                risk_score DOUBLE,
                anomaly_flags VARCHAR,
                rule_violations VARCHAR
            )
        """)

        # rule_violations テーブル作成
        conn.execute("""
            CREATE TABLE rule_violations (
                violation_id VARCHAR PRIMARY KEY,
                gl_detail_id VARCHAR,
                rule_id VARCHAR,
                severity VARCHAR,
                message VARCHAR
            )
        """)

        # audit_findings テーブル作成
        conn.execute("""
            CREATE TABLE audit_findings (
                finding_id VARCHAR PRIMARY KEY,
                workflow_id VARCHAR,
                agent_type VARCHAR,
                fiscal_year INTEGER,
                finding_title VARCHAR,
                finding_description VARCHAR,
                severity VARCHAR DEFAULT 'MEDIUM',
                category VARCHAR DEFAULT '',
                affected_amount DOUBLE DEFAULT 0,
                affected_count INTEGER DEFAULT 0,
                recommendation VARCHAR DEFAULT '',
                status VARCHAR DEFAULT 'open',
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # テストデータ挿入
        conn.execute("""
            INSERT INTO journal_entries VALUES
            ('JE001', 'J001', 2024, 1, '2024-01-15', '1000', 1000000, 'D',
             '期末調整仕訳', 'user1', 'user2', 85.0, 'HIGH:round_amount', 'R001'),
            ('JE002', 'J001', 2024, 1, '2024-01-15', '2000', -1000000, 'C',
             '期末調整仕訳', 'user1', 'user2', 85.0, 'HIGH:round_amount', 'R001'),
            ('JE003', 'J002', 2024, 3, '2024-03-28', '5100', 50000, 'D',
             '交際費精算', 'user3', 'user3', 72.0, 'MEDIUM:self_approval', 'R002'),
            ('JE004', 'J003', 2024, 6, '2024-06-30', '1000', 200000, 'D',
             '通常仕訳', 'user2', 'user1', 25.0, NULL, NULL),
            ('JE005', 'J004', 2024, 12, '2024-12-31', '3000', 5000000, 'D',
             '決算仕訳 棚卸資産評価損', 'user1', 'user2', 92.0, 'CRITICAL:year_end', 'R003'),
            ('JE006', 'J005', 2023, 6, '2023-06-15', '1000', 100000, 'D',
             '通常仕訳', 'user2', 'user1', 15.0, NULL, NULL)
        """)

        conn.execute("""
            INSERT INTO rule_violations VALUES
            ('V001', 'JE001', 'R001', 'high', '高額ラウンド金額'),
            ('V002', 'JE003', 'R002', 'medium', '自己承認'),
            ('V003', 'JE005', 'R003', 'critical', '期末異常取引')
        """)

    return db


@pytest.fixture
def mock_db(temp_db):
    """Patch the tools module to use temp DB."""
    with patch("app.agents.tools._db", temp_db), \
         patch("app.agents.tools.get_db", return_value=temp_db):
        yield temp_db


class TestQueryJournalEntries:
    """query_journal_entries ツールのテスト."""

    def test_no_filters(self, mock_db):
        """フィルタなしで全件取得."""
        from app.agents.tools import query_journal_entries

        result = query_journal_entries.invoke({})
        data = json.loads(result)
        assert len(data) >= 5  # 2024年のデータ + 2023年

    def test_filter_by_account(self, mock_db):
        """勘定科目番号でフィルタ."""
        from app.agents.tools import query_journal_entries

        result = query_journal_entries.invoke({"gl_account_number": "1000"})
        data = json.loads(result)
        assert len(data) >= 2
        for entry in data:
            assert entry["gl_account_number"].startswith("1000")

    def test_filter_by_fiscal_year(self, mock_db):
        """会計年度でフィルタ."""
        from app.agents.tools import query_journal_entries

        result = query_journal_entries.invoke({"fiscal_year": 2024})
        data = json.loads(result)
        assert len(data) == 5
        for entry in data:
            assert entry["fiscal_year"] == 2024

    def test_filter_by_amount(self, mock_db):
        """金額範囲でフィルタ."""
        from app.agents.tools import query_journal_entries

        result = query_journal_entries.invoke({"min_amount": 100000})
        data = json.loads(result)
        assert all(abs(e["amount"]) >= 100000 for e in data)

    def test_filter_by_risk_score(self, mock_db):
        """リスクスコアでフィルタ."""
        from app.agents.tools import query_journal_entries

        result = query_journal_entries.invoke({"min_risk_score": 70.0})
        data = json.loads(result)
        assert all(e["risk_score"] >= 70.0 for e in data)

    def test_limit(self, mock_db):
        """件数制限."""
        from app.agents.tools import query_journal_entries

        result = query_journal_entries.invoke({"limit": 2})
        data = json.loads(result)
        assert len(data) <= 2


class TestGetHighRiskEntries:
    """get_high_risk_entries ツールのテスト."""

    def test_default_threshold(self, mock_db):
        """デフォルト閾値（60）でフィルタ."""
        from app.agents.tools import get_high_risk_entries

        result = get_high_risk_entries.invoke({})
        data = json.loads(result)
        assert len(data) >= 3  # JE001, JE003, JE005
        assert all(e["risk_score"] >= 60.0 for e in data)

    def test_custom_threshold(self, mock_db):
        """カスタム閾値でフィルタ."""
        from app.agents.tools import get_high_risk_entries

        result = get_high_risk_entries.invoke({"risk_threshold": 80.0})
        data = json.loads(result)
        assert len(data) >= 2  # JE001, JE005
        assert all(e["risk_score"] >= 80.0 for e in data)

    def test_with_fiscal_year(self, mock_db):
        """会計年度指定."""
        from app.agents.tools import get_high_risk_entries

        result = get_high_risk_entries.invoke({"fiscal_year": 2024, "risk_threshold": 80.0})
        data = json.loads(result)
        assert len(data) >= 2


class TestGetRuleViolations:
    """get_rule_violations ツールのテスト."""

    def test_all_violations(self, mock_db):
        """全違反取得."""
        from app.agents.tools import get_rule_violations

        result = get_rule_violations.invoke({})
        data = json.loads(result)
        assert len(data) >= 3

    def test_filter_by_rule_id(self, mock_db):
        """ルールIDでフィルタ."""
        from app.agents.tools import get_rule_violations

        result = get_rule_violations.invoke({"rule_id": "R001"})
        data = json.loads(result)
        assert len(data) >= 1
        assert all(e["rule_id"] == "R001" for e in data)

    def test_filter_by_severity(self, mock_db):
        """重要度でフィルタ."""
        from app.agents.tools import get_rule_violations

        result = get_rule_violations.invoke({"severity": "critical"})
        data = json.loads(result)
        assert len(data) >= 1
        assert all(e["severity"] == "critical" for e in data)


class TestGetAccountSummary:
    """get_account_summary ツールのテスト."""

    def test_account_summary(self, mock_db):
        """勘定科目サマリー取得."""
        from app.agents.tools import get_account_summary

        result = get_account_summary.invoke({"gl_account_number": "1000"})
        data = json.loads(result)
        assert len(data) >= 1
        summary = data[0]
        assert summary["entry_count"] >= 2
        assert summary["gl_account_number"] == "1000"

    def test_account_summary_with_year(self, mock_db):
        """年度指定のサマリー."""
        from app.agents.tools import get_account_summary

        result = get_account_summary.invoke({
            "gl_account_number": "1000",
            "fiscal_year": 2024,
        })
        data = json.loads(result)
        assert len(data) >= 1


class TestGetUserActivity:
    """get_user_activity ツールのテスト."""

    def test_user_activity(self, mock_db):
        """ユーザーアクティビティ取得."""
        from app.agents.tools import get_user_activity

        result = get_user_activity.invoke({"user_id": "user1"})
        data = json.loads(result)
        assert len(data) >= 1
        activity = data[0]
        assert activity["prepared_by"] == "user1"
        assert activity["entry_count"] >= 2

    def test_self_approval_detection(self, mock_db):
        """自己承認の検知."""
        from app.agents.tools import get_user_activity

        result = get_user_activity.invoke({"user_id": "user3"})
        data = json.loads(result)
        assert len(data) >= 1
        activity = data[0]
        assert activity["self_approval_count"] >= 1


class TestGetPeriodComparison:
    """get_period_comparison ツールのテスト."""

    def test_period_comparison(self, mock_db):
        """期間比較."""
        from app.agents.tools import get_period_comparison

        result = get_period_comparison.invoke({"fiscal_year": 2024})
        data = json.loads(result)
        assert len(data) >= 3  # 少なくとも3つの期間

    def test_period_comparison_with_account(self, mock_db):
        """勘定科目指定の期間比較."""
        from app.agents.tools import get_period_comparison

        result = get_period_comparison.invoke({
            "fiscal_year": 2024,
            "gl_account_number": "1000",
        })
        data = json.loads(result)
        assert len(data) >= 1


class TestSearchJournalDescription:
    """search_journal_description ツールのテスト."""

    def test_search_found(self, mock_db):
        """検索ヒット."""
        from app.agents.tools import search_journal_description

        result = search_journal_description.invoke({"search_term": "期末調整"})
        data = json.loads(result)
        assert len(data) >= 2

    def test_search_not_found(self, mock_db):
        """検索ミス."""
        from app.agents.tools import search_journal_description

        result = search_journal_description.invoke({"search_term": "存在しない文字列XYZ"})
        data = json.loads(result)
        assert len(data) == 0


class TestSaveAndGetFindings:
    """save_audit_finding / get_saved_findings ツールのテスト."""

    def test_save_finding(self, mock_db):
        """発見事項の保存."""
        from app.agents.tools import save_audit_finding

        result = save_audit_finding.invoke({
            "workflow_id": "WF001",
            "agent_type": "analysis",
            "fiscal_year": 2024,
            "finding_title": "テスト発見事項",
            "finding_description": "テスト用の詳細説明",
            "severity": "HIGH",
            "category": "financial",
            "affected_amount": 1000000.0,
            "affected_count": 5,
            "recommendation": "追加調査が必要",
        })
        data = json.loads(result)
        assert "finding_id" in data
        assert data["status"] == "saved"
        assert data["finding_id"].startswith("AF-")

    def test_get_findings(self, mock_db):
        """保存した発見事項の取得."""
        from app.agents.tools import get_saved_findings, save_audit_finding

        # まず保存
        save_audit_finding.invoke({
            "workflow_id": "WF002",
            "agent_type": "investigation",
            "fiscal_year": 2024,
            "finding_title": "取得テスト",
            "finding_description": "取得テスト用",
        })

        # 取得
        result = get_saved_findings.invoke({"fiscal_year": 2024})
        data = json.loads(result)
        assert len(data) >= 1

    def test_get_findings_filter_by_severity(self, mock_db):
        """重要度フィルタ付き取得."""
        from app.agents.tools import get_saved_findings, save_audit_finding

        save_audit_finding.invoke({
            "workflow_id": "WF003",
            "agent_type": "review",
            "fiscal_year": 2024,
            "finding_title": "重大な発見",
            "finding_description": "重大テスト",
            "severity": "CRITICAL",
        })

        result = get_saved_findings.invoke({"severity": "CRITICAL"})
        data = json.loads(result)
        assert len(data) >= 1
        assert all(e["severity"] == "CRITICAL" for e in data)


class TestToolCollections:
    """ツールコレクションの構成テスト."""

    def test_analysis_tools(self):
        """分析ツールコレクション."""
        from app.agents.tools import ANALYSIS_TOOLS

        assert len(ANALYSIS_TOOLS) >= 7
        names = [t.name for t in ANALYSIS_TOOLS]
        assert "query_journal_entries" in names
        assert "get_high_risk_entries" in names
        assert "save_audit_finding" in names

    def test_investigation_tools(self):
        """調査ツールコレクション."""
        from app.agents.tools import INVESTIGATION_TOOLS

        assert len(INVESTIGATION_TOOLS) >= 7
        names = [t.name for t in INVESTIGATION_TOOLS]
        assert "get_rule_violations" in names
        assert "get_user_activity" in names
        assert "search_journal_description" in names

    def test_documentation_tools(self):
        """文書化ツールコレクション."""
        from app.agents.tools import DOCUMENTATION_TOOLS

        assert len(DOCUMENTATION_TOOLS) >= 8
        names = [t.name for t in DOCUMENTATION_TOOLS]
        assert "get_saved_findings" in names

    def test_review_tools(self):
        """レビューツールコレクション."""
        from app.agents.tools import REVIEW_TOOLS

        assert len(REVIEW_TOOLS) >= 5
        names = [t.name for t in REVIEW_TOOLS]
        assert "get_high_risk_entries" in names
        assert "save_audit_finding" in names

    def test_qa_tools(self):
        """Q&Aツールコレクション."""
        from app.agents.tools import QA_TOOLS

        assert len(QA_TOOLS) >= 6
        names = [t.name for t in QA_TOOLS]
        assert "get_dashboard_kpi" in names
        assert "search_journal_description" in names

    def test_all_tools_are_callable(self):
        """全ツールがcallableであること."""
        from app.agents.tools import (
            ANALYSIS_TOOLS,
            DOCUMENTATION_TOOLS,
            INVESTIGATION_TOOLS,
            QA_TOOLS,
            REVIEW_TOOLS,
        )

        all_tools = set()
        for collection in [
            ANALYSIS_TOOLS, INVESTIGATION_TOOLS, QA_TOOLS,
            REVIEW_TOOLS, DOCUMENTATION_TOOLS,
        ]:
            for t in collection:
                all_tools.add(t.name)

        # 全12ツールが定義されていること
        assert len(all_tools) >= 10
