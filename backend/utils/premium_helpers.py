"""
DropSafe Premium Calculation Helpers
Dynamic premium engine with ML-based risk adjustment
"""

import os
import httpx
from datetime import datetime
from typing import Optional, Tuple, Dict
from dotenv import load_dotenv

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHERAPI_KEY", "")
WEATHER_API_BASE = "http://api.weatherapi.com/v1"

# Cache for API responses (pincode -> (timestamp, data))
_weather_cache: Dict[str, Tuple[float, dict]] = {}
CACHE_TTL = 600  # 10 minutes


def get_seasonal_index() -> float:
    """
    Get seasonal risk multiplier based on current month.

    Seasons (India):
    - Monsoon (Jun-Sep): 1.35 - Heavy rain, floods, waterlogging
    - AQI Season (Oct-Nov): 1.30 - Delhi/North India AQI spike
    - Summer/Heat (Mar-May): 1.15 - Extreme heat, less order volume
    - Winter (Dec-Feb): 1.00 - Normal operations

    Returns:
        Seasonal multiplier (1.00, 1.15, 1.30, or 1.35)
    """
    current_month = datetime.now().month

    if 6 <= current_month <= 9:
        return 1.35  # Monsoon (highest risk)
    elif 10 <= current_month <= 11:
        return 1.30  # AQI season
    elif 3 <= current_month <= 5:
        return 1.15  # Summer/heat
    else:
        return 1.00  # Winter (normal)


def get_current_season_name() -> str:
    """Get current season name."""
    current_month = datetime.now().month

    if 6 <= current_month <= 9:
        return "monsoon"
    elif 10 <= current_month <= 11:
        return "aqi_season"
    elif 3 <= current_month <= 5:
        return "summer"
    else:
        return "winter"


async def get_ml_adjustment(pincode: str) -> float:
    """
    Calculate ML-based risk adjustment using weather forecast.

    Analyzes 3-day forecast:
    - Precipitation > 50mm: high (1.25)
    - Precipitation > 20mm: medium (1.10)
    - Temp > 40°C: high (1.20)
    - Default: low (0.90)

    Args:
        pincode: Zone pincode (e.g., "560102")

    Returns:
        ML adjustment factor (0.90 - 1.25)
        Returns 1.00 on API error (fail-safe)
    """
    try:
        # Check cache first
        if pincode in _weather_cache:
            cached_time, cached_data = _weather_cache[pincode]
            if datetime.now().timestamp() - cached_time < CACHE_TTL:
                return _calculate_adjustment_from_forecast(cached_data)

        # Get zone coordinates from Supabase
        from database import get_supabase

        supabase = get_supabase()

        zone_response = (
            supabase.table("zones").select("lat, lon").eq("pincode", pincode).execute()
        )

        if not zone_response.data:
            print(f"[WARNING] Zone not found for pincode {pincode}")
            return 1.00

        zone = zone_response.data[0]
        lat = zone.get("lat")
        lon = zone.get("lon")

        if not lat or not lon:
            print(f"[WARNING] Zone {pincode} missing coordinates")
            return 1.00

        # Fetch fresh forecast using lat,lon
        async with httpx.AsyncClient() as client:
            response = await client.get(
                f"{WEATHER_API_BASE}/forecast.json",
                params={
                    "key": WEATHER_API_KEY,
                    "q": f"{lat},{lon}",  # Fixed: Use lat,lon instead of pincode
                    "days": 3,
                    "aqi": "yes",
                },
                timeout=5.0,
            )
            response.raise_for_status()

        data = response.json()

        # Cache the response
        _weather_cache[pincode] = (datetime.now().timestamp(), data)

        return _calculate_adjustment_from_forecast(data)

    except Exception as e:
        print(f"[WARNING] Weather API error for {pincode}: {e}")
        return 1.00  # Fail-safe: neutral adjustment


def _calculate_adjustment_from_forecast(data: dict) -> float:
    """
    Calculate adjustment factor from forecast data.

    Args:
        data: WeatherAPI forecast response

    Returns:
        Adjustment factor (0.90 - 1.25)
    """
    try:
        forecast_days = data.get("forecast", {}).get("forecastday", [])

        if not forecast_days:
            return 1.00

        # Analyze 3-day forecast
        total_precip = 0.0
        max_temp = 0.0

        for day in forecast_days:
            day_data = day.get("day", {})
            total_precip += day_data.get("totalprecip_mm", 0.0)
            max_temp = max(max_temp, day_data.get("maxtemp_c", 0.0))

        # Calculate adjustment based on weather factors
        adjustment = 1.00

        # Precipitation risk
        if total_precip > 50:  # High rain
            adjustment = 1.25
        elif total_precip > 20:  # Moderate rain
            adjustment = 1.10
        elif total_precip > 0:  # Light rain
            adjustment = 1.02

        # Temperature risk (apply if higher)
        if max_temp > 45:  # Extreme heat
            temp_adjustment = 1.25
            adjustment = max(adjustment, temp_adjustment)
        elif max_temp > 40:  # High heat (spec: >40°C → 1.20)
            temp_adjustment = 1.20
            adjustment = max(adjustment, temp_adjustment)

        # Low risk scenario
        if total_precip == 0 and max_temp < 35:
            adjustment = 0.90

        return round(adjustment, 2)

    except Exception as e:
        print(f"[WARNING] Error calculating adjustment: {e}")
        return 1.00


def calculate_weekly_premium(
    base_rate: float,
    zone_risk: float,
    declared_hours: int,
    ml_adjustment: float = 1.00,
    seasonal_index: float = 1.00,
) -> float:
    """
    Calculate weekly insurance premium.

    Formula: base_rate × zone_risk × (hours/40) × ml_adjustment × seasonal_index

    Args:
        base_rate: Base premium (typically 38)
        zone_risk: Zone risk multiplier (from zones table)
        declared_hours: Weekly working hours (~40)
        ml_adjustment: ML weather adjustment (0.90-1.25)
        seasonal_index: Seasonal multiplier (1.00-1.35)

    Returns:
        Weekly premium in INR (rounded to 2 decimals)
    """
    hours_ratio = declared_hours / 40.0

    premium = base_rate * zone_risk * hours_ratio * ml_adjustment * seasonal_index

    return round(premium, 2)


def calculate_coverage_cap(
    declared_hours: int, avg_hourly_income: float, zone_risk: float = 1.0
) -> float:
    """
    Calculate maximum coverage amount per week.

    Cap = avg_hourly_income × declared_hours × 0.80
    (zone_risk is accepted for backwards compatibility but not applied to cap)

    Args:
        declared_hours: Weekly working hours
        avg_hourly_income: Average hourly income in INR
        zone_risk: Unused — kept for backwards compatibility

    Returns:
        Coverage cap in INR (rounded to 2 decimals)
    """
    cap = declared_hours * avg_hourly_income * 0.80

    return round(cap, 2)


async def get_weather_forecast_risk(pincode: str) -> str:
    """
    Get human-readable forecast risk level.

    Args:
        pincode: Zone pincode

    Returns:
        Risk level: "high", "medium", "low"
    """
    try:
        adjustment = await get_ml_adjustment(pincode)

        if adjustment >= 1.20:
            return "high"
        elif adjustment >= 1.05:
            return "medium"
        else:
            return "low"

    except Exception as e:
        print(f"[WARNING] Error getting forecast risk: {e}")
        return "unknown"


def clear_cache():
    """Clear weather API cache (for testing)."""
    global _weather_cache
    _weather_cache.clear()
    print("[OK] Weather cache cleared")
