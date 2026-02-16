"""SQLite connection manager for metadata operations."""

import sqlite3
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path
from typing import Any

from app.core.config import settings


class SQLiteManager:
    """Manager for SQLite connections and operations.

    SQLite is used for:
    - Application settings
    - Audit rules configuration
    - Analysis sessions
    - Insights and notes
    - User preferences
    """

    def __init__(self, db_path: Path | None = None) -> None:
        """Initialize SQLite manager.

        Args:
            db_path: Path to SQLite file. Defaults to settings.sqlite_path.
        """
        self.db_path = db_path or settings.sqlite_path
        self._ensure_directory()

    def _ensure_directory(self) -> None:
        """Ensure the database directory exists."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Generator[sqlite3.Connection, None, None]:
        """Create a connection context manager.

        Yields:
            SQLite connection object.

        Example:
            >>> with db.connect() as conn:
            ...     cursor = conn.execute("SELECT * FROM app_settings")
            ...     rows = cursor.fetchall()
        """
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        try:
            yield conn
        finally:
            conn.close()

    def execute(
        self,
        query: str,
        params: tuple[Any, ...] | dict[str, Any] | None = None,
    ) -> list[sqlite3.Row]:
        """Execute a query and return results.

        Args:
            query: SQL query to execute.
            params: Query parameters.

        Returns:
            List of result rows.
        """
        with self.connect() as conn:
            cursor = conn.execute(query, params) if params else conn.execute(query)
            return cursor.fetchall()

    def execute_many(
        self,
        query: str,
        params_list: list[tuple[Any, ...]] | list[dict[str, Any]],
    ) -> int:
        """Execute a query with multiple parameter sets.

        Args:
            query: SQL query to execute.
            params_list: List of parameter sets.

        Returns:
            Number of rows affected.
        """
        with self.connect() as conn:
            cursor = conn.executemany(query, params_list)
            conn.commit()
            return cursor.rowcount

    def insert(
        self,
        table: str,
        data: dict[str, Any],
    ) -> int:
        """Insert a single row.

        Args:
            table: Table name.
            data: Column-value mapping.

        Returns:
            ID of inserted row.
        """
        columns = ", ".join(data.keys())
        placeholders = ", ".join("?" * len(data))
        query = f"INSERT INTO {table} ({columns}) VALUES ({placeholders})"

        with self.connect() as conn:
            cursor = conn.execute(query, tuple(data.values()))
            conn.commit()
            return cursor.lastrowid or 0

    def update(
        self,
        table: str,
        data: dict[str, Any],
        where: str,
        where_params: tuple[Any, ...],
    ) -> int:
        """Update rows matching condition.

        Args:
            table: Table name.
            data: Column-value mapping to update.
            where: WHERE clause.
            where_params: Parameters for WHERE clause.

        Returns:
            Number of rows updated.
        """
        set_clause = ", ".join(f"{k} = ?" for k in data)
        query = f"UPDATE {table} SET {set_clause} WHERE {where}"
        params = tuple(data.values()) + where_params

        with self.connect() as conn:
            cursor = conn.execute(query, params)
            conn.commit()
            return cursor.rowcount

    def initialize_schema(self) -> None:
        """Initialize the metadata database schema."""
        with self.connect() as conn:
            # Application settings
            conn.execute("""
                CREATE TABLE IF NOT EXISTS app_settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    data_type TEXT DEFAULT 'string',
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Audit rules
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_rules (
                    rule_id TEXT PRIMARY KEY,
                    rule_name TEXT NOT NULL,
                    rule_name_en TEXT,
                    category TEXT NOT NULL,
                    description TEXT,
                    sql_condition TEXT,
                    severity TEXT DEFAULT 'MEDIUM',
                    is_enabled BOOLEAN DEFAULT TRUE,
                    parameters TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Analysis sessions
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_sessions (
                    session_id TEXT PRIMARY KEY,
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    ended_at TIMESTAMP,
                    status TEXT DEFAULT 'running',
                    fiscal_year INTEGER,
                    filters TEXT,
                    total_insights INTEGER DEFAULT 0,
                    summary TEXT
                )
            """)

            # Insights
            conn.execute("""
                CREATE TABLE IF NOT EXISTS insights (
                    insight_id TEXT PRIMARY KEY,
                    session_id TEXT NOT NULL,
                    category TEXT NOT NULL,
                    title TEXT NOT NULL,
                    description TEXT,
                    severity TEXT DEFAULT 'INFO',
                    evidence TEXT,
                    affected_count INTEGER DEFAULT 0,
                    affected_amount REAL DEFAULT 0,
                    recommendation TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (session_id) REFERENCES analysis_sessions(session_id)
                )
            """)

            # Journal entry notes
            conn.execute("""
                CREATE TABLE IF NOT EXISTS je_notes (
                    note_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    journal_id TEXT NOT NULL,
                    note_text TEXT NOT NULL,
                    note_type TEXT DEFAULT 'general',
                    created_by TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # Journal entry tags
            conn.execute("""
                CREATE TABLE IF NOT EXISTS je_tags (
                    tag_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    journal_id TEXT NOT NULL,
                    tag_name TEXT NOT NULL,
                    tag_color TEXT DEFAULT '#6B7280',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE(journal_id, tag_name)
                )
            """)

            # Import history
            conn.execute("""
                CREATE TABLE IF NOT EXISTS import_history (
                    import_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    filename TEXT NOT NULL,
                    file_type TEXT NOT NULL,
                    file_size INTEGER,
                    row_count INTEGER,
                    error_count INTEGER DEFAULT 0,
                    status TEXT DEFAULT 'completed',
                    started_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    completed_at TIMESTAMP,
                    error_details TEXT
                )
            """)

            # Audit trail
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audit_trail (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    event_type TEXT NOT NULL,
                    event_action TEXT NOT NULL,
                    user_id TEXT,
                    resource_type TEXT,
                    resource_id TEXT,
                    description TEXT,
                    details TEXT,
                    ip_address TEXT,
                    request_id TEXT
                )
            """)

            # Filter presets
            conn.execute("""
                CREATE TABLE IF NOT EXISTS filter_presets (
                    preset_id INTEGER PRIMARY KEY AUTOINCREMENT,
                    preset_name TEXT NOT NULL UNIQUE,
                    filters TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # LLM usage log
            conn.execute("""
                CREATE TABLE IF NOT EXISTS llm_usage_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    provider TEXT NOT NULL,
                    model TEXT NOT NULL,
                    input_tokens INTEGER DEFAULT 0,
                    output_tokens INTEGER DEFAULT 0,
                    estimated_cost_usd REAL DEFAULT 0,
                    latency_ms REAL DEFAULT 0,
                    request_type TEXT DEFAULT 'general',
                    session_id TEXT,
                    success BOOLEAN DEFAULT TRUE
                )
            """)

            # パフォーマンス向上用インデックス
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_trail_timestamp "
                "ON audit_trail(timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_audit_trail_event_type "
                "ON audit_trail(event_type)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_usage_timestamp "
                "ON llm_usage_log(timestamp DESC)"
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_llm_usage_provider "
                "ON llm_usage_log(provider)"
            )

            conn.commit()


# Global instance
sqlite_manager = SQLiteManager()
