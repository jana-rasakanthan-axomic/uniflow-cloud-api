"""Tests for router isolation and mounting."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestRouterMounting:
    """Test that all three routers are correctly mounted."""

    def test_auth_router_mounted_at_auth_prefix(self):
        """Auth router should be accessible at /api/v1/auth/."""
        response = client.post("/api/v1/auth/login", json={})
        # Expect a response (even if 422 for missing fields), not 404
        assert response.status_code != 404, "Auth router not mounted"

    def test_web_router_mounted_at_v1_prefix(self):
        """Web router should be accessible at /api/v1/."""
        response = client.get("/api/v1/dashboard")
        # Expect a response (even if 401 for no auth), not 404
        assert response.status_code != 404, "Web router not mounted"

    def test_edge_router_mounted_at_edge_prefix(self):
        """Edge router should be accessible at /api/v1/edge/."""
        response = client.post("/api/v1/edge/heartbeat", json={})
        # Expect a response (even if 422 for missing fields), not 404
        assert response.status_code != 404, "Edge router not mounted"

    def test_health_still_accessible(self):
        """Original health endpoint should still work."""
        response = client.get("/api/health")
        assert response.status_code == 200
        assert response.json() == {"status": "ok"}


class TestRouterIsolation:
    """Test that routers are in separate modules."""

    def test_routers_isolated_modules(self):
        """Each router should be importable from separate modules."""
        from app.api.routers import auth, edge, web

        assert hasattr(auth, "router"), "Auth module should export router"
        assert hasattr(web, "router"), "Web module should export router"
        assert hasattr(edge, "router"), "Edge module should export router"


class TestRouterTags:
    """Test that routers have correct OpenAPI tags."""

    def test_openapi_schema_has_three_router_tags(self):
        """OpenAPI schema should show three tagged groups in paths."""
        response = client.get("/openapi.json")
        assert response.status_code == 200

        schema = response.json()

        # Collect tags from all path operations
        tags_in_paths = set()
        for _path, methods in schema.get("paths", {}).items():
            for _method, operation in methods.items():
                if isinstance(operation, dict):
                    tags_in_paths.update(operation.get("tags", []))

        assert "auth" in tags_in_paths, "Auth tag missing from OpenAPI paths"
        assert "web" in tags_in_paths, "Web tag missing from OpenAPI paths"
        assert "edge" in tags_in_paths, "Edge tag missing from OpenAPI paths"
