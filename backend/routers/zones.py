"""
DropSafe Zones Router

Endpoints for zone analytics and risk management.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from database import get_supabase
import pytz

router = APIRouter(prefix="/zones", tags=["zones"])

IST = pytz.timezone("Asia/Kolkata")


@router.get("/summary")
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
                .select("id, payout_amount")
                .eq("zone_id", zone_id)
                .gte("created_at", week_start.isoformat())
                .lte("created_at", week_end.isoformat())
                .execute()
            )

            claims_count = len(claims_response.data) if claims_response.data else 0
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
