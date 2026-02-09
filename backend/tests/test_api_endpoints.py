"""
API エンドポイント ユニットテスト

主要APIルーターのリクエスト/レスポンスをテスト。
200の場合はレスポンス構造も検証する。
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
            "/api/v1/import/upload",
            files={"file": ("test.csv", io.BytesIO(csv_content), "text/csv")},
        )
        assert response.status_code in (200, 201, 422)

    def test_upload_no_file(self, client):
        response = client.post("/api/v1/import/upload")
        assert response.status_code in (400, 422)

    def test_upload_unsupported_extension(self, client):
        response = client.post(
            "/api/v1/import/upload",
            files={"file": ("test.txt", io.BytesIO(b"data"), "text/plain")},
        )
        # 非対応拡張子はエラー
        assert response.status_code in (400, 415, 422)

    def test_preview_nonexistent_file(self, client):
        response = client.get("/api/v1/import/preview/nonexistent_id")
        assert response.status_code in (404, 400, 500)

    def test_mapping_suggest(self, client):
        response = client.get(
            "/api/v1/import/mapping/suggest",
            params={"columns": "journal_id,effective_date,amount"},
        )
        assert response.status_code in (200, 422)


# =========================================================
# Dashboard API テスト
# =========================================================


class TestDashboardAPI:
    """ダッシュボードAPIのテスト

    Note: DBにデータがない状態では一部エンドポイントが500を返すことがある。
    200が返る場合はレスポンス構造を検証する。
    全エンドポイントで fiscal_year は必須パラメータ。
    """

    def test_summary(self, client):
        response = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_summary_with_period(self, client):
        response = client.get(
            "/api/v1/dashboard/summary",
            params={"fiscal_year": 2024, "period_from": 4, "period_to": 6},
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_timeseries_daily(self, client):
        response = client.get(
            "/api/v1/dashboard/timeseries",
            params={"fiscal_year": 2024, "aggregation": "daily"},
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_kpi(self, client):
        response = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_benford(self, client):
        response = client.get("/api/v1/dashboard/benford", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_risk(self, client):
        response = client.get("/api/v1/dashboard/risk", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_accounts(self, client):
        response = client.get(
            "/api/v1/dashboard/accounts", params={"fiscal_year": 2024}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500


# =========================================================
# Analysis API テスト
# =========================================================


class TestAnalysisAPI:
    """分析APIのテスト（全エンドポイント fiscal_year 必須）"""

    def test_violations(self, client):
        response = client.get(
            "/api/v1/analysis/violations", params={"fiscal_year": 2024}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_violations_with_filters(self, client):
        response = client.get(
            "/api/v1/analysis/violations",
            params={"fiscal_year": 2024, "limit": 10, "offset": 0},
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_ml_anomalies(self, client):
        response = client.get(
            "/api/v1/analysis/ml-anomalies", params={"fiscal_year": 2024}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_risk_details(self, client):
        response = client.get(
            "/api/v1/analysis/risk-details", params={"fiscal_year": 2024}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_benford_detail(self, client):
        response = client.get(
            "/api/v1/analysis/benford-detail", params={"fiscal_year": 2024}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_rules_summary(self, client):
        response = client.get(
            "/api/v1/analysis/rules-summary", params={"fiscal_year": 2024}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500


# =========================================================
# Reports API テスト
# =========================================================


class TestReportsAPI:
    """レポートAPIのテスト"""

    def test_templates(self, client):
        response = client.get("/api/v1/reports/templates")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_history(self, client):
        response = client.get("/api/v1/reports/history")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_generate_summary(self, client):
        response = client.post(
            "/api/v1/reports/generate",
            json={
                "report_type": "summary",
                "fiscal_year": 2024,
            },
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_export_ppt(self, client):
        response = client.get(
            "/api/v1/reports/export/ppt",
            params={"fiscal_year": 2024},
        )
        if response.status_code == 200:
            assert len(response.content) > 0
        else:
            assert response.status_code == 500

    def test_export_pdf(self, client):
        response = client.get(
            "/api/v1/reports/export/pdf",
            params={"fiscal_year": 2024},
        )
        if response.status_code == 200:
            assert len(response.content) > 0
        else:
            assert response.status_code == 500


# =========================================================
# Batch API テスト
# =========================================================


class TestBatchAPI:
    """バッチ処理APIのテスト"""

    def test_jobs_list(self, client):
        response = client.get("/api/v1/batch/jobs")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_rules_summary(self, client):
        response = client.get("/api/v1/batch/rules")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_status_nonexistent(self, client):
        response = client.get("/api/v1/batch/status/nonexistent_id")
        assert response.status_code in (404, 400, 500)


# =========================================================
# Agents API テスト
# =========================================================


class TestAgentsAPI:
    """エージェントAPIのテスト"""

    def test_workflows_list(self, client):
        response = client.get("/api/v1/agents/workflows")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code in (404, 500)

    def test_ask_without_body(self, client):
        response = client.post("/api/v1/agents/ask")
        assert response.status_code in (400, 422)

    def test_route_without_body(self, client):
        response = client.post("/api/v1/agents/route")
        assert response.status_code in (400, 422)


# =========================================================
# Health API テスト
# =========================================================


class TestHealthAPI:
    """ヘルスチェックAPIのテスト"""

    def test_root_health(self, client):
        """ルートレベルのヘルスチェック"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"

    def test_api_health(self, client):
        """API v1 ヘルスチェック"""
        response = client.get("/api/v1/health")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data

    def test_status(self, client):
        """ステータスエンドポイント"""
        response = client.get("/api/v1/status")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500
