"""
Application settings endpoints.

アプリケーション設定の取得・更新APIエンドポイント。
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter
from pydantic import BaseModel

from app.db import SQLiteManager

router = APIRouter()


def get_sqlite() -> SQLiteManager:
    """Get SQLite instance."""
    return SQLiteManager()


class SettingsUpdateRequest(BaseModel):
    """Settings update request body."""

    settings: dict[str, str]


@router.get("")
async def get_settings() -> dict[str, Any]:
    """Get all application settings.

    Returns:
        Dictionary of all stored settings.
    """
    db = get_sqlite()
    try:
        rows = db.execute("SELECT key, value, data_type FROM app_settings")
    except Exception:
        rows = []

    settings: dict[str, Any] = {}
    for row in rows:
        key, value, data_type = row[0], row[1], row[2]
        if data_type == "int":
            settings[key] = int(value)
        elif data_type == "float":
            settings[key] = float(value)
        elif data_type == "bool":
            settings[key] = value.lower() in ("true", "1", "yes")
        else:
            settings[key] = value

    return {"settings": settings}


@router.put("")
async def update_settings(request: SettingsUpdateRequest) -> dict[str, Any]:
    """Update application settings.

    Args:
        request: Dictionary of key-value pairs to update.

    Returns:
        Updated settings count.
    """
    db = get_sqlite()
    updated = 0

    for key, value in request.settings.items():
        # Determine data type
        data_type = "string"
        if isinstance(value, bool) or value.lower() in ("true", "false"):
            data_type = "bool"
        elif value.isdigit():
            data_type = "int"

        try:
            db.execute(
                """
                INSERT INTO app_settings (key, value, data_type, updated_at)
                VALUES (?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(key) DO UPDATE SET
                    value = excluded.value,
                    data_type = excluded.data_type,
                    updated_at = CURRENT_TIMESTAMP
                """,
                [key, str(value), data_type],
            )
            updated += 1
        except Exception:
            pass

    return {"updated": updated, "success": True}
