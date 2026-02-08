"""Initialize full database schema including rule_violations table."""

import os
import sys
from pathlib import Path

# Set up paths
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from app.db import DuckDBManager
from app.core.config import settings


def main():
    """Initialize full schema."""
    print("Initializing full database schema...")
    print(f"Database path: {settings.duckdb_path.absolute()}")

    db = DuckDBManager()

    # Create rule_violations table
    rule_violations_sql = """
    CREATE TABLE IF NOT EXISTS rule_violations (
        violation_id INTEGER PRIMARY KEY,
        gl_detail_id VARCHAR NOT NULL,
        journal_id VARCHAR,
        rule_id VARCHAR(50) NOT NULL,
        rule_name VARCHAR(200),
        category VARCHAR(50),
        severity VARCHAR(20) NOT NULL,
        message VARCHAR(500),
        violation_description VARCHAR(1000),
        details VARCHAR,
        score_impact DECIMAL(5, 2) DEFAULT 0,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );

    CREATE INDEX IF NOT EXISTS idx_rv_gl_detail ON rule_violations(gl_detail_id);
    CREATE INDEX IF NOT EXISTS idx_rv_rule ON rule_violations(rule_id);
    CREATE INDEX IF NOT EXISTS idx_rv_severity ON rule_violations(severity);
    CREATE INDEX IF NOT EXISTS idx_rv_category ON rule_violations(category);
    """

    # Add missing columns to journal_entries if they don't exist
    je_columns_sql = """
    ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS risk_score DECIMAL(5, 2) DEFAULT 0;
    ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS anomaly_flags VARCHAR(100);
    ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS rule_violations VARCHAR(200);
    """

    with db.connect() as conn:
        # Create rule_violations table
        print("Creating rule_violations table...")
        for stmt in rule_violations_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception as e:
                    print(f"  Warning: {e}")

        # Add missing columns
        print("Adding missing columns to journal_entries...")
        for stmt in je_columns_sql.split(";"):
            stmt = stmt.strip()
            if stmt:
                try:
                    conn.execute(stmt)
                except Exception as e:
                    print(f"  Warning: {e}")

        # Verify tables
        print("\nVerifying tables...")
        tables = conn.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'main'
        """).fetchall()
        print(f"  Tables: {[t[0] for t in tables]}")

        # Check rule_violations columns
        rv_cols = conn.execute("DESCRIBE rule_violations").fetchall()
        print(f"\nrule_violations columns:")
        for col in rv_cols:
            print(f"  {col[0]}: {col[1]}")

    print("\nSchema initialization complete!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
