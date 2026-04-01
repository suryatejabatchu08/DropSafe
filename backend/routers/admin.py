"""
DropSafe Admin Router
Admin endpoints for manual trigger simulation and system management
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime, timedelta
from database import get_supabase
import pytz
from services.claim_engine import ClaimEngine

router = APIRouter(prefix="/admin", tags=["admin"])

IST = pytz.timezone("Asia/Kolkata")


class TriggerSimulationRequest(BaseModel):
    """Request to simulate a trigger event."""

    zone_id: str = Field(..., description="Zone UUID")
    trigger_type: str = Field(
        ...,
        description="Trigger type: rain, heat, aqi, curfew, order_volume_drop, store_closure",
    )
    severity: float = Field(default=0.8, ge=0.0, le=1.0, description="Severity (0-1)")
    details: Optional[str] = None


class CurfewEventRequest(BaseModel):
    """Request to declare a zone curfew."""

    zone_id: str = Field(..., description="Zone UUID")
    duration_hours: int = Field(
        default=4, ge=1, le=24, description="Curfew duration in hours"
    )


class StoreClosureRequest(BaseModel):
    """Request to declare store closure."""

    zone_id: str = Field(..., description="Zone UUID")
    duration_hours: int = Field(
        default=3, ge=1, le=24, description="Closure duration in hours"
    )


@router.post("/trigger/simulate")
async def simulate_trigger(request: TriggerSimulationRequest):
    """
    ⚡ DEMO BUTTON: Manually fire a trigger event (verified).

    Critical for Phase 3 demo - simulate "fake rainstorm" or other triggers.

    Args:
        zone_id: Zone UUID
        trigger_type: Type of trigger to fire
        severity: Severity level (0.0-1.0)
        details: Optional custom details

    Returns:
        Created trigger event
    """
    try:
        supabase = get_supabase()

        # Verify zone exists
        zone_response = (
            supabase.table("zones")
            .select("id, dark_store_name")
            .eq("id", request.zone_id)
            .execute()
        )
        if not zone_response.data:
            raise HTTPException(status_code=404, detail="Zone not found")

        zone = zone_response.data[0]
        zone_name = zone["dark_store_name"]

        # Valid trigger types
        valid_triggers = [
            "rain",
            "heat",
            "aqi",
            "curfew",
            "order_collapse",
            "store_closure",
        ]
        if request.trigger_type not in valid_triggers:
            raise HTTPException(
                status_code=400,
                detail=f"Invalid trigger type. Must be one of: {', '.join(valid_triggers)}",
            )

        # Create trigger event (store IST time)
        now_ist = datetime.now(IST)
        now_ist_no_tz = now_ist.replace(tzinfo=None)
        end_ist = now_ist_no_tz + timedelta(hours=1)

        event_data = {
            "zone_id": request.zone_id,
            "trigger_type": request.trigger_type,
            "severity": float(request.severity),
            "verified": True,
            "start_time": now_ist_no_tz.isoformat(),
            "end_time": end_ist.isoformat(),
            "data_sources": {
                "source": "admin_simulation",
                "simulated_at": now_ist_no_tz.isoformat(),
            },
            "created_at": now_ist_no_tz.isoformat(),
        }

        response = supabase.table("trigger_events").insert(event_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to create trigger event"
            )

        event = response.data[0]
        trigger_event_id = event.get("id")

        print(
            f"[ADMIN] Simulated trigger: {request.trigger_type} in {zone_name} "
            f"(severity: {request.severity})"
        )

        # Automatically process claims (Step 7: Auto-Claim Engine)
        try:
            await ClaimEngine.process_trigger(trigger_event_id)
        except Exception as e:
            print(f"[WARNING] ClaimEngine failed for trigger {trigger_event_id}: {e}")

        return {
            "status": "success",
            "message": f"✅ {request.trigger_type} trigger fired in {zone_name}",
            "trigger_event": {
                "id": event.get("id"),
                "zone": zone_name,
                "trigger_type": event.get("trigger_type"),
                "severity": event.get("severity"),
                "verified": event.get("verified"),
                "created_at": event.get("created_at"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Trigger simulation failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/trigger/curfew")
async def declare_curfew(request: CurfewEventRequest):
    """
    Manually declare a zone curfew.

    Creates a curfew event that will trigger the curfew trigger.

    Args:
        zone_id: Zone UUID
        duration_hours: How long the curfew lasts

    Returns:
        Created curfew event
    """
    try:
        supabase = get_supabase()

        # Verify zone exists
        zone_response = (
            supabase.table("zones")
            .select("id, dark_store_name")
            .eq("id", request.zone_id)
            .execute()
        )
        if not zone_response.data:
            raise HTTPException(status_code=404, detail="Zone not found")

        zone = zone_response.data[0]

        # Create curfew event (store IST time)
        now_ist = datetime.now(IST)
        now_ist_no_tz = now_ist.replace(tzinfo=None)

        curfew_data = {
            "zone_id": request.zone_id,
            "duration_hours": request.duration_hours,
            "is_active": True,
            "declared_at": now_ist_no_tz.isoformat(),
        }

        response = supabase.table("curfew_events").insert(curfew_data).execute()

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to create curfew event")

        curfew = response.data[0]

        print(
            f"[ADMIN] Curfew declared: {zone['dark_store_name']} for {request.duration_hours}h"
        )

        return {
            "status": "success",
            "message": f"🚨 Curfew declared in {zone['dark_store_name']} for {request.duration_hours} hours",
            "curfew_event": {
                "id": curfew.get("id"),
                "zone": zone["dark_store_name"],
                "duration_hours": curfew.get("duration_hours"),
                "declared_at": curfew.get("declared_at"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Curfew declaration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.post("/trigger/store-closure")
async def declare_store_closure(request: StoreClosureRequest):
    """
    Manually declare a dark store closure.

    Creates a store closure event that will trigger the closure trigger.

    Args:
        zone_id: Zone UUID
        duration_hours: How long the store remains closed

    Returns:
        Created closure event
    """
    try:
        supabase = get_supabase()

        # Verify zone exists
        zone_response = (
            supabase.table("zones")
            .select("id, dark_store_name")
            .eq("id", request.zone_id)
            .execute()
        )
        if not zone_response.data:
            raise HTTPException(status_code=404, detail="Zone not found")

        zone = zone_response.data[0]

        # Create store closure event (store IST time)
        now_ist = datetime.now(IST)
        now_ist_no_tz = now_ist.replace(tzinfo=None)

        closure_data = {
            "zone_id": request.zone_id,
            "duration_hours": request.duration_hours,
            "is_active": True,
            "closed_at": now_ist_no_tz.isoformat(),
        }

        response = supabase.table("store_closures").insert(closure_data).execute()

        if not response.data:
            raise HTTPException(
                status_code=500, detail="Failed to create closure event"
            )

        closure = response.data[0]

        print(
            f"[ADMIN] Store closure declared: {zone['dark_store_name']} for {request.duration_hours}h"
        )

        return {
            "status": "success",
            "message": f"🔒 Store closure declared in {zone['dark_store_name']} for {request.duration_hours} hours",
            "closure_event": {
                "id": closure.get("id"),
                "zone": zone["dark_store_name"],
                "duration_hours": closure.get("duration_hours"),
                "closed_at": closure.get("closed_at"),
            },
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Store closure declaration failed: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")


@router.get("/triggers/active")
async def list_active_triggers():
    """
    Get all currently active (unresolved) trigger events.

    Used by insurer dashboard to see what's happening in real-time.

    Returns:
        List of active trigger events with zone details
    """
    try:
        supabase = get_supabase()

        # Fetch active triggers (verified, created in last 24 hours)
        triggers_response = (
            supabase.table("trigger_events")
            .select("*, zones(dark_store_name, pincode)")
            .eq("verified", True)
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )

        triggers = triggers_response.data if triggers_response.data else []

        # Group by zone
        by_zone = {}
        for trigger in triggers:
            zone = trigger.get("zones", {})
            zone_name = zone.get("dark_store_name", "Unknown")

            if zone_name not in by_zone:
                by_zone[zone_name] = []

            by_zone[zone_name].append(
                {
                    "id": trigger.get("id"),
                    "trigger_type": trigger.get("trigger_type"),
                    "severity": trigger.get("severity"),
                    "created_at": trigger.get("created_at"),
                    "details": trigger.get("details"),
                }
            )

        return {
            "total_active": len(triggers),
            "zones_affected": len(by_zone),
            "triggers_by_zone": by_zone,
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch active triggers: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch triggers")


@router.get("/triggers/zone/{zone_id}")
async def get_zone_trigger_history(zone_id: str):
    """
    Get trigger history for a specific zone.

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

        # Fetch trigger history
        triggers_response = (
            supabase.table("trigger_events")
            .select("*")
            .eq("zone_id", zone_id)
            .order("created_at", desc=True)
            .limit(50)
            .execute()
        )

        triggers = triggers_response.data if triggers_response.data else []

        # Group by trigger type
        by_type = {}
        for trigger in triggers:
            trigger_type = trigger.get("trigger_type")
            if trigger_type not in by_type:
                by_type[trigger_type] = []

            by_type[trigger_type].append(
                {
                    "id": trigger.get("id"),
                    "severity": trigger.get("severity"),
                    "verified": trigger.get("verified"),
                    "created_at": trigger.get("created_at"),
                    "details": trigger.get("details"),
                }
            )

        return {
            "zone": zone["dark_store_name"],
            "total_triggers": len(triggers),
            "triggers_by_type": by_type,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to fetch zone trigger history: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch history")


@router.post("/trigger/resolve/{trigger_id}")
async def resolve_trigger(trigger_id: str):
    """
    Mark a trigger event as resolved (manual override).

    Args:
        trigger_id: Trigger event UUID

    Returns:
        Updated trigger event
    """
    try:
        supabase = get_supabase()

        # Update trigger as resolved
        response = (
            supabase.table("trigger_events")
            .update(
                {
                    "verified": False,  # Mark as handled
                    "resolved_at": datetime.now(IST).isoformat(),
                }
            )
            .eq("id", trigger_id)
            .execute()
        )

        if not response.data:
            raise HTTPException(status_code=404, detail="Trigger not found")

        print(f"[ADMIN] Trigger resolved: {trigger_id}")

        return {
            "status": "success",
            "message": "✅ Trigger marked as resolved",
            "trigger_id": trigger_id,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to resolve trigger: {e}")
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")
