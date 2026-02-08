"""Health check endpoints."""

from fastapi import APIRouter

from app.core.config import settings
from app.db import DuckDBManager, SQLiteManager

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """
    APIヘルスチェックエンドポイント。

    Returns:
        dict: ヘルスステータス
    """
    return {
        "status": "healthy",
        "app": settings.app_name,
        "version": settings.app_version,
    }


@router.get("/status")
async def get_status() -> dict:
    """Get detailed application status.

    Returns:
        Application status including database connectivity.
    """
    duckdb = DuckDBManager()
    sqlite = SQLiteManager()

    # Check DuckDB
    duckdb_status = "healthy"
    je_count = 0
    try:
        if duckdb.table_exists("journal_entries"):
            je_count = duckdb.get_table_count("journal_entries")
    except Exception as e:
        duckdb_status = f"error: {e}"

    # Check SQLite
    sqlite_status = "healthy"
    try:
        sqlite.execute("SELECT 1")
    except Exception as e:
        sqlite_status = f"error: {e}"

    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "environment": settings.environment,
        "databases": {
            "duckdb": {
                "status": duckdb_status,
                "journal_entries_count": je_count,
            },
            "sqlite": {
                "status": sqlite_status,
            },
        },
    }
