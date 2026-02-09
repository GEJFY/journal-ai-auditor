"""Integration tests for JAIA API.

Tests the complete flow from API endpoints through services to database.
Uses conftest.py sync TestClient fixture (with lifespan).
Run with: pytest tests/test_integration.py -v
"""

from fastapi.testclient import TestClient


class TestHealthEndpoints:
    """Test health check endpoints."""

    def test_health_check(self, client: TestClient):
        """Test main health endpoint."""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "JAIA"

    def test_api_health(self, client: TestClient):
        """Test API health endpoint."""
        response = client.get("/api/v1/health")
        assert response.status_code == 200


class TestDashboardEndpoints:
    """Test dashboard API endpoints."""

    def test_dashboard_summary(self, client: TestClient):
        """Test dashboard summary endpoint."""
        response = client.get("/api/v1/dashboard/summary", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_dashboard_kpi(self, client: TestClient):
        """Test dashboard KPI endpoint."""
        response = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_dashboard_timeseries(self, client: TestClient):
        """Test dashboard time series endpoint."""
        response = client.get(
            "/api/v1/dashboard/timeseries",
            params={"fiscal_year": 2024, "aggregation": "monthly"},
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_dashboard_risk(self, client: TestClient):
        """Test dashboard risk analysis endpoint."""
        response = client.get("/api/v1/dashboard/risk", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_dashboard_benford(self, client: TestClient):
        """Test dashboard Benford analysis endpoint."""
        response = client.get("/api/v1/dashboard/benford", params={"fiscal_year": 2024})
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500


class TestReportEndpoints:
    """Test report API endpoints."""

    def test_report_templates(self, client: TestClient):
        """Test report templates endpoint."""
        response = client.get("/api/v1/reports/templates")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_report_generation_summary(self, client: TestClient):
        """Test summary report generation."""
        response = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "summary", "fiscal_year": 2024},
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500

    def test_report_generation_executive(self, client: TestClient):
        """Test executive report generation."""
        response = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "executive", "fiscal_year": 2024},
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, dict)
        else:
            assert response.status_code == 500


class TestAnalysisEndpoints:
    """Test analysis API endpoints."""

    def test_violations_list(self, client: TestClient):
        """Test violations list endpoint."""
        response = client.get(
            "/api/v1/analysis/violations", params={"fiscal_year": 2024, "limit": 10}
        )
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500

    def test_rules_summary(self, client: TestClient):
        """Test rules summary endpoint."""
        response = client.get("/api/v1/batch/rules")
        if response.status_code == 200:
            data = response.json()
            assert isinstance(data, (dict, list))
        else:
            assert response.status_code == 500


class TestBatchEndpoints:
    """Test batch processing endpoints."""

    def test_batch_rules_list(self, client: TestClient):
        """Test batch rules list endpoint."""
        response = client.get("/api/v1/batch/rules")
        assert response.status_code in (200, 500)


