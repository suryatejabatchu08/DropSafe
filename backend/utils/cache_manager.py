"""
DropSafe Caching Utilities

Implements multiple caching strategies:
- In-memory caching for frequently accessed data (zones, workers)
- API response caching with TTL
- Database query result caching
- Frontend-side caching with deduplication
"""

import time
from typing import Dict, Any, Optional, Callable, TypeVar, Tuple
from datetime import datetime, timedelta
from functools import wraps
import json

T = TypeVar("T")

# ============================================================================
# IN-MEMORY CACHE MANAGER
# ============================================================================


class CacheManager:
    """Singleton cache manager for all caching operations."""

    _instance = None
    _cache: Dict[str, Tuple[Any, float]] = {}  # key -> (value, expiry_time)
    _lock = False  # Simple lock for thread safety

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
        return cls._instance

    def get(self, key: str) -> Optional[Any]:
        """Get value from cache if not expired."""
        if key not in self._cache:
            return None

        value, expiry_time = self._cache[key]

        # Check if expired
        if time.time() > expiry_time:
            del self._cache[key]
            return None

        return value

    def set(self, key: str, value: Any, ttl: int = 300):
        """
        Set value in cache with TTL (seconds).

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default 5 min)
        """
        expiry_time = time.time() + ttl
        self._cache[key] = (value, expiry_time)

    def delete(self, key: str):
        """Delete key from cache."""
        if key in self._cache:
            del self._cache[key]

    def clear(self):
        """Clear entire cache."""
        self._cache.clear()

    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        return {
            "size": len(self._cache),
            "keys": list(self._cache.keys()),
            "memory_estimate_mb": len(str(self._cache)) / (1024 * 1024),
        }


# ============================================================================
# DECORATOR FOR FUNCTION RESULT CACHING
# ============================================================================


def cache_result(ttl: int = 300):
    """
    Decorator to cache function results.

    Usage:
        @cache_result(ttl=600)  # Cache for 10 minutes
        def expensive_operation(param1, param2):
            return result

    Args:
        ttl: Time to live in seconds
    """

    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            # Create cache key from function name and arguments
            cache_key = (
                f"{func.__name__}:{json.dumps(str(args) + str(kwargs), default=str)}"
            )

            # Try to get from cache
            manager = CacheManager()
            cached_value = manager.get(cache_key)
            if cached_value is not None:
                print(f"[CACHE HIT] {func.__name__}")
                return cached_value

            # Cache miss - execute function
            print(f"[CACHE MISS] {func.__name__}")
            result = func(*args, **kwargs)

            # Store in cache
            manager.set(cache_key, result, ttl)
            return result

        return wrapper

    return decorator


# ============================================================================
# SPECIFIC CACHE KEYS
# ============================================================================


class CacheKeys:
    """Standard cache key constants."""

    # Zones (rarely change)
    ZONES_LIST = "zones:list"
    ZONE_DETAIL = "zone:{zone_id}"
    ZONES_SUMMARY = "zones:summary"

    # Workers (medium frequency)
    WORKERS_BY_ZONE = "workers:zone:{zone_id}"
    WORKER_DETAIL = "worker:{worker_id}"

    # Policies (high frequency)
    ACTIVE_POLICIES = "policies:active:{zone_id}"
    WORKER_POLICIES = "policies:worker:{worker_id}"

    # Triggers (high frequency)
    ACTIVE_TRIGGERS = "triggers:active"
    ZONE_TRIGGERS = "triggers:zone:{zone_id}"

    # Dashboard Stats
    DASHBOARD_STATS = "dashboard:stats"
    CLAIMS_SUMMARY = "claims:summary:{period}"  # daily, weekly, monthly

    # API Responses (backend calls to external APIs)
    WEATHER_DATA = "api:weather:{lat}:{lon}"
    AQI_DATA = "api:aqi:{lat}:{lon}"

    # Fraud Detection
    FRAUD_ALERTS = "fraud:alerts"
    FRAUD_CLAIMS_REVIEW = "fraud:claims:review"


# ============================================================================
# SMART CACHE INVALIDATION
# ============================================================================


class CacheInvalidator:
    """Handles cache invalidation when data changes."""

    _manager = CacheManager()

    @staticmethod
    def invalidate_trigger(zone_id: str):
        """Invalidate trigger-related caches when trigger created/updated."""
        cache_keys = [
            CacheKeys.ACTIVE_TRIGGERS,
            CacheKeys.ZONE_TRIGGERS.format(zone_id=zone_id),
            CacheKeys.DASHBOARD_STATS,
        ]
        for key in cache_keys:
            CacheInvalidator._manager.delete(key)
        print(f"[CACHE INVALIDATED] Trigger cache for zone {zone_id}")

    @staticmethod
    def invalidate_claim(zone_id: str, worker_id: str):
        """Invalidate claim-related caches when claim created/updated."""
        cache_keys = [
            CacheKeys.FRAUD_ALERTS,
            CacheKeys.FRAUD_CLAIMS_REVIEW,
            CacheKeys.CLAIMS_SUMMARY.format(period="daily"),
            CacheKeys.CLAIMS_SUMMARY.format(period="weekly"),
            CacheKeys.DASHBOARD_STATS,
        ]
        for key in cache_keys:
            CacheInvalidator._manager.delete(key)
        print(f"[CACHE INVALIDATED] Claim cache for worker {worker_id}")

    @staticmethod
    def invalidate_policy(worker_id: str, zone_id: str):
        """Invalidate policy-related caches."""
        cache_keys = [
            CacheKeys.ACTIVE_POLICIES.format(zone_id=zone_id),
            CacheKeys.WORKER_POLICIES.format(worker_id=worker_id),
            CacheKeys.ZONES_SUMMARY,
        ]
        for key in cache_keys:
            CacheInvalidator._manager.delete(key)
        print(f"[CACHE INVALIDATED] Policy cache for worker {worker_id}")

    @staticmethod
    def invalidate_zones():
        """Invalidate all zone-related caches."""
        cache_keys = [
            CacheKeys.ZONES_LIST,
            CacheKeys.ZONES_SUMMARY,
        ]
        for key in cache_keys:
            CacheInvalidator._manager.delete(key)
        # Also invalidate all zone-specific keys
        CacheInvalidator._manager.clear()
        print(f"[CACHE INVALIDATED] All zone caches")


