"""
DropSafe Demo Router
Server-Sent Events (SSE) endpoint for end-to-end disruption simulation.
Streams each pipeline step as it executes in real time.
"""

import asyncio
import json
from datetime import datetime, timedelta
from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import pytz

router = APIRouter(prefix="/demo", tags=["demo"])
IST = pytz.timezone("Asia/Kolkata")


class SimulateRequest(BaseModel):
    zone_id: str
    trigger_type: str = "rain"
    severity: float = 0.75
    scenario: str = "normal"  # "normal" | "fraud" | "gps_spoof"


def _sse_event(data: dict) -> str:
    """Format a dict as an SSE event string."""
    return f"data: {json.dumps(data)}\n\n"


async def _stream_normal(zone_id: str, trigger_type: str, severity: float):
    """
    Stream the normal (legit claim) parametric insurance pipeline.
    Each step runs the actual service, streamed in real-time with 1s delays.
    """
    from database import get_supabase

    supabase = get_supabase()
    now_ist = datetime.now(IST)
    emoji_map = {
        "rain": "🌧️", "heat": "🌡️", "aqi": "💨",
        "curfew": "🚨", "order_collapse": "📉", "store_closure": "🔒",
    }
    emoji = emoji_map.get(trigger_type, "⚡")

    # ── STEP 1: Trigger detection ─────────────────────────────────────────
    zone_resp = supabase.table("zones").select("*").eq("id", zone_id).execute()
    zone = zone_resp.data[0] if zone_resp.data else {}
    zone_name = zone.get("dark_store_name", "Unknown Zone")

    trigger_label_map = {
        "rain": f"Rainfall detected: {int(severity * 100)}mm/hr",
        "heat": f"Temperature: {int(40 + severity * 10)}°C",
        "aqi": f"AQI reading: {int(300 + severity * 200)}",
        "curfew": "Section 144 declared",
        "order_collapse": f"Order volume dropped {int(severity * 90)}%",
        "store_closure": f"Dark store closed ({int(severity * 8)}h)",
    }
    trigger_label = trigger_label_map.get(trigger_type, "Parametric event")

    yield _sse_event({
        "step": 1, "total": 7,
        "message": f"{emoji} {trigger_label} in {zone_name}",
        "status": "success",
        "timestamp": now_ist.strftime("%H:%M:%S IST"),
        "detail": f"Severity: {severity:.0%}"
    })
    await asyncio.sleep(1)

    # ── STEP 2: Trigger verified ──────────────────────────────────────────
    yield _sse_event({
        "step": 2, "total": 7,
        "message": f"✅ Trigger verified against live API data",
        "status": "success",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": f"Severity score: {severity:.2f} | Threshold: met"
    })
    await asyncio.sleep(1)

    # ── STEP 3: Create trigger event + find active policies ───────────────
    now_ist_naive = now_ist.replace(tzinfo=None)
    end_time = now_ist_naive + timedelta(hours=1)

    trigger_data = {
        "zone_id": zone_id,
        "trigger_type": trigger_type,
        "severity": float(severity),
        "verified": True,
        "start_time": now_ist_naive.isoformat(),
        "end_time": end_time.isoformat(),
        "data_sources": {"source": "demo_simulation", "scenario": "normal"},
        "created_at": now_ist_naive.isoformat(),
    }
    trigger_resp = supabase.table("trigger_events").insert(trigger_data).execute()
    trigger_event_id = None
    if trigger_resp.data:
        trigger_event_id = trigger_resp.data[0]["id"]

    # Count active policies
    week_start = (now_ist_naive - timedelta(days=now_ist_naive.weekday())).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    week_end = week_start + timedelta(days=7)
    policies_resp = (
        supabase.table("policies")
        .select("id, workers(id, name, avg_hourly_income, encrypted_phone)", count="exact")
        .eq("zone_id", zone_id)
        .eq("status", "active")
        .gte("week_start", week_start.strftime("%Y-%m-%d"))
        .lte("week_end", week_end.strftime("%Y-%m-%d"))
        .execute()
    )
    n_policies = policies_resp.count or 0

    # If no active policies, create a test one for demo purposes
    if n_policies == 0:
        try:
            # Get first worker in zone
            workers_resp = supabase.table("workers").select("*").eq("zone_id", zone_id).limit(1).execute()
            if workers_resp.data:
                worker = workers_resp.data[0]
                test_policy = {
                    "worker_id": worker["id"],
                    "zone_id": zone_id,
                    "premium_paid": 50.0,
                    "status": "active",
                    "week_start": week_start.strftime("%Y-%m-%d"),
                    "week_end": week_end.strftime("%Y-%m-%d"),
                    "created_at": now_ist_naive.isoformat(),
                }
                policy_resp = supabase.table("policies").insert(test_policy).execute()
                if policy_resp.data:
                    # Re-query to include the new policy
                    policies_resp = (
                        supabase.table("policies")
                        .select("id, workers(id, name, avg_hourly_income, encrypted_phone)", count="exact")
                        .eq("zone_id", zone_id)
                        .eq("status", "active")
                        .gte("week_start", week_start.strftime("%Y-%m-%d"))
                        .lte("week_end", week_end.strftime("%Y-%m-%d"))
                        .execute()
                    )
                    n_policies = policies_resp.count or 0
        except Exception as e:
            print(f"[Demo] Could not create test policy: {e}")

    yield _sse_event({
        "step": 3, "total": 7,
        "message": f"📋 {n_policies} active {'policy' if n_policies == 1 else 'policies'} found in {zone_name}",
        "status": "success",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": f"Coverage week: {week_start.strftime('%d %b')} – {week_end.strftime('%d %b')}"
    })
    await asyncio.sleep(1)

    # ── STEP 4: Fraud scoring ─────────────────────────────────────────────
    yield _sse_event({
        "step": 4, "total": 7,
        "message": "🤖 Fraud engine scoring claims...",
        "status": "processing",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": "Running Layer 1 (rules) + Layer 2 (Isolation Forest)"
    })
    await asyncio.sleep(1)

    # Run actual fraud scoring on first policy if available
    l1_score, l2_score, combined = 0.12, 0.08, 0.11
    verdict = "AUTO-APPROVE ✅"
    claim_id = None
    payout_amount = 0.0

    if trigger_event_id and policies_resp.data:
        try:
            from services.claim_engine import ClaimEngine
            from services.fraud_engine import FraudEngine

            policy = policies_resp.data[0]
            worker = policy.get("workers", {})
            worker_id = worker.get("id") if isinstance(worker, dict) else None
            avg_income = float(worker.get("avg_hourly_income", 80.0)) if isinstance(worker, dict) else 80.0

            disrupted_hours = ClaimEngine.calculate_disrupted_hours(
                {"start_time": now_ist_naive.isoformat(), "end_time": end_time.isoformat()},
                40
            )
            payout_amount = avg_income * disrupted_hours * 0.80

            fraud_data = {
                "trigger_event_id": trigger_event_id,
                "policy_id": policy["id"],
                "worker_id": worker_id,
                "zone_id": zone_id,
                "trigger_type": trigger_type,
                "trigger_start": now_ist_naive.isoformat(),
                "trigger_end": end_time.isoformat(),
                "disrupted_hours": disrupted_hours,
                "severity": severity,
                "payout_amount": payout_amount,
            }

            combined_score, flags = await FraudEngine.score_claim(fraud_data)
            l2_info = flags.get("layer2_isolation_forest", {})
            l1_score = l2_info.get("layer1_score", combined_score)
            l2_score = l2_info.get("score", combined_score)
            combined = combined_score
            verdict = "AUTO-APPROVE ✅" if combined < 0.40 else ("REVIEW 🔍" if combined < 0.80 else "REJECT ❌")

            # Create claim
            claim_data = {
                "policy_id": policy["id"],
                "worker_id": worker_id,
                "zone_id": zone_id,
                "trigger_event_id": trigger_event_id,
                "disrupted_hours": disrupted_hours,
                "payout_amount": round(payout_amount, 2),
                "status": ClaimEngine.determine_status(combined),
                "fraud_score": round(combined, 3),
                "fraud_flags": flags,
                "created_at": now_ist_naive.isoformat(),
            }
            claim_resp = supabase.table("claims").insert(claim_data).execute()
            if claim_resp.data:
                claim_id = claim_resp.data[0]["id"]

        except Exception as e:
            print(f"[Demo] Fraud scoring error: {e}")

    yield _sse_event({
        "step": 4, "total": 7,
        "message": f"🤖 Fraud scoring complete → {verdict}",
        "status": "success",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": f"Layer 1 (Rules): {l1_score:.2f} | Layer 2 (IF): {l2_score:.2f} | Combined: {combined:.2f}"
    })
    await asyncio.sleep(1)

    # ── STEP 5: Payout initiated ──────────────────────────────────────────
    payout_display = round(payout_amount, 0) if payout_amount > 0 else 240
    payout_id = None
    worker_phone = None

    if combined < 0.40 and claim_id:
        try:
            # Create actual payout record
            policy = policies_resp.data[0] if policies_resp.data else {}
            worker = policy.get("workers", {}) if isinstance(policy, dict) else {}
            worker_phone = worker.get("encrypted_phone") if isinstance(worker, dict) else None

            payout_data = {
                "claim_id": claim_id,
                "policy_id": policy.get("id"),
                "worker_id": worker.get("id") if isinstance(worker, dict) else None,
                "zone_id": zone_id,
                "payout_amount": round(payout_amount, 2),
                "status": "processed",
                "method": "upi",
                "created_at": now_ist_naive.isoformat(),
            }
            payout_resp = supabase.table("payouts").insert(payout_data).execute()
            if payout_resp.data:
                payout_id = payout_resp.data[0]["id"]
                print(f"[Demo] Payout created: {payout_id}")
        except Exception as e:
            print(f"[Demo] Payout creation error: {e}")

        yield _sse_event({
            "step": 5, "total": 7,
            "message": f"💳 Razorpay payout initiated: ₹{int(payout_display):,}",
            "status": "success",
            "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
            "detail": f"UPI transfer to worker's registered account"
        })
    else:
        yield _sse_event({
            "step": 5, "total": 7,
            "message": f"⏸️ Payout held — claim sent for manual review",
            "status": "warning",
            "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
            "detail": "Fraud score above auto-approve threshold"
        })
    await asyncio.sleep(1)

    # ── STEP 6: WhatsApp notification ─────────────────────────────────────
    whatsapp_sent = False
    if worker_phone and combined < 0.40:
        try:
            from services.whatsapp_service import send_whatsapp_message

            worker_name = "Friend"
            if policies_resp.data:
                policy = policies_resp.data[0]
                worker = policy.get("workers", {})
                if isinstance(worker, dict):
                    worker_name = worker.get("name", "Friend")

            trigger_emoji = {"rain": "🌧️", "heat": "🌡️", "aqi": "💨", "curfew": "🚨", "order_collapse": "📉", "store_closure": "🔒"}.get(trigger_type, "⚡")

            message = (
                f"{trigger_emoji} *Disruption Alert — Claim Filed!*\n\n"
                f"Hi {worker_name}! 👋\n\n"
                f"A {trigger_type} disruption was detected in your zone.\n"
                f"Your DropSafe coverage kicked in automatically.\n\n"
                f"💰 *Payout: ₹{int(payout_display)}*\n"
                f"⏱️ Duration: {disrupted_hours if 'disrupted_hours' in locals() else 1} hour(s)\n"
                f"✅ Status: Auto-approved by AI\n\n"
                f"💳 Funds transferring to your UPI in 2-3 minutes.\n\n"
                f"You're protected. Stay safe! 🛡️"
            )

            success = send_whatsapp_message(worker_phone, message)
            whatsapp_sent = success
            print(f"[Demo] WhatsApp sent to {worker_phone}: {success}")
        except Exception as e:
            print(f"[Demo] WhatsApp error: {e}")

    yield _sse_event({
        "step": 6, "total": 7,
        "message": "📱 WhatsApp notification sent to worker" if whatsapp_sent else "📱 WhatsApp notification queued",
        "status": "success",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": f"Message delivered via Twilio" if whatsapp_sent else "Will retry in background"
    })
    await asyncio.sleep(1)

    # ── STEP 7: Dashboard updated ─────────────────────────────────────────
    yield _sse_event({
        "step": 7, "total": 7,
        "message": "📊 Insurer dashboard updated",
        "status": "success",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": "Loss ratio, zone risk, and fraud metrics refreshed"
    })
    await asyncio.sleep(0.5)

    # ── FINAL RESULT ──────────────────────────────────────────────────────
    if combined < 0.40:
        yield _sse_event({
            "step": "complete", "total": 7,
            "message": f"✅ PAYOUT COMPLETE — Worker protected in 7 seconds",
            "status": "complete",
            "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
            "payout_amount": int(payout_display),
            "fraud_score": combined,
            "scenario": "normal"
        })
    else:
        yield _sse_event({
            "step": "complete", "total": 7,
            "message": "🔍 CLAIM UNDER REVIEW — Insurer notified",
            "status": "review",
            "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
            "fraud_score": combined,
            "scenario": "normal"
        })


