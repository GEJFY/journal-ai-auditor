"""Audit trail endpoints.

監査証跡の取得APIエンドポイント。
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import APIRouter, HTTPException, Query

from app.services.audit_service import AuditService

logger = logging.getLogger(__name__)

router = APIRouter()


def get_audit_service() -> AuditService:
    """Get AuditService instance."""
    return AuditService()


@router.get("")
async def get_audit_events(
    event_type: str | None = Query(None, description="Filter by event type"),
    event_action: str | None = Query(None, description="Filter by action"),
    resource_type: str | None = Query(None, description="Filter by resource type"),
    limit: int = Query(100, ge=1, le=1000),
    offset: int = Query(0, ge=0),
) -> dict[str, Any]:
    """Get audit trail events.

    Returns:
        Paginated list of audit events.
    """
    service = get_audit_service()
    return service.get_events(
        event_type=event_type,
        event_action=event_action,
        resource_type=resource_type,
        limit=limit,
        offset=offset,
    )


@router.get("/{event_id}")
async def get_audit_event(event_id: int) -> dict[str, Any]:
    """Get a single audit event by ID.

    Args:
        event_id: Audit event ID.

    Returns:
        Audit event details.
    """
    service = get_audit_service()
    event = service.get_event_by_id(event_id)
    if event is None:
        raise HTTPException(status_code=404, detail="Audit event not found")
    return event
