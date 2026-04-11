from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import Optional
from datetime import datetime
from database import get_supabase
import pytz
from services.payout_engine import PayoutEngine
from utils.whatsapp_helpers import send_whatsapp_message

router = APIRouter(prefix="/fraud", tags=["fraud"])

IST = pytz.timezone("Asia/Kolkata")


class FraudScoreRequest(BaseModel):
    gps_match: bool
    order_volume_collapsed: bool
    cell_tower_match: bool
    shift_active: bool


class FraudScoreResponse(BaseModel):
    fraud_score: float = Field(..., ge=0.0, le=1.0)


class ClaimApprovalRequest(BaseModel):
    """Request to approve a claim."""

    reason: Optional[str] = None  # Manual review reason


class ClaimRejectionRequest(BaseModel):
    """Request to reject a claim."""

    reason: str = Field(..., description="Reason for rejection")


@router.post("/score", response_model=FraudScoreResponse)
async def fraud_score(payload: FraudScoreRequest):
    # Simple weighted "probability of fraud" for Phase 1 demo purposes.
    # Suspicious conditions push the score toward 1.0.
    weights = {
        "gps_mismatch": 0.35,
        "order_volume_not_collapsed": 0.25,
        "cell_tower_mismatch": 0.25,
        "shift_inactive": 0.15,
    }

    suspicious_sum = 0.0
    if not payload.gps_match:
        suspicious_sum += weights["gps_mismatch"]
    if not payload.order_volume_collapsed:
        suspicious_sum += weights["order_volume_not_collapsed"]
    if not payload.cell_tower_match:
        suspicious_sum += weights["cell_tower_mismatch"]
    if not payload.shift_active:
        suspicious_sum += weights["shift_inactive"]

    # weights intentionally sum to 1.0
    fraud_score_value = max(0.0, min(1.0, suspicious_sum))
    return FraudScoreResponse(fraud_score=round(fraud_score_value, 3))


@router.get("/claims/review")
async def get_review_queue():
    """
    Get queue of claims awaiting manual review.

    Shows claims with status='review' that need human verification.

    Returns:
        List of claims with full details including fraud flags
    """
    try:
        supabase = get_supabase()

        # Fetch claims awaiting review
        claims_response = (
            supabase.table("claims")
            .select(
                "*, workers(name, encrypted_phone), "
                "trigger_events(trigger_type, severity, start_time)"
            )
            .eq("status", "review")
            .order("created_at", desc=True)
            .limit(100)
            .execute()
        )

        if not claims_response.data:
            return {"total_pending": 0, "claims": []}

        claims = claims_response.data
        formatted = []

        for claim in claims:
            worker = claim.get("workers", {})
            trigger = claim.get("trigger_events", {})

            # Reconstruct fraud details from fraud_flags JSONB
            fraud_flags = claim.get("fraud_flags", {})
            failed_checks = [
                detail.get("name")
                for detail in fraud_flags.get("details", [])
                if not detail.get("passed")
            ]

            formatted.append(
                {
                    "id": claim.get("id"),
                    "worker_name": worker.get("name", "Unknown"),
                    "phone": worker.get("encrypted_phone"),
                    "zone": claim.get("zone_id"),
                    "trigger_type": trigger.get("trigger_type"),
                    "disrupted_hours": claim.get("disrupted_hours"),
                    "payout_amount": claim.get("payout_amount"),
                    "fraud_score": claim.get("fraud_score"),
                    "failed_checks": failed_checks,
                    "created_at": claim.get("created_at"),
                }
            )

        return {"total_pending": len(formatted), "claims": formatted}

    except Exception as e:
        print(f"[ERROR] Failed to fetch review queue: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch claims")


