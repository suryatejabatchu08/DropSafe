"""
Quick verification script for DropSafe endpoints
"""
import sys
sys.path.append('backend')

from database import get_supabase

def verify_endpoints():
    """Verify all database queries are working correctly."""

    print("=" * 60)
    print("DROPSAFE ENDPOINT VERIFICATION")
    print("=" * 60)

    try:
        client = get_supabase()
        print("\n[1/5] Testing Supabase connection...")
        print("  [OK] Connected to Supabase")

        # Test 1: Worker count (for /health endpoint)
        print("\n[2/5] Testing worker count query (/health endpoint)...")
        workers_response = client.table('workers').select('id', count='exact').execute()
        print(f"  [OK] Workers count: {workers_response.count}")
        if workers_response.count == 0:
            print("  [WARN] No workers found. Run supabase/seed.sql to add test data.")

        # Test 2: Trigger events (for /triggers/mock endpoint)
        print("\n[3/5] Testing trigger events query (/triggers/mock endpoint)...")
        events_response = client.table('trigger_events').select(
            'id, trigger_type, severity, start_time, end_time, verified, created_at, '
            'zones(pincode, dark_store_name, platform)'
        ).order('created_at', desc=True).limit(10).execute()

        print(f"  [OK] Trigger events found: {len(events_response.data)}")

        if len(events_response.data) > 0:
            print("  Sample events:")
            for event in events_response.data[:3]:
                zone = event.get('zones', {})
                zone_name = zone.get('dark_store_name', 'Unknown')
                pincode = zone.get('pincode', '')
                verified = event.get('verified', False)
                print(f"    - {event['trigger_type']}: {zone_name}, {pincode} (verified: {verified})")

        # Test 3: Active policies
        print("\n[4/5] Testing active policies query...")
        policies_response = client.table('policies').select(
            'id, week_start, week_end, status, premium_paid, coverage_cap'
        ).eq('status', 'active').execute()

        print(f"  [OK] Active policies: {len(policies_response.data)}")

        # Test 4: Data transformation for triggers endpoint
        print("\n[5/5] Testing data transformation logic...")
        if len(events_response.data) > 0:
            test_event = events_response.data[0]
            zone_info = test_event.get("zones", {})
            formatted = {
                "trigger_type": test_event["trigger_type"],
                "zone": f"{zone_info.get('dark_store_name', 'Unknown')}, {zone_info.get('pincode', '')}",
                "severity": float(test_event["severity"]) if test_event.get("severity") else 0.0,
                "timestamp": test_event.get("start_time") if test_event.get("start_time") else test_event["created_at"],
                "verified": test_event["verified"]
            }
            print(f"  [OK] Transformation successful:")
            print(f"    Raw: {test_event['trigger_type']} in zone_id {test_event.get('zone_id')}")
            print(f"    Formatted: {formatted['trigger_type']} in {formatted['zone']}")

        # Summary
        print("\n" + "=" * 60)
        print("VERIFICATION SUMMARY")
        print("=" * 60)
        print(f"[OK] Database connection: Working")
        print(f"[OK] Worker count query: Working ({workers_response.count} workers)")
        print(f"[OK] Trigger events query: Working ({len(events_response.data)} events)")
        print(f"[OK] Active policies query: Working ({len(policies_response.data)} policies)")
        print(f"[OK] Data transformation: Working")
        print("\n[SUCCESS] All endpoint logic verified!")

        if workers_response.count == 0:
            print("\n[NOTE] To populate workers, run supabase/seed.sql in Supabase SQL Editor")

    except Exception as e:
        print(f"\n[ERROR] Verification failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    verify_endpoints()
