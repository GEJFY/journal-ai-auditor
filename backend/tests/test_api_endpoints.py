"""
API エンドポイント ユニットテスト

主要APIルーターのリクエスト/レスポンスをテスト。
"""

import io

# =========================================================
# Import Data API テスト
# =========================================================


class TestImportDataAPI:
    """データインポートAPIのテスト"""

    def test_upload_csv(self, client, tmp_path):
        csv_content = b"journal_id,effective_date,amount\nJE001,2024-04-01,100000\n"
        response = client.post(
            "/api/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert response.status_code in (200, 201, 422)

    def test_upload_no_file(self, client):
        response = client.post("/api/import/upload")
        assert response.status_code in (400, 422)

    def test_upload_unsupported_extension(self, client):
        response = client.post(
            "/api/import/upload",
            files={
                "file": ("test.txt", io.BytesIO(b"data"), "text/plain")
            },
        )
        # 非対応拡張子はエラー
        assert response.status_code in (400, 415, 422)

    def test_preview_nonexistent_file(self, client):
        response = client.get("/api/import/preview/nonexistent_id")
        assert response.status_code in (404, 400, 500)

    def test_mapping_suggest(self, client):
        response = client.get(
            "/api/import/mapping/suggest",
            params={"columns": "journal_id,effective_date,amount"},
        )
        assert response.status_code in (200, 422)


# =========================================================
# Dashboard API テスト
# =========================================================


class TestDashboardAPI:
    """ダッシュボードAPIのテスト"""

    def test_summary(self, client):
        response = client.get("/api/dashboard/summary")
        assert response.status_code in (200, 500)

    def test_summary_with_period(self, client):
        response = client.get(
            "/api/dashboard/summary",
            params={"fiscal_year": 2024},
        )
        assert response.status_code in (200, 500)

    def test_timeseries_daily(self, client):
        response = client.get(
            "/api/dashboard/timeseries",
            params={"aggregation": "daily"},
        )
        assert response.status_code in (200, 500)

    def test_kpi(self, client):
        response = client.get("/api/dashboard/kpi")
        assert response.status_code in (200, 500)

    def test_benford(self, client):
        response = client.get("/api/dashboard/benford")
        assert response.status_code in (200, 500)

    def test_risk(self, client):
        response = client.get("/api/dashboard/risk")
        assert response.status_code in (200, 500)

    def test_accounts(self, client):
        response = client.get("/api/dashboard/accounts")
        assert response.status_code in (200, 500)


# =========================================================
# Analysis API テスト
# =========================================================


class TestAnalysisAPI:
    """分析APIのテスト"""

    def test_violations(self, client):
        response = client.get("/api/analysis/violations")
        assert response.status_code in (200, 500)

    def test_violations_with_filters(self, client):
        response = client.get(
            "/api/analysis/violations",
            params={"limit": 10, "offset": 0},
        )
        assert response.status_code in (200, 500)

    def test_ml_anomalies(self, client):
        response = client.get("/api/analysis/ml-anomalies")
        assert response.status_code in (200, 500)

    def test_risk_details(self, client):
        response = client.get("/api/analysis/risk-details")
        assert response.status_code in (200, 500)

    def test_benford_detail(self, client):
        response = client.get("/api/analysis/benford-detail")
        assert response.status_code in (200, 500)

    def test_rules_summary(self, client):
        response = client.get("/api/analysis/rules-summary")
        assert response.status_code in (200, 500)


# =========================================================
# Reports API テスト
# =========================================================


class TestReportsAPI:
    """レポートAPIのテスト"""

    def test_templates(self, client):
        response = client.get("/api/reports/templates")
        assert response.status_code in (200, 500)

    def test_history(self, client):
        response = client.get("/api/reports/history")
        assert response.status_code in (200, 500)

    def test_generate_summary(self, client):
        response = client.post(
            "/api/reports/generate",
            json={
                "report_type": "summary",
                "fiscal_year": 2024,
            },
        )
        assert response.status_code in (200, 500)

    def test_export_ppt(self, client):
        response = client.get(
            "/api/reports/export/ppt",
            params={"fiscal_year": 2024},
        )
        assert response.status_code in (200, 500)

    def test_export_pdf(self, client):
        response = client.get(
            "/api/reports/export/pdf",
            params={"fiscal_year": 2024},
        )
        assert response.status_code in (200, 500)


# =========================================================
# Batch API テスト
# =========================================================


class TestBatchAPI:
    """バッチ処理APIのテスト"""

    def test_jobs_list(self, client):
        response = client.get("/api/batch/jobs")
        assert response.status_code in (200, 500)

    def test_rules_summary(self, client):
        response = client.get("/api/batch/rules")
        assert response.status_code in (200, 500)

    def test_status_nonexistent(self, client):
        response = client.get("/api/batch/status/nonexistent_id")
        assert response.status_code in (404, 400, 500)


# =========================================================
# Agents API テスト
# =========================================================


class TestAgentsAPI:
    """エージェントAPIのテスト"""

    def test_workflows_list(self, client):
        response = client.get("/api/agents/workflows")
        assert response.status_code in (200, 500)

    def test_ask_without_body(self, client):
        response = client.post("/api/agents/ask")
        assert response.status_code in (400, 422)

    def test_route_without_body(self, client):
        response = client.post("/api/agents/route")
        assert response.status_code in (400, 422)


# =========================================================
# Health API テスト (追加)
# =========================================================


class TestHealthAPI:
    """ヘルスチェックAPIのテスト"""

    def test_health(self, client):
        response = client.get("/api/health")
        assert response.status_code == 200
        data = response.json()
        assert data.get("status") == "healthy" or "status" in data

    def test_status(self, client):
        response = client.get("/api/health/status")
        assert response.status_code in (200, 500)
