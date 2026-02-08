"""DuckDB connection manager for OLAP operations."""

from contextlib import contextmanager
from pathlib import Path
from typing import Any, Generator

import duckdb
import polars as pl

from app.core.config import settings


class DuckDBManager:
    """Manager for DuckDB connections and operations.

    DuckDB is used for:
    - Main journal_entries table (OLAP)
    - Aggregation tables (agg_*)
    - Complex analytical queries
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize DuckDB manager.

        Args:
            db_path: Path to DuckDB file. Defaults to settings.duckdb_path.
        """
        self.db_path = db_path or settings.duckdb_path
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Create a connection context manager.

        Yields:
            DuckDB connection object.

        Example:
            >>> with db.connect() as conn:
            ...     result = conn.execute("SELECT * FROM journal_entries LIMIT 10")
            ...     rows = result.fetchall()
        """
        conn = duckdb.connect(str(self.db_path))
        try:
            # Enable parallel execution
            conn.execute("SET threads TO 4")
            yield conn
        finally:
            conn.close()

    def execute(self, query: str, params: list[Any] | None = None) -> list[tuple[Any, ...]]:
        """Execute a query and return results.

        Args:
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            List of result tuples.
        """
        with self.connect() as conn:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return result.fetchall()

    def execute_df(self, query: str, params: list[Any] | None = None) -> pl.DataFrame:
        """Execute a query and return results as Polars DataFrame.

        Args:
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            Polars DataFrame with query results.
        """
        with self.connect() as conn:
            if params:
                result = conn.execute(query, params)
            else:
                result = conn.execute(query)
            return result.pl()

    def insert_df(self, table_name: str, df: pl.DataFrame) -> int:
        """Insert a Polars DataFrame into a table.

        Args:
            table_name: Target table name.
            df: DataFrame to insert.

        Returns:
            Number of rows inserted.
        """
        with self.connect() as conn:
            conn.register("df_to_insert", df.to_arrow())
            conn.execute(f"INSERT INTO {table_name} SELECT * FROM df_to_insert")
            return len(df)

    def table_exists(self, table_name: str) -> bool:
        """Check if a table exists.

        Args:
            table_name: Table name to check.

        Returns:
            True if table exists, False otherwise.
        """
        query = """
            SELECT COUNT(*) FROM information_schema.tables
            WHERE table_name = ?
        """
        result = self.execute(query, [table_name])
        return result[0][0] > 0

    def get_table_count(self, table_name: str) -> int:
        """Get the row count of a table.

        Args:
            table_name: Table name to count.

        Returns:
            Number of rows in the table.
        """
        result = self.execute(f"SELECT COUNT(*) FROM {table_name}")
        return result[0][0]

    def initialize_schema(self) -> None:
        """Initialize the database schema.

        Creates all required tables for JAIA using schema definitions.
        """
        from app.db.schema import DUCKDB_SCHEMA

        with self.connect() as conn:
            # Execute the full schema
            for statement in DUCKDB_SCHEMA.split(";"):
                statement = statement.strip()
                if statement and not statement.startswith("--"):
                    try:
                        conn.execute(statement)
                    except Exception:
                        # Skip errors for already existing objects
                        pass


# Global instance
duckdb_manager = DuckDBManager()
