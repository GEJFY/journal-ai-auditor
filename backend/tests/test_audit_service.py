"""Audit service and API tests."""

from fastapi.testclient import TestClient


class TestAuditTrailAPI:
    """Audit trail endpoint tests."""

    def test_get_audit_events_empty(self, client: TestClient):
        """Test getting audit events returns list."""
        response = client.get("/api/v1/audit-trail")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data
        assert isinstance(data["events"], list)

    def test_get_audit_event_not_found(self, client: TestClient):
        """Test getting non-existent audit event returns 404."""
        response = client.get("/api/v1/audit-trail/99999")
        assert response.status_code == 404

    def test_get_audit_events_with_filters(self, client: TestClient):
        """Test audit events with query filters."""
        response = client.get(
            "/api/v1/audit-trail",
            params={"event_type": "import", "limit": 10, "offset": 0},
        )
        assert response.status_code == 200
        data = response.json()
        assert "events" in data


class TestAuditService:
    """AuditService unit tests."""

    def test_log_and_retrieve_event(self):
        """Test logging an event and retrieving it."""
        from app.services.audit_service import AuditService

        service = AuditService()
        event_id = service.log_event(
            "test",
            "create",
            user_id="test_user",
            resource_type="test_resource",
            resource_id="123",
            description="Test event",
            details={"key": "value"},
        )
        assert event_id > 0

        # Retrieve by ID
        event = service.get_event_by_id(event_id)
        assert event is not None
        assert event["event_type"] == "test"
        assert event["event_action"] == "create"
        assert event["user_id"] == "test_user"
        assert event["details"] == {"key": "value"}

    def test_get_events_with_filter(self):
        """Test getting events with type filter."""
        from app.services.audit_service import AuditService

        service = AuditService()
        # Log events of different types
        service.log_event("import", "create", description="Import 1")
        service.log_event("settings", "update", description="Settings 1")
        service.log_event("import", "create", description="Import 2")

        result = service.get_events(event_type="import")
        assert result["total"] >= 2
        for evt in result["events"]:
            assert evt["event_type"] == "import"
