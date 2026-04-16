"""
DropSafe Analytics Router
Loss ratio, predictive analytics, and fraud summary endpoints.
"""

import os
import asyncio
from fastapi import APIRouter, Query
from datetime import datetime, timedelta
from typing import Optional
import httpx
import pytz

router = APIRouter(prefix="/analytics", tags=["analytics"])

IST = pytz.timezone("Asia/Kolkata")
WEATHER_API_KEY = os.getenv("WEATHERAPI_KEY", "")

# ─── In-memory cache for predictive analytics (expensive WeatherAPI call) ────
_predictive_cache: dict = {"data": None, "cached_at": None}
CACHE_TTL_SECONDS = int(os.getenv("PREDICTIVE_CACHE_TTL_SECONDS", "3600"))  # 1 hour

# Seasonal risk index for India (by month)
SEASONAL_INDEX = {
    1: 0.7, 2: 0.7, 3: 0.8, 4: 0.9,
    5: 1.0, 6: 1.3, 7: 1.5, 8: 1.5,  # Monsoon peak
    9: 1.2, 10: 0.9, 11: 0.8, 12: 0.7,
}


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/loss-ratio
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/loss-ratio")
async def get_loss_ratio(period: str = Query("current_week", enum=["current_week", "current_month", "all_time"])):
    """
    Calculate Loss Ratio = Total Payouts / Total Premiums Collected.

    Industry benchmark: 0.65–0.75 (green zone)
    > 0.90 = high risk for insurer (red alert)

    Returns:
        { total_premiums_collected, total_payouts_made, loss_ratio, period }
    """
    try:
        from database import get_supabase
        supabase = get_supabase()

        now_ist = datetime.now(IST).replace(tzinfo=None)

        # Determine date range
        if period == "current_week":
            days_offset = now_ist.weekday()
            start_date = (now_ist - timedelta(days=days_offset)).replace(
                hour=0, minute=0, second=0, microsecond=0
            )
        elif period == "current_month":
            start_date = now_ist.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        else:  # all_time
            start_date = datetime(2020, 1, 1)

        start_str = start_date.isoformat()

        # Total premiums collected (from active/expired policies in period)
        premiums_resp = (
            supabase.table("policies")
            .select("premium_paid")
            .in_("status", ["active", "expired"])
            .gte("week_start", start_str[:10])  # Date comparison
            .execute()
        )
        total_premiums = sum(
            float(p.get("premium_paid", 0)) for p in (premiums_resp.data or [])
        )

        # Total successful payouts in period
        payouts_resp = (
            supabase.table("payouts")
            .select("amount")
            .eq("status", "success")
            .gte("paid_at", start_str)
            .execute()
        )
        total_payouts = sum(
            float(p.get("amount", 0)) for p in (payouts_resp.data or [])
        )

        # Calculate loss ratio
        if total_premiums > 0:
            loss_ratio = round(total_payouts / total_premiums, 4)
        else:
            loss_ratio = 0.0

        return {
            "period": period,
            "total_premiums_collected": round(total_premiums, 2),
            "total_payouts_made": round(total_payouts, 2),
            "loss_ratio": loss_ratio,
            "loss_ratio_percent": round(loss_ratio * 100, 1),
            "benchmark_low": 0.65,
            "benchmark_high": 0.75,
            "risk_level": (
                "green" if loss_ratio < 0.70
                else "yellow" if loss_ratio < 0.90
                else "red"
            ),
        }

    except Exception as e:
        print(f"[Analytics] Loss ratio error: {e}")
        # Return safe default
        return {
            "period": period,
            "total_premiums_collected": 0.0,
            "total_payouts_made": 0.0,
            "loss_ratio": 0.0,
            "loss_ratio_percent": 0.0,
            "benchmark_low": 0.65,
            "benchmark_high": 0.75,
            "risk_level": "green",
            "error": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/predictive
# ─────────────────────────────────────────────────────────────────────────────

async def _get_weather_risk(lat: float, lon: float) -> float:
    """
    Fetch 7-day weather forecast and compute risk factor [0.5–2.0].

    Risk factors:
    - Rain probability > 60% → +0.5
    - Max temp > 40°C → +0.3
    - Rain probability > 80% → +0.7 (severe)
    Falls back to 1.0 if WeatherAPI unavailable.
    """
    if not WEATHER_API_KEY or lat is None or lon is None:
        return 1.0

    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                "http://api.weatherapi.com/v1/forecast.json",
                params={
                    "key": WEATHER_API_KEY,
                    "q": f"{lat},{lon}",
                    "days": 7,
                    "aqi": "no",
                    "alerts": "no",
                },
            )
            resp.raise_for_status()
            data = resp.json()

        forecast_days = data.get("forecast", {}).get("forecastday", [])
        if not forecast_days:
            return 1.0

        # Compute risk from 7-day forecast
        max_rain_prob = max(
            d.get("day", {}).get("daily_chance_of_rain", 0) for d in forecast_days
        )
        max_temp = max(
            d.get("day", {}).get("maxtemp_c", 30) for d in forecast_days
        )

        risk = 1.0
        if max_rain_prob > 80:
            risk += 0.7
        elif max_rain_prob > 60:
            risk += 0.5
        elif max_rain_prob > 40:
            risk += 0.2

        if max_temp > 43:
            risk += 0.5
        elif max_temp > 40:
            risk += 0.3

        return round(min(risk, 2.0), 2)

    except Exception as e:
        print(f"[Analytics] WeatherAPI error for ({lat},{lon}): {e}")
        return 1.0


