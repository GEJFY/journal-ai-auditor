"""Recreate rule_violations table with auto-increment."""

import os
import sys
from pathlib import Path

# Set up paths
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from app.db import DuckDBManager


def main():
    """Recreate rule_violations table."""
    db = DuckDBManager()

    print("Recreating rule_violations table...")

    with db.connect() as conn:
        # Drop existing table
        conn.execute("DROP TABLE IF EXISTS rule_violations")

        # Create sequence
        conn.execute("CREATE SEQUENCE IF NOT EXISTS seq_violation_id START 1")

        # Create table with auto-increment
        conn.execute("""
            CREATE TABLE rule_violations (
                violation_id INTEGER DEFAULT nextval('seq_violation_id'),
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
            )
        """)

        # Create indexes
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rv_gl_detail ON rule_violations(gl_detail_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rv_rule ON rule_violations(rule_id)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rv_severity ON rule_violations(severity)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_rv_category ON rule_violations(category)")

        # Verify
        cols = conn.execute("DESCRIBE rule_violations").fetchall()
        print("Table columns:")
        for col in cols:
            print(f"  {col[0]}: {col[1]}")

    print("\nTable recreated successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
