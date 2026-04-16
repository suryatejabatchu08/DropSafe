"""
DropSafe Worker Router
Mobile-friendly worker dashboard endpoints.
No authentication required for demo — worker_id in URL acts as token.
"""

from fastapi import APIRouter, HTTPException
from datetime import datetime, timedelta
import pytz

router = APIRouter(prefix="/worker", tags=["worker"])
IST = pytz.timezone("Asia/Kolkata")

TRIGGER_EMOJI = {
    "rain": "🌧️",
    "heat": "🌡️",
    "aqi": "💨",
    "curfew": "🚨",
    "order_collapse": "📉",
    "store_closure": "🔒",
}


# ─────────────────────────────────────────────────────────────────────────────
# GET /worker/{worker_id}/dashboard
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{worker_id}/dashboard")
async def get_worker_dashboard(worker_id: str):
    """
    Worker dashboard data — no auth required (demo mode).

    Returns:
        {
            worker: { name, zone_name, platform },
            active_policy: { week_start, week_end, premium_paid,
                             coverage_cap, days_remaining } | null,
            earnings_protected_week: float,
            disruption_count_week: int,
            recent_payouts: [...last 4],
            active_zone_alerts: [...]
        }
    """
    try:
        from database import get_supabase
        supabase = get_supabase()

        # Fetch worker + zone
        worker_resp = (
            supabase.table("workers")
            .select("id, name, zone_id, platform, created_at")
            .eq("id", worker_id)
            .execute()
        )

        if not worker_resp.data:
            raise HTTPException(status_code=404, detail="Worker not found")

        worker = worker_resp.data[0]
        zone_id = worker.get("zone_id")
        platform = worker.get("platform", "unknown")

        # Fetch zone name
        zone_name = "Unknown Zone"
        if zone_id:
            zone_resp = (
                supabase.table("zones")
                .select("dark_store_name")
                .eq("id", zone_id)
                .execute()
            )
            if zone_resp.data:
                zone_name = zone_resp.data[0].get("dark_store_name", "Unknown Zone")

        # Current week boundaries
        now_ist = datetime.now(IST)
        days_since_monday = now_ist.weekday()
        week_start = (now_ist - timedelta(days=days_since_monday)).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        week_end = week_start + timedelta(days=7)

        # Active policy this week
        policy_resp = (
            supabase.table("policies")
            .select("*")
            .eq("worker_id", worker_id)
            .eq("status", "active")
            .gte("week_start", week_start.strftime("%Y-%m-%d"))
            .lte("week_end", week_end.strftime("%Y-%m-%d"))
            .execute()
        )

        active_policy = None
        if policy_resp.data:
            p = policy_resp.data[0]
            week_end_dt = datetime.fromisoformat(p["week_end"])
            days_remaining = max(0, (week_end_dt - now_ist.replace(tzinfo=None)).days)
            active_policy = {
                "week_start": p["week_start"],
                "week_end": p["week_end"],
                "premium_paid": float(p["premium_paid"]),
                "coverage_cap": float(p["coverage_cap"]),
                "days_remaining": days_remaining,
                "policy_id": p["id"],
            }

        # Earnings protected this week (paid/auto_approved claims)
        claims_resp = (
            supabase.table("claims")
            .select("payout_amount, status, trigger_event_id, created_at")
            .eq("worker_id", worker_id)
            .gte("created_at", week_start.isoformat())
            .execute()
        )

        claims_this_week = claims_resp.data or []
        earnings_protected = sum(
            float(c.get("payout_amount", 0))
            for c in claims_this_week
            if c.get("status") in ["auto_approved", "approved", "paid"]
        )
        disruption_count = len(
            set(c.get("trigger_event_id") for c in claims_this_week)
        )

        # Last 4 payouts (all time)
        payouts_resp = (
            supabase.table("payouts")
            .select("amount, status, paid_at, claim_id")
            .eq("worker_id", worker_id)
            .order("paid_at", desc=True)
            .limit(4)
            .execute()
        )

        recent_payouts = []
        for payout in (payouts_resp.data or []):
            # Get trigger type from claim → trigger_event
            trigger_type = "unknown"
            trigger_emoji = "⚡"
            if payout.get("claim_id"):
                claim_resp = (
                    supabase.table("claims")
                    .select("trigger_event_id")
                    .eq("id", payout["claim_id"])
                    .execute()
                )
                if claim_resp.data:
                    te_id = claim_resp.data[0].get("trigger_event_id")
                    if te_id:
                        te_resp = (
                            supabase.table("trigger_events")
                            .select("trigger_type")
                            .eq("id", te_id)
                            .execute()
                        )
                        if te_resp.data:
                            trigger_type = te_resp.data[0].get("trigger_type", "unknown")
                            trigger_emoji = TRIGGER_EMOJI.get(trigger_type, "⚡")

            paid_at = payout.get("paid_at", "")
            try:
                date_display = datetime.fromisoformat(
                    str(paid_at).replace("Z", "+00:00")
                ).astimezone(IST).strftime("%d %b")
            except Exception:
                date_display = "N/A"

            recent_payouts.append({
                "trigger_type": trigger_type,
                "trigger_emoji": trigger_emoji,
                "date": date_display,
                "amount": float(payout.get("amount", 0)),
                "status": payout.get("status", "unknown"),
            })

        # Active zone alerts (triggers in last 6 hours)
        six_hours_ago = (now_ist - timedelta(hours=6)).replace(tzinfo=None).isoformat()
        alerts_resp = (
            supabase.table("trigger_events")
            .select("trigger_type, severity, created_at")
            .eq("zone_id", zone_id)
            .eq("verified", True)
            .gte("created_at", six_hours_ago)
            .order("created_at", desc=True)
            .execute()
        )

        active_alerts = []
        for alert in (alerts_resp.data or []):
            try:
                created_at = datetime.fromisoformat(
                    str(alert["created_at"]).replace("Z", "+00:00")
                ).astimezone(IST)
                mins_ago = int((now_ist - created_at).total_seconds() / 60)
                time_since = (
                    f"{mins_ago}m ago" if mins_ago < 60
                    else f"{mins_ago // 60}h ago"
                )
            except Exception:
                time_since = "recently"

            active_alerts.append({
                "trigger_type": alert["trigger_type"],
                "trigger_emoji": TRIGGER_EMOJI.get(alert["trigger_type"], "⚡"),
                "severity": float(alert["severity"]),
                "time_since": time_since,
            })

        return {
            "worker": {
                "id": worker_id,
                "name": worker.get("name", "Worker"),
                "zone_name": zone_name,
                "platform": platform,
            },
            "active_policy": active_policy,
            "earnings_protected_week": round(earnings_protected, 2),
            "disruption_count_week": disruption_count,
            "coverage_cap": active_policy["coverage_cap"] if active_policy else 0,
            "recent_payouts": recent_payouts,
            "active_zone_alerts": active_alerts,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Worker Router] Dashboard error: {e}")
        raise HTTPException(status_code=500, detail=f"Dashboard error: {str(e)}")


