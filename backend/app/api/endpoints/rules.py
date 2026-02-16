"""Audit rule management endpoints.

ルールの一覧取得・有効/無効切替・パラメータ更新APIエンドポイント。
"""

from __future__ import annotations

import json
import logging
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.db import SQLiteManager
from app.db.schema import DEFAULT_AUDIT_RULES
from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_sqlite() -> SQLiteManager:
    """Get SQLite instance."""
    return SQLiteManager()


def ensure_rules_seeded(db: SQLiteManager) -> None:
    """Ensure default audit rules are seeded in the database."""
    rows = db.execute("SELECT COUNT(*) FROM audit_rules")
    count = rows[0][0] if rows else 0
    if count > 0:
        return

    for rule in DEFAULT_AUDIT_RULES:
        db.insert(
            "audit_rules",
            {
                "rule_id": rule["rule_id"],
                "rule_name": rule["rule_name"],
                "rule_name_en": rule.get("rule_name_en"),
                "category": rule["category"],
                "description": rule.get("description"),
                "severity": rule.get("severity", "MEDIUM"),
                "is_enabled": True,
                "parameters": json.dumps(rule.get("parameters", {}), ensure_ascii=False)
                if rule.get("parameters")
                else None,
            },
        )
    logger.info("Seeded %d default audit rules", len(DEFAULT_AUDIT_RULES))


class RuleUpdateRequest(BaseModel):
    """Rule update request body."""

    is_enabled: bool | None = None
    severity: str | None = None
    parameters: dict[str, Any] | None = None


# --- Endpoints ---


@router.get("/categories")
async def get_rule_categories() -> dict[str, Any]:
    """Get all rule categories with counts.

    Returns:
        List of categories with rule counts.
    """
    db = get_sqlite()
    ensure_rules_seeded(db)

    rows = db.execute("""
        SELECT category, COUNT(*) as count,
               SUM(CASE WHEN is_enabled THEN 1 ELSE 0 END) as enabled_count
        FROM audit_rules
        GROUP BY category
        ORDER BY category
    """)

    categories = []
    for row in rows:
        categories.append(
            {
                "category": row[0],
                "total": row[1],
                "enabled": row[2],
            }
        )

    return {"categories": categories}


@router.get("")
async def get_rules(
    category: str | None = None,
    enabled_only: bool = False,
) -> dict[str, Any]:
    """Get all audit rules.

    Args:
        category: Filter by category.
        enabled_only: Return only enabled rules.

    Returns:
        List of audit rules.
    """
    db = get_sqlite()
    ensure_rules_seeded(db)

    conditions: list[str] = []
    params: list[Any] = []

    if category:
        conditions.append("category = ?")
        params.append(category)
    if enabled_only:
        conditions.append("is_enabled = 1")

    where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

    rows = db.execute(
        f"""
        SELECT rule_id, rule_name, rule_name_en, category, description,
               severity, is_enabled, parameters, created_at, updated_at
        FROM audit_rules
        {where}
        ORDER BY rule_id
        """,
        tuple(params) or None,
    )

    rules = []
    for row in rows:
        params_val = row[7]
        if params_val and isinstance(params_val, str):
            try:
                params_val = json.loads(params_val)
            except (json.JSONDecodeError, TypeError):
                pass

        rules.append(
            {
                "rule_id": row[0],
                "rule_name": row[1],
                "rule_name_en": row[2],
                "category": row[3],
                "description": row[4],
                "severity": row[5],
                "is_enabled": bool(row[6]),
                "parameters": params_val,
                "created_at": row[8],
                "updated_at": row[9],
            }
        )

    return {"rules": rules, "total": len(rules)}


@router.get("/{rule_id}")
async def get_rule(rule_id: str) -> dict[str, Any]:
    """Get a single audit rule by ID.

    Args:
        rule_id: Rule identifier.

    Returns:
        Rule details.
    """
    db = get_sqlite()
    ensure_rules_seeded(db)

    rows = db.execute(
        """
        SELECT rule_id, rule_name, rule_name_en, category, description,
               severity, is_enabled, parameters, created_at, updated_at
        FROM audit_rules
        WHERE rule_id = ?
        """,
        (rule_id,),
    )

    if not rows:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    row = rows[0]
    params_val = row[7]
    if params_val and isinstance(params_val, str):
        try:
            params_val = json.loads(params_val)
        except (json.JSONDecodeError, TypeError):
            pass

    return {
        "rule_id": row[0],
        "rule_name": row[1],
        "rule_name_en": row[2],
        "category": row[3],
        "description": row[4],
        "severity": row[5],
        "is_enabled": bool(row[6]),
        "parameters": params_val,
        "created_at": row[8],
        "updated_at": row[9],
    }


