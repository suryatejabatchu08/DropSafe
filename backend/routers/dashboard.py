"""
DropSafe Dashboard Router

Endpoints for insurer dashboard to fetch key metrics and analytics.
Includes comprehensive caching for performance optimization.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from database import get_supabase
import pytz
from utils.cache_manager import CacheManager, CacheKeys, PerformanceMetrics
import time

router = APIRouter(prefix="/dashboard", tags=["dashboard"])

IST = pytz.timezone("Asia/Kolkata")
cache_manager = CacheManager()


@router.get("/stats")
async def get_dashboard_stats():
    """
    Get top-level dashboard statistics with caching.

    Returns:
        {
            "active_policies": int,
            "total_payout_week": float,
            "active_triggers": int,
            "fraud_alerts": int
        }
    """
    start_time = time.time()

    # Try cache first (TTL: 30 seconds - frequent updates)
    cached_stats = cache_manager.get(CacheKeys.DASHBOARD_STATS)
    if cached_stats is not None:
        PerformanceMetrics.record_api_call(
            "/dashboard/stats", (time.time() - start_time) * 1000, cached=True
        )
        return cached_stats

    try:
        supabase = get_supabase()

        # Get current week boundaries (IST)
        now_ist = datetime.now(IST).replace(tzinfo=None)
        week_start = now_ist - timedelta(days=now_ist.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Active policies this week (status = 'active')
        policies_response = (
            supabase.table("policies")
            .select("id", count="exact")
            .eq("status", "active")
            .gte("week_start", week_start.strftime("%Y-%m-%d"))
            .lte("week_end", week_end.strftime("%Y-%m-%d"))
            .execute()
        )

        active_policies = policies_response.count or 0

        # Total payout this week
        payouts_response = (
            supabase.table("payouts")
            .select("amount")
            .eq("status", "success")
            .gte("paid_at", week_start.isoformat())
            .execute()
        )

        total_payout = sum(p.get("amount", 0) for p in (payouts_response.data or []))

        # Active triggers
        triggers_response = (
            supabase.table("trigger_events")
            .select("id", count="exact")
            .eq("verified", True)
            .gte(
                "created_at",
                (datetime.now(IST) - timedelta(hours=6))
                .replace(tzinfo=None)
                .isoformat(),
            )
            .execute()
        )

        active_triggers = triggers_response.count or 0

        # Fraud alerts (review status)
        fraud_response = (
            supabase.table("claims")
            .select("id", count="exact")
            .eq("status", "review")
            .execute()
        )

        fraud_alerts = fraud_response.count or 0

        result = {
            "active_policies": active_policies,
            "total_payout_week": float(total_payout),
            "active_triggers": active_triggers,
            "fraud_alerts": fraud_alerts,
        }

        # Cache for 30 seconds (frequent updates)
        cache_manager.set(CacheKeys.DASHBOARD_STATS, result, ttl=30)

        PerformanceMetrics.record_api_call(
            "/dashboard/stats", (time.time() - start_time) * 1000
        )
        return result

    except Exception as e:
        print(f"[ERROR] Failed to fetch dashboard stats: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch stats")


@router.get("/claims/daily-summary")
async def get_claims_daily_summary():
    """
    Get daily claim counts for last 7 days, grouped by status.

    Returns:
        List of daily summaries with claim counts by status
    """
    try:
        supabase = get_supabase()

        # Get last 7 days of claims (IST)
        week_ago = (datetime.now(IST) - timedelta(days=7)).replace(tzinfo=None)

        response = (
            supabase.table("claims")
            .select("created_at, status")
            .gte("created_at", week_ago.isoformat())
            .execute()
        )

        claims = response.data or []

        # Group by date and status
        daily_totals: dict = {}

        for claim in claims:
            created_at = claim.get("created_at", "")
            if created_at:
                date = created_at.split("T")[0]
                status = claim.get("status", "unknown")

                if date not in daily_totals:
                    daily_totals[date] = {
                        "date": date,
                        "auto_approved": 0,
                        "review": 0,
                        "rejected": 0,
                        "paid": 0,
                        "approved": 0,
                    }

                if status in daily_totals[date]:
                    daily_totals[date][status] += 1

        # Format for chart
        result = sorted(daily_totals.values(), key=lambda x: x["date"])

        return (
            result
            if result
            else [
                {
                    "date": (datetime.now(IST) - timedelta(days=i)).strftime(
                        "%Y-%m-%d"
                    ),
                    "auto_approved": 0,
                    "review": 0,
                    "rejected": 0,
                    "paid": 0,
                    "approved": 0,
                }
                for i in range(7)
            ]
        )

    except Exception as e:
        print(f"[ERROR] Failed to fetch daily claims summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.get("/zones/summary")
async def get_zones_summary():
    """
    Get summary statistics for all zones.

    Returns:
        List of zones with active policies, claims this week, and loss ratio
    """
    try:
        supabase = get_supabase()

        # Get current week (IST)
        now_ist = datetime.now(IST).replace(tzinfo=None)
        week_start = now_ist - timedelta(days=now_ist.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        week_end = week_start + timedelta(days=7)

        # Get all zones
        zones_response = supabase.table("zones").select("*").execute()
        zones = zones_response.data or []

        result = []

        for zone in zones:
            zone_id = zone.get("id")

            # Active policies in zone
            policies_response = (
                supabase.table("policies")
                .select("id", count="exact")
                .eq("zone_id", zone_id)
                .eq("status", "active")
                .gte("week_start", week_start.strftime("%Y-%m-%d"))
                .lte("week_end", week_end.strftime("%Y-%m-%d"))
                .execute()
            )

            active_policies = policies_response.count or 0

            # Claims this week
            claims_response = (
                supabase.table("claims")
                .select("id, payout_amount", count="exact")
                .eq("zone_id", zone_id)
                .gte("created_at", week_start.isoformat())
                .lte("created_at", week_end.isoformat())
                .execute()
            )

            claims_count = claims_response.count or 0
            claims_total_payout = sum(
                c.get("payout_amount", 0) for c in (claims_response.data or [])
            )

            # Loss ratio (claims payout / active policies coverage cap)
            if active_policies > 0:
                avg_coverage = 3200  # Approximate average coverage cap
                loss_ratio = min(
                    1.0, claims_total_payout / (active_policies * avg_coverage)
                )
            else:
                loss_ratio = 0.0

            result.append(
                {
                    "id": zone_id,
                    "dark_store_name": zone.get("dark_store_name"),
                    "platform": zone.get("platform"),
                    "risk_multiplier": float(zone.get("risk_multiplier", 1.0)),
                    "active_policies": active_policies,
                    "claims_this_week": claims_count,
                    "loss_ratio": round(loss_ratio, 3),
                }
            )

        return result

    except Exception as e:
        print(f"[ERROR] Failed to fetch zones summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.get("/performance")
async def get_performance_report():
    """
    Get performance metrics and cache statistics.

    Useful for monitoring and optimization.
    Returns cache hit/miss rates and endpoint timings.
    """
    return {
        "cache": cache_manager.get_stats(),
        "performance": PerformanceMetrics.get_report(),
    }
