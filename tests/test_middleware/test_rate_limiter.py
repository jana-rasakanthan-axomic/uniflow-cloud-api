import asyncio
import time

from app.middleware.rate_limiter import RateLimiter


class TestRateLimiter:
    """Tests for the RateLimiter sliding window implementation."""

    def test_allows_requests_within_limit(self):
        """First N requests within window should pass."""
        limiter = RateLimiter(requests=5, window_seconds=60)

        for i in range(5):
            allowed, retry_after = asyncio.run(limiter.check_limit("test_key"))
            assert allowed is True, f"Request {i+1} should be allowed"
            assert retry_after == 0, "No retry delay when within limit"

    def test_blocks_requests_over_limit(self):
        """Request N+1 should return 429 with Retry-After."""
        limiter = RateLimiter(requests=5, window_seconds=60)

        # Make 5 allowed requests
        for _ in range(5):
            allowed, _ = asyncio.run(limiter.check_limit("test_key"))
            assert allowed is True

        # 6th request should be blocked
        allowed, retry_after = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is False, "Request over limit should be blocked"
        assert retry_after > 0, "Should return positive retry delay"
        assert retry_after <= 60, "Retry delay should not exceed window"

    def test_returns_429_with_retry_after(self):
        """429 response must include Retry-After header."""
        limiter = RateLimiter(requests=3, window_seconds=10)

        # Exhaust limit
        for _ in range(3):
            asyncio.run(limiter.check_limit("test_key"))

        # Next request should include retry_after
        allowed, retry_after = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is False
        assert retry_after > 0
        assert retry_after <= 10

    def test_different_keys_have_independent_counters(self):
        """Different keys should have separate rate limit counters."""
        limiter = RateLimiter(requests=2, window_seconds=60)

        # Key 1: use up limit
        for _ in range(2):
            allowed, _ = asyncio.run(limiter.check_limit("key1"))
            assert allowed is True

        # Key 1: should be blocked
        allowed, _ = asyncio.run(limiter.check_limit("key1"))
        assert allowed is False, "key1 should be blocked"

        # Key 2: should still be allowed (independent counter)
        allowed, _ = asyncio.run(limiter.check_limit("key2"))
        assert allowed is True, "key2 should have independent counter"

    def test_window_expires_and_resets(self):
        """Requests should be allowed after window expires."""
        limiter = RateLimiter(requests=2, window_seconds=1)

        # Use up limit
        for _ in range(2):
            allowed, _ = asyncio.run(limiter.check_limit("test_key"))
            assert allowed is True

        # Should be blocked
        allowed, _ = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is False

        # Wait for window to expire
        time.sleep(1.1)

        # Should be allowed again
        allowed, _ = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is True, "Requests should be allowed after window expires"

    def test_cleanup_removes_expired_entries(self):
        """Expired entries should be automatically cleaned up."""
        limiter = RateLimiter(requests=5, window_seconds=1)

        # Make some requests
        for _ in range(3):
            asyncio.run(limiter.check_limit("key1"))
            asyncio.run(limiter.check_limit("key2"))

        # Keys should exist in internal storage
        assert "key1" in limiter._requests
        assert "key2" in limiter._requests

        # Wait for window to expire
        time.sleep(1.1)

        # Make new request to trigger cleanup
        asyncio.run(limiter.check_limit("key1"))

        # After cleanup, old timestamps should be removed
        # (implementation should clean up during check_limit)
        assert len(limiter._requests["key1"]) <= 1, "Old timestamps should be cleaned up"

    def test_sliding_window_algorithm(self):
        """Window should slide correctly (not fixed bucket)."""
        limiter = RateLimiter(requests=3, window_seconds=2)

        # T=0: Make 3 requests
        for _ in range(3):
            allowed, _ = asyncio.run(limiter.check_limit("test_key"))
            assert allowed is True

        # T=0: 4th request should be blocked
        allowed, _ = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is False

        # T=1: Still blocked (within 2-second window)
        time.sleep(1.0)
        allowed, _ = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is False

        # T=2.1: Window has slid, should be allowed
        time.sleep(1.2)
        allowed, _ = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is True, "Sliding window should allow request after expiry"


class TestRateLimiterEdgeCases:
    """Edge case tests for rate limiter."""

    def test_zero_requests_always_blocks(self):
        """Rate limiter with 0 requests should always block."""
        limiter = RateLimiter(requests=0, window_seconds=60)

        allowed, retry_after = asyncio.run(limiter.check_limit("test_key"))
        assert allowed is False
        assert retry_after > 0

    def test_concurrent_requests_same_key(self):
        """Concurrent requests for same key should be properly counted."""
        limiter = RateLimiter(requests=10, window_seconds=60)

        async def make_request():
            return await limiter.check_limit("concurrent_key")

        async def run_concurrent():
            # Make 10 concurrent requests
            results = await asyncio.gather(*[make_request() for _ in range(10)])
            return results

        results = asyncio.run(run_concurrent())
        allowed_count = sum(1 for allowed, _ in results if allowed)

        # All 10 should be allowed (within limit)
        assert allowed_count == 10

        # 11th request should be blocked
        allowed, _ = asyncio.run(limiter.check_limit("concurrent_key"))
        assert allowed is False

    def test_empty_key_string(self):
        """Empty string key should be treated as valid key."""
        limiter = RateLimiter(requests=2, window_seconds=60)

        allowed, _ = asyncio.run(limiter.check_limit(""))
        assert allowed is True

        allowed, _ = asyncio.run(limiter.check_limit(""))
        assert allowed is True

        # 3rd request should be blocked
        allowed, _ = asyncio.run(limiter.check_limit(""))
        assert allowed is False
