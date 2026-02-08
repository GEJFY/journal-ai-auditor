"""Load sample data directly into database."""

import os
import sys
from pathlib import Path

# Set up paths
project_root = Path(__file__).parent.parent
backend_dir = project_root / "backend"

# Change to backend directory so relative paths work correctly
os.chdir(backend_dir)

# Add backend to path
sys.path.insert(0, str(backend_dir))

import polars as pl
from app.db import DuckDBManager
from app.core.config import settings

def main():
    """Load sample data."""
    sample_file = project_root / "sample_data" / "10_journal_entries.csv"

    if not sample_file.exists():
        print(f"Error: Sample file not found: {sample_file}")
        return 1

    print(f"Loading sample data from: {sample_file}")
    print(f"Database path: {settings.duckdb_path.absolute()}")

    # Ensure data directory exists
    settings.ensure_data_dir()

    # Initialize database
    db = DuckDBManager()
    print("Initializing database schema...")

    # Create journal_entries table manually
    create_table_sql = """
    CREATE TABLE IF NOT EXISTS journal_entries (
        gl_detail_id VARCHAR,
        business_unit_code VARCHAR(20),
        fiscal_year INTEGER,
        accounting_period INTEGER,
        journal_id VARCHAR(50),
        journal_id_line_number INTEGER,
        effective_date DATE,
        entry_date DATE,
        entry_time TIME,
        gl_account_number VARCHAR(20),
        amount DECIMAL(18, 2),
        amount_currency VARCHAR(3),
        functional_amount DECIMAL(18, 2),
        debit_credit_indicator VARCHAR(1),
        je_line_description VARCHAR(500),
        source VARCHAR(50),
        vendor_code VARCHAR(50),
        dept_code VARCHAR(50),
        prepared_by VARCHAR(50),
        approved_by VARCHAR(50),
        approved_date DATE,
        last_modified_by VARCHAR(50),
        last_modified_date TIMESTAMP,
        fraud_flag VARCHAR(10),
        anomaly_flag VARCHAR(10)
    );
    """
    with db.connect() as conn:
        conn.execute(create_table_sql)
        print("  Table journal_entries created/verified")

    # Check if data already exists
    if db.table_exists("journal_entries"):
        count = db.get_table_count("journal_entries")
        if count > 0:
            print(f"Data already loaded: {count} rows in journal_entries")
            return 0

    # Insert data using DuckDB native CSV import for better performance
    print("Inserting data into DuckDB...")
    csv_path = str(sample_file).replace("\\", "/")
    with db.connect() as conn:
        # Use DuckDB's native CSV reader for better performance
        conn.execute(f"""
            INSERT INTO journal_entries
            SELECT * FROM read_csv_auto('{csv_path}')
        """)

        # Verify count
        result = conn.execute("SELECT COUNT(*) FROM journal_entries").fetchone()
        count = result[0]

    print(f"Successfully imported {count} rows!")
    print(f"Database file size: {settings.duckdb_path.stat().st_size / (1024*1024):.2f} MB")

    return 0


if __name__ == "__main__":
    sys.exit(main())