@router.put("/{rule_id}")
async def update_rule(rule_id: str, request: RuleUpdateRequest) -> dict[str, Any]:
    """Update a rule's settings (enabled, severity, parameters).

    Args:
        rule_id: Rule identifier.
        request: Fields to update.

    Returns:
        Updated rule.
    """
    db = get_sqlite()
    ensure_rules_seeded(db)

    # Check rule exists
    existing = db.execute(
        "SELECT rule_id FROM audit_rules WHERE rule_id = ?", (rule_id,)
    )
    if not existing:
        raise HTTPException(status_code=404, detail=f"Rule '{rule_id}' not found")

    # Build update
    data: dict[str, Any] = {"updated_at": "CURRENT_TIMESTAMP"}
    changes: dict[str, Any] = {}

    if request.is_enabled is not None:
        data["is_enabled"] = request.is_enabled
        changes["is_enabled"] = request.is_enabled
    if request.severity is not None:
        valid_severities = ("LOW", "MEDIUM", "HIGH", "CRITICAL")
        if request.severity.upper() not in valid_severities:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid severity. Must be one of: {valid_severities}",
            )
        data["severity"] = request.severity.upper()
        changes["severity"] = request.severity.upper()
    if request.parameters is not None:
        data["parameters"] = json.dumps(request.parameters, ensure_ascii=False)
        changes["parameters"] = request.parameters

    if not changes:
        raise HTTPException(status_code=400, detail="No fields to update")

    # updated_at needs special handling (SQL function, not a parameter)
    update_parts = []
    update_params: list[Any] = []
    for key, val in data.items():
        if key == "updated_at":
            update_parts.append("updated_at = CURRENT_TIMESTAMP")
        else:
            update_parts.append(f"{key} = ?")
            update_params.append(val)

    update_params.append(rule_id)
    with db.connect() as conn:
        conn.execute(
            f"UPDATE audit_rules SET {', '.join(update_parts)} WHERE rule_id = ?",
            update_params,
        )
        conn.commit()

    # Log audit event
    try:
        audit = AuditService(db)
        audit.log_event(
            "settings",
            "update",
            resource_type="rule",
            resource_id=rule_id,
            description=f"Rule {rule_id} updated",
            details=changes,
        )
    except Exception:
        logger.warning("Failed to log audit event for rule update", exc_info=True)

    # Return updated rule (reuse get_rule logic)
    return await get_rule(rule_id)


@router.post("/{rule_id}/reset")
async def reset_rule(rule_id: str) -> dict[str, Any]:
    """Reset a rule to its default settings.

    Args:
        rule_id: Rule identifier.

    Returns:
        Reset rule.
    """
    db = get_sqlite()
    ensure_rules_seeded(db)

    # Find default
    default = next((r for r in DEFAULT_AUDIT_RULES if r["rule_id"] == rule_id), None)
    if default is None:
        raise HTTPException(
            status_code=404, detail=f"No default found for rule '{rule_id}'"
        )

    with db.connect() as conn:
        conn.execute(
            """
            UPDATE audit_rules
            SET severity = ?, is_enabled = 1, parameters = NULL,
                updated_at = CURRENT_TIMESTAMP
            WHERE rule_id = ?
            """,
            (default.get("severity", "MEDIUM"), rule_id),
        )
        conn.commit()

    # Log audit event
    try:
        audit = AuditService(db)
        audit.log_event(
            "settings",
            "update",
            resource_type="rule",
            resource_id=rule_id,
            description=f"Rule {rule_id} reset to defaults",
        )
    except Exception:
        logger.warning("Failed to log audit event for rule reset", exc_info=True)

    return await get_rule(rule_id)
