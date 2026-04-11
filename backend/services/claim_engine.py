"""
DropSafe Auto-Claim Engine
Automatically processes trigger events and creates claims for affected policies
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from database import get_supabase
import pytz
from .fraud_engine import FraudEngine
from .payout_engine import PayoutEngine

IST = pytz.timezone("Asia/Kolkata")


class ClaimEngine:
    """Automatically process triggers and manage claims."""

    @staticmethod
    async def process_trigger(trigger_event_id: str):
        """
        Process a verified trigger event and create auto-claims for affected policies.

        Flow:
        1. Fetch trigger_event and validate verified=True
        2. Query all active policies in affected zone for current week
        3. For each policy, calculate disrupted_hours and claim amount
        4. Call FraudEngine to score each claim
        5. Create claims with auto_approved/review/rejected status
        6. Send WhatsApp notifications to workers

        Args:
            trigger_event_id: UUID of verified trigger event
        """
        try:
            supabase = get_supabase()

            # Fetch trigger event
            trigger_response = (
                supabase.table("trigger_events")
                .select("*, zones(id, dark_store_name, pincode)")
                .eq("id", trigger_event_id)
                .execute()
            )

            if not trigger_response.data:
                print(f"[ClaimEngine] Trigger {trigger_event_id} not found")
                return

            trigger = trigger_response.data[0]

            # Validate trigger is verified
            if not trigger.get("verified"):
                print(f"[ClaimEngine] Trigger {trigger_event_id} is not verified")
                return

            zone = trigger.get("zones", {})
            zone_id = zone.get("id")
            zone_name = zone.get("dark_store_name", "Unknown")
            trigger_type = trigger.get("trigger_type")
            severity = trigger.get("severity", 0.5)
            trigger_start = trigger.get("start_time")
            trigger_end = trigger.get("end_time")

            print(f"\n[ClaimEngine] Processing {trigger_type} trigger in {zone_name}")

            # Get current UTC week boundaries (Monday-Sunday)
            now_utc = datetime.now(pytz.UTC)
            days_since_monday = now_utc.weekday()
            week_start = now_utc - timedelta(days=days_since_monday)
            week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
            week_end = week_start + timedelta(days=7)

            # Query active policies in zone for this week
            policies_response = (
                supabase.table("policies")
                .select("*, workers(id, encrypted_phone, name, avg_hourly_income)")
                .eq("zone_id", zone_id)
                .eq("status", "active")
                .gte("week_start", week_start.strftime("%Y-%m-%d"))
                .lte("week_end", week_end.strftime("%Y-%m-%d"))
                .execute()
            )

            if not policies_response.data:
                print(f"[ClaimEngine] No active policies in {zone_name} this week")
                return

            policies = policies_response.data
            print(f"[ClaimEngine] Found {len(policies)} active policies in {zone_name}")

            # Process each policy
            claims_created = 0
            for policy in policies:
                try:
                    worker = policy.get("workers", {})
                    worker_id = worker.get("id")
                    phone = worker.get("encrypted_phone")
                    worker_name = worker.get("name", "Worker")

                    # Check if already claimed for this trigger
                    existing_claim = (
                        supabase.table("claims")
                        .select("id")
                        .eq("trigger_event_id", trigger_event_id)
                        .eq("policy_id", policy.get("id"))
                        .execute()
                    )

                    if existing_claim.data:
                        print(
                            f"  [SKIP] Worker {worker_name} already claimed for this trigger"
                        )
                        continue

                    # Calculate disrupted hours
                    # Use worker's declared hours from the worker object
                    worker_declared_hours = worker.get("declared_weekly_hours", 40)
                    disrupted_hours = ClaimEngine.calculate_disrupted_hours(
                        trigger, worker_declared_hours
                    )

                    # Calculate payout amount
                    # Formula: avg_hourly_income × disrupted_hours × 0.80
                    avg_hourly_income = float(worker.get("avg_hourly_income", 80.0))
                    payout_amount = avg_hourly_income * disrupted_hours * 0.80

                    # Score claim for fraud
                    fraud_score, fraud_flags = await FraudEngine.score_claim(
                        claim_data={
                            "trigger_event_id": trigger_event_id,
                            "policy_id": policy.get("id"),
                            "worker_id": worker_id,
                            "zone_id": zone_id,
                            "trigger_type": trigger_type,
                            "trigger_start": trigger_start,
                            "trigger_end": trigger_end,
                            "disrupted_hours": disrupted_hours,
                            "severity": severity,
                        }
                    )

                    # Determine claim status based on fraud score
                    claim_status = ClaimEngine.determine_status(fraud_score)

                    # Create claim record (store times in IST)
                    now_ist = datetime.now(IST)
                    now_ist_no_tz = now_ist.replace(tzinfo=None)
                    claim_data = {
                        "policy_id": policy.get("id"),
                        "worker_id": worker_id,
                        "zone_id": zone_id,
                        "trigger_event_id": trigger_event_id,
                        "disrupted_hours": disrupted_hours,
                        "payout_amount": round(payout_amount, 2),
                        "status": claim_status,
                        "fraud_score": round(fraud_score, 2),
                        "fraud_flags": fraud_flags,
                        "created_at": now_ist_no_tz.isoformat(),
                        "reviewed_at": None,
                        "reviewed_by": None,
                        "rejection_reason": None,
                    }

                    response = supabase.table("claims").insert(claim_data).execute()

                    if response.data:
                        claim = response.data[0]
                        claim_id = claim.get("id")

                        # Send notification
                        await ClaimEngine.notify_worker(
                            phone=phone,
                            worker_name=worker_name,
                            claim_status=claim_status,
                            payout_amount=payout_amount,
                            trigger_type=trigger_type,
                            zone_name=zone_name,
                            disrupted_hours=disrupted_hours,
                            claim_id=claim_id,
                        )

                        # If auto_approved, immediately process payout
                        if claim_status == "auto_approved":
                            payout_result = await PayoutEngine.process_payout(claim_id)
                            if payout_result.get("status") == "success":
                                print(
                                    f"    [💸] Payout {payout_result.get('payout_id')[:8]} initiated"
                                )

                        claims_created += 1
                        print(
                            f"  [OK] Claim {claim_id[:8]} created for {worker_name} | "
                            f"₹{payout_amount:.2f} | Status: {claim_status}"
                        )

                except Exception as e:
                    print(
                        f"  [ERROR] Failed to process policy for {worker.get('name')}: {e}"
                    )
                    continue

            print(
                f"[ClaimEngine] Created {claims_created} claims for {trigger_type} in {zone_name}\n"
            )

            # CLUSTER FRAUD FREEZE: After all claims processed, check if >30%
            # of claims for this trigger are flagged. If so, freeze auto-approved
            # payouts by moving them to review (prevents coordinated fraud payouts).
            if claims_created > 0:
                await ClaimEngine._freeze_cluster_fraud_payouts(
                    supabase, trigger_event_id, zone_name, trigger_type
                )

        except Exception as e:
            print(f"[ERROR] ClaimEngine.process_trigger failed: {e}")

    @staticmethod
    async def _freeze_cluster_fraud_payouts(
        supabase, trigger_event_id: str, zone_name: str, trigger_type: str
    ):
        """
        CLUSTER FRAUD FREEZE
        After all claims are created for a trigger, check the overall fraud rate.
        If >30% of claims are flagged (review/rejected), move all auto_approved
        claims for this trigger to 'review' — preventing any payout from going out
        until a human investigator clears the batch.

        Args:
            supabase: Supabase client
            trigger_event_id: Trigger event UUID
            zone_name: Zone name (for logging)
            trigger_type: Trigger type (for logging)
        """
        try:
            # Get all claims for this trigger
            all_claims_resp = (
                supabase.table("claims")
                .select("id, status")
                .eq("trigger_event_id", trigger_event_id)
                .execute()
            )

            if not all_claims_resp.data:
                return

            all_claims = all_claims_resp.data
            total = len(all_claims)
            flagged = sum(
                1 for c in all_claims if c.get("status") in ("review", "rejected")
            )
            fraud_rate = (flagged / total) * 100 if total > 0 else 0.0

            print(
                f"[ClaimEngine] Cluster fraud check: {flagged}/{total} flagged "
                f"({fraud_rate:.1f}%) for trigger {trigger_event_id[:8]} in {zone_name}"
            )

            if fraud_rate > 30.0:
                # Freeze: move all auto_approved claims for this trigger to 'review'
                auto_approved_ids = [
                    c["id"]
                    for c in all_claims
                    if c.get("status") == "auto_approved"
                ]

                if auto_approved_ids:
                    now_ist_no_tz = datetime.now(IST).replace(tzinfo=None)
                    supabase.table("claims").update(
                        {
                            "status": "review",
                            "rejection_reason": (
                                f"⚠️ CLUSTER FRAUD FREEZE: {fraud_rate:.0f}% of zone claims flagged. "
                                f"Manual review required."
                            ),
                            "updated_at": now_ist_no_tz.isoformat(),
                        }
                    ).in_("id", auto_approved_ids).execute()

                    print(
                        f"[ClaimEngine] ⚠️  CLUSTER FRAUD DETECTED in {zone_name} "
                        f"({trigger_type}): {fraud_rate:.0f}% fraud rate. "
                        f"Froze {len(auto_approved_ids)} auto-approved claims → review."
                    )

        except Exception as e:
            print(f"[WARNING] Cluster fraud freeze check failed: {e}")

    @staticmethod
    def calculate_disrupted_hours(trigger: dict, worker_declared_hours: int) -> float:
        """
        Calculate hours of business disruption from trigger event.

        Capped at 8 hours max per day (realistic business impact).

        Args:
            trigger: Trigger event dict with start_time and end_time
            worker_declared_hours: Worker's declared weekly hours (for context)

        Returns:
            Disrupted hours (0-8)
        """
        try:
            start = trigger.get("start_time")
            end = trigger.get("end_time")

            if not start or not end:
                return 1.0  # Default to 1 hour if times missing

            # Parse ISO format timestamps
            start_dt = datetime.fromisoformat(start.replace("Z", "+00:00"))
            end_dt = datetime.fromisoformat(end.replace("Z", "+00:00"))

            # Calculate hours duration
            duration = (end_dt - start_dt).total_seconds() / 3600

            # Cap at 8 hours (realistic business operating hours)
            disrupted_hours = min(float(duration), 8.0)

            return round(disrupted_hours, 2)

        except Exception as e:
            print(f"[WARNING] Error calculating disrupted hours: {e}")
            return 1.0

    @staticmethod
    def determine_status(fraud_score: float) -> str:
        """
        Determine claim status based on fraud score.

        TESTING MODE: Thresholds temporarily adjusted for demonstration
        - 0.00-0.30: auto_approved (low risk)
        - 0.30-0.60: review (moderate risk, needs manual review)
        - 0.60-0.85: review (DEMO MODE - lowered rejection threshold for testing)
        - 0.85-1.00: rejected (high risk, automatic reject)

        Args:
            fraud_score: MSAS score (0-1)

        Returns:
            Status: "auto_approved", "review", or "rejected"
        """
        if fraud_score < 0.30:
            return "auto_approved"
        elif fraud_score < 0.85:  # DEMO: Changed from 0.60 to 0.85
            return "review"
        else:
            return "rejected"

    @staticmethod
    async def notify_worker(
        phone: str,
        worker_name: str,
        claim_status: str,
        payout_amount: float,
        trigger_type: str,
        zone_name: str,
        disrupted_hours: float,
        claim_id: str,
    ):
        """
        Send WhatsApp notification to worker about claim status.

        Args:
            phone: Worker phone number (without +91)
            worker_name: Worker display name
            claim_status: "auto_approved", "review", or "rejected"
            payout_amount: Claim payout in INR
            trigger_type: Type of trigger (rain, heat, aqi, curfew, order_collapse, store_closure)
            zone_name: Zone name
            disrupted_hours: Disrupted hours
            claim_id: Claim UUID
        """
        try:
            from .whatsapp_service import WhatsAppService

            # Emoji map for trigger types
            emoji_map = {
                "rain": "🌧️",
                "heat": "🔥",
                "aqi": "😷",
                "curfew": "🚨",
                "order_collapse": "📉",
                "store_closure": "🔒",
            }

            emoji = emoji_map.get(trigger_type, "⚠️")

            if claim_status == "auto_approved":
                message = (
                    f"✅ *Claim Approved!*\n\n"
                    f"Hey {worker_name}, your claim has been *auto-approved*.\n\n"
                    f"{emoji} *Incident*: {trigger_type.replace('_', ' ').title()}\n"
                    f"📍 *Zone*: {zone_name}\n"
                    f"⏱️ *Disruption*: {disrupted_hours:.1f} hours\n"
                    f"💰 *Payout*: ₹{payout_amount:.2f}\n\n"
                    f"Amount will be credited within 24 hours."
                )
            elif claim_status == "review":
                message = (
                    f"⏳ *Claim Under Review*\n\n"
                    f"Hey {worker_name}, your claim is under review.\n\n"
                    f"{emoji} *Incident*: {trigger_type.replace('_', ' ').title()}\n"
                    f"📍 *Zone*: {zone_name}\n"
                    f"⏱️ *Disruption*: {disrupted_hours:.1f} hours\n"
                    f"💰 *Potential Payout*: ₹{payout_amount:.2f}\n\n"
                    f"Our team will review and confirm within 2 hours.\n"
                    f"Claim ID: {claim_id[:8]}"
                )
            else:  # rejected
                message = (
                    f"❌ *Claim Not Approved*\n\n"
                    f"Hey {worker_name}, your claim could not be approved.\n\n"
                    f"{emoji} *Incident*: {trigger_type.replace('_', ' ').title()}\n"
                    f"📍 *Zone*: {zone_name}\n"
                    f"⏱️ *Disruption*: {disrupted_hours:.1f} hours\n\n"
                    f"This may be due to location or timing mismatches.\n"
                    f"Reply *DISPUTE* to challenge this decision.\n"
                    f"Claim ID: {claim_id[:8]}"
                )

            await WhatsAppService.send_message(phone, message)

        except Exception as e:
            print(f"[WARNING] Failed to send WhatsApp notification: {e}")
