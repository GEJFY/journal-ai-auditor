"""Database layer unit tests using temporary DuckDB."""

import tempfile
from pathlib import Path

import pytest

from app.db.duckdb import DuckDBManager


@pytest.fixture
def temp_db():
    """Create a temporary DuckDB instance for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.duckdb"
        db = DuckDBManager(db_path=db_path)
        yield db


class TestDuckDBManager:
    """Test DuckDB manager operations."""

    def test_initialize_schema(self, temp_db):
        temp_db.initialize_schema()
        assert temp_db.table_exists("journal_entries")
        assert temp_db.table_exists("audit_rules")
        assert temp_db.table_exists("audit_findings")

    def test_table_not_exists(self, temp_db):
        assert temp_db.table_exists("nonexistent_table") is False

    def test_execute_simple_query(self, temp_db):
        result = temp_db.execute("SELECT 1 AS val")
        assert result[0][0] == 1

    def test_insert_and_query(self, temp_db):
        temp_db.initialize_schema()
        temp_db.execute(
            """INSERT INTO audit_findings
               (finding_id, workflow_id, agent_type, fiscal_year, finding_title)
               VALUES (?, ?, ?, ?, ?)""",
            ["AF-TEST001", "WF-001", "analysis", 2025, "テスト発見事項"],
        )
        result = temp_db.execute(
            "SELECT finding_title FROM audit_findings WHERE finding_id = ?",
            ["AF-TEST001"],
        )
        assert result[0][0] == "テスト発見事項"

    def test_get_table_count(self, temp_db):
        temp_db.initialize_schema()
        count = temp_db.get_table_count("audit_findings")
        assert count == 0

        # Insert and check again
        temp_db.execute(
            """INSERT INTO audit_findings
               (finding_id, workflow_id, agent_type, fiscal_year, finding_title)
               VALUES (?, ?, ?, ?, ?)""",
            ["AF-TEST002", "WF-002", "review", 2025, "テスト2"],
        )
        count = temp_db.get_table_count("audit_findings")
        assert count == 1

    def test_execute_df(self, temp_db):
        temp_db.initialize_schema()
        temp_db.execute(
            """INSERT INTO audit_findings
               (finding_id, workflow_id, agent_type, fiscal_year,
                finding_title, severity)
               VALUES
               ('AF-001', 'WF-001', 'analysis', 2025, '発見1', 'HIGH'),
               ('AF-002', 'WF-001', 'analysis', 2025, '発見2', 'MEDIUM')""",
        )
        df = temp_db.execute_df(
            "SELECT * FROM audit_findings WHERE severity = 'HIGH'"
        )
        assert len(df) == 1
        assert df["finding_id"][0] == "AF-001"

    def test_insert_df(self, temp_db):
        import polars as pl

        temp_db.initialize_schema()
        df = pl.DataFrame({
            "finding_id": ["AF-DF1", "AF-DF2"],
            "workflow_id": ["WF-DF", "WF-DF"],
            "agent_type": ["analysis", "review"],
            "fiscal_year": [2025, 2025],
            "finding_title": ["DF発見1", "DF発見2"],
            "finding_description": [None, "説明"],
            "severity": ["HIGH", "LOW"],
            "category": [None, None],
            "affected_amount": [0.0, 1000.0],
            "affected_count": [0, 5],
            "evidence": [None, None],
            "recommendation": [None, None],
            "status": ["open", "open"],
            "reviewed_by": [None, None],
            "reviewed_at": [None, None],
            "created_at": [None, None],
        })
        rows = temp_db.insert_df("audit_findings", df)
        assert rows == 2
        assert temp_db.get_table_count("audit_findings") == 2

    def test_schema_has_journal_entries_columns(self, temp_db):
        temp_db.initialize_schema()
        result = temp_db.execute(
            """SELECT column_name FROM information_schema.columns
               WHERE table_name = 'journal_entries'
               ORDER BY ordinal_position"""
        )
        columns = [r[0] for r in result]
        assert "gl_detail_id" in columns
        assert "fiscal_year" in columns
        assert "amount" in columns
        assert "risk_score" in columns

    def test_schema_has_audit_rules(self, temp_db):
        temp_db.initialize_schema()
        # audit_rules should be populated with default rules
        assert temp_db.table_exists("audit_rules")

    def test_connect_context_manager(self, temp_db):
        with temp_db.connect() as conn:
            result = conn.execute("SELECT 42 AS answer").fetchone()
            assert result[0] == 42
