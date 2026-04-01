"""
DropSafe Caching Service
Redis-based distributed caching with fallback to in-memory cache
Handles: API responses, database queries, computations
"""

import os
import json
import time
from typing import Any, Optional, Callable
from datetime import datetime, timedelta
import hashlib
import functools
import asyncio
from enum import Enum


class CacheTTL(Enum):
    """Cache TTL (Time-To-Live) configurations"""

    VERY_SHORT = 60  # 1 minute - rapidly changing data
    SHORT = 300  # 5 minutes - weather, AQI
    MEDIUM = 600  # 10 minutes - trigger checks
    LONG = 1800  # 30 minutes - premium calculations
    VERY_LONG = 3600  # 1 hour - zone data, static lookups
    DAILY = 86400  # 1 day - daily summaries


class CacheLayer:
    """Multi-layer caching: Redis → In-Memory → Compute"""

    def __init__(self):
        self.memory_cache = {}
        self.memory_ttl = {}
        self.redis_available = False
        self.redis_client = None

        # Try to initialize Redis
        try:
            import redis

            redis_url = os.getenv("REDIS_URL", "redis://localhost:6379/0")
            self.redis_client = redis.from_url(redis_url, decode_responses=True)
            self.redis_client.ping()
            self.redis_available = True
            print("[✓] Redis connected for caching")
        except Exception as e:
            print(f"[!] Redis unavailable ({e}), using in-memory cache only")
            self.redis_available = False

    def _get_key(self, namespace: str, *args, **kwargs) -> str:
        """Generate cache key from namespace and arguments"""
        key_parts = [namespace] + [str(arg) for arg in args]
        if kwargs:
            key_parts.append(
                hashlib.md5(json.dumps(kwargs, sort_keys=True).encode()).hexdigest()[:8]
            )
        return ":".join(key_parts)

    def get(self, namespace: str, *args, **kwargs) -> Optional[Any]:
        """Retrieve from cache (Redis → Memory)"""
        key = self._get_key(namespace, *args, **kwargs)

        # Check memory cache first (fastest)
        if key in self.memory_cache:
            if time.time() < self.memory_ttl.get(key, 0):
                return self.memory_cache[key]
            else:
                del self.memory_cache[key]

        # Check Redis cache (if available)
        if self.redis_available:
            try:
                value = self.redis_client.get(key)
                if value:
                    data = json.loads(value)
                    # Re-populate memory cache
                    self.memory_cache[key] = data
                    self.memory_ttl[key] = time.time() + CacheTTL.MEDIUM.value
                    return data
            except Exception as e:
                print(f"[!] Redis get error: {e}")

        return None

    def set(
        self,
        namespace: str,
        value: Any,
        ttl: CacheTTL = CacheTTL.MEDIUM,
        *args,
        **kwargs,
    ):
        """Store in cache (Memory + Redis)"""
        key = self._get_key(namespace, *args, **kwargs)
        ttl_seconds = ttl.value

        # Store in memory
        self.memory_cache[key] = value
        self.memory_ttl[key] = time.time() + ttl_seconds

        # Store in Redis
        if self.redis_available:
            try:
                self.redis_client.setex(key, ttl_seconds, json.dumps(value))
            except Exception as e:
                print(f"[!] Redis set error: {e}")

    def delete(self, namespace: str, *args, **kwargs):
        """Delete from cache"""
        key = self._get_key(namespace, *args, **kwargs)

        if key in self.memory_cache:
            del self.memory_cache[key]

        if self.redis_available:
            try:
                self.redis_client.delete(key)
            except Exception as e:
                print(f"[!] Redis delete error: {e}")

    def clear_pattern(self, pattern: str):
        """Clear all keys matching pattern"""
        if self.redis_available:
            try:
                keys = self.redis_client.keys(pattern)
                if keys:
                    self.redis_client.delete(*keys)
            except Exception as e:
                print(f"[!] Redis pattern delete error: {e}")

    def clear_all(self):
        """Clear all caches"""
        self.memory_cache.clear()
        self.memory_ttl.clear()
        if self.redis_available:
            try:
                self.redis_client.flushdb()
            except Exception as e:
                print(f"[!] Redis flush error: {e}")


# Global cache instance
cache = CacheLayer()


def cached(namespace: str, ttl: CacheTTL = CacheTTL.MEDIUM):
    """
    Decorator for caching function results

    Usage:
        @cached("premium:calculate", ttl=CacheTTL.LONG)
        async def calculate_premium(zone_id, hours):
            ...
    """

    def decorator(func):
        @functools.wraps(func)
        async def async_wrapper(*args, **kwargs):
            cached_result = cache.get(namespace, *args, **kwargs)
            if cached_result is not None:
                return cached_result

            result = await func(*args, **kwargs)
            cache.set(namespace, result, ttl, *args, **kwargs)
            return result

        @functools.wraps(func)
        def sync_wrapper(*args, **kwargs):
            cached_result = cache.get(namespace, *args, **kwargs)
            if cached_result is not None:
                return cached_result

            result = func(*args, **kwargs)
            cache.set(namespace, result, ttl, *args, **kwargs)
            return result

        # Return appropriate wrapper
        return async_wrapper if asyncio.iscoroutinefunction(func) else sync_wrapper

    return decorator


# Cache statistics for monitoring
class CacheStats:
    """Track cache hit/miss rates"""

    def __init__(self):
        self.hits = 0
        self.misses = 0
        self.start_time = time.time()

    @property
    def hit_rate(self) -> float:
        """Cache hit rate percentage"""
        total = self.hits + self.misses
        return (self.hits / total * 100) if total > 0 else 0.0

    @property
    def uptime(self) -> int:
        """Seconds since cache started"""
        return int(time.time() - self.start_time)

    def report(self) -> dict:
        """Get cache statistics report"""
        return {
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate_percent": round(self.hit_rate, 2),
            "uptime_seconds": self.uptime,
            "memory_size_mb": len(str(cache.memory_cache)) / 1024 / 1024,
        }


cache_stats = CacheStats()
