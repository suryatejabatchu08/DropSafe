"""
DropSafe Trigger Monitor
Checks all 6 parametric triggers across zones every 15 minutes
"""

import os
import httpx
import random
from datetime import datetime, timedelta
from typing import Optional, Dict, List
from database import get_supabase
from dotenv import load_dotenv
import pytz
from .claim_engine import ClaimEngine

load_dotenv()

WEATHER_API_KEY = os.getenv("WEATHERAPI_KEY", "")
IQAIR_API_KEY = os.getenv("IQAIR_API_KEY", "")

IST = pytz.timezone("Asia/Kolkata")

# Trigger event type constants
TRIGGER_RAIN = "rain"
TRIGGER_HEAT = "heat"
TRIGGER_AQI = "aqi"
TRIGGER_CURFEW = "curfew"
TRIGGER_ORDER_VOLUME = "order_collapse"  # Fixed: matches schema
TRIGGER_STORE_CLOSURE = "store_closure"


class TriggerMonitor:
    """Monitor and check all 6 parametric triggers for all zones."""

    @staticmethod
    async def run_all_zones():
        """
        Check all triggers for all zones every 15 minutes.
        """
        try:
            print(f"\n[TriggerMonitor] Starting trigger checks at {datetime.now(IST)}")

            supabase = get_supabase()

            # Fetch all zones
            zones_response = supabase.table("zones").select("*").execute()

            if not zones_response.data:
                print("[TriggerMonitor] No zones found")
                return

            zones = zones_response.data
            print(f"[TriggerMonitor] Checking {len(zones)} zones...")

            # Check all zones in parallel (for efficiency)
            results_summary = {
                "zones_checked": 0,
                "triggers_fired": 0,
                "triggers_by_type": {},
            }

            for zone in zones:
                zone_name = zone.get("dark_store_name", "Unknown")
                await TriggerMonitor.check_zone(zone, results_summary)

            print(
                f"\n[TriggerMonitor] Summary: {results_summary['zones_checked']} zones, "
                f"{results_summary['triggers_fired']} triggers fired"
            )
            print(
                f"[TriggerMonitor] Breakdown: {results_summary['triggers_by_type']}\n"
            )

        except Exception as e:
            print(f"[ERROR] TriggerMonitor.run_all_zones failed: {e}")

    @staticmethod
    async def check_zone(zone: dict, results_summary: dict):
        """
        Check all 6 triggers for a specific zone.

        Args:
            zone: Zone data from Supabase
            results_summary: Dict to track results
        """
        zone_id = zone["id"]
        zone_name = zone.get("dark_store_name", "Unknown")
        pincode = zone.get("pincode", "")

        results_summary["zones_checked"] += 1

        trigger_results = {
            "rain": False,
            "heat": False,
            "aqi": False,
            "curfew": False,
            "order_volume": False,
            "store_closure": False,
        }

        try:
            # Check all triggers
            trigger_results["rain"] = await TriggerMonitor.check_rainfall(zone)
            trigger_results["heat"] = await TriggerMonitor.check_heat(zone)
            trigger_results["aqi"] = await TriggerMonitor.check_aqi(zone)
            trigger_results["curfew"] = await TriggerMonitor.check_curfew(zone)
            trigger_results["order_volume"] = await TriggerMonitor.check_order_volume(
                zone, trigger_results
            )
            trigger_results["store_closure"] = await TriggerMonitor.check_store_closure(
                zone
            )

            # Format and log results
            status_str = " | ".join(
                [
                    f"Rain: {'FIRED' if trigger_results['rain'] else 'OK'}",
                    f"Heat: {'FIRED' if trigger_results['heat'] else 'OK'}",
                    f"AQI: {'FIRED' if trigger_results['aqi'] else 'OK'}",
                    f"Curfew: {'FIRED' if trigger_results['curfew'] else 'OK'}",
                    f"OVC: {'FIRED' if trigger_results['order_volume'] else 'OK'}",
                    f"Closure: {'FIRED' if trigger_results['store_closure'] else 'OK'}",
                ]
            )

            print(f"[TriggerMonitor] Zone: {zone_name} | {status_str}")

            # Count fired triggers
            fired_count = sum(1 for v in trigger_results.values() if v)
            if fired_count > 0:
                results_summary["triggers_fired"] += fired_count
                for trigger_type, fired in trigger_results.items():
                    if fired:
                        results_summary["triggers_by_type"][trigger_type] = (
                            results_summary["triggers_by_type"].get(trigger_type, 0) + 1
                        )

        except Exception as e:
            print(f"[ERROR] Error checking zone {zone_name}: {e}")

    @staticmethod
    async def check_rainfall(zone: dict) -> bool:
        """
        Trigger 1: Heavy Rainfall (≥50mm).

        Checks current precipitation via WeatherAPI.

        Args:
            zone: Zone data

        Returns:
            True if trigger fired (precip >= 50mm)
        """
        try:
            lat = zone.get("lat")
            lon = zone.get("lon")

            if not lat or not lon:
                return False

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://api.weatherapi.com/v1/current.json",
                    params={
                        "key": WEATHER_API_KEY,
                        "q": f"{lat},{lon}",
                        "aqi": "yes"
                    },
                    timeout=5.0
                )
                response.raise_for_status()

            data = response.json()
            current = data.get("current", {})
            precip_mm = current.get("precip_mm", 0.0)

            if precip_mm >= 50:
                severity = min(precip_mm / 100, 1.0)
                await TriggerMonitor._create_trigger_event(
                    zone["id"], TRIGGER_RAIN, severity=severity
                )
                print(
                    f"  [FIRED] Rain trigger: {precip_mm}mm in {zone.get('dark_store_name')}"
                )
                return True

            return False

        except Exception as e:
            print(f"  [WARNING] Rain check error: {e}")
            return False

    @staticmethod
    async def check_heat(zone: dict) -> bool:
        """
        Trigger 2: Extreme Heat (≥43°C).

        Checks current temperature via WeatherAPI.

        Args:
            zone: Zone data

        Returns:
            True if trigger fired (temp >= 43°C)
        """
        try:
            lat = zone.get("lat")
            lon = zone.get("lon")

            if not lat or not lon:
                return False

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://api.weatherapi.com/v1/current.json",
                    params={
                        "key": WEATHER_API_KEY,
                        "q": f"{lat},{lon}"
                    },
                    timeout=5.0
                )
                response.raise_for_status()

            data = response.json()
            current = data.get("current", {})
            temp_c = current.get("temp_c", 0.0)

            if temp_c >= 43:
                severity = min((temp_c - 43) / 10, 1.0)
                await TriggerMonitor._create_trigger_event(
                    zone["id"], TRIGGER_HEAT, severity=severity
                )
                print(
                    f"  [FIRED] Heat trigger: {temp_c}°C in {zone.get('dark_store_name')}"
                )
                return True

            return False

        except Exception as e:
            print(f"  [WARNING] Heat check error: {e}")
            return False

    @staticmethod
    async def check_aqi(zone: dict) -> bool:
        """
        Trigger 3: Severe AQI (≥400 US AQI scale).

        Checks air quality via IQAir API using lat/lon.

        Args:
            zone: Zone data (must have lat, lon)

        Returns:
            True if trigger fired (AQI >= 400)
        """
        try:
            lat = zone.get("lat")
            lon = zone.get("lon")

            if not lat or not lon:
                print(f"  [WARNING] Zone {zone.get('dark_store_name')} missing lat/lon")
                return False

            async with httpx.AsyncClient() as client:
                response = await client.get(
                    "http://api.airvisual.com/v2/nearest_city",
                    params={"lat": lat, "lon": lon, "key": IQAIR_API_KEY},
                    timeout=5.0,
                )
                response.raise_for_status()

            data = response.json()

            if data.get("status") != "success":
                return False

            current = data.get("data", {}).get("current", {})
            pollution = current.get("pollution", {})
            aqius = pollution.get("aqius", 0)

            if aqius >= 400:
                severity = min(aqius / 500, 1.0)
                await TriggerMonitor._create_trigger_event(
                    zone["id"], TRIGGER_AQI, severity=severity
                )
                print(
                    f"  [FIRED] AQI trigger: {aqius} in {zone.get('dark_store_name')}"
                )
                return True

            return False

        except Exception as e:
            print(f"  [WARNING] AQI check error: {e}")
            return False

    @staticmethod
    async def check_curfew(zone: dict) -> bool:
        """
        Trigger 4: Zone Curfew (MOCK).

        Checks if admin has declared a curfew for the zone.

        Args:
            zone: Zone data

        Returns:
            True if active curfew exists
        """
        try:
            supabase = get_supabase()
            zone_id = zone["id"]

            # Check for active curfew events
            curfew_response = (
                supabase.table("curfew_events")
                .select("*")
                .eq("zone_id", zone_id)
                .eq("is_active", True)
                .execute()
            )

            if curfew_response.data:
                curfew = curfew_response.data[0]
                declared_at = curfew.get("declared_at")
                duration = curfew.get("duration_hours", 0)

                await TriggerMonitor._create_trigger_event(
                    zone_id, TRIGGER_CURFEW, severity=0.95  # Very high impact
                )
                print(f"  [FIRED] Curfew trigger: {zone.get('dark_store_name')}")
                return True

            return False

        except Exception as e:
            print(f"  [WARNING] Curfew check error: {e}")
            return False

    @staticmethod
    async def check_order_volume(zone: dict, trigger_results: dict) -> bool:
        """
        Trigger 5: Order Volume Collapse (MOCK + Novel).

        Simulates order volume patterns with time-of-day factors.
        Requires at least 1 other trigger for auto-approval (fraud prevention).

        Args:
            zone: Zone data
            trigger_results: Results from other triggers (for cross-validation)

        Returns:
            True if volume collapse detected
        """
        try:
            # Simulate current order volume
            base_orders = zone.get("risk_multiplier", 1.0) * 100

            # Time-of-day factor
            current_hour = datetime.now(IST).hour
            if 12 <= current_hour <= 14 or 19 <= current_hour <= 21:
                time_factor = 1.5  # Peak delivery hours
            elif 2 <= current_hour <= 5:
                time_factor = 0.3  # Off-peak
            else:
                time_factor = 1.0  # Normal

            # Random variance
            variance = random.uniform(0.8, 1.2)
            current_orders = base_orders * time_factor * variance

            # If weather trigger active, 10% chance of order collapse
            weather_trigger_active = trigger_results.get("rain") or trigger_results.get(
                "heat"
            )
            if weather_trigger_active and random.random() < 0.10:
                current_orders = current_orders * 0.15  # 85% drop

            # Average orders
            avg_orders = base_orders * time_factor

            # Check collapse (when current < 25% of average)
            if current_orders < (avg_orders * 0.25):
                # Fraud prevention: require at least 1 other trigger
                other_triggers_fired = sum(
                    1 for k, v in trigger_results.items() if k != "order_volume" and v
                )

                if other_triggers_fired >= 1:
                    severity = 1.0 - (current_orders / avg_orders)
                    severity = min(severity, 1.0)

                    await TriggerMonitor._create_trigger_event(
                        zone["id"], TRIGGER_ORDER_VOLUME, severity=severity
                    )
                    print(
                        f"  [FIRED] Order Volume trigger: {current_orders:.0f} "
                        f"orders in {zone.get('dark_store_name')}"
                    )
                    return True

            return False

        except Exception as e:
            print(f"  [WARNING] Order volume check error: {e}")
            return False

    @staticmethod
    async def check_store_closure(zone: dict) -> bool:
        """
        Trigger 6: Dark Store Closure (MOCK).

        Checks if admin has declared store closure > 2 hours.

        Args:
            zone: Zone data

        Returns:
            True if active closure exists (duration > 2 hours)
        """
        try:
            supabase = get_supabase()
            zone_id = zone["id"]

            # Check for active store closures
            closure_response = (
                supabase.table("store_closures")
                .select("*")
                .eq("zone_id", zone_id)
                .eq("is_active", True)
                .execute()
            )

            if closure_response.data:
                closure = closure_response.data[0]
                duration_hours = closure.get("duration_hours", 0)

                if duration_hours > 2:
                    severity = min(duration_hours / 8, 1.0)  # Max severity at 8 hours

                    await TriggerMonitor._create_trigger_event(
                        zone_id, TRIGGER_STORE_CLOSURE, severity=severity
                    )
                    print(
                        f"  [FIRED] Store Closure trigger: "
                        f"{zone.get('dark_store_name')} closed {duration_hours}h"
                    )
                    return True

            return False

        except Exception as e:
            print(f"  [WARNING] Store closure check error: {e}")
            return False

    @staticmethod
    async def _create_trigger_event(zone_id: str, trigger_type: str, severity: float):
        """
        Create a trigger event record in Supabase.

        Args:
            zone_id: Zone UUID
            trigger_type: Type of trigger (rain, heat, aqi, etc.)
            severity: Severity score (0-1)
        """
        try:
            supabase = get_supabase()

            # Store IST timestamps (database stores timestamp without time zone)
            now_ist = datetime.now(IST)
            now_ist_no_tz = now_ist.replace(tzinfo=None)
            end_ist = now_ist_no_tz + timedelta(hours=1)

            event_data = {
                "zone_id": zone_id,
                "trigger_type": trigger_type,
                "severity": float(min(severity, 1.0)),
                "verified": True,
                "start_time": now_ist_no_tz.isoformat(),  # IST time
                "end_time": end_ist.isoformat(),  # IST time
                "data_sources": {
                    "source": "automated_monitor",
                    "detection_time": now_ist_no_tz.isoformat(),
                },
                "created_at": now_ist_no_tz.isoformat(),
            }

            print(f"[DEBUG] Inserting trigger event: {event_data}")
            response = supabase.table("trigger_events").insert(event_data).execute()

            if response.data:
                trigger_event = response.data[0]
                trigger_event_id = trigger_event.get("id")
                print(
                    f"  [OK] Created trigger_event: {trigger_type} (severity: {severity:.2f})"
                )

                # Automatically process claims (Step 7: Auto-Claim Engine)
                await ClaimEngine.process_trigger(trigger_event_id)

        except Exception as e:
            print(f"  [ERROR] Failed to create trigger event: {e}")
