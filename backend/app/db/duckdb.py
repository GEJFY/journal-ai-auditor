"""DuckDB connection manager for OLAP operations."""

import threading
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

import duckdb
import polars as pl

from app.core.config import settings


class DuckDBManager:
    """Manager for DuckDB connections and operations.

    DuckDB is used for:
    - Main journal_entries table (OLAP)
    - Aggregation tables (agg_*)
    - Complex analytical queries

    永続接続を保持し、カーソルベースで読み取りクエリを実行する。
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize DuckDB manager.

        Args:
            db_path: Path to DuckDB file. Defaults to settings.duckdb_path.
        """
        self.db_path = db_path or settings.duckdb_path
        self._conn: duckdb.DuckDBPyConnection | None = None
        self._lock = threading.Lock()
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    def _get_connection(self) -> duckdb.DuckDBPyConnection:
        """Get or create the persistent connection."""
        if self._conn is None:
            with self._lock:
                if self._conn is None:
                    self._conn = duckdb.connect(str(self.db_path))
                    self._conn.execute("SET threads TO 4")
        return self._conn

    @contextmanager
    def connect(self) -> Generator[duckdb.DuckDBPyConnection, None, None]:
        """Create a cursor context manager on the persistent connection.

        Yields:
            DuckDB cursor object (same API as connection).

        Example:
            >>> with db.connect() as conn:
            ...     result = conn.execute("SELECT * FROM journal_entries LIMIT 10")
            ...     rows = result.fetchall()
        """
        conn = self._get_connection()
        cursor = conn.cursor()
        try:
            yield cursor
        finally:
            cursor.close()

    def execute(
        self, query: str, params: list[Any] | None = None
    ) -> list[tuple[Any, ...]]:
        """Execute a query and return results.

        Args:
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            List of result tuples.
        """
        with self.connect() as cursor:
            result = cursor.execute(query, params) if params else cursor.execute(query)
            return result.fetchall()

    def execute_df(self, query: str, params: list[Any] | None = None) -> pl.DataFrame:
        """Execute a query and return results as Polars DataFrame.

        Args:
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            Polars DataFrame with query results.
        """
        with self.connect() as cursor:
            result = cursor.execute(query, params) if params else cursor.execute(query)
            return result.pl()

    def insert_df(self, table_name: str, df: pl.DataFrame) -> int:
        """Insert a Polars DataFrame into a table.

        Args:
            table_name: Target table name.
            df: DataFrame to insert.

        Returns:
            Number of rows inserted.
        """
        conn = self._get_connection()
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

    def close(self) -> None:
        """Close the persistent connection."""
        if self._conn is not None:
            with self._lock:
                if self._conn is not None:
                    self._conn.close()
                    self._conn = None

    def initialize_schema(self) -> None:
        """Initialize the database schema.

        Creates all required tables for JAIA using schema definitions.
        """
        from app.db.schema import DUCKDB_SCHEMA

        conn = self._get_connection()
        # Execute the full schema
        for statement in DUCKDB_SCHEMA.split(";"):
            # Strip comment-only lines to get actual SQL
            lines = [
                line
                for line in statement.split("\n")
                if line.strip() and not line.strip().startswith("--")
            ]
            clean_stmt = "\n".join(lines).strip()
            if clean_stmt:
                try:
                    conn.execute(clean_stmt)
                except Exception:
                    # Skip errors for already existing objects
                    pass


# Global instance
duckdb_manager = DuckDBManager()


def get_db() -> DuckDBManager:
    """Get global DuckDB manager instance."""
    return duckdb_manager
