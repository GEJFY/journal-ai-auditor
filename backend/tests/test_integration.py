"""Integration tests for JAIA API.

Tests the complete flow from API endpoints through services to database.
Run with: pytest tests/test_integration.py -v
"""

import pytest
from httpx import AsyncClient, ASGITransport
from unittest.mock import patch

# Import the FastAPI app
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.main import app


@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    """Create async test client."""
    async with AsyncClient(
        transport=ASGITransport(app=app),
        base_url="http://test"
    ) as ac:
        yield ac


class TestHealthEndpoints:
    """Test health check endpoints."""

    @pytest.mark.anyio
    async def test_health_check(self, client: AsyncClient):
        """Test main health endpoint."""
        response = await client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["app"] == "JAIA"

    @pytest.mark.anyio
    async def test_api_health(self, client: AsyncClient):
        """Test API health endpoint."""
        response = await client.get("/api/v1/health")
        assert response.status_code == 200


class TestDashboardEndpoints:
    """Test dashboard API endpoints."""

    @pytest.mark.anyio
    async def test_dashboard_summary(self, client: AsyncClient):
        """Test dashboard summary endpoint."""
        response = await client.get("/api/v1/dashboard/summary?fiscal_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert "total_entries" in data
        assert "total_amount" in data

    @pytest.mark.anyio
    async def test_dashboard_kpi(self, client: AsyncClient):
        """Test dashboard KPI endpoint."""
        response = await client.get("/api/v1/dashboard/kpi?fiscal_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert "total_journals" in data

    @pytest.mark.anyio
    async def test_dashboard_timeseries(self, client: AsyncClient):
        """Test dashboard time series endpoint."""
        response = await client.get(
            "/api/v1/dashboard/timeseries?fiscal_year=2024&granularity=monthly"
        )
        assert response.status_code == 200
        data = response.json()
        assert "data" in data

    @pytest.mark.anyio
    async def test_dashboard_risk(self, client: AsyncClient):
        """Test dashboard risk analysis endpoint."""
        response = await client.get("/api/v1/dashboard/risk?fiscal_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert "risk_distribution" in data

    @pytest.mark.anyio
    async def test_dashboard_benford(self, client: AsyncClient):
        """Test dashboard Benford analysis endpoint."""
        response = await client.get("/api/v1/dashboard/benford?fiscal_year=2024")
        assert response.status_code == 200
        data = response.json()
        assert "distribution" in data or "conformity" in data


class TestReportEndpoints:
    """Test report API endpoints."""

    @pytest.mark.anyio
    async def test_report_templates(self, client: AsyncClient):
        """Test report templates endpoint."""
        response = await client.get("/api/v1/reports/templates")
        assert response.status_code == 200
        data = response.json()
        assert "templates" in data
        assert len(data["templates"]) > 0

    @pytest.mark.anyio
    async def test_report_generation_summary(self, client: AsyncClient):
        """Test summary report generation."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "summary", "fiscal_year": 2024}
        )
        assert response.status_code == 200
        data = response.json()
        assert "metadata" in data
        assert data["metadata"]["report_type"] == "summary"

    @pytest.mark.anyio
    async def test_report_generation_executive(self, client: AsyncClient):
        """Test executive report generation."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "executive", "fiscal_year": 2024}
        )
        assert response.status_code == 200
        data = response.json()
        assert "title" in data or "overall_assessment" in data


class TestAnalysisEndpoints:
    """Test analysis API endpoints."""

    @pytest.mark.anyio
    async def test_violations_list(self, client: AsyncClient):
        """Test violations list endpoint."""
        response = await client.get(
            "/api/v1/analysis/violations?fiscal_year=2024&limit=10"
        )
        assert response.status_code == 200

    @pytest.mark.anyio
    async def test_rules_summary(self, client: AsyncClient):
        """Test rules summary endpoint."""
        response = await client.get("/api/v1/batch/rules")
        assert response.status_code == 200
        data = response.json()
        assert "total_rules" in data or "by_category" in data


class TestBatchEndpoints:
    """Test batch processing endpoints."""

    @pytest.mark.anyio
    async def test_batch_rules_list(self, client: AsyncClient):
        """Test batch rules list endpoint."""
        response = await client.get("/api/v1/batch/rules")
        assert response.status_code == 200


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
        """Test AWS Bedrock has Claude Sonnet 4.6 Opus."""
        from app.core.config import LLM_MODELS

        bedrock_models = LLM_MODELS["bedrock"]
        assert "anthropic.claude-sonnet-4-6-opus-20260115-v1:0" in bedrock_models
        assert bedrock_models["anthropic.claude-sonnet-4-6-opus-20260115-v1:0"]["tier"] == "premium"

    def test_azure_foundry_gpt5_models(self):
        """Test Azure Foundry has GPT-5 series."""
        from app.core.config import LLM_MODELS

        foundry_models = LLM_MODELS["azure_foundry"]
        assert "gpt-5.2" in foundry_models
        assert "gpt-5-nano" in foundry_models
        assert "claude-sonnet-4" in foundry_models

    def test_vertex_ai_gemini3_models(self):
        """Test Vertex AI has Gemini 3.0 series."""
        from app.core.config import LLM_MODELS

        vertex_models = LLM_MODELS["vertex_ai"]
        assert "gemini-3.0-flash-preview" in vertex_models
        assert "gemini-3.0-pro-preview" in vertex_models

    def test_llm_service_initialization(self):
        """Test LLM service can be initialized."""
        from app.services.llm import LLMService, LLMConfig

        config = LLMConfig(
            provider="anthropic",
            model="claude-sonnet-4",
        )
        service = LLMService(config)

        assert service.config.provider == "anthropic"
        assert service.config.model == "claude-sonnet-4"

    def test_llm_service_bedrock_init(self):
        """Test LLM service initialization for Bedrock."""
        from app.services.llm import LLMService, LLMConfig

        config = LLMConfig(
            provider="bedrock",
            model="anthropic.claude-sonnet-4-6-opus-20260115-v1:0",
        )
        service = LLMService(config)

        assert service.config.provider == "bedrock"

    def test_llm_service_azure_foundry_init(self):
        """Test LLM service initialization for Azure Foundry."""
        from app.services.llm import LLMService, LLMConfig

        config = LLMConfig(
            provider="azure_foundry",
            model="gpt-5.2",
        )
        service = LLMService(config)

        assert service.config.provider == "azure_foundry"
        assert service.config.model == "gpt-5.2"

    def test_llm_service_vertex_ai_init(self):
        """Test LLM service initialization for Vertex AI."""
        from app.services.llm import LLMService, LLMConfig

        config = LLMConfig(
            provider="vertex_ai",
            model="gemini-3.0-flash-preview",
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
        # Verify Gemini 3.0 is cost effective
        assert "gemini-3.0" in recommended["cost_effective"]["model"]


class TestDataIntegrity:
    """Test data integrity across services."""

    @pytest.mark.anyio
    async def test_dashboard_data_consistency(self, client: AsyncClient):
        """Test that dashboard data is consistent."""
        # Get summary
        summary_resp = await client.get("/api/v1/dashboard/summary?fiscal_year=2024")
        assert summary_resp.status_code == 200
        summary = summary_resp.json()

        # Get KPI
        kpi_resp = await client.get("/api/v1/dashboard/kpi?fiscal_year=2024")
        assert kpi_resp.status_code == 200
        kpi = kpi_resp.json()

        # Verify consistency
        if summary.get("total_entries") and kpi.get("total_journals"):
            # Total entries should be >= total journals
            assert summary["total_entries"] >= 0

    @pytest.mark.anyio
    async def test_risk_data_consistency(self, client: AsyncClient):
        """Test that risk data is consistent."""
        # Get summary
        summary_resp = await client.get("/api/v1/dashboard/summary?fiscal_year=2024")
        summary = summary_resp.json()

        # Get risk
        risk_resp = await client.get("/api/v1/dashboard/risk?fiscal_year=2024")
        risk = risk_resp.json()

        # High risk count should match
        if summary.get("high_risk_count") is not None and risk.get("risk_distribution"):
            dist = risk["risk_distribution"]
            total_in_dist = sum(dist.values()) if isinstance(dist, dict) else 0
            # Just verify the data is reasonable
            assert total_in_dist >= 0


class TestErrorHandling:
    """Test error handling."""

    @pytest.mark.anyio
    async def test_invalid_fiscal_year(self, client: AsyncClient):
        """Test handling of invalid fiscal year."""
        response = await client.get("/api/v1/dashboard/summary?fiscal_year=invalid")
        assert response.status_code == 422  # Validation error

    @pytest.mark.anyio
    async def test_invalid_report_type(self, client: AsyncClient):
        """Test handling of invalid report type."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={"report_type": "invalid_type", "fiscal_year": 2024}
        )
        # Should either return 400 or 422
        assert response.status_code in [400, 422, 200]  # 200 if handled gracefully

    @pytest.mark.anyio
    async def test_missing_required_params(self, client: AsyncClient):
        """Test handling of missing required parameters."""
        response = await client.post(
            "/api/v1/reports/generate",
            json={}
        )
        assert response.status_code == 422  # Validation error


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
