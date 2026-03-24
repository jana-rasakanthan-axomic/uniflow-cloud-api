"""Rate limiting middleware using sliding window algorithm."""

import asyncio
import time
from collections import deque
from collections.abc import Callable


class RateLimiter:
    """
    In-memory rate limiter using sliding window algorithm.

    This implementation uses a deque to store timestamps of requests per key,
    providing O(W) performance where W is the number of requests in the window.
    """

    def __init__(self, requests: int, window_seconds: int, key_func: Callable = None):
        """
        Initialize rate limiter.

        Args:
            requests: Maximum requests allowed within the window
            window_seconds: Time window in seconds (60 for per-minute limiting)
            key_func: Optional function to extract rate limit key from Request
        """
        self.requests = requests
        self.window_seconds = window_seconds
        self.key_func = key_func

        # Storage: key -> deque of request timestamps
        self._requests: dict[str, deque] = {}

        # Per-key locks for thread safety
        self._locks: dict[str, asyncio.Lock] = {}

    async def check_limit(self, key: str) -> tuple[bool, int]:
        """
        Check if request is allowed under rate limit.

        Args:
            key: Rate limit key (e.g., IP address, user_id, agent_id)

        Returns:
            tuple: (is_allowed: bool, retry_after_seconds: int)
                - is_allowed: True if request should be processed
                - retry_after_seconds: Seconds to wait before retry (0 if allowed)
        """
        # Get or create lock for this key
        if key not in self._locks:
            self._locks[key] = asyncio.Lock()

        async with self._locks[key]:
            now = time.time()

            # Initialize deque for new keys
            if key not in self._requests:
                self._requests[key] = deque()

            request_times = self._requests[key]

            # Remove expired timestamps (outside the window)
            cutoff_time = now - self.window_seconds
            while request_times and request_times[0] < cutoff_time:
                request_times.popleft()

            # Check if limit is exceeded
            if len(request_times) >= self.requests:
                # Calculate retry_after: time until oldest request expires
                if request_times:
                    oldest_timestamp = request_times[0]
                    retry_after = int(self.window_seconds - (now - oldest_timestamp)) + 1
                else:
                    retry_after = self.window_seconds

                return False, retry_after

            # Allow request and record timestamp
            request_times.append(now)

            # Cleanup: remove key if deque is empty after window
            # This helps prevent memory leaks from abandoned keys
            if len(request_times) == 0:
                del self._requests[key]
                del self._locks[key]

            return True, 0
