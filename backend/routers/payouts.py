"""
DropSafe Payouts Router

Endpoints for viewing and managing payouts.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
from database import get_supabase
import pytz
from services.payout_engine import PayoutEngine

router = APIRouter(prefix="/payouts", tags=["payouts"])

IST = pytz.timezone("Asia/Kolkata")


@router.get("/worker/{worker_id}")
async def get_worker_payouts(worker_id: str):
    """
    Get all payouts for a worker.

    Returns list of all payouts ordered by newest first.

    Args:
        worker_id: Worker UUID

    Returns:
        List of payouts with claim details
    """
    try:
        supabase = get_supabase()

        payouts_response = (
            supabase.table("payouts")
            .select("*, claims(*, trigger_events(trigger_type))")
            .eq("worker_id", worker_id)
            .order("paid_at", desc=True)
            .limit(50)
            .execute()
        )

        if not payouts_response.data:
            return {"worker_id": worker_id, "total_payouts": 0, "payouts": []}

        payouts = payouts_response.data
        total_amount = sum(p.get("amount", 0) for p in payouts)

        formatted = []
        for payout in payouts:
            claim = payout.get("claims", {})
            trigger = claim.get("trigger_events", {})

            formatted.append(
                {
                    "id": payout.get("id")[:8],
                    "claim_id": claim.get("id"),
                    "amount": payout.get("amount"),
                    "channel": payout.get("channel"),
                    "razorpay_ref": payout.get("razorpay_ref"),
                    "status": payout.get("status"),
                    "trigger_type": trigger.get("trigger_type"),
                    "paid_at": payout.get("paid_at"),
                }
            )

        return {
            "worker_id": worker_id,
            "total_amount": float(total_amount),
            "total_payouts": len(formatted),
            "payouts": formatted,
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch worker payouts: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch payouts")


@router.get("/summary")
async def get_payout_summary():
    """
    Get payout summary statistics.

    Returns:
        {
            "today": {
                "total": float,
                "count": int,
                "successful": int
            },
            "week": {
                "total": float,
                "count": int,
                "successful": int
            },
            "pending": int,
            "failed": int,
            "success_rate": float
        }
    """
    try:
        supabase = get_supabase()

        # Get current dates in IST
        now_ist = datetime.now(IST)
        today_start = now_ist.replace(hour=0, minute=0, second=0, microsecond=0)
        week_start = now_ist - timedelta(days=now_ist.weekday())
        week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)

        # Use IST times for database query (all stored as IST now)
        today_start_ist = today_start.replace(tzinfo=None).isoformat()
        week_start_ist = week_start.replace(tzinfo=None).isoformat()

        # Today's payouts
        today_response = (
            supabase.table("payouts")
            .select("id, amount, status")
            .gte("paid_at", today_start_ist)
            .execute()
        )

        # Week's payouts
        week_response = (
            supabase.table("payouts")
            .select("id, amount, status")
            .gte("paid_at", week_start_ist)
            .execute()
        )

        # Pending payouts (status = initiated or queued)
        pending_response = (
            supabase.table("payouts")
            .select("id", count="exact")
            .in_("status", ["initiated", "queued"])
            .execute()
        )

        # Failed payouts
        failed_response = (
            supabase.table("payouts")
            .select("id", count="exact")
            .eq("status", "failed")
            .execute()
        )

        # All payouts for success rate
        all_response = (
            supabase.table("payouts").select("id, status", count="exact").execute()
        )

        # Calculate totals
        today_payouts = today_response.data or []
        week_payouts = week_response.data or []
        all_payouts = all_response.data or []

        today_total = sum(p.get("amount", 0) for p in today_payouts)
        today_successful = len(
            [p for p in today_payouts if p.get("status") in ["success", "processed"]]
        )

        week_total = sum(p.get("amount", 0) for p in week_payouts)
        week_successful = len(
            [p for p in week_payouts if p.get("status") in ["success", "processed"]]
        )

        all_successful = len(
            [p for p in all_payouts if p.get("status") in ["success", "processed"]]
        )
        all_total = len(all_payouts)
        success_rate = (all_successful / all_total * 100) if all_total > 0 else 0

        pending_count = pending_response.count or 0
        failed_count = failed_response.count or 0

        return {
            "today": {
                "total": float(today_total),
                "count": len(today_payouts),
                "successful": today_successful,
            },
            "week": {
                "total": float(week_total),
                "count": len(week_payouts),
                "successful": week_successful,
            },
            "pending": pending_count,
            "failed": failed_count,
            "success_rate": round(success_rate, 2),
        }

    except Exception as e:
        print(f"[ERROR] Failed to fetch payout summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch summary")


@router.get("/daily-summary")
async def get_daily_payout_summary():
    """
    Get daily payout amounts for last 7 days.

    Returns:
        List of {date, amount} for chart plotting
    """
    try:
        supabase = get_supabase()

        # Get last 7 days payouts
        week_ago = datetime.now(IST) - timedelta(days=7)
        week_ago_ist = week_ago.replace(tzinfo=None).isoformat()

        response = (
            supabase.table("payouts")
            .select("paid_at, amount")
            .gte("paid_at", week_ago_ist)
            .eq("status", "success")
            .execute()
        )

        payouts = response.data or []

        # Group by date
        daily_totals = {}
        for payout in payouts:
            paid_at = payout.get("paid_at", "")
            if paid_at:
                date = paid_at.split("T")[0]  # Extract YYYY-MM-DD
                if date not in daily_totals:
                    daily_totals[date] = 0
                daily_totals[date] += float(payout.get("amount", 0))

        # Format for chart
        result = [
            {"date": date, "amount": amount}
            for date, amount in sorted(daily_totals.items())
        ]

        return result

    except Exception as e:
        print(f"[ERROR] Failed to fetch daily payout summary: {e}")
        raise HTTPException(status_code=500, detail="Failed to fetch daily summary")


@router.post("/retry/{payout_id}")
async def retry_failed_payout(payout_id: str):
    """
    Manually retry a failed payout.

    Changes status back to 'initiated' to trigger retry.

    Args:
        payout_id: Razorpay payout ID (from payouts.razorpay_ref)

    Returns:
        {"status": "retrying", "payout_id": str}
    """
    try:
        supabase = get_supabase()

        # Fetch payout
        payout_response = (
            supabase.table("payouts")
            .select("id, claim_id, status")
            .eq("razorpay_ref", payout_id)
            .execute()
        )

        if not payout_response.data:
            raise HTTPException(status_code=404, detail="Payout not found")

        payout = payout_response.data[0]

        if payout.get("status") != "failed":
            raise HTTPException(
                status_code=400,
                detail=f"Can only retry failed payouts (current: {payout.get('status')})",
            )

        claim_id = payout.get("claim_id")
        if not claim_id:
            raise HTTPException(status_code=400, detail="Payout has no associated claim")

        # First mark the old payout record as superseded
        supabase.table("payouts").update({"status": "initiated"}).eq(
            "razorpay_ref", payout_id
        ).execute()

        # Mark the claim back to approved so PayoutEngine will process it
        supabase.table("claims").update({"status": "approved"}).eq(
            "id", claim_id
        ).execute()

        print(f"[PayoutEngine] Retrying payout for claim {claim_id[:8]}")

        # Re-invoke the full payout engine (creates a fresh Razorpay call)
        payout_result = await PayoutEngine.process_payout(claim_id)

        if payout_result.get("status") not in ("success", "skipped"):
            raise HTTPException(
                status_code=502,
                detail=f"Razorpay retry failed: {payout_result.get('message')}",
            )

        return {
            "status": "retrying",
            "payout_id": payout_result.get("payout_id", payout_id),
            "claim_id": claim_id,
            "message": payout_result.get("message", "Payout retry initiated"),
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[ERROR] Failed to retry payout: {e}")
        raise HTTPException(status_code=500, detail="Failed to retry payout")


@router.post("/webhook/razorpay")
async def razorpay_webhook(payload: dict):
    """
    Handle Razorpay webhook events.

    Processes events:
    - payout.processed → update status to 'success'
    - payout.failed    → update status to 'failed'
    - payout.reversed  → update status to 'reversed'

    Returns:
        {"status": "processed"}
    """
    try:
        result = PayoutEngine.handle_razorpay_webhook(payload)
        return result
    except Exception as e:
        print(f"[ERROR] Razorpay webhook error: {e}")
        raise HTTPException(status_code=500, detail="Webhook processing failed")
