"""Insert sample violations directly for testing reports."""

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
    """Insert sample violations."""
    db = DuckDBManager()

    print("Inserting sample violations...")

    # Get sample journal entries
    with db.connect() as conn:
        # Get some journal entries to create violations for
        sample_entries = conn.execute("""
            SELECT gl_detail_id, journal_id, amount, prepared_by, approved_by
            FROM journal_entries
            LIMIT 1000
        """).fetchall()

        print(f"  Found {len(sample_entries)} sample entries")

        # Create sample violations
        violations = []

        # Self-approval violations (where prepared_by = approved_by)
        self_approvals = conn.execute("""
            SELECT gl_detail_id, journal_id
            FROM journal_entries
            WHERE prepared_by = approved_by
            AND prepared_by IS NOT NULL
            LIMIT 500
        """).fetchall()

        for gl_id, je_id in self_approvals:
            violations.append({
                "gl_detail_id": gl_id,
                "journal_id": je_id,
                "rule_id": "APPROVAL_001",
                "rule_name": "自己承認",
                "category": "approval",
                "severity": "high",
                "message": "起票者と承認者が同一人物です",
                "violation_description": "起票者と承認者が同一人物です",
            })

        print(f"  Self-approval violations: {len(self_approvals)}")

        # High amount violations (amount > 1,000,000)
        high_amounts = conn.execute("""
            SELECT gl_detail_id, journal_id, amount
            FROM journal_entries
            WHERE ABS(amount) >= 1000000
            LIMIT 500
        """).fetchall()

        for gl_id, je_id, amount in high_amounts:
            violations.append({
                "gl_detail_id": gl_id,
                "journal_id": je_id,
                "rule_id": "AMOUNT_005",
                "rule_name": "高額仕訳",
                "category": "amount",
                "severity": "medium",
                "message": f"高額仕訳: {amount:,.0f}円",
                "violation_description": f"高額仕訳: {amount:,.0f}円",
            })

        print(f"  High amount violations: {len(high_amounts)}")

        # Round amount violations
        round_amounts = conn.execute("""
            SELECT gl_detail_id, journal_id, amount
            FROM journal_entries
            WHERE ABS(amount) >= 100000
            AND MOD(CAST(ABS(amount) AS INTEGER), 10000) = 0
            LIMIT 500
        """).fetchall()

        for gl_id, je_id, amount in round_amounts:
            violations.append({
                "gl_detail_id": gl_id,
                "journal_id": je_id,
                "rule_id": "AMOUNT_002",
                "rule_name": "丸め金額",
                "category": "amount",
                "severity": "low",
                "message": f"端数のない金額: {amount:,.0f}円",
                "violation_description": f"端数のない金額: {amount:,.0f}円",
            })

        print(f"  Round amount violations: {len(round_amounts)}")

        # Insert violations
        print(f"\n  Inserting {len(violations)} violations...")

        for v in violations:
            conn.execute("""
                INSERT INTO rule_violations
                    (gl_detail_id, journal_id, rule_id, rule_name, category, severity,
                     message, violation_description)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, [
                v["gl_detail_id"],
                v["journal_id"],
                v["rule_id"],
                v["rule_name"],
                v["category"],
                v["severity"],
                v["message"],
                v["violation_description"],
            ])

        # Verify count
        count = conn.execute("SELECT COUNT(*) FROM rule_violations").fetchone()[0]
        print(f"\nTotal violations in database: {count:,}")

        # Update journal_entries risk_score for entries with violations
        conn.execute("""
            UPDATE journal_entries
            SET risk_score = LEAST(100, (
                SELECT COUNT(*) * 10 FROM rule_violations rv
                WHERE rv.gl_detail_id = journal_entries.gl_detail_id
            ))
            WHERE gl_detail_id IN (SELECT DISTINCT gl_detail_id FROM rule_violations)
        """)

        high_risk = conn.execute("""
            SELECT COUNT(*) FROM journal_entries WHERE risk_score >= 60
        """).fetchone()[0]
        print(f"High risk entries (score >= 60): {high_risk:,}")

    print("\nSample violations inserted successfully!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
