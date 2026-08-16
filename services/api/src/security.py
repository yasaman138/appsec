from typing import Annotated, Optional
from fastapi import Depends, Header, HTTPException, status
import jwt
from pydantic import BaseModel
from services.api.src.config import settings


class AuthenticatedUser(BaseModel):
    user_id: str
    username: str
    email: str
    tenant_id: str
    role: str


async def get_current_user(
    authorization: Annotated[Optional[str], Header()] = None,
) -> AuthenticatedUser:
    if not authorization:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
            headers={"WWW-Authenticate": "Bearer"},
        )

    parts = authorization.split()
    if len(parts) != 2 or parts[0].lower() != "bearer":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Authorization header format. Expected 'Bearer <token>'",
            headers={"WWW-Authenticate": "Bearer"},
        )

    token = parts[1]
    try:
        payload = jwt.decode(
            token,
            settings.JWT_SECRET_KEY,
            algorithms=[settings.JWT_ALGORITHM],
            options={"verify_signature": True, "verify_exp": True},
        )
        user_id = payload.get("sub")
        username = payload.get("username")
        email = payload.get("email")
        tenant_id = payload.get("tenant_id")
        role = payload.get("role", "user")

        if not user_id or not tenant_id:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing required claims (sub, tenant_id)",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return AuthenticatedUser(
            user_id=user_id,
            username=username or "",
            email=email or "",
            tenant_id=tenant_id,
            role=role,
        )
    except jwt.ExpiredSignatureError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Token has expired",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e
    except jwt.PyJWTError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Could not validate credentials: {str(e)}",
            headers={"WWW-Authenticate": "Bearer"},
        ) from e


import time
from collections import defaultdict
from typing import Callable, Dict, List
from fastapi import Request
from services.api.src.cache import cache_client


class RateLimiter:
    """
    Sliding window rate limiter with Redis backend and in-memory fallback.
    """
    def __init__(
        self,
        max_requests: Optional[int] = None,
        window_seconds: Optional[int] = None,
        prefix: str = "general",
        key_func: Optional[Callable[[Request], str]] = None,
    ):
        self.max_requests = max_requests or settings.RATE_LIMIT_MAX_REQUESTS
        self.window_seconds = window_seconds or settings.RATE_LIMIT_WINDOW_SECONDS
        self.prefix = prefix
        self.key_func = key_func or self._default_key_func
        self._history: Dict[str, List[float]] = defaultdict(list)

    @staticmethod
    def _default_key_func(request: Request) -> str:
        forwarded = request.headers.get("X-Forwarded-For")
        if forwarded:
            return forwarded.split(",")[0].strip()
        client = request.client
        return client.host if client else "unknown_client"

    async def __call__(self, request: Request) -> None:
        if not settings.RATE_LIMITING_ENABLED:
            return

        key = self.key_func(request)

        # 1. If Redis is available, use distributed rate limiting
        if cache_client.is_connected and cache_client._redis:
            redis_key = f"ratelimit:{self.prefix}:{key}"
            try:
                current_count = await cache_client._redis.incr(redis_key)
                if current_count == 1:
                    await cache_client._redis.expire(redis_key, self.window_seconds)

                if current_count > self.max_requests:
                    ttl = await cache_client._redis.ttl(redis_key)
                    raise HTTPException(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        detail="Too many requests. Please try again later.",
                        headers={"Retry-After": str(max(1, ttl))},
                    )
                return
            except HTTPException:
                raise
            except Exception:
                # Redis error -> fallback to in-memory
                pass

        # 2. In-memory sliding window fallback
        now = time.time()
        window_start = now - self.window_seconds
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

