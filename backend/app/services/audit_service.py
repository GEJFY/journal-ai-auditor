"""Audit trail service.

監査証跡の記録・取得を行うサービス。
"""

from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime
from typing import Any

from app.db import SQLiteManager

logger = logging.getLogger(__name__)


class AuditService:
    """監査証跡の記録・取得サービス。"""

    def __init__(self, db: SQLiteManager | None = None) -> None:
        self.db = db or SQLiteManager()

    def log_event(
        self,
        event_type: str,
        event_action: str,
        *,
        user_id: str | None = None,
        resource_type: str | None = None,
        resource_id: str | None = None,
        description: str | None = None,
        details: dict[str, Any] | None = None,
        ip_address: str | None = None,
        request_id: str | None = None,
    ) -> int:
        """監査イベントを記録する。

        Args:
            event_type: イベント種別 (import, analysis, settings, report, auth, system)
            event_action: アクション (create, update, delete, execute, export)
            user_id: ユーザーID
            resource_type: リソース種別 (journal, rule, report, session)
            resource_id: リソースID
            description: イベント説明
            details: 追加詳細情報 (JSON)
            ip_address: クライアントIPアドレス
            request_id: リクエストID

        Returns:
            挿入された行のID
        """
        if request_id is None:
            request_id = uuid.uuid4().hex[:12]

        details_json = (
            json.dumps(details, ensure_ascii=False, default=str) if details else None
        )

        row_id = self.db.insert(
            "audit_trail",
            {
                "timestamp": datetime.now().isoformat(),
                "event_type": event_type,
                "event_action": event_action,
                "user_id": user_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "description": description,
                "details": details_json,
                "ip_address": ip_address,
                "request_id": request_id,
            },
        )
        logger.debug(
            "Audit event logged: %s/%s (id=%d)", event_type, event_action, row_id
        )
        return row_id

    def get_events(
        self,
        *,
        event_type: str | None = None,
        event_action: str | None = None,
        resource_type: str | None = None,
        limit: int = 100,
        offset: int = 0,
    ) -> dict[str, Any]:
        """監査イベントを取得する。

        Args:
            event_type: フィルタ: イベント種別
            event_action: フィルタ: アクション
            resource_type: フィルタ: リソース種別
            limit: 取得件数上限
            offset: オフセット

        Returns:
            events一覧とtotal件数
        """
        conditions: list[str] = []
        params: list[Any] = []

        if event_type:
            conditions.append("event_type = ?")
            params.append(event_type)
        if event_action:
            conditions.append("event_action = ?")
            params.append(event_action)
        if resource_type:
            conditions.append("resource_type = ?")
            params.append(resource_type)

        where = f"WHERE {' AND '.join(conditions)}" if conditions else ""

        # 件数取得
        count_rows = self.db.execute(
            f"SELECT COUNT(*) FROM audit_trail {where}", tuple(params) or None
        )
        total = count_rows[0][0] if count_rows else 0

        # データ取得
        params_with_paging = params + [limit, offset]
        rows = self.db.execute(
            f"""
            SELECT id, timestamp, event_type, event_action, user_id,
                   resource_type, resource_id, description, details,
                   ip_address, request_id
            FROM audit_trail
            {where}
            ORDER BY timestamp DESC
            LIMIT ? OFFSET ?
            """,
            tuple(params_with_paging),
        )

        events = []
        for row in rows:
            detail_val = row[8]
            if detail_val and isinstance(detail_val, str):
                try:
                    detail_val = json.loads(detail_val)
                except (json.JSONDecodeError, TypeError):
                    pass

            events.append(
                {
                    "id": row[0],
                    "timestamp": row[1],
                    "event_type": row[2],
                    "event_action": row[3],
                    "user_id": row[4],
                    "resource_type": row[5],
                    "resource_id": row[6],
                    "description": row[7],
                    "details": detail_val,
                    "ip_address": row[9],
                    "request_id": row[10],
                }
            )

        return {"events": events, "total": total}

    def get_event_by_id(self, event_id: int) -> dict[str, Any] | None:
        """IDで監査イベントを1件取得する。"""
        rows = self.db.execute(
            """
            SELECT id, timestamp, event_type, event_action, user_id,
                   resource_type, resource_id, description, details,
                   ip_address, request_id
            FROM audit_trail
            WHERE id = ?
            """,
            (event_id,),
        )

        if not rows:
            return None

        row = rows[0]
        detail_val = row[8]
        if detail_val and isinstance(detail_val, str):
            try:
                detail_val = json.loads(detail_val)
            except (json.JSONDecodeError, TypeError):
                pass

        return {
            "id": row[0],
            "timestamp": row[1],
            "event_type": row[2],
            "event_action": row[3],
            "user_id": row[4],
            "resource_type": row[5],
            "resource_id": row[6],
            "description": row[7],
            "details": detail_val,
            "ip_address": row[9],
            "request_id": row[10],
        }
