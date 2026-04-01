"""
DropSafe Premium Calculation Router
Dynamic premium engine with ML-based risk adjustment
"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from database import get_supabase
from utils.premium_helpers import (
    get_seasonal_index,
    get_current_season_name,
    get_ml_adjustment,
    calculate_weekly_premium,
    calculate_coverage_cap,
    get_weather_forecast_risk,
)

router = APIRouter(prefix="/premium", tags=["premium"])


class PremiumCalculateRequest(BaseModel):
    """Premium calculation request."""

    worker_id: Optional[str] = None  # If enrolled worker
    zone_pincode: str = Field(..., description="Zone PIN code")
    declared_hours: int = Field(
        default=40, ge=1, le=168, description="Weekly working hours"
    )
    platform: Optional[str] = None  # "zepto" or "blinkit" (for reference)
    avg_hourly_income: Optional[float] = Field(
        default=80.0, ge=0, description="Average hourly income in INR"
    )


class PremiumBreakdown(BaseModel):
    """Premium calculation breakdown."""

    base_rate: float
    zone_name: str
    zone_risk_multiplier: float
    hours: int
    hours_ratio: float
    season: str
    seasonal_index: float
    forecast_risk: str
    ml_adjustment: float


class PremiumCalculateResponse(BaseModel):
    """Premium calculation response."""

    weekly_premium: float
    coverage_cap: float
    zone_risk_multiplier: float
    seasonal_index: float
    ml_adjustment: float
    breakdown: PremiumBreakdown


@router.post("/calculate", response_model=PremiumCalculateResponse)
async def calculate_premium(request: PremiumCalculateRequest):
    """
    Calculate dynamic weekly insurance premium for delivery partner.

    Formula: base_rate × zone_risk × (hours/40) × ml_adjustment × seasonal_index

    Args:
        zone_pincode: Zone PIN code to look up risk multiplier
        declared_hours: Weekly working hours (default: 40)
        avg_hourly_income: Average hourly income for coverage cap (default: 80)

    Returns:
        Premium amount, coverage cap, and calculation breakdown
    """
    try:
        supabase = get_supabase()

        # Look up zone by pincode
        zones_response = (
            supabase.table("zones")
            .select("id, pincode, dark_store_name, risk_multiplier")
            .eq("pincode", request.zone_pincode)
            .execute()
        )

        if not zones_response.data:
            raise HTTPException(
                status_code=404,
                detail=f"Zone not found for pincode: {request.zone_pincode}",
            )

        zone = zones_response.data[0]
        zone_id = zone["id"]
        zone_name = zone["dark_store_name"]
        zone_risk = float(zone["risk_multiplier"])

        # Get seasonal multiplier
        seasonal_index = get_seasonal_index()
        season_name = get_current_season_name()

        # Get ML weather adjustment
        ml_adjustment = await get_ml_adjustment(request.zone_pincode)

        # Get forecast risk level
        forecast_risk = await get_weather_forecast_risk(request.zone_pincode)

        # Calculate premium
        base_rate = 38.0
        weekly_premium = calculate_weekly_premium(
            base_rate=base_rate,
            zone_risk=zone_risk,
            declared_hours=request.declared_hours,
            ml_adjustment=ml_adjustment,
            seasonal_index=seasonal_index,
        )

        # Calculate coverage cap
        coverage_cap = calculate_coverage_cap(
            declared_hours=request.declared_hours,
            avg_hourly_income=request.avg_hourly_income,
            zone_risk=zone_risk,
        )

        # Build breakdown
        breakdown = PremiumBreakdown(
            base_rate=base_rate,
            zone_name=zone_name,
            zone_risk_multiplier=zone_risk,
            hours=request.declared_hours,
            hours_ratio=request.declared_hours / 40.0,
            season=season_name,
            seasonal_index=seasonal_index,
            forecast_risk=forecast_risk,
            ml_adjustment=ml_adjustment,
        )

        print(
            f"[PREMIUM] Calculated ₹{weekly_premium} for {zone_name} | "
            f"Season={season_name} | ML={ml_adjustment} | Risk={forecast_risk}"
        )

        return PremiumCalculateResponse(
            weekly_premium=weekly_premium,
            coverage_cap=coverage_cap,
            zone_risk_multiplier=zone_risk,
            seasonal_index=seasonal_index,
            ml_adjustment=ml_adjustment,
            breakdown=breakdown,
        )

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Premium calculation failed: {e}")
        raise HTTPException(
            status_code=500, detail=f"Premium calculation error: {str(e)}"
        )


@router.get("/zones")
async def list_premium_zones():
    """
    List all zones with risk multipliers for premium calculation.

    Used by frontend to show available zones and their risk levels.
    """
    try:
        supabase = get_supabase()

        zones_response = (
            supabase.table("zones")
            .select("id, pincode, dark_store_name, risk_multiplier")
            .execute()
        )

        zones = zones_response.data if zones_response.data else []

        return {
            "total_zones": len(zones),
            "zones": [
                {
                    "zone_id": z["id"],
                    "pincode": z["pincode"],
                    "name": z["dark_store_name"],
                    "risk_multiplier": z["risk_multiplier"],
                    "risk_level": (
                        "high"
                        if z["risk_multiplier"] > 1.3
                        else "medium" if z["risk_multiplier"] > 1.1 else "low"
                    ),
                }
                for z in zones
            ],
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch zones: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch zones")