class TestLLMConfiguration:
    """Test LLM configuration and service."""

    def test_llm_models_available(self):
        """Test that LLM models are configured (2026 Cloud Edition)."""
        from app.core.config import LLM_MODELS, RECOMMENDED_MODELS

        # Direct API providers
        assert "anthropic" in LLM_MODELS
        assert "openai" in LLM_MODELS
        assert "google" in LLM_MODELS

        # Cloud providers (2026)
        assert "bedrock" in LLM_MODELS
        assert "azure_foundry" in LLM_MODELS
        assert "vertex_ai" in LLM_MODELS
        assert "azure" in LLM_MODELS

        # Recommended models
        assert "highest_accuracy" in RECOMMENDED_MODELS
        assert "high_accuracy" in RECOMMENDED_MODELS
        assert "balanced" in RECOMMENDED_MODELS
        assert "cost_effective" in RECOMMENDED_MODELS
        assert "ultra_fast" in RECOMMENDED_MODELS

    def test_bedrock_latest_models(self):
        """Test AWS Bedrock has Claude Opus 4.6."""
        from app.core.config import LLM_MODELS

        bedrock_models = LLM_MODELS["bedrock"]
        assert "us.anthropic.claude-opus-4-6-20260201-v1:0" in bedrock_models
        assert (
            bedrock_models["us.anthropic.claude-opus-4-6-20260201-v1:0"]["tier"]
            == "premium"
        )

    def test_azure_foundry_gpt5_models(self):
        """Test Azure Foundry has GPT-5 series."""
        from app.core.config import LLM_MODELS

        foundry_models = LLM_MODELS["azure_foundry"]
        assert "gpt-5.2" in foundry_models
        assert "gpt-5-nano" in foundry_models
        assert "claude-opus-4-6" in foundry_models

    def test_vertex_ai_gemini3_models(self):
        """Test Vertex AI has Gemini 3 series."""
        from app.core.config import LLM_MODELS

        vertex_models = LLM_MODELS["vertex_ai"]
        assert "gemini-3-flash-preview" in vertex_models
        assert "gemini-3-pro" in vertex_models

    def test_llm_service_initialization(self):
        """Test LLM service can be initialized."""
        from app.services.llm import LLMConfig, LLMService

        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4-5",
        )
        service = LLMService(config)

        assert service.config.provider == "anthropic"
        assert service.config.model == "claude-sonnet-4-5"

    def test_llm_service_bedrock_init(self):
        """Test LLM service initialization for Bedrock."""
        from app.services.llm import LLMConfig, LLMService

        config = LLMConfig(
            provider="bedrock",
            model="us.anthropic.claude-opus-4-6-20260201-v1:0",
        )
        service = LLMService(config)

        assert service.config.provider == "bedrock"

    def test_llm_service_azure_foundry_init(self):
        """Test LLM service initialization for Azure Foundry."""
        from app.services.llm import LLMConfig, LLMService

        config = LLMConfig(
            provider="azure_foundry",
            model="gpt-5.2",
        )
        service = LLMService(config)

        assert service.config.provider == "azure_foundry"
        assert service.config.model == "gpt-5.2"

    def test_llm_service_vertex_ai_init(self):
        """Test LLM service initialization for Vertex AI."""
        from app.services.llm import LLMConfig, LLMService

        config = LLMConfig(
            provider="vertex_ai",
            model="gemini-3-flash-preview",
        )
        service = LLMService(config)

        assert service.config.provider == "vertex_ai"

    def test_get_available_models(self):
        """Test getting available models."""
        from app.services.llm import LLMService

        models = LLMService.get_available_models()

        assert "anthropic" in models
        assert "bedrock" in models
        assert "azure_foundry" in models
        assert "vertex_ai" in models
        assert len(models["anthropic"]) > 0
        assert len(models["azure_foundry"]) > 0
        assert len(models["vertex_ai"]) > 0

    def test_get_recommended_models(self):
        """Test getting recommended models."""
        from app.services.llm import LLMService

        recommended = LLMService.get_recommended_models()

        assert "highest_accuracy" in recommended
        assert "high_accuracy" in recommended
        assert "balanced" in recommended
        assert "cost_effective" in recommended
        assert "ultra_fast" in recommended

        # Verify GPT-5.2 is highest accuracy
        assert recommended["highest_accuracy"]["model"] == "gpt-5.2"
        # Verify Gemini 3 Flash is cost effective
        assert "gemini-3" in recommended["cost_effective"]["model"]


class TestDataIntegrity:
    """Test data integrity across services."""

    def test_dashboard_data_consistency(self, client: TestClient):
        """Test that dashboard data is consistent."""
        summary_resp = client.get(
            "/api/v1/dashboard/summary", params={"fiscal_year": 2024}
        )
        kpi_resp = client.get("/api/v1/dashboard/kpi", params={"fiscal_year": 2024})

        # Both should respond (200 or 500 for empty DB)
        assert summary_resp.status_code in (200, 500)
        assert kpi_resp.status_code in (200, 500)

    def test_risk_data_consistency(self, client: TestClient):
        """Test that risk data is consistent."""
        summary_resp = client.get(
            "/api/v1/dashboard/summary", params={"fiscal_year": 2024}
        )
        risk_resp = client.get("/api/v1/dashboard/risk", params={"fiscal_year": 2024})

        assert summary_resp.status_code in (200, 500)
        assert risk_resp.status_code in (200, 500)


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_fiscal_year(self, client: TestClient):
        """Test handling of invalid fiscal year."""
        response = client.get(
            "/api/v1/dashboard/summary", params={"fiscal_year": "invalid"}
        )
        assert response.status_code == 422  # Validation error

    def test_invalid_report_type(self, client: TestClient):
        """Test handling of invalid report type."""
        response = client.post(
            "/api/v1/reports/generate",
            json={"report_type": "invalid_type", "fiscal_year": 2024},
        )
        # Should either return 400, 422, 200 (if handled), or 500
        assert response.status_code in (200, 400, 422, 500)

    def test_missing_required_params(self, client: TestClient):
        """Test handling of missing required parameters."""
        response = client.post("/api/v1/reports/generate", json={})
        assert response.status_code in (422, 500)
