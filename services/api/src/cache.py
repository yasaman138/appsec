import json
import logging
from typing import Any, Optional
import redis.asyncio as aioredis
from services.api.src.config import settings

logger = logging.getLogger("api.cache")


class CacheClient:
    def __init__(self, redis_url: str = settings.REDIS_URL):
        self.redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._connected = False

    async def connect(self) -> None:
        if not settings.CACHE_ENABLED:
            return
        try:
            self._redis = aioredis.from_url(
                self.redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_connect_timeout=2.0,
                socket_timeout=2.0,
            )
            await self._redis.ping()
            self._connected = True
            logger.info("Connected to Redis cache successfully.")
        except Exception as e:
            self._connected = False
            self._redis = None
            logger.warning(f"Redis cache connection failed: {e}. Falling back to non-cached mode.")

    async def disconnect(self) -> None:
        if self._redis:
            await self._redis.close()
            self._connected = False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._redis is not None

    def make_record_key(self, tenant_id: str, record_id: str) -> str:
        return f"record:{tenant_id}:{record_id}"

    def make_tenant_pattern(self, tenant_id: str) -> str:
        return f"record:{tenant_id}:*"

    async def get(self, key: str) -> Optional[Any]:
        if not self.is_connected:
            return None
        try:
            data = await self._redis.get(key)
            if data:
                return json.loads(data)
            return None
        except Exception as e:
            logger.warning(f"Cache get error for key '{key}': {e}")
            return None

    async def set(
        self,
        key: str,
        value: Any,
        ttl_seconds: int = settings.CACHE_DEFAULT_TTL_SECONDS,
    ) -> bool:
        if not self.is_connected:
            return False
        try:
            serialized = json.dumps(value, default=str)
            await self._redis.set(key, serialized, ex=ttl_seconds)
            return True
        except Exception as e:
            logger.warning(f"Cache set error for key '{key}': {e}")
            return False

    async def delete(self, key: str) -> bool:
        if not self.is_connected:
            return False
        try:
            await self._redis.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Cache delete error for key '{key}': {e}")
            return False

    async def invalidate_tenant(self, tenant_id: str) -> int:
        if not self.is_connected:
            return 0
        try:
            pattern = self.make_tenant_pattern(tenant_id)
            keys = []
            async for k in self._redis.scan_iter(match=pattern):
                keys.append(k)
            if keys:
                return await self._redis.delete(*keys)
            return 0
        except Exception as e:
            logger.warning(f"Cache invalidate_tenant error for tenant '{tenant_id}': {e}")
            return 0


# Global cache instance
cache_client = CacheClient()
