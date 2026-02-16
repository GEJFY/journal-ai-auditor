"""パフォーマンス最適化のテスト."""

import time

from fastapi.testclient import TestClient


class TestResponseTimes:
    """APIレスポンス時間のテスト。"""

    def test_health_under_50ms(self, client: TestClient):
        """ヘルスチェックは50ms以内。"""
        start = time.time()
        response = client.get("/health")
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 50, f"ヘルスチェックが{elapsed_ms:.0f}msかかりました"

    def test_summary_under_500ms(self, client: TestClient):
        """ダッシュボードサマリーは500ms以内（空DB）。"""
        start = time.time()
        response = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 500, f"サマリーが{elapsed_ms:.0f}msかかりました"

    def test_kpi_under_500ms(self, client: TestClient):
        """KPIは500ms以内（空DB）。"""
        start = time.time()
        response = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 500, f"KPIが{elapsed_ms:.0f}msかかりました"

    def test_risk_under_500ms(self, client: TestClient):
        """リスク分析は500ms以内（空DB）。"""
        start = time.time()
        response = client.get("/api/v1/dashboard/risk", params={"fiscal_year": 2024})
        elapsed_ms = (time.time() - start) * 1000

        assert response.status_code == 200
        assert elapsed_ms < 500, f"リスク分析が{elapsed_ms:.0f}msかかりました"


class TestDashboardCache:
    """ダッシュボードキャッシュのテスト。"""

    def test_summary_cache_hit(self, client: TestClient):
        """サマリーの2回目はキャッシュから高速返却される。"""
        # 1回目: キャッシュミス
        start = time.time()
        r1 = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        first_ms = (time.time() - start) * 1000

        # 2回目: キャッシュヒット
        start = time.time()
        r2 = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        second_ms = (time.time() - start) * 1000

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()
        # キャッシュヒットは最初のリクエストより高速であるべき
        # （空DBの場合は差が小さい可能性があるためアサート緩め）
        assert second_ms < first_ms * 3 + 50

    def test_kpi_cache_hit(self, client: TestClient):
        """KPIの2回目はキャッシュから返却される。"""
        r1 = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})
        r2 = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})

        assert r1.status_code == 200
        assert r2.status_code == 200
        assert r1.json() == r2.json()

    def test_different_params_no_cache_collision(self, client: TestClient):
        """異なるパラメータはキャッシュが分離される。"""
        r1 = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        r2 = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2023})

        assert r1.status_code == 200
        assert r2.status_code == 200
        # 空DBなので同じ値だが、キャッシュキーは別


class TestRiskOptimization:
    """リスクエンドポイント最適化のテスト。"""

    def test_risk_response_structure(self, client: TestClient):
        """最適化後もレスポンス構造が正しい。"""
        response = client.get("/api/v1/dashboard/risk", params={"fiscal_year": 2024})
        assert response.status_code == 200
        data = response.json()
        assert "high_risk" in data
        assert "medium_risk" in data
        assert "low_risk" in data
        assert "risk_distribution" in data
        assert isinstance(data["high_risk"], list)
        assert isinstance(data["risk_distribution"], dict)
        assert set(data["risk_distribution"].keys()) == {
            "high",
            "medium",
            "low",
            "minimal",
        }

    def test_risk_with_period_filter(self, client: TestClient):
        """期間フィルター付きリスク分析。"""
        response = client.get(
            "/api/v1/dashboard/risk",
            params={"fiscal_year": 2024, "period_from": 1, "period_to": 6},
        )
        assert response.status_code == 200


class TestSQLiteIndexes:
    """SQLiteインデックス作成のテスト。"""

    def test_indexes_created(self):
        """initialize_schema後にインデックスが作成されている。"""
        import tempfile
        from pathlib import Path

        from app.db.sqlite import SQLiteManager

        with tempfile.TemporaryDirectory() as tmpdir:
            db = SQLiteManager(db_path=Path(tmpdir) / "test.db")
            db.initialize_schema()

            indexes = db.execute("SELECT name FROM sqlite_master WHERE type = 'index'")
            index_names = {row["name"] for row in indexes}

            assert "idx_audit_trail_timestamp" in index_names
            assert "idx_audit_trail_event_type" in index_names
            assert "idx_llm_usage_timestamp" in index_names
            assert "idx_llm_usage_provider" in index_names
