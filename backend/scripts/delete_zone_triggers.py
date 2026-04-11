"""
DropSafe Testing Utility - Delete All Zone Triggers

Removes all trigger events from a specific zone to clean up before testing.
Use this when simulating triggers creates unwanted fraud claims.

Usage:
    python delete_zone_triggers.py <zone_id>

Example:
    python delete_zone_triggers.py 550e8400-e29b-41d4-a716-446655440000
"""

import sys
import os
from datetime import datetime
import pytz
from dotenv import load_dotenv

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from database import get_supabase

load_dotenv()

IST = pytz.timezone('Asia/Kolkata')


def delete_zone_triggers(zone_id: str):
    """
    Delete all trigger events for a zone.

    Args:
        zone_id: Zone UUID

    Returns:
        dict with deletion results
    """
    try:
        supabase = get_supabase()

        print(f"\n{'='*70}")
        print(f"🗑️  DropSafe Zone Triggers Deletion")
        print(f"{'='*70}\n")

        zone_id = zone_id.strip()
        print(f"📍 Zone ID: {zone_id}")

        # Step 1: Verify zone exists
        print("\n[1/3] Verifying zone exists...")
        zone_response = supabase.table("zones").select("*").eq("id", zone_id).execute()

        if not zone_response.data:
            print(f"❌ Zone not found with ID: {zone_id}")
            return {"success": False, "error": "Zone not found"}

        zone = zone_response.data[0]
        zone_name = zone.get("dark_store_name", "Unknown")

        print(f"✅ Found zone: {zone_name}")

        # Step 2: Find all triggers for this zone
        print("\n[2/3] Finding all triggers for this zone...")
        triggers_response = supabase.table("trigger_events").select("*").eq(
            "zone_id", zone_id
        ).execute()

        triggers = triggers_response.data or []
        print(f"   Found {len(triggers)} trigger event(s)")

        if triggers:
            # Show summary
            trigger_types = {}
            for trigger in triggers:
                t_type = trigger.get("trigger_type", "unknown")
                trigger_types[t_type] = trigger_types.get(t_type, 0) + 1

            print(f"\n   Trigger breakdown:")
            for t_type, count in trigger_types.items():
                print(f"   • {t_type}: {count}")

            # Confirmation
            confirm = input(
                f"\n⏸️  This will delete {len(triggers)} trigger(s) and ALL related claims/payouts. Type 'DELETE' to confirm: "
            ).strip().upper()
            if confirm != "DELETE":
                print("❌ Deletion cancelled")
                return {"success": False, "error": "User cancelled deletion"}

            # Delete in proper cascade order: payouts → claims → trigger_events
            print("\n[3/3] Deleting in cascade order...")
            deleted_count = 0
            deleted_claims = 0
            deleted_payouts = 0

            for trigger in triggers:
                trigger_id = trigger["id"]
                trigger_type = trigger.get("trigger_type", "unknown")
                severity = trigger.get("severity", 0)

                try:
                    # Step 1: Find all claims for this trigger
                    claims_response = supabase.table("claims").select("*").eq(
                        "trigger_event_id", trigger_id
                    ).execute()

                    claims = claims_response.data or []

                    if claims:
                        print(
                            f"\n   Processing {trigger_type} trigger (severity: {severity}, ID: {trigger_id[:8]}...)"
                        )
                        print(f"   • Found {len(claims)} claim(s) linked to this trigger")

                        # Step 2: Delete payouts for each claim
                        for claim in claims:
                            claim_id = claim["id"]
                            payouts_response = supabase.table("payouts").select(
                                "id"
                            ).eq("claim_id", claim_id).execute()

                            payouts = payouts_response.data or []
                            for payout in payouts:
                                supabase.table("payouts").delete().eq(
                                    "id", payout["id"]
                                ).execute()
                                deleted_payouts += 1

                            # Step 3: Delete the claim
                            supabase.table("claims").delete().eq(
                                "id", claim_id
                            ).execute()
                            deleted_claims += 1

                    # Step 4: Delete the trigger event
                    supabase.table("trigger_events").delete().eq(
                        "id", trigger_id
                    ).execute()
                    deleted_count += 1
                    print(
                        f"   ✅ Deleted {trigger_type} trigger (ID: {trigger_id[:8]}...)"
                    )

                except Exception as e:
                    print(
                        f"   ❌ Failed to delete trigger {trigger_id[:8]}...: {str(e)}"
                    )

            print(f"\n   Summary of deleted records:")
            print(f"   • Trigger events: {deleted_count}")
            print(f"   • Claims: {deleted_claims}")
            print(f"   • Payouts: {deleted_payouts}")

        else:
            print("   No triggers found")
            deleted_count = 0
            deleted_claims = 0
            deleted_payouts = 0

        # Verify deletion
        print("\n   Verifying deletion...")
        verify_response = supabase.table("trigger_events").select("*").eq(
            "zone_id", zone_id
        ).execute()

        remaining = len(verify_response.data or [])

        if remaining == 0:
            print("   ✅ All triggers removed\n")

            print(f"{'='*70}")
            print("✅ DELETION COMPLETE")
            print(f"{'='*70}")
            print(f"\nSummary:")
            print(f"  • Zone: {zone_name}")
            print(f"  • Zone ID: {zone_id}")
            print(f"  • Triggers deleted: {deleted_count}")
            print(f"\n✨ Ready for clean trigger simulation!\n")

            return {
                "success": True,
                "zone_id": zone_id,
                "zone_name": zone_name,
                "triggers_deleted": deleted_count,
            }
        else:
            print(f"   ⚠️  {remaining} trigger(s) still exist")
            return {
                "success": False,
                "error": f"Verification failed - {remaining} triggers still in database",
            }

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        return {"success": False, "error": str(e)}


def list_zones():
    """List all available zones to help user identify zone_id."""
    try:
        supabase = get_supabase()

        zones_response = supabase.table("zones").select(
            "id, dark_store_name, pincode, latitude, longitude"
        ).execute()

        zones = zones_response.data or []

        if not zones:
            print("\n❌ No zones found in database\n")
            return

        print(f"\n{'='*70}")
        print("Available Zones:")
        print(f"{'='*70}\n")

        for zone in zones:
            zone_id = zone["id"]
            zone_name = zone.get("dark_store_name", "Unknown")
            pincode = zone.get("pincode", "N/A")

            print(f"Zone ID: {zone_id}")
            print(f"  Name: {zone_name}")
            print(f"  Pincode: {pincode}")
            print()

    except Exception as e:
        print(f"\n❌ Error listing zones: {str(e)}\n")


if __name__ == "__main__":
    if len(sys.argv) == 1:
        print("\nUsage:")
        print("  python delete_zone_triggers.py <zone_id>")
        print("  python delete_zone_triggers.py --list  (to see all zones)\n")
        print("Example:")
        print(
            "  python delete_zone_triggers.py 550e8400-e29b-41d4-a716-446655440000\n"
        )
        sys.exit(1)

    arg = sys.argv[1]

    if arg == "--list":
        list_zones()
        sys.exit(0)

    result = delete_zone_triggers(arg)
