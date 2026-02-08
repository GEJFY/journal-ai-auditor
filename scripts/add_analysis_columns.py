"""Add analysis columns to journal_entries table."""

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
    """Add analysis columns."""
    db = DuckDBManager()

    print("Adding analysis columns to journal_entries table...")

    alter_statements = [
        "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS risk_score DECIMAL(5, 2) DEFAULT 0",
        "ALTER TABLE journal_entries ADD COLUMN IF NOT EXISTS rule_violations VARCHAR(200)",
    ]

    with db.connect() as conn:
        for stmt in alter_statements:
            try:
                conn.execute(stmt)
                print(f"  Executed: {stmt[:60]}...")
            except Exception as e:
                print(f"  Skipped (already exists or error): {e}")

    # Verify columns
    with db.connect() as conn:
        result = conn.execute("DESCRIBE journal_entries").fetchall()
        print("\nTable columns:")
        for row in result:
            print(f"  {row[0]}: {row[1]}")

    print("\nDone!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
