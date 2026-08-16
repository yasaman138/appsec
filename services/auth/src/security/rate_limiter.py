import time
from collections import defaultdict
from typing import Callable, Dict, List, Optional
from fastapi import HTTPException, Request, status
from services.auth.src.config import settings


class RateLimiter:
    """
    Sliding window rate limiter with in-memory storage and optional distributed Redis support.
    """
    def __init__(
        self,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self.key_func = key_func or self._default_key_func
        self._history: Dict[str, List[float]] = defaultdict(list)

    @staticmethod
    def _default_key_func(request: Request) -> str:
        # Extract client IP from forwarded header or direct client
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown_client"

    async def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMITING_ENABLED:
            return

        key = self.key_func(request)
        now = time.time()
        window_start = now - self.window_seconds

        # Prune old timestamps
        timestamps = self._history[key]
        self._history[key] = [t for t in timestamps if t > window_start]

        if len(self._history[key]) >= self.max_requests:
            retry_after = int(self.window_seconds - (now - self._history[key][0]))
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={"Retry-After": str(max(1, retry_after))},
            )

        self._history[key].append(now)

    def reset(self) -> None:
        self._history.clear()
