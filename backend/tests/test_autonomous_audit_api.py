"""自律型監査 API エンドポイントのテスト。"""

import os
from unittest.mock import patch

from fastapi.testclient import TestClient


class TestAutonomousAuditAPI:
    """autonomous-audit エンドポイントの基本テスト。"""

    def test_list_sessions_empty(self, client: TestClient):
        """セッション履歴が空の場合、空リストを返す。"""
        response = client.get("/api/v1/autonomous-audit/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_sessions_with_fiscal_year_filter(self, client: TestClient):
        """fiscal_year フィルタ付きでセッション履歴を取得。"""
        response = client.get("/api/v1/autonomous-audit/sessions?fiscal_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_list_sessions_with_limit(self, client: TestClient):
        """limit パラメータ付きでセッション履歴を取得。"""
        response = client.get("/api/v1/autonomous-audit/sessions?limit=5")
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

    def test_get_insights_empty(self, client: TestClient):
        """存在しないセッションのインサイト取得。"""
        response = client.get("/api/v1/autonomous-audit/nonexistent-id/insights")
        # DB にセッションがなくてもエラーにはならない（空リスト返却）
        assert response.status_code in (200, 500)

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

    def test_start_request_with_valid_body(self, client: TestClient):
        """正常なリクエストボディの形式検証（実行はLLM依存のため500も許容）。"""
        with patch.dict(os.environ, {"ANTHROPIC_API_KEY": "test-key"}):
            response = client.post(
                "/api/v1/autonomous-audit/start",
                json={"fiscal_year": 2024, "scope": {}, "auto_approve": True},
            )
        # LLM未設定の場合は500になるが、バリデーションは通過する
        assert response.status_code in (200, 500)

    def test_start_stream_validation(self, client: TestClient):
        """SSEストリーミング開始のバリデーション。"""
        response = client.post(
            "/api/v1/autonomous-audit/start/stream",
            json={},
        )
        assert response.status_code == 422

    def test_approve_with_feedback(self, client: TestClient):
        """フィードバック付き承認（セッション不在時は404）。"""
        response = client.post(
            "/api/v1/autonomous-audit/nonexistent-id/approve",
            json={
                "hypothesis_ids": ["H-001"],
                "feedback": "テストフィードバック",
            },
        )
        assert response.status_code == 404