# ─────────────────────────────────────────────────────────────────────────────
# GET /worker/{worker_id}/history
# ─────────────────────────────────────────────────────────────────────────────

@router.get("/{worker_id}/history")
async def get_worker_history(
    worker_id: str,
    page: int = 1,
    limit: int = 10,
):
    """
    Full payout history for a worker, paginated.

    Returns:
        { payouts: [...], total, page, limit, has_more }
    """
    try:
        from database import get_supabase
        supabase = get_supabase()

        offset = (page - 1) * limit

        # Verify worker exists
        worker_resp = (
            supabase.table("workers")
            .select("id")
            .eq("id", worker_id)
            .execute()
        )
        if not worker_resp.data:
            raise HTTPException(status_code=404, detail="Worker not found")

        # Fetch paginated payouts
        payouts_resp = (
            supabase.table("payouts")
            .select("amount, status, paid_at, claim_id", count="exact")
            .eq("worker_id", worker_id)
            .order("paid_at", desc=True)
            .range(offset, offset + limit - 1)
            .execute()
        )

        total = payouts_resp.count or 0
        payouts = [
            {
                "amount": float(p.get("amount", 0)),
                "status": p.get("status"),
                "paid_at": p.get("paid_at"),
                "claim_id": p.get("claim_id"),
            }
            for p in (payouts_resp.data or [])
        ]

        return {
            "payouts": payouts,
            "total": total,
            "page": page,
            "limit": limit,
            "has_more": (offset + limit) < total,
        }

    except HTTPException:
        raise
    except Exception as e:
        print(f"[Worker Router] History error: {e}")
        raise HTTPException(status_code=500, detail=f"History error: {str(e)}")
