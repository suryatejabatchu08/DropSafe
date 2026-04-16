"""
DropSafe Fraud Detection Engine — Layer 1 + Layer 2

Layer 1: Rule-based Multi-Signal Anomaly Score (MSAS) — 7 deterministic checks
Layer 2: Isolation Forest ML — learned anomaly patterns (40% weight)
Combined: weighted average, capped at 1.0
"""

from datetime import datetime, timedelta
from typing import Dict, Tuple, List
from database import get_supabase
import pytz
import math

IST = pytz.timezone("Asia/Kolkata")


class FraudEngine:
    """MSAS fraud detection engine with 6 rule-based checks."""

    @staticmethod
    async def score_claim(claim_data: dict) -> Tuple[float, dict]:  # type: ignore[override]
        """
        Score a claim for fraud using Multi-Signal Anomaly Score (MSAS).

        6 Rule-Based Checks:
        1. GPS Zone Check (+0.40): Worker location mismatches trigger zone
        2. Shift Timing Check (+0.35): Trigger outside typical working hours
        3. Duplicate Claim Check (+1.00): Already claimed for this trigger (hard reject)
        4. Frequency Check (+0.30): Worker filed >8 claims in last 30 days
        5. Order Volume Contradiction (+0.30): OVC trigger but high platform activity
        6. Platform Activity Check (+0.25): No/high app activity during disruption window
        7. New Worker Check (+0.15): Worker registered <7 days ago

        Returns MSA Score (0.0-1.0) and detailed fraud flags.

        Args:
            claim_data: Dict with claim details
                - trigger_event_id, policy_id, worker_id, zone_id
                - trigger_type, trigger_start, trigger_end
                - disrupted_hours, severity

        Returns:
            Tuple of (fraud_score: float, fraud_flags: dict)
        """
        fraud_flags = {"checks_passed": 0, "checks_failed": 0, "details": []}

        msas_score = 0.0

        try:
            supabase = get_supabase()

            # Debug header
            trigger_type = claim_data.get("trigger_type", "unknown")
            print(f"\n[FraudEngine] Scoring {trigger_type} trigger claim for worker {claim_data.get('worker_id', 'unknown')[:8]}...")
            print(f"   Running 7 fraud detection checks:\n")

            # RULE 1: GPS Zone Check (+0.40)
            gps_check = await FraudEngine._check_gps_zone(
                supabase, claim_data.get("worker_id"), claim_data.get("zone_id")
            )
            fraud_flags["details"].append(gps_check)
            if not gps_check["passed"]:
                msas_score += gps_check["weight"]
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ GPS Zone Check FAILED: {gps_check['reason']} (+{gps_check['weight']})")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ GPS Zone Check PASSED: {gps_check['reason']}")

            # RULE 2: Shift Timing Check (+0.35)
            timing_check = await FraudEngine._check_shift_timing(
                supabase,
                claim_data.get("worker_id"),
                claim_data.get("trigger_start"),
                claim_data.get("trigger_end"),
            )
            fraud_flags["details"].append(timing_check)
            if not timing_check["passed"]:
                msas_score += timing_check["weight"]
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ Shift Timing Check FAILED: {timing_check['reason']} (+{timing_check['weight']})")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ Shift Timing Check PASSED: {timing_check['reason']}")

            # RULE 3: Duplicate Claim Check (+1.00) - Hard Reject
            dup_check = await FraudEngine._check_duplicate_claim(
                supabase,
                claim_data.get("policy_id"),
                claim_data.get("trigger_event_id"),
            )
            fraud_flags["details"].append(dup_check)
            if not dup_check["passed"]:
                msas_score += dup_check["weight"]  # Auto-reject at 1.0
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ Duplicate Claim Check FAILED: {dup_check['reason']} (+{dup_check['weight']})")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ Duplicate Claim Check PASSED: {dup_check['reason']}")

            # RULE 4: Claim Frequency Check (+0.30)
            freq_check = await FraudEngine._check_claim_frequency(
                supabase, claim_data.get("worker_id")
            )
            fraud_flags["details"].append(freq_check)
            if not freq_check["passed"]:
                msas_score += freq_check["weight"]
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ Frequency Check FAILED: {freq_check['reason']} (+{freq_check['weight']})")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ Frequency Check PASSED: {freq_check['reason']}")

            # RULE 5: Order Volume Contradiction (+0.30)
            if claim_data.get("trigger_type") == "order_collapse":
                ovc_check = await FraudEngine._check_order_volume_contradiction(
                    supabase,
                    claim_data.get("worker_id"),
                    claim_data.get("trigger_start"),
                    claim_data.get("trigger_end"),
                )
                fraud_flags["details"].append(ovc_check)
                if not ovc_check["passed"]:
                    msas_score += ovc_check["weight"]
                    fraud_flags["checks_failed"] += 1
                    print(f"   ❌ Order Volume Check FAILED: {ovc_check['reason']} (+{ovc_check['weight']})")
                else:
                    fraud_flags["checks_passed"] += 1
                    print(f"   ✅ Order Volume Check PASSED: {ovc_check['reason']}")

            # RULE 5: Platform Activity Check (+0.25)
            activity_check = await FraudEngine._check_platform_activity(
                supabase,
                claim_data.get("worker_id"),
                claim_data.get("trigger_start"),
                claim_data.get("trigger_end"),
            )
            fraud_flags["details"].append(activity_check)
            if not activity_check["passed"]:
                msas_score += activity_check["weight"]
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ Platform Activity Check FAILED: {activity_check['reason']} (+{activity_check['weight']})")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ Platform Activity Check PASSED: {activity_check['reason']}")

            # RULE 6: New Worker Check (+0.15)
            new_worker_check = await FraudEngine._check_new_worker(
                supabase, claim_data.get("worker_id")
            )
            fraud_flags["details"].append(new_worker_check)
            if not new_worker_check["passed"]:
                msas_score += new_worker_check["weight"]
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ New Worker Check FAILED: {new_worker_check['reason']} (+{new_worker_check['weight']})")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ New Worker Check PASSED: {new_worker_check['reason']}")

            # CLUSTER FRAUD DETECTION: Check zone-wide fraud pattern
            cluster_check = await FraudEngine._check_cluster_fraud(
                supabase, claim_data.get("trigger_event_id"), claim_data.get("zone_id")
            )
            fraud_flags["details"].append(cluster_check)
            if not cluster_check["passed"]:
                # Cluster fraud increases score (multiplier effect)
                msas_score = min(msas_score + 0.20, 1.0)
                fraud_flags["checks_failed"] += 1
                print(f"   ❌ Cluster Fraud Check FAILED: {cluster_check['reason']} (+0.20)")
            else:
                fraud_flags["checks_passed"] += 1
                print(f"   ✅ Cluster Fraud Check PASSED: {cluster_check['reason']}")

            # Cap Layer 1 at 1.0
            msas_score = min(msas_score, 1.0)

            # ── HARD REJECT: skip Layer 2 if already at maximum ──────────
            if msas_score >= 1.00:
                print(f"   🚫 HARD REJECT at Layer 1 (score=1.0) — skipping Layer 2")
                fraud_flags["layer2_isolation_forest"] = {
                    "score": None,
                    "layer1_score": msas_score,
                    "combined_score": 1.0,
                    "model": "skipped_hard_reject",
                }
                print(f"   Final Combined Score: 1.00 | ❌ HARD REJECT\n")
                return 1.00, fraud_flags

            # ── LAYER 2: Isolation Forest ──────────────────────────────────
            layer2_score: float = msas_score  # Default fallback = Layer 1 score
            try:
                from .isolation_forest_scorer import IsolationForestScorer

                if IsolationForestScorer.is_loaded():
                    # Fetch worker/zone/trigger records for feature building
                    worker_id = claim_data.get("worker_id", "")
                    zone_id = claim_data.get("zone_id", "")
                    trigger_event_id = claim_data.get("trigger_event_id", "")

                    # Fetch supporting records
                    worker_resp = supabase.table("workers").select(
                        "id, created_at, avg_hourly_income"
                    ).eq("id", worker_id).execute()
                    worker_rec = worker_resp.data[0] if worker_resp.data else {}

                    zone_resp = supabase.table("zones").select(
                        "id, risk_multiplier"
                    ).eq("id", zone_id).execute()
                    zone_rec = zone_resp.data[0] if zone_resp.data else {}

                    trigger_resp = supabase.table("trigger_events").select(
                        "id, severity, trigger_type"
                    ).eq("id", trigger_event_id).execute()
                    trigger_rec = trigger_resp.data[0] if trigger_resp.data else {
                        "severity": claim_data.get("severity", 0.5)
                    }

                    # 30-day claim count for this worker
                    thirty_ago = (datetime.now(IST) - timedelta(days=30))
                    thirty_ago_str = thirty_ago.replace(tzinfo=None).isoformat()
                    freq_resp = supabase.table("claims").select(
                        "id", count="exact"
                    ).eq("worker_id", worker_id).gte(
                        "created_at", thirty_ago_str
                    ).execute()
                    worker_claim_count_30d = freq_resp.count or 0

                    # Concurrent claims in same zone/hour
                    now_ist = datetime.now(IST)
                    hour_start = now_ist.replace(minute=0, second=0, microsecond=0)
                    hour_start_str = hour_start.replace(tzinfo=None).isoformat()
                    zone_hour_resp = supabase.table("claims").select(
                        "id", count="exact"
                    ).eq("zone_id", zone_id).gte(
                        "created_at", hour_start_str
                    ).execute()
                    zone_claim_count_hour = zone_hour_resp.count or 0

                    # Build claim dict for scorer
                    claim_for_scorer = {
                        "payout_amount": claim_data.get("payout_amount",
                            claim_data.get("disrupted_hours", 2.0) * 80.0 * 0.80),
                        "disrupted_hours": claim_data.get("disrupted_hours", 2.0),
                        "created_at": datetime.now(IST).isoformat(),
                    }

                    layer2_score = await IsolationForestScorer.score(
                        claim=claim_for_scorer,
                        worker=worker_rec,
                        trigger=trigger_rec,
                        zone=zone_rec,
                        layer1_score=msas_score,
                        worker_claim_count_30d=worker_claim_count_30d,
                        zone_claim_count_hour=zone_claim_count_hour,
                        fallback_score=msas_score,  # fallback = Layer 1
                    )
                    print(f"   🤖 Layer 2 (IF): {layer2_score:.3f}")
                else:
                    print("   ⚠️ Layer 2 model not loaded — using Layer 1 only")

            except Exception as l2_err:
                print(f"   ⚠️ Layer 2 error: {l2_err} — falling back to Layer 1")

            # ── COMBINED SCORE: 60% Layer 1 + 40% Layer 2 ─────────────────
            combined_score = (msas_score * 0.60) + (layer2_score * 0.40)
            combined_score = round(min(combined_score, 1.0), 3)

            fraud_flags["layer2_isolation_forest"] = {
                "score": round(layer2_score, 3),
                "layer1_score": round(msas_score, 3),
                "combined_score": combined_score,
                "model": "IsolationForest_v1",
            }

            # Determine claim status based on COMBINED score
            if combined_score < 0.40:
                status = "auto_approved"
                status_emoji = "✅"
            elif combined_score < 0.80:
                status = "review"
                status_emoji = "🔍"
            else:
                status = "rejected"
                status_emoji = "❌"

            print(
                f"\n   Layer 1: {msas_score:.3f} | "
                f"Layer 2: {layer2_score:.3f} | "
                f"Combined: {combined_score:.3f}"
            )
            print(
                f"   Passed: {fraud_flags['checks_passed']} | "
                f"Failed: {fraud_flags['checks_failed']}"
            )
            print(f"   {status_emoji} CLAIM STATUS: {status.upper()}\n")

            return combined_score, fraud_flags

        except Exception as e:
            print(f"[ERROR] FraudEngine.score_claim failed: {e}")
            # Return neutral score on error (fail-safe)
            return 0.5, fraud_flags

    @staticmethod
    async def _check_gps_zone(supabase, worker_id: str, zone_id: str) -> dict:
        """
        CHECK 1: GPS Zone Verification
        Worker location must be in zone (85% in zone = pass, 15% outside = weak flag)

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            from utils.fraud_helpers import get_mock_worker_location, haversine_distance

            # Get zone coordinates
            zone_response = (
                supabase.table("zones").select("lat, lon").eq("id", zone_id).execute()
            )

            if not zone_response.data:
                return {
                    "name": "gps_zone_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": "Zone coordinates not found (skip)",
                }

            zone = zone_response.data[0]
            zone_lat = zone.get("lat")
            zone_lon = zone.get("lon")

            # Get mock worker location (85% chance in zone)
            worker_lat, worker_lon = await get_mock_worker_location(
                worker_id, zone_lat, zone_lon
            )

            # Calculate distance (should be <5km for zone)
            distance_km = haversine_distance(zone_lat, zone_lon, worker_lat, worker_lon)

            passed = distance_km <= 5.0  # Within 5km = in zone

            return {
                "name": "gps_zone_check",
                "passed": passed,
                "weight": 0.40 if not passed else 0.0,
                "reason": f"Distance {distance_km:.1f}km from zone center {'✓' if passed else '✗'}",
            }

        except Exception as e:
            print(f"[WARNING] GPS zone check error: {e}")
            return {
                "name": "gps_zone_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_shift_timing(
        supabase, worker_id: str, trigger_start: str, trigger_end: str
    ) -> dict:
        """
        CHECK 2: Shift Timing Verification
        Trigger must occur during expected working hours (6 AM - 11 PM IST)

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            if not trigger_start:
                return {
                    "name": "shift_timing_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": "No trigger time (skip)",
                }

            # Parse trigger start time
            try:
                trigger_dt = datetime.fromisoformat(
                    trigger_start.replace("Z", "+00:00")
                )
                trigger_ist = trigger_dt.astimezone(IST)
                hour = trigger_ist.hour
            except (ValueError, AttributeError, TypeError) as e:
                print(f"[WARNING] Could not parse trigger time: {e}")
                return {
                    "name": "shift_timing_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": f"Could not parse time (skip)",
                }

            # Expected working hours: 6 AM - 11 PM IST
            expected_hours = (6, 23)  # 6 to 22 hour (11 PM inclusive)
            passed = expected_hours[0] <= hour < expected_hours[1]

            return {
                "name": "shift_timing_check",
                "passed": passed,
                "weight": 0.35 if not passed else 0.0,
                "reason": f"Trigger at {hour:02d}:00 IST {'✓' if passed else '✗ off-hours'}",
            }

        except Exception as e:
            print(f"[WARNING] Shift timing check error: {e}")
            return {
                "name": "shift_timing_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_duplicate_claim(
        supabase, policy_id: str, trigger_event_id: str
    ) -> dict:
        """
        CHECK 3: Duplicate Claim Prevention (Hard Reject)
        Worker cannot claim same trigger twice.

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            existing = (
                supabase.table("claims")
                .select("id")
                .eq("policy_id", policy_id)
                .eq("trigger_event_id", trigger_event_id)
                .execute()
            )

            passed = not existing.data  # Pass if NO existing claims

            return {
                "name": "duplicate_claim_check",
                "passed": passed,
                "weight": 1.00 if not passed else 0.0,
                "reason": (
                    "Duplicate claim" if not passed else "First claim for trigger"
                ),
            }

        except Exception as e:
            print(f"[WARNING] Duplicate claim check error: {e}")
            return {
                "name": "duplicate_claim_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_claim_frequency(supabase, worker_id: str) -> dict:
        """
        CHECK 4: Claim Frequency Verification (+0.30)
        Flag workers who have filed more than 8 claims in the last 30 days.

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            thirty_days_ago = (datetime.now(IST) - timedelta(days=30)).replace(
                tzinfo=None
            ).isoformat()

            result = (
                supabase.table("claims")
                .select("id", count="exact")
                .eq("worker_id", worker_id)
                .gte("created_at", thirty_days_ago)
                .execute()
            )

            count = result.count or 0
            passed = count <= 8

            return {
                "name": "frequency_check",
                "passed": passed,
                "weight": 0.30 if not passed else 0.0,
                "reason": f"{count} claims in last 30 days {'✓' if passed else '✗ too frequent (>8)'}",
            }

        except Exception as e:
            print(f"[WARNING] Frequency check error: {e}")
            return {
                "name": "frequency_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_order_volume_contradiction(
        supabase, worker_id: str, trigger_start: str, trigger_end: str
    ) -> dict:
        """
        CHECK 5: Order Volume Contradiction
        If OVC trigger fired, but worker shows high delivery activity, flag.
        Context: OVC claims when orders collapsed but worker still delivered.

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            # Get mock platform activity (90% activity rate simulated)
            from utils.fraud_helpers import get_mock_platform_activity

            activity_rate = await get_mock_platform_activity(worker_id)

            # High activity (>70%) during OVC = contradiction
            passed = activity_rate <= 0.70  # Pass if low activity

            return {
                "name": "order_volume_contradiction",
                "passed": passed,
                "weight": 0.30 if not passed else 0.0,
                "reason": f"Activity {activity_rate*100:.0f}% {'✓' if passed else '✗ high during OVC'}",
            }

        except Exception as e:
            print(f"[WARNING] OVC contradiction check error: {e}")
            return {
                "name": "order_volume_contradiction",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_platform_activity(
        supabase, worker_id: str, trigger_start: str, trigger_end: str
    ) -> dict:
        """
        CHECK 6: Platform Activity During Disruption
        Worker should show NO app activity during disruption window.
        If they have activity, they may have worked elsewhere = fraud risk.

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            from utils.fraud_helpers import get_mock_platform_activity

            activity_rate = await get_mock_platform_activity(worker_id)

            # No activity (0%) during disruption = legitimate; high activity = suspicious
            passed = activity_rate < 0.30  # Pass if low activity

            return {
                "name": "platform_activity_check",
                "passed": passed,
                "weight": 0.25 if not passed else 0.0,
                "reason": f"App activity {activity_rate*100:.0f}% {'✓' if passed else '✗ active during disruption'}",
            }

        except Exception as e:
            print(f"[WARNING] Platform activity check error: {e}")
            return {
                "name": "platform_activity_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_new_worker(supabase, worker_id: str) -> dict:
        """
        CHECK 7: New Worker Verification
        Workers registered <7 days are slightly higher risk.

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            worker_response = (
                supabase.table("workers")
                .select("created_at")
                .eq("id", worker_id)
                .execute()
            )

            if not worker_response.data:
                return {
                    "name": "new_worker_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": "Worker not found (skip)",
                }

            worker = worker_response.data[0]
            created_at_str = worker.get("created_at")

            if not created_at_str:
                return {
                    "name": "new_worker_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": "No registration date (skip)",
                }

            # Parse creation date
            try:
                # Try parsing as ISO format with timezone
                if "+" in created_at_str or created_at_str.endswith("Z"):
                    created_at = datetime.fromisoformat(
                        created_at_str.replace("Z", "+00:00")
                    )
                else:
                    # Assume UTC for naive timestamps
                    created_at = datetime.fromisoformat(created_at_str)
                    created_at = created_at.replace(tzinfo=pytz.UTC)
            except:
                return {
                    "name": "new_worker_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": "Could not parse registration date (skip)",
                }

            now = datetime.now(IST)
            days_active = (now - created_at).days

            passed = days_active >= 7  # Pass if 7+ days old

            return {
                "name": "new_worker_check",
                "passed": passed,
                "weight": 0.15 if not passed else 0.0,
                "reason": f"Registered {days_active} days ago {'✓' if passed else '✗ very new'}",
            }

        except Exception as e:
            print(f"[WARNING] New worker check error: {e}")
            return {
                "name": "new_worker_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }

    @staticmethod
    async def _check_cluster_fraud(
        supabase, trigger_event_id: str, zone_id: str
    ) -> dict:
        """
        CLUSTER FRAUD DETECTION
        If >30% of workers in zone show fraud for same trigger, flag entire cluster.
        This prevents coordinated fraud across delivery partners.

        Args:
            trigger_event_id: Trigger event UUID
            zone_id: Zone UUID

        Returns:
            Dict with {passed: bool, weight: float, reason: str}
        """
        try:
            # Get current week boundaries (Monday-Sunday)
            now = datetime.now(pytz.UTC)
            days_since_monday = now.weekday()
            week_start = now - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)

            # Get all active policies in zone for this week
            policies_response = (
                supabase.table("policies")
                .select("id")
                .eq("zone_id", zone_id)
                .eq("status", "active")
                .gte("week_start", week_start.strftime("%Y-%m-%d"))
                .lte("week_end", week_end.strftime("%Y-%m-%d"))
                .execute()
            )

            if not policies_response.data:
                return {
                    "name": "cluster_fraud_check",
                    "passed": True,
                    "weight": 0.0,
                    "reason": "No policies in zone",
                }

            total_policies = len(policies_response.data)

            # Get fraud claims for this trigger in zone
            fraud_claims = (
                supabase.table("claims")
                .select("id")
                .eq("trigger_event_id", trigger_event_id)
                .in_("status", ["rejected", "review"])
                .execute()
            )

            fraud_count = len(fraud_claims.data) if fraud_claims.data else 0
            fraud_percentage = (
                (fraud_count / total_policies) * 100 if total_policies > 0 else 0
            )

            # >30% fraud rate triggers cluster detection
            passed = fraud_percentage <= 30.0

            return {
                "name": "cluster_fraud_check",
                "passed": passed,
                "weight": 0.20 if not passed else 0.0,
                "reason": f"Zone fraud rate {fraud_percentage:.1f}% ({fraud_count}/{total_policies}) "
                f"{'✓' if passed else '✗ cluster detected'}",
            }

        except Exception as e:
            print(f"[WARNING] Cluster fraud check error: {e}")
            return {
                "name": "cluster_fraud_check",
                "passed": True,
                "weight": 0.0,
                "reason": f"Check skipped (error: {str(e)[:30]})",
            }
