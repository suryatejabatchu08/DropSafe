"""
DropSafe Database Module - PRODUCTION VERSION
Uses service_role key for backend operations (bypasses RLS)
"""

import os
from typing import Optional
from supabase import create_client, Client
from dotenv import load_dotenv

load_dotenv()

# PRODUCTION: Use service_role key for backend operations
SUPABASE_URL: str = os.getenv("SUPABASE_URL", "")
SUPABASE_SERVICE_KEY: str = os.getenv("SUPABASE_SERVICE_ROLE_KEY", "")
SUPABASE_ANON_KEY: str = os.getenv("SUPABASE_ANON_KEY", "")

# Two clients: one for backend (service), one for frontend (anon)
supabase_service: Optional[Client] = None
supabase_anon: Optional[Client] = None


def init_supabase_service() -> Client:
    """
    Initialize Supabase client with SERVICE ROLE key.
    Use this for backend operations that bypass RLS.
    """
    global supabase_service

    if not SUPABASE_URL or not SUPABASE_SERVICE_KEY:
        raise ValueError("Missing SUPABASE_URL or SUPABASE_SERVICE_ROLE_KEY")

    if supabase_service is None:
        supabase_service = create_client(SUPABASE_URL, SUPABASE_SERVICE_KEY)
        print(f"[OK] Supabase (SERVICE) connected: {SUPABASE_URL}")

    return supabase_service


def get_supabase() -> Client:
    """
    Get service role client for backend operations.
    This bypasses RLS and has full database access.
    """
    if supabase_service is None:
        return init_supabase_service()
    return supabase_service


# All your existing helper functions remain the same...
# They now use service_role client which bypasses RLS
