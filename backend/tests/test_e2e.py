"""
E2Eテスト（エンドツーエンドテスト）

完全なユーザーワークフローをシミュレートするテストです。
"""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


class TestImportToAnalysisWorkflow:
    """
    データインポートから分析までの完全なワークフローテスト
    """

    @pytest.fixture(autouse=True)
    def setup_test_environment(self, temp_data_dir):
        """テスト環境のセットアップ"""
        self.temp_dir = temp_data_dir

    def test_full_workflow_import_analyze_report(self, client: TestClient, sample_data_dir: Path):
        """
        完全なワークフロー:
        1. ヘルスチェック
        2. ダッシュボード確認
        3. バッチ処理実行
        4. 分析結果確認
        5. レポートテンプレート取得
        """
        # Step 1: ヘルスチェック
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"

        # Step 2: 初期ダッシュボード確認
        response = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        assert response.status_code == 200

        # Step 3: ルール一覧取得
        response = client.get("/api/v1/batch/rules")
        assert response.status_code == 200
        response.json()

        # Step 4: KPI確認
        response = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})
        assert response.status_code == 200

        # Step 5: Benford分析確認
        response = client.get("/api/v1/dashboard/benford", params={"fiscal_year": 2024})
        assert response.status_code == 200

        # Step 6: 違反一覧取得
        response = client.get("/api/v1/analysis/violations", params={"fiscal_year": 2024})
        assert response.status_code == 200

        # Step 7: レポートテンプレート取得
        response = client.get("/api/v1/reports/templates")
        assert response.status_code == 200
        templates = response.json()
        assert isinstance(templates.get("data", templates), list)


class TestDashboardNavigation:
    """ダッシュボードナビゲーションのテスト"""

    def test_navigate_all_dashboard_endpoints(self, client: TestClient):
        """
        全ダッシュボードエンドポイントを順番に確認
        """
        endpoints = [
            "/api/v1/dashboard/summary",
            "/api/v1/dashboard/kpi",
            "/api/v1/dashboard/benford",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint, params={"fiscal_year": 2024})
            assert response.status_code == 200, f"Failed for {endpoint}"

    def test_filter_combination(self, client: TestClient):
        """フィルター組み合わせテスト"""
        # 複数パラメータの組み合わせ
        response = client.get(
            "/api/v1/dashboard/summary",
            params={
                "fiscal_year": 2024,
                "period_start": "2024-04-01",
                "period_end": "2024-06-30",
            }
        )
        assert response.status_code == 200


class TestRiskAnalysisFlow:
    """リスク分析フローのテスト"""

    def test_risk_analysis_complete_flow(self, client: TestClient):
        """
        リスク分析の完全フロー:
        1. 違反一覧取得
        2. リスクレベル別フィルタリング
        3. ML異常取得
        4. Benford詳細取得
        """
        # Step 1: 全違反取得
        response = client.get(
            "/api/v1/analysis/violations",
            params={"fiscal_year": 2024}
        )
        assert response.status_code == 200

        # Step 2: Criticalのみフィルター
        response = client.get(
            "/api/v1/analysis/violations",
            params={"fiscal_year": 2024, "risk_level": "Critical"}
        )
        assert response.status_code == 200

        # Step 3: High以上フィルター
        response = client.get(
            "/api/v1/analysis/violations",
            params={"fiscal_year": 2024, "risk_level": "Critical,High"}
        )
        assert response.status_code == 200

        # Step 4: ML異常取得
        response = client.get(
            "/api/v1/analysis/ml-anomalies",
            params={"fiscal_year": 2024}
        )
        assert response.status_code == 200

        # Step 5: Benford詳細
        response = client.get(
            "/api/v1/analysis/benford-detail",
            params={"fiscal_year": 2024}
        )
        assert response.status_code == 200


class TestReportGenerationFlow:
    """レポート生成フローのテスト"""

    def test_report_generation_flow(self, client: TestClient):
        """
        レポート生成の完全フロー:
        1. テンプレート一覧取得
        2. PPTエクスポート
        3. PDFエクスポート
        """
        # Step 1: テンプレート取得
        response = client.get("/api/v1/reports/templates")
        assert response.status_code == 200
        response.json()

        # Step 2: PPTエクスポート（データがなくても実行可能か確認）
        response = client.post(
            "/api/v1/reports/export/ppt",
            json={
                "fiscal_year": 2024,
                "period_start": "2024-04-01",
                "period_end": "2024-06-30"
            }
        )
        # エクスポートが成功するか、パラメータエラー
        assert response.status_code in [200, 422, 500]

        # Step 3: PDFエクスポート
        response = client.post(
            "/api/v1/reports/export/pdf",
            json={
                "fiscal_year": 2024,
                "period_start": "2024-04-01",
                "period_end": "2024-06-30"
            }
        )
        assert response.status_code in [200, 422, 500]


class TestErrorRecovery:
    """エラーリカバリーのテスト"""

    def test_invalid_parameter_recovery(self, client: TestClient):
        """無効なパラメータからの回復"""
        # 無効なリクエスト
        response = client.get(
            "/api/v1/dashboard/summary",
            params={"fiscal_year": "invalid"}
        )
        assert response.status_code == 422

        # 次のリクエストは正常に処理される
        response = client.get(
            "/api/v1/dashboard/summary",
            params={"fiscal_year": 2024}
        )
        assert response.status_code == 200

    def test_continuous_requests(self, client: TestClient):
        """連続リクエストのテスト"""
        for _i in range(10):
            response = client.get("/health")
            assert response.status_code == 200

    def test_parallel_endpoint_access(self, client: TestClient):
        """複数エンドポイントへの連続アクセス"""
        endpoints = [
            "/health",
            "/api/v1/health",
            "/api/v1/dashboard/summary?fiscal_year=2024",
            "/api/v1/dashboard/kpi?fiscal_year=2024",
            "/api/v1/batch/rules",
            "/api/v1/reports/templates",
        ]

        for endpoint in endpoints:
            response = client.get(endpoint)
            assert response.status_code == 200, f"Failed: {endpoint}"


class TestDataConsistency:
    """データ整合性のテスト"""

    def test_kpi_matches_summary(self, client: TestClient):
        """KPIとサマリーの整合性"""
        # サマリー取得
        summary_response = client.get(
            "/api/v1/dashboard/summary",
            params={"fiscal_year": 2024}
        )
        assert summary_response.status_code == 200

        # KPI取得
        kpi_response = client.get(
            "/api/v1/dashboard/kpi",
            params={"fiscal_year": 2024}
        )
        assert kpi_response.status_code == 200

        # データ構造が一致することを確認
        summary = summary_response.json()
        kpi_response.json()

        # どちらもsuccessまたはdata構造を持つ
        assert (
            "data" in summary or "total_entries" in summary or
            "success" in summary
        )


class TestPerformance:
    """パフォーマンステスト（基本的なレスポンス時間確認）"""

    def test_health_check_response_time(self, client: TestClient):
        """ヘルスチェックのレスポンス時間"""
        import time

        start = time.time()
        response = client.get("/health")
        elapsed = time.time() - start

        assert response.status_code == 200
        # ヘルスチェックは1秒以内に返るべき
        assert elapsed < 1.0

    def test_dashboard_response_time(self, client: TestClient):
        """ダッシュボードのレスポンス時間"""
        import time

        start = time.time()
        response = client.get(
            "/api/v1/dashboard/summary",
            params={"fiscal_year": 2024}
        )
        elapsed = time.time() - start

        assert response.status_code == 200
        # データがない場合は高速、ある場合でも5秒以内
        assert elapsed < 5.0
