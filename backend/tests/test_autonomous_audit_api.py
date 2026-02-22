"""自律型監査 API エンドポイントのテスト。"""

from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient


class TestAutonomousAuditAPI:
    """autonomous-audit エンドポイントの基本テスト。"""

    def test_list_sessions_empty(self, client: TestClient):
        """セッション履歴が空の場合、空リストを返す。"""
        response = client.get("/api/v1/autonomous-audit/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_status_not_found(self, client: TestClient):
        """存在しないセッションの状態取得は 404。"""
        response = client.get("/api/v1/autonomous-audit/nonexistent-id/status")
        assert response.status_code == 404

    def test_get_hypotheses_not_found(self, client: TestClient):
        """存在しないセッションの仮説取得は 404。"""
        response = client.get("/api/v1/autonomous-audit/nonexistent-id/hypotheses")
        assert response.status_code == 404

    def test_approve_not_found(self, client: TestClient):
        """存在しないセッションの承認は 404。"""
        response = client.post(
            "/api/v1/autonomous-audit/nonexistent-id/approve",
            json={"hypothesis_ids": None, "feedback": None},
        )
        assert response.status_code == 404

    def test_get_report_not_found(self, client: TestClient):
        """存在しないセッションのレポート取得は 404。"""
        response = client.get("/api/v1/autonomous-audit/nonexistent-id/report")
        assert response.status_code == 404

    def test_start_request_validation(self, client: TestClient):
        """fiscal_year 必須パラメータの検証。"""
        response = client.post(
            "/api/v1/autonomous-audit/start",
            json={},
        )
        assert response.status_code == 422  # Validation error
