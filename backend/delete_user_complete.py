"""
DropSafe Testing Utility - Complete User Deletion

DANGEROUS: Permanently removes a worker and ALL their data from the database.
Use only for testing purposes to record data from the first signup.

Usage:
    python delete_user_complete.py <worker_phone>

Example:
    python delete_user_complete.py +919876543210

This will delete:
    - All policies (past and future)
    - All claims
    - All payouts
    - All fraud detection records
    - The worker record itself
"""

import sys
import os
import hashlib
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')


def delete_complete_user(phone_number: str):
    """
    Permanently delete a worker and ALL their data.

    Args:
        phone_number: Worker phone number (with +91 prefix)

    Returns:
        dict with deletion results
    """
    try:
        supabase = get_supabase()

        print(f"\n{'='*70}")
        print(f"🗑️  DropSafe Complete User Deletion Tool")
        print(f"{'='*70}")
        print(f"\n⚠️  WARNING: This will PERMANENTLY delete all data for this user!")
        print(f"{'='*70}\n")

        phone_number = phone_number.strip()
        print(f"📱 Phone: {phone_number}")

        # Step 1: Find worker by phone_hash
        print("\n[1/6] Finding worker...")
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
        worker_zone = worker.get("zone_id", "Unknown")

        print(f"✅ Found worker: {worker_name} (ID: {worker_id[:8]}...)")
        print(f"   Zone: {worker_zone}")
        print(f"   WhatsApp State: {worker.get('whatsapp_state', {}).get('step', 'unknown')}")

        # Confirmation
        confirm = input("\n⏸️  Type 'DELETE' to confirm permanent deletion: ").strip().upper()
        if confirm != "DELETE":
            print("❌ Deletion cancelled")
            return {"success": False, "error": "User cancelled deletion"}

        # Step 2: Find ALL policies for this worker
        print("\n[2/6] Finding all policies for this worker...")
        policies_response = supabase.table("policies").select("*").eq(
            "worker_id", worker_id
        ).execute()

        policies = policies_response.data or []
        print(f"   Found {len(policies)} policy(policies)")

        deleted_payouts = 0
        deleted_claims = 0
        deleted_fraud_records = 0

        # Step 3: Delete all payouts, claims, and fraud records
        for policy in policies:
            policy_id = policy["id"]
            print(f"\n   Processing policy: {policy_id[:8]}... (Status: {policy['status']})")

            # Find claims for this policy
            claims_response = supabase.table("claims").select("*").eq(
                "policy_id", policy_id
            ).execute()

            claims = claims_response.data or []

            for claim in claims:
                claim_id = claim["id"]

                # Delete payouts for this claim
                payouts_response = supabase.table("payouts").select("id").eq(
                    "claim_id", claim_id
                ).execute()

                payouts = payouts_response.data or []
                for payout in payouts:
                    supabase.table("payouts").delete().eq("id", payout["id"]).execute()
                    deleted_payouts += 1

                # Delete fraud records for this claim
                fraud_response = supabase.table("fraud_detection").select("id").eq(
                    "claim_id", claim_id
                ).execute()

                fraud_records = fraud_response.data or []
                for fraud in fraud_records:
                    supabase.table("fraud_detection").delete().eq(
                        "id", fraud["id"]
                    ).execute()
                    deleted_fraud_records += 1

                # Delete the claim
                supabase.table("claims").delete().eq("id", claim_id).execute()
                deleted_claims += 1

            # Delete the policy
            supabase.table("policies").delete().eq("id", policy_id).execute()

        print(f"\n[3/6] Deleted records:")
        print(f"   ✅ Policies: {len(policies)}")
        print(f"   ✅ Claims: {deleted_claims}")
        print(f"   ✅ Payouts: {deleted_payouts}")
        print(f"   ✅ Fraud Detection Records: {deleted_fraud_records}")

        # Step 4: Find and delete any worker payments/transactions
        print("\n[4/6] Checking for payments/transactions...")
        try:
            # Try to find any other related records
            payments_response = supabase.table("payments").select("*").eq(
                "worker_id", worker_id
            ).execute()

            payments = payments_response.data or []
            if payments:
                print(f"   Found {len(payments)} payment record(s)")
                for payment in payments:
                    supabase.table("payments").delete().eq(
                        "id", payment["id"]
                    ).execute()
                print(f"   ✅ Deleted {len(payments)} payment(s)")
            else:
                print("   No payment records found")
        except Exception as e:
            print(f"   ⚠️  Could not check payments: {str(e)}")

        # Step 5: Delete worker document
        print("\n[5/6] Deleting worker record...")
        supabase.table("workers").delete().eq("id", worker_id).execute()
        print(f"   ✅ Worker record deleted")

        # Step 6: Verify deletion
        print("\n[6/6] Verifying deletion...")
        verify_response = supabase.table("workers").select("*").eq(
            "phone_hash", phone_hash
        ).execute()

        if not verify_response.data:
            print("   ✅ User completely removed from database\n")

            print(f"{'='*70}")
            print("✅ DELETION COMPLETE")
            print(f"{'='*70}")
            print(f"\nSummary:")
            print(f"  • Worker: {worker_name}")
            print(f"  • Phone: {phone_number}")
            print(f"  • Policies deleted: {len(policies)}")
            print(f"  • Claims deleted: {deleted_claims}")
            print(f"  • Payouts deleted: {deleted_payouts}")
            print(f"  • Fraud records deleted: {deleted_fraud_records}")
            print(f"  • Total records removed: {1 + len(policies) + deleted_claims + deleted_payouts + deleted_fraud_records}")
            print(f"\n✨ Ready for fresh signup!\n")

            return {
                "success": True,
                "worker_id": worker_id,
                "worker_name": worker_name,
                "phone": phone_number,
                "policies_deleted": len(policies),
                "claims_deleted": deleted_claims,
                "payouts_deleted": deleted_payouts,
                "fraud_records_deleted": deleted_fraud_records,
                "total_records_deleted": 1 + len(policies) + deleted_claims + deleted_payouts + deleted_fraud_records,
            }
        else:
            print("   ❌ Worker record still exists!")
            return {"success": False, "error": "Verification failed - worker still in database"}

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("\n❌ Usage: python delete_user_complete.py <phone_number>")
        print("\nExample: python delete_user_complete.py +919876543210\n")
        sys.exit(1)

    phone = sys.argv[1]
    result = delete_complete_user(phone)
