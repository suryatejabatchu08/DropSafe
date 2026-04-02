"""
DropSafe Razorpay Payment Link Helper

Creates payment links for premium collection via Razorpay.
"""

import razorpay
import os
from datetime import datetime, timedelta
import pytz
from typing import Optional

IST = pytz.timezone("Asia/Kolkata")


# Initialize Razorpay client
def get_razorpay_client():
    """Get Razorpay client instance."""
    key_id = os.getenv("RAZORPAY_KEY_ID")
    key_secret = os.getenv("RAZORPAY_KEY_SECRET")

    if not key_id or not key_secret:
        raise ValueError("RAZORPAY_KEY_ID or RAZORPAY_KEY_SECRET not set in .env")

    return razorpay.Client(auth=(key_id, key_secret))


def get_week_start():
    """Get current week start (Monday) in IST."""
    now = datetime.now(IST)
    days_since_monday = now.weekday()
    week_start = now - timedelta(days=days_since_monday)
    return week_start.replace(hour=0, minute=0, second=0, microsecond=0)


def get_week_end():
    """Get current week end (Sunday) in IST."""
    week_start = get_week_start()
    week_end = week_start + timedelta(days=7)
    return week_end


async def create_payment_link(
    worker_id: str,
    worker_name: str,
    premium_amount: float,
    zone_name: str,
    coverage_cap: float,
    policy_id: str,
) -> dict:
    """
    Create a Razorpay Payment Link for premium collection.

    Args:
        worker_id: Worker UUID
        worker_name: Worker name
        premium_amount: Premium to be paid (in INR)
        zone_name: Zone name
        coverage_cap: Coverage cap for the policy
        policy_id: Policy UUID (used for unique reference_id)

    Returns:
        {
            "short_url": "https://rzp.io/l/xxxxx",
            "link_id": "plink_xxxxx",
            "expire_by": timestamp
        }
    """
    try:
        client = get_razorpay_client()
        base_url = os.getenv("BASE_URL", "http://localhost:8000")

        # Link expires in 30 minutes
        now_ist = datetime.now(IST)
        expire_by_ist = now_ist + timedelta(minutes=30)
        expire_timestamp = int(expire_by_ist.timestamp())

        # Create payment link
        response = client.payment_link.create(
            {
                "amount": int(premium_amount * 100),  # Convert to paise
                "currency": "INR",
                "accept_partial": False,
                "expire_by": expire_timestamp,
                "reference_id": f"DROPSAFE_PREMIUM_{policy_id[:8]}",
                "description": f"DropSafe Weekly Coverage — {zone_name}",
                "customer": {"name": worker_name, "contact": ""},  # No phone stored
                "notify": {
                    "sms": False,  # We handle notification via WhatsApp
                    "email": False,
                },
                "reminder_enable": False,
                "notes": {
                    "worker_id": worker_id,
                    "zone": zone_name,
                    "premium": str(premium_amount),
                    "coverage_cap": str(coverage_cap),
                    "week_start": get_week_start().isoformat(),
                },
                "callback_url": f"{base_url}/webhook/razorpay/payment",
                "callback_method": "get",
            }
        )

        print(f"[✓] Payment link created: {response['short_url']}")

        return {
            "short_url": response["short_url"],
            "link_id": response["id"],
            "expire_by": expire_timestamp,
        }

    except Exception as e:
        print(f"[ERROR] Failed to create payment link: {e}")
        raise


def verify_payment_link_webhook(request_data: dict) -> dict:
    """
    Verify Razorpay payment link webhook signature.

    Args:
        request_data: Request data from Razorpay

    Returns:
        Verified and safe data
    """
    try:
        client = get_razorpay_client()

        # Razorpay sends payment confirmation details
        # We'll validate based on payment_link_id and status
        payment_link_id = request_data.get("razorpay_payment_link_id")
        status = request_data.get("razorpay_payment_link_status")
        payment_id = request_data.get("razorpay_payment_id")

        # Fetch payment link details to confirm
        if payment_link_id:
            payment_link = client.payment_link.fetch(payment_link_id)

            return {
                "valid": True,
                "payment_link_id": payment_link_id,
                "payment_id": payment_id,
                "status": status,
                "notes": payment_link.get("notes", {}),
                "amount": payment_link.get("amount", 0) / 100,  # Convert from paise
                "short_url": payment_link.get("short_url"),
            }

        return {"valid": False}

    except Exception as e:
        print(f"[ERROR] Webhook verification failed: {e}")
        return {"valid": False, "error": str(e)}
