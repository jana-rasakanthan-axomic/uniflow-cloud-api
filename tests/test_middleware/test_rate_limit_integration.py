"""Integration tests for router-specific rate limiting."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class TestAuthRouterRateLimit:
    """Test auth router rate limit (20 req/min/IP)."""

    def test_auth_router_rate_limit_20_per_minute(self):
        """Auth router should block 21st request from same IP."""
        # Make 20 requests - should all succeed
        for i in range(20):
            response = client.post("/api/v1/auth/login", json={})
            assert response.status_code in [200, 422], f"Request {i+1} should be allowed"

        # 21st request should be rate limited
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 429, "21st request should be rate limited"
        assert "retry-after" in response.headers, "429 should include Retry-After header"

    def test_auth_429_includes_retry_after_header(self):
        """429 response must include Retry-After header."""
        # Exhaust limit
        for _ in range(20):
            client.post("/api/v1/auth/login", json={})

        # Get rate limited response
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 429
        assert "retry-after" in response.headers

        retry_after = int(response.headers["retry-after"])
        assert retry_after > 0, "Retry-After should be positive"
        assert retry_after <= 60, "Retry-After should not exceed window"


class TestWebRouterRateLimit:
    """Test web router rate limit (120 req/min/user)."""

    def test_web_router_rate_limit_120_per_minute(self):
        """Web router should block 121st request from same user."""
        # Make 120 requests - should all succeed or return auth errors
        for i in range(120):
            response = client.get(
                "/api/v1/dashboard",
                headers={"X-User-ID": "test-user-123"},  # Placeholder for JWT
            )
            # Accept 200, 401, or 422 but not 429
            assert response.status_code != 429, f"Request {i+1} should not be rate limited"

        # 121st request should be rate limited
        response = client.get(
            "/api/v1/dashboard", headers={"X-User-ID": "test-user-123"}
        )
        assert response.status_code == 429, "121st request should be rate limited"
        assert "retry-after" in response.headers


class TestEdgeRouterRateLimit:
    """Test edge router rate limit (60 req/min/agent)."""

    def test_edge_router_rate_limit_60_per_minute(self):
        """Edge router should block 61st request from same agent."""
        # Make 60 requests - should all succeed or return auth errors
        for i in range(60):
            response = client.post(
                "/api/v1/edge/heartbeat",
                json={},
                headers={"X-Agent-ID": "test-agent-456"},  # Placeholder for JWT
            )
            # Accept 200, 401, or 422 but not 429
            assert response.status_code != 429, f"Request {i+1} should not be rate limited"

        # 61st request should be rate limited
        response = client.post(
            "/api/v1/edge/heartbeat",
            json={},
            headers={"X-Agent-ID": "test-agent-456"},
        )
        assert response.status_code == 429, "61st request should be rate limited"
        assert "retry-after" in response.headers


class TestRateLimitIsolation:
    """Test that rate limits are independent per router."""

    def test_edge_flood_does_not_affect_web(self):
        """1000 edge requests should not affect web router."""
        # Flood edge router with different agent IDs
        for i in range(100):
            agent_id = f"agent-{i % 10}"  # Use 10 different agents
            for _ in range(10):
                client.post(
                    "/api/v1/edge/heartbeat",
                    json={},
                    headers={"X-Agent-ID": agent_id},
                )

        # Web router should still be responsive
        response = client.get(
            "/api/v1/dashboard", headers={"X-User-ID": "web-user-999"}
        )
        assert response.status_code != 429, "Web should not be affected by edge flood"

    def test_auth_and_web_have_independent_counters(self):
        """Auth rate limit should not affect web rate limit."""
        # Exhaust auth limit
        for _ in range(20):
            client.post("/api/v1/auth/login", json={})

        # Auth should be rate limited
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 429, "Auth should be rate limited"

        # Web should still work (independent counter)
        response = client.get(
            "/api/v1/dashboard", headers={"X-User-ID": "independent-user"}
        )
        assert response.status_code != 429, "Web should have independent rate limit"

    def test_different_users_have_independent_web_limits(self):
        """Different users should have separate web rate limit counters."""
        # User 1: exhaust limit
        for _ in range(120):
            client.get("/api/v1/dashboard", headers={"X-User-ID": "user-1"})

        # User 1: should be blocked
        response = client.get("/api/v1/dashboard", headers={"X-User-ID": "user-1"})
        assert response.status_code == 429, "user-1 should be rate limited"

        # User 2: should still work (independent counter)
        response = client.get("/api/v1/dashboard", headers={"X-User-ID": "user-2"})
        assert response.status_code != 429, "user-2 should have independent counter"


class TestRateLimitKeyExtraction:
    """Test rate limit key extraction functions."""

    def test_auth_uses_ip_as_key(self):
        """Auth router should rate limit by IP address."""
        # Same IP, different requests should share counter
        # TestClient uses 127.0.0.1 by default

        # Make 20 requests to auth
        for _ in range(20):
            client.post("/api/v1/auth/login", json={})

        # 21st should be blocked
        response = client.post("/api/v1/auth/login", json={})
        assert response.status_code == 429

    def test_web_uses_user_id_as_key(self):
        """Web router should rate limit by user_id from header."""
        # Same user_id should share counter
        user_id = "test-user-key-extraction"

        # Make 120 requests with same user_id
        for _ in range(120):
            client.get("/api/v1/dashboard", headers={"X-User-ID": user_id})

        # 121st should be blocked
        response = client.get("/api/v1/dashboard", headers={"X-User-ID": user_id})
        assert response.status_code == 429

    def test_edge_uses_agent_id_as_key(self):
        """Edge router should rate limit by agent_id from header."""
        # Same agent_id should share counter
        agent_id = "test-agent-key-extraction"

        # Make 60 requests with same agent_id
        for _ in range(60):
            client.post(
                "/api/v1/edge/heartbeat", json={}, headers={"X-Agent-ID": agent_id}
            )

        # 61st should be blocked
        response = client.post(
            "/api/v1/edge/heartbeat", json={}, headers={"X-Agent-ID": agent_id}
        )
        assert response.status_code == 429