@router.get("/predictive")
async def get_predictive_analytics():
    """
    Per-zone disruption probability forecast for next 7 days.

    Formula:
        P = zone.risk_multiplier × seasonal_index × weather_risk_factor × 0.4
        Capped at 0.95

    Results cached for 1 hour (expensive WeatherAPI calls).

    Returns:
        List of zone forecasts with disruption probability and exposure estimate
    """
    global _predictive_cache

    # Return cached data if still fresh
    now = datetime.now(IST)
    if (
        _predictive_cache["data"] is not None
        and _predictive_cache["cached_at"] is not None
        and (now - _predictive_cache["cached_at"]).total_seconds() < CACHE_TTL_SECONDS
    ):
        print("[Analytics] Returning cached predictive data")
        return _predictive_cache["data"]

    try:
        from database import get_supabase
        supabase = get_supabase()

        # Get all zones
        zones_resp = supabase.table("zones").select("*").execute()
        zones = zones_resp.data or []

        seasonal = SEASONAL_INDEX.get(now.month, 1.0)

        # Get current week active policy counts per zone
        now_ist_naive = now.replace(tzinfo=None)
        week_start = (now_ist_naive - timedelta(days=now_ist_naive.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0
        )

        # Fetch weather risks concurrently for all zones
        weather_tasks = [
            _get_weather_risk(z.get("lat"), z.get("lon")) for z in zones
        ]
        weather_risks = await asyncio.gather(*weather_tasks, return_exceptions=True)

        result = []
        for zone, weather_risk in zip(zones, weather_risks):
            zone_id = zone.get("id")

            if isinstance(weather_risk, Exception):
                weather_risk = 1.0

            risk_multiplier = float(zone.get("risk_multiplier", 1.0))

            # P = risk_multiplier × seasonal_index × weather_risk × 0.4
            raw_prob = risk_multiplier * seasonal * float(weather_risk) * 0.4
            disruption_prob = round(min(raw_prob, 0.95), 3)

            # Active policies in zone
            policies_resp = (
                supabase.table("policies")
                .select("id, coverage_cap", count="exact")
                .eq("zone_id", zone_id)
                .eq("status", "active")
                .gte("week_start", week_start.strftime("%Y-%m-%d"))
                .execute()
            )
            n_policies = policies_resp.count or 0
            avg_coverage = (
                sum(float(p.get("coverage_cap", 1280)) for p in (policies_resp.data or []))
                / max(n_policies, 1)
            )

            # Estimated claims and exposure
            est_claims = round(n_policies * disruption_prob)
            est_exposure = round(est_claims * avg_coverage * 0.7)  # 70% claim rate

            if disruption_prob < 0.30:
                risk_level = "low"
            elif disruption_prob < 0.60:
                risk_level = "medium"
            else:
                risk_level = "high"

            result.append({
                "zone_id": zone_id,
                "zone_name": zone.get("dark_store_name"),
                "platform": zone.get("platform"),
                "disruption_probability": disruption_prob,
                "disruption_probability_pct": round(disruption_prob * 100, 1),
                "risk_level": risk_level,
                "risk_multiplier": risk_multiplier,
                "seasonal_index": seasonal,
                "weather_risk_factor": float(weather_risk),
                "active_policies": n_policies,
                "estimated_claims": est_claims,
                "estimated_exposure_inr": est_exposure,
            })

        # Sort by risk descending
        result.sort(key=lambda x: x["disruption_probability"], reverse=True)

        # Cache result
        _predictive_cache = {"data": result, "cached_at": now}
        print(f"[Analytics] Predictive analytics refreshed for {len(result)} zones, cached for {CACHE_TTL_SECONDS}s")
        return result

    except Exception as e:
        print(f"[Analytics] Predictive analytics error: {e}")
        return []


# ─────────────────────────────────────────────────────────────────────────────
# GET /analytics/fraud-summary
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/fraud-summary")
async def get_fraud_summary():
    """
    Aggregated ML fraud scoring statistics for the insurer dashboard.

    Returns:
        {
            total_scored, auto_approved, review, auto_rejected,
            avg_layer1_score, avg_layer2_score, avg_combined_score,
            cluster_alerts_active, false_positive_rate_est
        }
    """
    try:
        from database import get_supabase
        supabase = get_supabase()

        # All claims
        claims_resp = (
            supabase.table("claims")
            .select("status, fraud_score, fraud_flags")
            .execute()
        )
        claims = claims_resp.data or []

        total = len(claims)
        auto_approved = sum(1 for c in claims if c.get("status") == "auto_approved")
        review = sum(1 for c in claims if c.get("status") == "review")
        rejected = sum(1 for c in claims if c.get("status") == "rejected")

        # Collect layer scores
        l1_scores, l2_scores, combined_scores = [], [], []
        cluster_alerts = 0

        for c in claims:
            flags = c.get("fraud_flags") or {}
            l2_info = flags.get("layer2_isolation_forest", {})

            if l2_info:
                if l2_info.get("layer1_score") is not None:
                    l1_scores.append(float(l2_info["layer1_score"]))
                if l2_info.get("score") is not None:
                    l2_scores.append(float(l2_info["score"]))
                if l2_info.get("combined_score") is not None:
                    combined_scores.append(float(l2_info["combined_score"]))

            # Check cluster fraud flag
            for detail in (flags.get("details") or []):
                if (
                    detail.get("name") == "cluster_fraud_check"
                    and not detail.get("passed")
                ):
                    cluster_alerts += 1

        def safe_avg(lst):
            return round(sum(lst) / len(lst), 3) if lst else None

        # Estimated false positive rate from model metadata
        fpr_est = None
        try:
            import json
            from services.isolation_forest_trainer import METADATA_PATH
            if os.path.exists(METADATA_PATH):
                with open(METADATA_PATH) as f:
                    meta = json.load(f)
                fpr_est = meta.get("bias_metrics", {}).get("false_positive_rate")
        except Exception:
            pass

        return {
            "total_scored": total,
            "auto_approved": auto_approved,
            "review": review,
            "auto_rejected": rejected,
            "auto_approved_pct": round(auto_approved / total * 100, 1) if total else 0,
            "review_pct": round(review / total * 100, 1) if total else 0,
            "rejected_pct": round(rejected / total * 100, 1) if total else 0,
            "avg_layer1_score": safe_avg(l1_scores),
            "avg_layer2_score": safe_avg(l2_scores),
            "avg_combined_score": safe_avg(combined_scores),
            "claims_with_layer2": len(l2_scores),
            "cluster_alerts_active": cluster_alerts,
            "false_positive_rate_est": fpr_est,
        }

    except Exception as e:
        print(f"[Analytics] Fraud summary error: {e}")
        return {
            "total_scored": 0,
            "auto_approved": 0,
            "review": 0,
            "auto_rejected": 0,
            "error": str(e),
        }