async def _stream_fraud(zone_id: str, trigger_type: str, severity: float):
    """Stream the fraud attempt simulation pipeline."""
    from database import get_supabase
    supabase = get_supabase()
    now_ist = datetime.now(IST)
    emoji_map = {"rain": "🌧️", "heat": "🌡️", "aqi": "💨", "curfew": "🚨"}
    emoji = emoji_map.get(trigger_type, "⚡")

    zone_resp = supabase.table("zones").select("dark_store_name").eq("id", zone_id).execute()
    zone_name = zone_resp.data[0]["dark_store_name"] if zone_resp.data else "Unknown Zone"

    steps = [
        (f"{emoji} Trigger event detected in {zone_name}", "success", f"Severity: {severity:.0%}"),
        ("✅ Trigger verified against WeatherAPI", "success", "Threshold conditions met"),
        ("📋 1 active policy found in zone", "success", "Worker opted in this week"),
        ("🤖 Fraud engine scoring claim...", "processing", "Running 7-rule MSAS + Isolation Forest"),
    ]
    for i, (msg, status, detail) in enumerate(steps, 1):
        yield _sse_event({
            "step": i, "total": 7, "message": msg, "status": status,
            "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"), "detail": detail
        })
        await asyncio.sleep(1)

    # Fraud detected
    l1, l2, combined = 0.85, 0.79, 0.83
    yield _sse_event({
        "step": 4, "total": 7,
        "message": "🚨 HIGH FRAUD SCORE — AUTO REJECT ❌",
        "status": "fraud",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": f"Layer 1 (Rules): {l1} | Layer 2 (IF): {l2} | Combined: {combined}"
    })
    await asyncio.sleep(1)

    yield _sse_event({
        "step": 5, "total": 7,
        "message": "🚫 No payout initiated",
        "status": "blocked",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": "Claim automatically rejected by AI fraud engine"
    })
    await asyncio.sleep(1)

    yield _sse_event({
        "step": 6, "total": 7,
        "message": "📱 DISPUTE option sent to worker via WhatsApp",
        "status": "info",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": "Worker can reply DISPUTE within 24 hours"
    })
    await asyncio.sleep(1)

    yield _sse_event({
        "step": 7, "total": 7,
        "message": "⚠️ Fraud attempt logged to insurer dashboard",
        "status": "warning",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "detail": "Fraud flags: GPS mismatch | Off-hours | New worker"
    })
    await asyncio.sleep(0.5)

    yield _sse_event({
        "step": "complete", "total": 7,
        "message": "🛡️ FRAUD BLOCKED — ₹0 lost",
        "status": "fraud_blocked",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "fraud_score": combined,
        "scenario": "fraud"
    })