# ============================================================================
# FRONTEND CACHING RECOMMENDATIONS
# ============================================================================

FRONTEND_CACHE_CONFIG = {
    # Static data (rarely changes)
    "zones": {
        "ttl": 3600,  # 1 hour
        "endpoint": "/zones/summary",
        "stale_while_revalidate": 1800,  # SWR: 30 min
    },
    # Dashboard data (refreshes frequently)
    "dashboard_stats": {
        "ttl": 30,  # 30 seconds
        "endpoint": "/dashboard/stats",
        "stale_while_revalidate": 10,
    },
    # Live trigger feed (updates every 15 min from backend)
    "triggers": {
        "ttl": 60,  # 1 minute
        "endpoint": "/triggers/active",
        "stale_while_revalidate": 30,
    },
    # Claims data (updates when new claims created)
    "claims": {
        "ttl": 120,  # 2 minutes
        "endpoint": "/fraud/claims/review",
        "stale_while_revalidate": 60,
    },
    # Payouts (updates on transaction)
    "payouts": {
        "ttl": 60,  # 1 minute
        "endpoint": "/payouts/summary",
        "stale_while_revalidate": 30,
    },
    # Fraud alerts (updates when fraud detected)
    "fraud_alerts": {
        "ttl": 120,  # 2 minutes
        "endpoint": "/fraud/alerts",
        "stale_while_revalidate": 60,
    },
}


# ============================================================================
# QUERY OPTIMIZATION CONSTANTS
# ============================================================================

# Recommended batch sizes for database queries
QUERY_BATCH_SIZES = {
    "zones": 1000,
    "workers": 500,
    "policies": 1000,
    "claims": 5000,
    "triggers": 10000,
}

# Recommended indexes to create in Supabase
RECOMMENDED_INDEXES = [
    # Policies
    "CREATE INDEX idx_policies_zone_status ON policies(zone_id, status)",
    "CREATE INDEX idx_policies_week ON policies(week_start, week_end)",
    # Claims
    "CREATE INDEX idx_claims_zone_created ON claims(zone_id, created_at)",
    "CREATE INDEX idx_claims_status_fraud ON claims(status, fraud_score)",
    "CREATE INDEX idx_claims_worker_id ON claims(worker_id)",
    # Triggers
    "CREATE INDEX idx_triggers_zone_time ON trigger_events(zone_id, start_time)",
    "CREATE INDEX idx_triggers_verified ON trigger_events(verified, created_at)",
    # Workers
    "CREATE INDEX idx_workers_zone_created ON workers(zone_id, created_at)",
    # Payouts
    "CREATE INDEX idx_payouts_status_time ON payouts(status, created_at)",
]


# ============================================================================
# PERFORMANCE METRICS
# ============================================================================


class PerformanceMetrics:
    """Track and report performance metrics."""

    _metrics: Dict[str, Dict[str, Any]] = {}

    @staticmethod
    def record_api_call(endpoint: str, duration_ms: float, cached: bool = False):
        """Record API call metrics."""
        if endpoint not in PerformanceMetrics._metrics:
            PerformanceMetrics._metrics[endpoint] = {
                "count": 0,
                "total_time": 0,
                "avg_time": 0,
                "cached_count": 0,
                "p95_time": 0,
                "times": [],
            }

        metrics = PerformanceMetrics._metrics[endpoint]
        metrics["count"] += 1
        metrics["total_time"] += duration_ms
        metrics["avg_time"] = metrics["total_time"] / metrics["count"]
        metrics["times"].append(duration_ms)

        if cached:
            metrics["cached_count"] += 1

        # Calculate P95
        if len(metrics["times"]) >= 20:
            metrics["times"].sort()
            metrics["p95_time"] = metrics["times"][int(len(metrics["times"]) * 0.95)]

    @staticmethod
    def get_report() -> Dict[str, Any]:
        """Generate performance report."""
        slow_endpoints = []

        for endpoint, metrics in PerformanceMetrics._metrics.items():
            if metrics["avg_time"] > 100:  # Slow if > 100ms
                slow_endpoints.append(
                    {
                        "endpoint": endpoint,
                        "avg_time": f"{metrics['avg_time']:.1f}ms",
                        "p95_time": f"{metrics['p95_time']:.1f}ms",
                        "calls": metrics["count"],
                        "cached": metrics["cached_count"],
                    }
                )

        return {
            "total_endpoints": len(PerformanceMetrics._metrics),
            "slow_endpoints": sorted(
                slow_endpoints,
                key=lambda x: float(x["avg_time"].rstrip("ms")),
                reverse=True,
            ),
            "endpoints": PerformanceMetrics._metrics,
        }


if __name__ == "__main__":
    # Test caching
    cache = CacheManager()

    # Set and get
    cache.set("test_key", {"data": "value"}, ttl=10)
    print("Get:", cache.get("test_key"))

    # Stats
    print("Cache stats:", cache.get_stats())

    # Decorator test
    @cache_result(ttl=10)
    def expensive_operation(x, y):
        print(f"  Computing {x} + {y}...")
        return x + y

    print("\nFirst call:", expensive_operation(5, 3))
    print("Second call (cached):", expensive_operation(5, 3))
