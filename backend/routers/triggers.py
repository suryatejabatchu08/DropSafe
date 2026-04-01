from datetime import datetime, timezone, timedelta
from fastapi import APIRouter, HTTPException
from database import get_trigger_events, get_supabase
import pytz

router = APIRouter(prefix="/triggers", tags=["triggers"])


@router.get("/mock")
async def mock_triggers():
    """
    Fetch recent trigger events from Supabase.
    Returns both verified and unverified events for demo purposes.
    """
    try:
        events = await get_trigger_events(verified_only=False, limit=10)

        # Transform database records to match frontend expected format
        formatted_events = []
        for event in events:
            zone_info = event.get("zones", {})
            formatted_events.append(
                {
                    "trigger_type": event["trigger_type"],
                    "zone": f"{zone_info.get('dark_store_name', 'Unknown')}, {zone_info.get('pincode', '')}",
                    "severity": float(event["severity"]) if event["severity"] else 0.0,
                    "timestamp": (
                        event["start_time"]
                        if event["start_time"]
                        else event["created_at"]
                    ),
                    "verified": event["verified"],
                }
            )

        return formatted_events

    except Exception as e:
        print(f"[ERROR] Error fetching triggers from database: {e}")
        # Fallback to hardcoded data if database fails
        now = datetime.now(timezone.utc).isoformat()
        return [
            {
                "trigger_type": "rain",
                "zone": "Koramangala, Bengaluru",
                "severity": 0.82,
                "timestamp": now,
                "verified": False,
            },
            {
                "trigger_type": "aqi",
                "zone": "Dwarka, Delhi NCR",
                "severity": 0.91,
                "timestamp": now,
                "verified": False,
            },
        ]


@router.get("/active")
async def get_active_triggers():
    """
    Get all currently active (verified) trigger events.

    Returns trigger events that have been verified and not yet resolved.
    """
    try:
        supabase = get_supabase()

        # Fetch verified triggers
        triggers_response = (
            supabase.table("trigger_events")
            .select("*, zones(dark_store_name, pincode)")
            .eq("verified", True)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        triggers = triggers_response.data if triggers_response.data else []

        formatted = []
        for trigger in triggers:
            zone = trigger.get("zones", {})
            formatted.append(
                {
                    "id": trigger.get("id"),
                    "trigger_type": trigger.get("trigger_type"),
                    "zone": zone.get("dark_store_name", "Unknown"),
                    "severity": trigger.get("severity", 0),
                    "created_at": trigger.get("created_at"),
                    "details": trigger.get("details"),
                }
            )

        return {"total_active": len(formatted), "triggers": formatted}

    except Exception as e:
        print(f"[ERROR] Failed to fetch active triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch triggers")


@router.get("/zone/{zone_id}")
async def get_zone_triggers(zone_id: str):
    """
    Get recent trigger history for a specific zone.

    Args:
        zone_id: Zone UUID

    Returns:
        List of recent trigger events for the zone
    """
    try:
        supabase = get_supabase()

        # Verify zone exists
        zone_response = (
            supabase.table("zones")
            .select("id, dark_store_name")
            .eq("id", zone_id)
            .execute()
        )
        if not zone_response.data:
            raise HTTPException(status_code=404, detail="Zone not found")

        zone = zone_response.data[0]

        # Fetch triggers for zone
        triggers_response = (
            supabase.table("trigger_events")
            .select("*")
            .eq("zone_id", zone_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        triggers = triggers_response.data if triggers_response.data else []

        formatted = []
        for trigger in triggers:
            formatted.append(
                {
                    "id": trigger.get("id"),
                    "trigger_type": trigger.get("trigger_type"),
                    "severity": trigger.get("severity"),
                    "verified": trigger.get("verified"),
                    "created_at": trigger.get("created_at"),
                    "details": trigger.get("details"),
                }
            )

        return {
            "zone": zone["dark_store_name"],
            "total_triggers": len(formatted),
            "triggers": formatted,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to fetch zone triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch triggers")


@router.get("/type/{trigger_type}")
async def get_triggers_by_type(trigger_type: str):
    """
    Get all triggers of a specific type across all zones.

    Args:
        trigger_type: Type of trigger (rain, heat, aqi, curfew, order_volume_drop, store_closure)

    Returns:
        List of triggers of the specified type
    """
    try:
        supabase = get_supabase()

        valid_types = [
            "rain",
            "heat",
            "aqi",
            "curfew",
            "order_collapse",
            "store_closure",
        ]
        if trigger_type not in valid_types:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trigger type. Must be one of: {', '.join(valid_types)}",
            )

        # Fetch triggers by type
        triggers_response = (
            supabase.table("trigger_events")
            .select("*, zones(dark_store_name)")
            .eq("trigger_type", trigger_type)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )

        triggers = triggers_response.data if triggers_response.data else []

        formatted = []
        for trigger in triggers:
            zone = trigger.get("zones", {})
            formatted.append(
                {
                    "id": trigger.get("id"),
                    "zone": zone.get("dark_store_name", "Unknown"),
                    "severity": trigger.get("severity"),
                    "created_at": trigger.get("created_at"),
                    "details": trigger.get("details"),
                }
            )

        return {
            "trigger_type": trigger_type,
            "total": len(formatted),
            "triggers": formatted,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to fetch triggers by type: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch triggers")


@router.get("/zone/history")
async def get_trigger_history(days: int = 30):
    """
    Get trigger event history for last N days, grouped by date and trigger type.

    Args:
        days: Number of days to fetch history for (default: 30)

    Returns:
        List of daily trigger counts by type
    """
    try:
        supabase = get_supabase()

        # Get start date
        now_utc = datetime.now(pytz.UTC).replace(tzinfo=None)
        start_date = now_utc - timedelta(days=days)

        # Fetch triggers
        triggers_response = (
            supabase.table("trigger_events")
            .select("created_at, trigger_type")
            .gte("created_at", start_date.isoformat())
            .execute()
        )

        triggers = triggers_response.data or []

        # Group by date and trigger type
        daily_totals: dict = {}

        for trigger in triggers:
            created_at = trigger.get("created_at", "")
            if created_at:
                date = created_at.split("T")[0]
                trigger_type = trigger.get("trigger_type", "unknown")

                if date not in daily_totals:
                    daily_totals[date] = {
                        "date": date,
                        "rain": 0,
                        "heat": 0,
                        "aqi": 0,
                        "curfew": 0,
                        "order_collapse": 0,
                        "store_closure": 0,
                    }

                if trigger_type in daily_totals[date]:
                    daily_totals[date][trigger_type] += 1

        result = sorted(daily_totals.values(), key=lambda x: x["date"])

        return result

    except Exception as e:
        print(f"[ERROR] Failed to fetch trigger history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")
