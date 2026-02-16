"""Rules API endpoint tests."""

import pytest
from fastapi.testclient import TestClient

from app.db import SQLiteManager
from app.main import app


@pytest.fixture(autouse=True)
def _ensure_schema():
    """Ensure SQLite schema is initialized before each test."""
    db = SQLiteManager()
    db.initialize_schema()


@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)


class TestRulesAPI:
    """Rule management endpoint tests."""

    def test_get_rules_list(self, client: TestClient):
        """Test getting all rules."""
        response = client.get("/api/v1/rules")
        assert response.status_code == 200
        data = response.json()
        assert "rules" in data
        assert "total" in data
        assert data["total"] > 0

    def test_get_rules_by_category(self, client: TestClient):
        """Test filtering rules by category."""
        response = client.get("/api/v1/rules", params={"category": "AMOUNT"})
        assert response.status_code == 200
        data = response.json()
        for rule in data["rules"]:
            assert rule["category"] == "AMOUNT"

    def test_get_rule_categories(self, client: TestClient):
        """Test getting rule categories."""
        response = client.get("/api/v1/rules/categories")
        assert response.status_code == 200
        data = response.json()
        assert "categories" in data
        assert len(data["categories"]) > 0

        # Check structure
        cat = data["categories"][0]
        assert "category" in cat
        assert "total" in cat
        assert "enabled" in cat

    def test_get_single_rule(self, client: TestClient):
        """Test getting a single rule."""
        response = client.get("/api/v1/rules/AMOUNT_001")
        assert response.status_code == 200
        data = response.json()
        assert data["rule_id"] == "AMOUNT_001"
        assert data["is_enabled"] is True

    def test_get_rule_not_found(self, client: TestClient):
        """Test getting non-existent rule returns 404."""
        response = client.get("/api/v1/rules/NONEXISTENT")
        assert response.status_code == 404

    def test_update_rule_severity(self, client: TestClient):
        """Test updating rule severity."""
        response = client.put(
            "/api/v1/rules/AMOUNT_001",
            json={"severity": "HIGH"},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["severity"] == "HIGH"

    def test_update_rule_toggle_enabled(self, client: TestClient):
        """Test toggling rule enabled state."""
        # Disable
        response = client.put(
            "/api/v1/rules/AMOUNT_002",
            json={"is_enabled": False},
        )
        assert response.status_code == 200
        assert response.json()["is_enabled"] is False

        # Re-enable
        response = client.put(
            "/api/v1/rules/AMOUNT_002",
            json={"is_enabled": True},
        )
        assert response.status_code == 200
        assert response.json()["is_enabled"] is True

    def test_update_rule_invalid_severity(self, client: TestClient):
        """Test updating with invalid severity returns 400."""
        response = client.put(
            "/api/v1/rules/AMOUNT_001",
            json={"severity": "INVALID"},
        )
        assert response.status_code == 400

    def test_update_rule_no_fields(self, client: TestClient):
        """Test updating with no fields returns 400."""
        response = client.put(
            "/api/v1/rules/AMOUNT_001",
            json={},
        )
        assert response.status_code == 400

    def test_reset_rule(self, client: TestClient):
        """Test resetting rule to defaults."""
        # First modify
        client.put(
            "/api/v1/rules/AMOUNT_001",
            json={"severity": "CRITICAL", "is_enabled": False},
        )

        # Then reset
        response = client.post("/api/v1/rules/AMOUNT_001/reset")
        assert response.status_code == 200
        data = response.json()
        assert data["severity"] == "LOW"  # AMOUNT_001 default is LOW
        assert data["is_enabled"] is True

    def test_reset_nonexistent_rule(self, client: TestClient):
        """Test resetting non-existent rule returns 404."""
        response = client.post("/api/v1/rules/NONEXISTENT/reset")
        assert response.status_code == 404
