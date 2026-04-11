"""
DropSafe Testing Utility - Clean Worker Weekly Coverage

Safely removes a worker's weekly coverage to test end-to-end flow.
Handles cascading deletes for related records (claims, payouts).

Usage:
    python cleanup_worker_coverage.py <worker_phone>

Example:
    python cleanup_worker_coverage.py +919876543210
"""

import sys
import os
from datetime import datetime, timedelta
import pytz
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')


def get_week_boundaries():
    """Get current week start and end dates (IST)"""
    now_ist = datetime.now(IST).replace(tzinfo=None)
    week_start = now_ist - timedelta(days=now_ist.weekday())
    week_start = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
    week_end = week_start + timedelta(days=7)

    return week_start, week_end


def cleanup_worker_coverage(phone_number: str):
    """
    Delete a worker's weekly coverage and related records.

    Args:
        phone_number: Worker phone number (with +91 prefix)

    Returns:
        dict with cleanup results
    """
    try:
        supabase = get_supabase()

        print(f"\n{'='*60}")
        print(f"DropSafe Coverage Cleanup Tool")
        print(f"{'='*60}\n")
        print(f"📱 Phone: {phone_number}")

        # Step 1: Find worker by phone_hash
        print("\n[1/5] Finding worker...")
        import hashlib
        phone_hash = hashlib.sha256(phone_number.encode()).hexdigest()

        worker_response = supabase.table("workers").select("*").eq(
            "phone_hash", phone_hash
        ).execute()

        if not worker_response.data:
            print(f"❌ Worker not found with phone: {phone_number}")
            return {"success": False, "error": "Worker not found"}

        worker = worker_response.data[0]
        worker_id = worker["id"]
        worker_name = worker.get("name", "Unknown")

        print(f"✅ Found worker: {worker_name} (ID: {worker_id[:8]}...)")

        # Step 2: Find policy for this week
        print("\n[2/5] Finding weekly policy...")
        week_start, week_end = get_week_boundaries()

        policy_response = supabase.table("policies").select("*").eq(
            "worker_id", worker_id
        ).gte("week_start", week_start.strftime("%Y-%m-%d")).lte(
            "week_end", week_end.strftime("%Y-%m-%d")
        ).execute()

        if not policy_response.data:
            print(f"❌ No active policy found for this week")
            return {"success": False, "error": "No policy found for this week"}

        policy = policy_response.data[0]
        policy_id = policy["id"]
        premium = policy["premium_paid"]
        status = policy["status"]

        print(f"✅ Found policy: {policy_id[:8]}... (Status: {status}, Premium: ₹{premium})")

        # Step 3: Find and delete related claims
        print("\n[3/5] Checking for related claims...")
        claims_response = supabase.table("claims").select("id").eq(
            "policy_id", policy_id
        ).execute()

        claims = claims_response.data or []
        print(f"   Found {len(claims)} claim(s)")

        if claims:
            # Delete payouts first
            print("\n[4/5] Deleting related payouts...")
            for claim in claims:
                claim_id = claim["id"]
                payout_response = supabase.table("payouts").select("id").eq(
                    "claim_id", claim_id
                ).execute()

                payouts = payout_response.data or []
                for payout in payouts:
                    supabase.table("payouts").delete().eq(
                        "id", payout["id"]
                    ).execute()
                    print(f"   ✓ Deleted payout: {payout['id'][:8]}...")

            # Delete claims
            print("\n[5/5] Deleting claims...")
            for claim in claims:
                supabase.table("claims").delete().eq(
                    "id", claim["id"]
                ).execute()
                print(f"   ✓ Deleted claim: {claim['id'][:8]}...")

        # Step 6: Delete policy
        print("\n[Final] Deleting policy...")
        supabase.table("policies").delete().eq(
            "id", policy_id
        ).execute()
        print(f"✅ Deleted policy: {policy_id[:8]}...")

        # Step 7: Reset worker WhatsApp state
        print("\n[Bonus] Resetting WhatsApp state...")
        supabase.table("workers").update({
            "whatsapp_state": {"step": "enrolled"}
        }).eq("id", worker_id).execute()
        print(f"✅ Reset WhatsApp state to 'enrolled'")

        print(f"\n{'='*60}")
        print(f"✅ CLEANUP SUCCESSFUL")
        print(f"{'='*60}")
        print(f"\nWorker {worker_name} can now test the flow from scratch.")
        print(f"Send 'YES' on WhatsApp to activate next week's coverage.\n")

        return {
            "success": True,
            "worker_id": worker_id,
            "worker_name": worker_name,
            "policy_deleted": True,
            "claims_deleted": len(claims),
            "message": f"Cleaned up coverage for {worker_name}"
        }

    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def main():
    """Main entry point"""
    if len(sys.argv) < 2:
        print("\n❌ Usage: python cleanup_worker_coverage.py <phone_number>")
        print("   Example: python cleanup_worker_coverage.py +919876543210\n")
        sys.exit(1)

    phone_number = sys.argv[1]

    # Validate phone format
    if not phone_number.startswith("+91"):
        phone_number = "+91" + phone_number.lstrip("+").lstrip("91")

    if not (phone_number.startswith("+91") and len(phone_number) == 13):
        print(f"\n❌ Invalid phone number format: {phone_number}")
        print("   Expected format: +919876543210 or 9876543210\n")
        sys.exit(1)

    result = cleanup_worker_coverage(phone_number)

    if result["success"]:
        sys.exit(0)
    else:
        sys.exit(1)


if __name__ == "__main__":
    main()