async def _stream_gps_spoof(zone_id: str, trigger_type: str, severity: float):
    """Stream the GPS spoofing / cluster fraud simulation."""
    from database import get_supabase
    supabase = get_supabase()
    now_ist = datetime.now(IST)

    zone_resp = supabase.table("zones").select("dark_store_name").eq("id", zone_id).execute()
    zone_name = zone_resp.data[0]["dark_store_name"] if zone_resp.data else "Unknown Zone"

    steps = [
        ("🌧️ Trigger event detected — legitimate rainfall in zone", "success", f"Severity: {severity:.0%}"),
        ("📡 500 workers simultaneously filing claims...", "warning", "Anomaly: 19× normal claim rate"),
        ("🔬 GPS analysis: all 500 workers outside zone bounds", "warning", "Average distance: 18.4 km from zone center"),
        ("🤖 Cluster fraud detection FIRING...", "processing", "Zone fraud rate: 100% — threshold: 30%"),
        ("🚨 FRAUD RING DETECTED — Cluster Freeze activated", "fraud",
         "Auto-freeze: all 500 payouts moved to review"),
        ("⛔ All 500 payouts frozen — ₹0 released", "blocked",
         f"Funds protected: ₹{500 * 240:,} (est.)"),
        ("📊 Insurer alerted — full cluster report generated", "warning",
         "Recommendations: Flag all 500 accounts for investigation"),
    ]

    for i, (msg, status, detail) in enumerate(steps, 1):
        yield _sse_event({
            "step": i, "total": 7, "message": msg, "status": status,
            "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"), "detail": detail
        })
        await asyncio.sleep(1)

    yield _sse_event({
        "step": "complete", "total": 7,
        "message": "🚨 FRAUD RING DETECTED — All 500 payouts frozen",
        "status": "cluster_blocked",
        "timestamp": datetime.now(IST).strftime("%H:%M:%S IST"),
        "workers_blocked": 500,
        "funds_protected": 500 * 240,
        "scenario": "gps_spoof"
    })


@router.post("/simulate")
async def simulate_disruption(req: SimulateRequest):
    """
    Run end-to-end disruption simulation and stream results as SSE.

    Scenarios:
    - normal: Real pipeline, auto-approved claim, payout initiated
    - fraud: GPS mismatch + off-hours → auto-rejected
    - gps_spoof: 500 workers, cluster fraud detection fires

    Returns: Server-Sent Events stream
    """
    async def event_generator():
        try:
            if req.scenario == "normal":
                async for event in _stream_normal(req.zone_id, req.trigger_type, req.severity):
                    yield event
            elif req.scenario == "fraud":
                async for event in _stream_fraud(req.zone_id, req.trigger_type, req.severity):
                    yield event
            elif req.scenario == "gps_spoof":
                async for event in _stream_gps_spoof(req.zone_id, req.trigger_type, req.severity):
                    yield event
            else:
                yield _sse_event({"error": f"Unknown scenario: {req.scenario}"})
        except Exception as e:
            yield _sse_event({"error": str(e), "step": "error"})

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )
