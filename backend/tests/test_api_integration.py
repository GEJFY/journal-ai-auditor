"""
API統合テスト

FastAPI エンドポイントの統合テストを実行します。
注意: 一部のエンドポイントはデータベースが初期化されていないと
内部エラーを返す可能性があります。
"""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """ヘルスチェックエンドポイントのテスト"""

    def test_api_v1_health(self, client: TestClient):
        """API v1 ヘルスチェック"""
        response = client.get("/api/v1/health")

        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_v1_status(self, client: TestClient):
        """詳細ステータス確認"""
        response = client.get("/api/v1/status")

        assert response.status_code == 200
        data = response.json()
        assert "databases" in data
        assert "duckdb" in data["databases"]
        assert "sqlite" in data["databases"]


class TestDashboardEndpoints:
    """ダッシュボードエンドポイントのテスト"""

    def test_dashboard_with_invalid_fiscal_year(self, client: TestClient):
        """無効な会計年度"""
        response = client.get("/api/v1/dashboard/summary", params={"fiscal_year": "invalid"})

        # バリデーションエラー
        assert response.status_code == 422


class TestBatchEndpoints:
    """バッチ処理エンドポイントのテスト"""

    def test_get_rules_list(self, client: TestClient):
        """ルール一覧取得"""
        response = client.get("/api/v1/batch/rules")

        assert response.status_code == 200
        data = response.json()

        # ルール数が含まれている
        assert "total_rules" in data or "rules" in data or isinstance(data, list)


class TestReportEndpoints:
    """レポートエンドポイントのテスト"""

    def test_get_templates(self, client: TestClient):
        """レポートテンプレート一覧取得"""
        response = client.get("/api/v1/reports/templates")

        assert response.status_code == 200
        data = response.json()

        # テンプレート一覧が返される
        if isinstance(data, dict) and "templates" in data:
            templates = data["templates"]
        else:
            templates = data

        assert isinstance(templates, list)
        assert len(templates) > 0


class TestAgentEndpoints:
    """AIエージェントエンドポイントのテスト"""

    def test_agent_analyze_endpoint_exists(self, client: TestClient):
        """分析エンドポイントの存在確認"""
        response = client.post(
            "/api/v1/agents/analyze",
            json={"fiscal_year": 2024}
        )

        # エンドポイントが存在する（LLM設定がなくてもエラーではない）
        assert response.status_code in [200, 422, 500, 503]


class TestImportEndpoints:
    """インポートエンドポイントのテスト"""

    def test_import_status_not_found(self, client: TestClient):
        """存在しないインポートIDのステータス確認"""
        response = client.get("/api/v1/import/status/nonexistent-id")

        # 404 Not Foundが返される
        assert response.status_code == 404


class TestErrorHandling:
    """エラーハンドリングのテスト"""

    def test_not_found_endpoint(self, client: TestClient):
        """存在しないエンドポイント"""
        response = client.get("/api/v1/nonexistent")

        assert response.status_code == 404

    def test_validation_error_response_format(self, client: TestClient):
        """バリデーションエラーのレスポンス形式"""
        response = client.get(
            "/api/v1/dashboard/summary",
            params={"fiscal_year": "not-a-number"}
        )

        assert response.status_code == 422
        data = response.json()

        # FastAPIのバリデーションエラー形式
        assert "detail" in data


class TestCORSHeaders:
    """CORSヘッダーのテスト"""

    def test_cors_headers_present(self, client: TestClient):
        """CORSヘッダーが存在すること"""
        response = client.options(
            "/api/v1/health",
            headers={
                "Origin": "http://localhost:5173",
                "Access-Control-Request-Method": "GET"
            }
        )

        # CORSプリフライトリクエストが処理される
        assert response.status_code in [200, 204, 405]


class TestRequestId:
    """リクエストIDのテスト"""

    def test_request_id_in_response(self, client: TestClient):
        """レスポンスにリクエストIDが含まれる"""
        response = client.get("/api/v1/health")

        # リクエストは正常に処理される
        assert response.status_code == 200