@router.post("/claims/{claim_id}/approve")
async def approve_claim(claim_id: str, request: ClaimApprovalRequest):
    """
    Manually approve a flagged claim.

    Changes status from 'review' to 'approved'.

    Args:
        claim_id: Claim UUID
        reason: Optional reason for manual approval

    Returns:
        Updated claim details
    """
    try:
        supabase = get_supabase()

        # Verify claim exists and is in review
        claim_response = (
            supabase.table("claims").select("*").eq("id", claim_id).execute()
        )

        if not claim_response.data:
            raise HTTPException(status_code=404, detail="Claim not found")

        claim = claim_response.data[0]

        if claim.get("status") != "review":
            raise HTTPException(
                status_code=400,
                detail=f"Claim is in '{claim.get('status')}' status, not 'review'",
            )

        # Update claim status (use IST timestamps)
        now_ist = datetime.now(IST)
        now_ist_no_tz = now_ist.replace(tzinfo=None)

        update_data = {
            "status": "approved",
            "reviewed_at": now_ist_no_tz.isoformat(),
            "reviewed_by": "manual_review",
            "rejection_reason": None,
        }

        response = (
            supabase.table("claims").update(update_data).eq("id", claim_id).execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update claim")

        print(
            f"[FRAUD] Claim {claim_id[:8]} manually approved | ₹{claim.get('payout_amount')}"
        )

        # Trigger payout processing
        payout_result = await PayoutEngine.process_payout(claim_id)
        if payout_result.get("status") == "success":
            print(f"  [💸] Payout {payout_result.get('payout_id')[:8]} initiated")

        return {
            "status": "success",
            "message": "✅ Claim approved & payout initiated",
            "claim_id": claim_id,
            "payout_amount": claim.get("payout_amount"),
            "payout_id": payout_result.get("payout_id"),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to approve claim: {e}")
        raise HTTPException(status_code=500, detail="Failed to approve claim")


@router.post("/claims/{claim_id}/reject")
async def reject_claim(claim_id: str, request: ClaimRejectionRequest):
    """
    Manually reject a flagged claim.

    Changes status from 'review' to 'rejected'.

    Args:
        claim_id: Claim UUID
        reason: Reason for rejection

    Returns:
        Updated claim details
    """
    try:
        supabase = get_supabase()

        # Verify claim exists and is in review
        claim_response = (
            supabase.table("claims").select("*").eq("id", claim_id).execute()
        )

        if not claim_response.data:
            raise HTTPException(status_code=404, detail="Claim not found")

        claim = claim_response.data[0]

        if claim.get("status") != "review":
            raise HTTPException(
                status_code=400,
                detail=f"Claim is in '{claim.get('status')}' status, not 'review'",
            )

        # Update claim status (use IST timestamps)
        now_ist = datetime.now(IST)
        now_ist_no_tz = now_ist.replace(tzinfo=None)

        update_data = {
            "status": "rejected",
            "reviewed_at": now_ist_no_tz.isoformat(),
            "reviewed_by": "manual_review",
            "rejection_reason": request.reason,
        }

        response = (
            supabase.table("claims").update(update_data).eq("id", claim_id).execute()
        )

        if not response.data:
            raise HTTPException(status_code=500, detail="Failed to update claim")

        print(
            f"[FRAUD] Claim {claim_id[:8]} manually rejected | Reason: {request.reason}"
        )

        # Notify worker via WhatsApp about the rejection
        try:
            worker_resp = (
                supabase.table("claims")
                .select("policies(workers(encrypted_phone, name))")
                .eq("id", claim_id)
                .execute()
            )
            if worker_resp.data:
                worker = (
                    worker_resp.data[0]
                    .get("policies", {})
                    .get("workers", {})
                )
                phone = worker.get("encrypted_phone")
                name = worker.get("name", "there")
                if phone:
                    send_whatsapp_message(
                        phone,
                        f"❌ *Claim Rejected*\n\n"
                        f"Hi {name}, your claim has been manually reviewed "
                        f"and unfortunately could not be approved.\n\n"
                        f"📝 *Reason*: {request.reason}\n\n"
                        f"Reply *DISPUTE* within 24 hours to challenge this decision.",
                    )
        except Exception as notify_err:
            print(f"[WARNING] Failed to notify worker of rejection: {notify_err}")

        return {
            "status": "success",
            "message": "❌ Claim rejected",
            "claim_id": claim_id,
            "reason": request.reason,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to reject claim: {e}")
        raise HTTPException(status_code=500, detail="Failed to reject claim")


@router.get("/alerts")
async def get_fraud_alerts():
    """
    Get fraud detection alerts and summary.

    Shows high-level fraud metrics and cluster fraud detections.

    Returns:
        Fraud alert summary with statistics
    """
    try:
        supabase = get_supabase()

        # Get fraud statistics
        total_claims = supabase.table("claims").select("id", count="exact").execute()

        auto_approved_claims = (
            supabase.table("claims")
            .select("id", count="exact")
            .eq("status", "auto_approved")
            .execute()
        )

        rejected_claims = (
            supabase.table("claims")
            .select("id", count="exact")
            .eq("status", "rejected")
            .execute()
        )

        review_claims = (
            supabase.table("claims")
            .select("id", count="exact")
            .eq("status", "review")
            .execute()
        )

        approved_claims = (
            supabase.table("claims")
            .select("id", count="exact")
            .eq("status", "approved")
            .execute()
        )

        # Calculate fraud rate
        total_count = total_claims.count or 0
        auto_approved_count = auto_approved_claims.count or 0
        rejected_count = rejected_claims.count or 0
        review_count = review_claims.count or 0
        approved_count = approved_claims.count or 0

        fraud_rate = (rejected_count / total_count * 100) if total_count > 0 else 0.0

        # Get recent high-fraud alerts (fraud_score > 0.7)
        high_fraud = (
            supabase.table("claims")
            .select("id, fraud_score, created_at, trigger_events(trigger_type)")
            .gt("fraud_score", 0.7)
            .order("created_at", desc=True)
            .limit(10)
            .execute()
        )

        return {
            "summary": {
                "total_claims": total_count,
                "auto_approved": auto_approved_count,
                "approved": approved_count,
                "review": review_count,
                "rejected": rejected_count,
                "fraud_rate_percent": round(fraud_rate, 2),
            },
            "high_fraud_alerts": [
                {
                    "claim_id": alert.get("id")[:8],
                    "fraud_score": alert.get("fraud_score"),
                    "trigger_type": alert.get("trigger_events", {}).get("trigger_type"),
                    "detected_at": alert.get("created_at"),
                }
                for alert in (high_fraud.data or [])
            ],
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch fraud alerts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch alerts")
