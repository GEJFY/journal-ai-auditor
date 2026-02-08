"""Run batch processing and store violations."""

import os
import sys
from pathlib import Path

# Set up paths
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"
os.chdir(backend_dir)
sys.path.insert(0, str(backend_dir))

from app.services.batch import BatchOrchestrator, BatchConfig, BatchMode


def main():
    """Run batch processing with violation storage."""
    print("Running batch processing with violation storage...")

    config = BatchConfig(
        mode=BatchMode.RULES_ONLY,
        fiscal_year=2024,
        store_violations=True,
        update_risk_scores=True,
        update_aggregations=False,
    )

    orchestrator = BatchOrchestrator()
    result = orchestrator.execute(config)

    print(f"\nBatch completed:")
    print(f"  Success: {result.success}")
    print(f"  Total entries: {result.total_entries:,}")
    print(f"  Rules executed: {result.rules_executed}")
    print(f"  Rules failed: {result.rules_failed}")
    print(f"  Total violations: {result.total_violations:,}")
    print(f"  Execution time: {result.execution_time_ms/1000:.2f}s")

    print(f"\n  Violations by severity:")
    for sev, count in result.violations_by_severity.items():
        print(f"    {sev}: {count:,}")

    print(f"\n  Violations by category:")
    for cat, count in result.violations_by_category.items():
        print(f"    {cat}: {count:,}")

    if result.errors:
        print(f"\n  Errors:")
        for err in result.errors:
            print(f"    {err}")

    print(f"\n  Phase timings:")
    for phase, ms in result.phase_timings.items():
        print(f"    {phase}: {ms/1000:.2f}s")

    # Verify violations stored
    from app.db import DuckDBManager
    db = DuckDBManager()
    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM rule_violations").fetchone()[0]
        print(f"\nViolations in database: {count:,}")

        # Sample violations
        sample = conn.execute("""
            SELECT rule_id, rule_name, severity, COUNT(*) as cnt
            FROM rule_violations
            GROUP BY rule_id, rule_name, severity
            ORDER BY cnt DESC
            LIMIT 10
        """).fetchall()

        print(f"\nTop 10 rules by violation count:")
        for row in sample:
            print(f"  {row[0]} ({row[2]}): {row[3]:,}")

    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
