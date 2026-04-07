"""Per-IP rate limiting middleware using an in-memory token bucket.

Implements C-SEC-04 from the controls catalog. Configurable via settings:
  - RATE_LIMIT_DEFAULT:  general endpoints  (e.g. "100/minute")
  - RATE_LIMIT_LOGIN:    auth endpoints      (e.g. "10/minute")
  - RATE_LIMIT_UPLOAD:   upload endpoints    (e.g. "20/minute")

Design notes:
  - In-memory store — suitable for single-instance or low-replica deploys.
    For horizontal scaling, swap the _buckets dict for a Redis backend.
  - Old bucket entries are lazily evicted to prevent unbounded memory growth.
  - Rate limit violations are logged for detective controls (T06).
  - Health endpoints are excluded from rate limiting.
"""

import time
from dataclasses import dataclass, field
from typing import Callable

from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from app.core.logging import get_logger

logger = get_logger(component="rate_limit")

# Paths that are never rate-limited
_EXEMPT_PREFIXES = ("/health/",)

# Evict bucket entries older than this (seconds)
_EVICTION_AGE = 600


def _parse_rate(rate_str: str) -> tuple[int, float]:
    """Parse a rate string like '100/minute' into (max_tokens, refill_period_seconds)."""
    count_str, _, period = rate_str.partition("/")
    count = int(count_str)
    periods = {"second": 1.0, "minute": 60.0, "hour": 3600.0}
    seconds = periods.get(period, 60.0)
    return count, seconds


@dataclass
class _Bucket:
    tokens: float
    max_tokens: int
    refill_rate: float  # tokens per second
    last_refill: float = field(default_factory=time.monotonic)
    last_access: float = field(default_factory=time.monotonic)

    def consume(self) -> bool:
        """Try to consume one token. Returns True if allowed."""
        now = time.monotonic()
        elapsed = now - self.last_refill
        self.tokens = min(self.max_tokens, self.tokens + elapsed * self.refill_rate)
        self.last_refill = now
        self.last_access = now
        if self.tokens >= 1.0:
            self.tokens -= 1.0
            return True
        return False

    @property
    def retry_after(self) -> float:
        """Seconds until at least one token is available."""
        if self.tokens >= 1.0:
            return 0.0
        return (1.0 - self.tokens) / self.refill_rate


class RateLimitMiddleware(BaseHTTPMiddleware):
    """Token-bucket rate limiter keyed by client IP address."""

    def __init__(self, app, *, default_rate: str = "100/minute") -> None:
        super().__init__(app)
        max_tokens, period = _parse_rate(default_rate)
        self._max_tokens = max_tokens
        self._refill_rate = max_tokens / period
        self._buckets: dict[str, _Bucket] = {}
        self._last_eviction = time.monotonic()

    def _get_client_ip(self, request: Request) -> str:
        """Extract client IP, respecting X-Forwarded-For behind a trusted proxy."""
        forwarded = request.headers.get("x-forwarded-for")
        if forwarded:
            return forwarded.split(",")[0].strip()
        return request.client.host if request.client else "unknown"

    def _get_bucket(self, key: str) -> _Bucket:
        if key not in self._buckets:
            self._buckets[key] = _Bucket(
                tokens=float(self._max_tokens),
                max_tokens=self._max_tokens,
                refill_rate=self._refill_rate,
            )
        return self._buckets[key]

    def _maybe_evict(self) -> None:
        """Lazily evict stale bucket entries to prevent memory growth."""
        now = time.monotonic()
        if now - self._last_eviction < _EVICTION_AGE:
            return
        self._last_eviction = now
        cutoff = now - _EVICTION_AGE
        stale = [k for k, v in self._buckets.items() if v.last_access < cutoff]
        for k in stale:
            del self._buckets[k]

    async def dispatch(self, request: Request, call_next: RequestResponseEndpoint) -> Response:
        # Skip rate limiting for health endpoints
        if any(request.url.path.startswith(p) for p in _EXEMPT_PREFIXES):
            return await call_next(request)

        client_ip = self._get_client_ip(request)
        bucket = self._get_bucket(client_ip)

        if not bucket.consume():
            retry_after = int(bucket.retry_after) + 1
            logger.warning(
                "rate_limit_exceeded",
                client_ip=client_ip,
                path=request.url.path,
                retry_after=retry_after,
            )
            return JSONResponse(
                status_code=429,
                content={
                    "error": "rate_limit_exceeded",
                    "detail": "Too many requests. Please retry later.",
                    "retry_after_seconds": retry_after,
                },
                headers={"Retry-After": str(retry_after)},
            )

        self._maybe_evict()

        response = await call_next(request)
        # Include rate limit info in response headers
        response.headers["X-RateLimit-Limit"] = str(self._max_tokens)
        response.headers["X-RateLimit-Remaining"] = str(int(bucket.tokens))
        return response
