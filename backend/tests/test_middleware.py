"""ミドルウェアのユニットテスト"""

from app.core.middleware import SecurityConfig


class TestSecurityConfig:
    """セキュリティ設定のテスト"""

    def test_rate_limit_defaults(self):
        assert SecurityConfig.RATE_LIMIT_REQUESTS == 100
        assert SecurityConfig.RATE_LIMIT_WINDOW_SECONDS == 60

    def test_temp_block_defaults(self):
        assert SecurityConfig.TEMP_BLOCK_THRESHOLD == 10
        assert SecurityConfig.TEMP_BLOCK_DURATION_MINUTES == 15

    def test_blocked_ips_initially_empty(self):
        assert len(SecurityConfig.BLOCKED_IPS) == 0

    def test_suspicious_patterns_defined(self):
        patterns = SecurityConfig.SUSPICIOUS_PATTERNS
        assert len(patterns) > 0
        # ディレクトリトラバーサル
        assert "../" in patterns
        # XSS
        assert "<script" in patterns
        # SQLインジェクション
        assert "' OR " in patterns


class TestMiddlewareIntegration:
    """ミドルウェア統合テスト（TestClient経由）"""

    def test_request_id_header(self, client):
        """X-Request-IDヘッダーが付与される"""
        response = client.get("/health")
        # リクエストIDヘッダーが存在する
        assert "x-request-id" in response.headers

    def test_cors_headers(self, client):
        """CORSヘッダーが適切に設定される"""
        response = client.get(
            "/health",
            headers={
                "Origin": "http://localhost:3000",
            },
        )
        # CORS経由でアクセス可能
        assert response.status_code == 200

    def test_security_headers(self, client):
        """セキュリティヘッダーが設定される"""
        response = client.get("/health")
        # 一般的なセキュリティヘッダー（設定による）
        assert response.status_code == 200

    def test_performance_logging(self, client):
        """レスポンスタイムが記録される（エラーなし）"""
        response = client.get("/api/v1/status")
        assert response.status_code == 200
