"""
DropSafe Unit Economics Analytics
Business viability metrics for the insurer dashboard
"""

from fastapi import APIRouter
from datetime import datetime, timedelta
from typing import Optional
import pytz

router = APIRouter(prefix="/analytics", tags=["analytics"])
IST = pytz.timezone("Asia/Kolkata")


@router.get("/unit-economics")
async def get_unit_economics():
    """
    Calculate unit economics from real Supabase data.

    Returns comprehensive business viability metrics including:
    - Per-worker economics (weekly average)
    - Portfolio economics (all workers)
    - Zone-by-zone profitability
    - Break-even analysis
    """
    try:
        from database import get_supabase

        supabase = get_supabase()
        now_ist = datetime.now(IST)

        # ─────────────────────────────────────────────────────────────────
        # SECTION 1: Per-Worker Economics
        # ─────────────────────────────────────────────────────────────────

        # Get current week policies
        week_start = (now_ist - timedelta(days=now_ist.weekday())).replace(
            hour=0, minute=0, second=0, microsecond=0, tzinfo=None
        )
        week_start_str = week_start.isoformat()

        # Fetch all active policies this week
        policies_resp = (
            supabase.table("policies")
            .select("id, premium_paid, worker_id, coverage_cap")
            .eq("status", "active")
            .gte("week_start", week_start_str[:10])
            .execute()
        )
        policies = policies_resp.data or []

        # Fetch all claims this week
        claims_resp = (
            supabase.table("claims")
            .select("worker_id, payout_amount, status")
            .gte("created_at", week_start_str)
            .execute()
        )
        claims = claims_resp.data or []

        # Calculate per-worker metrics
        total_policies = len(policies)
        total_premiums_collected = sum(float(p.get("premium_paid", 0)) for p in policies)
        avg_premium_per_worker = (
            total_premiums_collected / total_policies if total_policies > 0 else 0
        )

        # Claims analysis
        paid_claims = [c for c in claims if c.get("status") in ["auto_approved", "approved", "paid"]]
        total_payouts = sum(float(c.get("payout_amount", 0)) for c in paid_claims)

        avg_payout_per_claim = (
            total_payouts / len(paid_claims) if len(paid_claims) > 0 else 0
        )

        # Worker-level claim frequency
        worker_claim_counts = {}
        for claim in claims:
            wid = claim.get("worker_id")
            if wid:
                worker_claim_counts[wid] = worker_claim_counts.get(wid, 0) + 1

        avg_claims_per_worker = (
            sum(worker_claim_counts.values()) / total_policies if total_policies > 0 else 0
        )

        expected_payout_per_worker = avg_payout_per_claim * avg_claims_per_worker
        gross_margin_per_worker = avg_premium_per_worker - expected_payout_per_worker

        per_worker = {
            "avg_premium": round(avg_premium_per_worker, 2),
            "avg_payout_per_claim": round(avg_payout_per_claim, 2),
            "avg_claims_per_worker_week": round(avg_claims_per_worker, 2),
            "expected_payout_per_worker": round(expected_payout_per_worker, 2),
            "gross_margin_per_worker": round(gross_margin_per_worker, 2),
            "margin_pct": round((gross_margin_per_worker / avg_premium_per_worker * 100) if avg_premium_per_worker > 0 else 0, 1),
        }

        # ─────────────────────────────────────────────────────────────────
        # SECTION 2: Portfolio Economics
        # ─────────────────────────────────────────────────────────────────

        operating_expense_rate = 0.15  # 15% of premiums
        operating_expenses = total_premiums_collected * operating_expense_rate

        net_margin = total_premiums_collected - total_payouts - operating_expenses
        loss_ratio = (total_payouts / total_premiums_collected * 100) if total_premiums_collected > 0 else 0

        # Risk level assessment
        if loss_ratio < 65:
            risk_level = "UNDERPRICED"
        elif loss_ratio < 75:
            risk_level = "HEALTHY"
        elif loss_ratio < 85:
            risk_level = "MONITOR"
        else:
            risk_level = "UNSUSTAINABLE"

        portfolio = {
            "total_premiums_week": round(total_premiums_collected, 2),
            "total_payouts_week": round(total_payouts, 2),
            "operating_expenses_week": round(operating_expenses, 2),
            "loss_ratio_pct": round(loss_ratio, 1),
            "net_margin": round(net_margin, 2),
            "net_margin_pct": round((net_margin / total_premiums_collected * 100) if total_premiums_collected > 0 else 0, 1),
            "risk_level": risk_level,
            "benchmark_low": 65,
            "benchmark_high": 75,
        }

        # ─────────────────────────────────────────────────────────────────
        # SECTION 3: Zone-by-Zone Economics
        # ─────────────────────────────────────────────────────────────────

        zones_resp = supabase.table("zones").select("id, dark_store_name").execute()
        zones_map = {z["id"]: z["dark_store_name"] for z in (zones_resp.data or [])}

        zone_economics = []

        # Get all zones with policies this week
        zone_policies = {}
        for policy in policies:
            zone_id = policy.get("zone_id")
            if zone_id:
                if zone_id not in zone_policies:
                    zone_policies[zone_id] = []
                zone_policies[zone_id].append(policy)

        for zone_id, zone_pols in zone_policies.items():
            zone_name = zones_map.get(zone_id, "Unknown Zone")

            zone_premium = sum(float(p.get("premium_paid", 0)) for p in zone_pols)
            zone_payout = sum(
                float(c.get("payout_amount", 0))
                for c in paid_claims
                if c.get("zone_id") == zone_id
            )

            zone_loss_ratio = (zone_payout / zone_premium * 100) if zone_premium > 0 else 0

            if zone_loss_ratio < 75:
                verdict = "Profitable ✅"
            elif zone_loss_ratio < 90:
                verdict = "Borderline ⚠️"
            else:
                verdict = "Reprice needed 🔴"

            zone_economics.append({
                "zone_id": zone_id,
                "zone_name": zone_name,
                "avg_premium": round(zone_premium / len(zone_pols), 2) if zone_pols else 0,
                "avg_payout_per_claim": round(
                    sum(float(c.get("payout_amount", 0)) for c in paid_claims if c.get("zone_id") == zone_id) /
                    len([c for c in paid_claims if c.get("zone_id") == zone_id]) if [c for c in paid_claims if c.get("zone_id") == zone_id] else 0,
                    2
                ),
                "loss_ratio_pct": round(zone_loss_ratio, 1),
                "verdict": verdict,
            })

        # ─────────────────────────────────────────────────────────────────
        # SECTION 4: Break-even Analysis
        # ─────────────────────────────────────────────────────────────────

        # Assume fixed costs per zone per week (mock for now)
        fixed_costs_per_zone = 2000  # ₹2000/week assumed

        # Break-even: fixed_costs = (premium - expected_payout) × n_workers
        # n_workers = fixed_costs / (premium - expected_payout)

        profit_per_worker = avg_premium_per_worker - expected_payout_per_worker

        if profit_per_worker > 0:
            breakeven_workers = int(np.ceil(fixed_costs_per_zone / profit_per_worker))
        else:
            breakeven_workers = -1  # Business model not viable at current rates

        breakeven = {
            "fixed_costs_per_zone_week": fixed_costs_per_zone,
            "profit_per_worker": round(profit_per_worker, 2),
            "breakeven_workers_per_zone": breakeven_workers,
            "interpretation": (
                f"At current premium/payout rates, each zone needs {breakeven_workers} "
                f"active workers to break even (excluding growth)"
                if breakeven_workers > 0
                else "Current pricing model is not viable"
            ),
        }

        # ─────────────────────────────────────────────────────────────────

        import numpy as np

        return {
            "period": "current_week",
            "per_worker": per_worker,
            "portfolio": portfolio,
            "by_zone": zone_economics,
            "breakeven": breakeven,
            "summary": {
                "total_policies_active": total_policies,
                "total_workers_enrolled": len(set(p.get("worker_id") for p in policies if p.get("worker_id"))),
                "claims_this_week": len(claims),
                "paid_claims_this_week": len(paid_claims),
                "generated_at": now_ist.isoformat(),
            }
        }

    except Exception as e:
        print(f"[Analytics] Unit economics error: {e}")
        import traceback
        traceback.print_exc()
        return {"error": str(e), "status": "failed"}
