"""
DropSafe Database Module
Supabase client initialization and helper functions
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Supabase configuration
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_ROLE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

# Global Supabase client instance
supabase: Optional[Client] = None


def init_supabase() -> Client:
    """
    Initialize and return Supabase client with SERVICE ROLE key.
    Service role bypasses RLS and has full database access.
    Use this for backend operations (automation, reporting, admin tasks).
    Raises ValueError if environment variables are not set.
    """
    global supabase

    if not SUPABASE_URL or not SUPABASE_SERVICE_ROLE_KEY:
        raise ValueError(
            "Missing Supabase credentials. Please set SUPABASE_URL and SUPABASE_SERVICE_ROLE_KEY "
            "environment variables in your .env file."
        )

    if supabase is None:
        supabase = create_client(SUPABASE_URL, SUPABASE_SERVICE_ROLE_KEY)
        print(f"[OK] Supabase connected (SERVICE ROLE): {SUPABASE_URL}")

    return supabase


def get_supabase() -> Client:
    """
    Get the Supabase client instance.
    Initializes if not already initialized.
    """
    if supabase is None:
        return init_supabase()
    return supabase


# Helper functions for common database operations


async def get_worker_count() -> int:
    """Get total number of registered workers."""
    try:
        client = get_supabase()
        response = client.table("workers").select("id", count="exact").execute()
        return response.count if response.count else 0
    except Exception as e:
        print(f"[ERROR] Error fetching worker count: {e}")
        return 0


async def get_trigger_events(verified_only: bool = False, limit: int = 10):
    """
    Fetch trigger events from database.

    Args:
        verified_only: If True, only return verified events
        limit: Maximum number of events to return

    Returns:
        List of trigger events with zone information
    """
    try:
        client = get_supabase()
        query = client.table("trigger_events").select(
            "id, trigger_type, severity, start_time, end_time, verified, created_at, "
            "zones(pincode, dark_store_name, platform)"
        )

        if verified_only:
            query = query.eq("verified", True)

        query = query.order("created_at", desc=True).limit(limit)

        response = query.execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] Error fetching trigger events: {e}")
        return []


async def get_active_policies(worker_id: str = None):
    """
    Fetch active policies.

    Args:
        worker_id: If provided, fetch policies for specific worker

    Returns:
        List of active policies
    """
    try:
        client = get_supabase()
        query = (
            client.table("policies")
            .select(
                "id, worker_id, week_start, week_end, premium_paid, coverage_cap, status, "
                "workers(name, platform), zones(dark_store_name, pincode)"
            )
            .eq("status", "active")
        )

        if worker_id:
            query = query.eq("worker_id", worker_id)

        response = query.execute()
        return response.data
    except Exception as e:
        print(f"[ERROR] Error fetching active policies: {e}")
        return []


async def create_claim(
    policy_id: str,
    trigger_event_id: str,
    disrupted_hours: float,
    payout_amount: float,
    fraud_score: float = 0.0,
) -> Optional[dict]:
    """
    Create a new claim (auto-generated from trigger event).

    Args:
        policy_id: UUID of the policy
        trigger_event_id: UUID of the trigger event
        disrupted_hours: Number of hours the worker was disrupted
        payout_amount: Amount to be paid out
        fraud_score: ML-based fraud detection score

    Returns:
        Created claim data or None if error
    """
    try:
        client = get_supabase()
        claim_data = {
            "policy_id": policy_id,
            "trigger_event_id": trigger_event_id,
            "disrupted_hours": disrupted_hours,
            "payout_amount": payout_amount,
            "fraud_score": fraud_score,
            "status": "auto_approved" if fraud_score < 0.3 else "review",
        }

        response = client.table("claims").insert(claim_data).execute()
        return response.data[0] if response.data else None
    except Exception as e:
        print(f"[ERROR] Error creating claim: {e}")
        return None
