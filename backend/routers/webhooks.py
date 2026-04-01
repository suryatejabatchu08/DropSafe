"""
DropSafe Webhooks Router

Handles Razorpay payment confirmations and other webhook events.
"""

from fastapi import APIRouter, HTTPException, Request
from datetime import datetime, timedelta
from database import get_supabase
import pytz
from utils.razorpay_helpers import verify_payment_link_webhook, get_week_start
from utils.whatsapp_helpers import send_whatsapp_message

router = APIRouter(prefix="/webhook", tags=["webhooks"])

IST = pytz.timezone("Asia/Kolkata")


@router.get("/razorpay/payment")
async def handle_razorpay_payment_webhook(request: Request):
    """
    Handle Razorpay payment link callback.

    When payment is completed, Razorpay redirects here with payment details.

    Query params:
        razorpay_payment_link_id: Payment link ID
        razorpay_payment_link_status: Status (paid, cancelled, expired)
        razorpay_payment_id: Payment ID (if status=paid)
    """
    try:
        supabase = get_supabase()

        # Extract query parameters
        payment_link_id = request.query_params.get("razorpay_payment_link_id")
        status = request.query_params.get("razorpay_payment_link_status")
        payment_id = request.query_params.get("razorpay_payment_id")

        print(
            f"[WEBHOOK] Razorpay payment callback: link_id={payment_link_id}, status={status}"
        )

        # Verify webhook
        webhook_data = verify_payment_link_webhook(
            {
                "razorpay_payment_link_id": payment_link_id,
                "razorpay_payment_link_status": status,
                "razorpay_payment_id": payment_id,
            }
        )

        if not webhook_data.get("valid"):
            print(f"[WARNING] Invalid webhook data")
            return {"status": "error", "message": "Invalid webhook"}

        # Payment successful
        if status == "paid":
            notes = webhook_data.get("notes", {})
            worker_id = notes.get("worker_id")
            zone_name = notes.get("zone")
            coverage_cap = float(notes.get("coverage_cap", 0))

            if not worker_id:
                print(f"[ERROR] No worker_id in payment link notes")
                return {"status": "error", "message": "Missing worker_id"}

            # Fetch worker for WhatsApp
            worker_response = (
                supabase.table("workers")
                .select("id, name, encrypted_phone, zone_id")
                .eq("id", worker_id)
                .execute()
            )

            if not worker_response.data:
                print(f"[ERROR] Worker {worker_id} not found")
                return {"status": "error", "message": "Worker not found"}

            worker = worker_response.data[0]
            worker_phone = worker.get("encrypted_phone")
            worker_name = worker.get("name", "Worker")

            # Activate policy (set status from pending_payment to active)
            week_start = get_week_start()
            week_start_str = week_start.strftime("%Y-%m-%d")

            policy_update = (
                supabase.table("policies")
                .update({"status": "active"})
                .eq("worker_id", worker_id)
                .eq("status", "pending_payment")
                .gte("week_start", week_start_str)
                .execute()
            )

            if not policy_update.data:
                print(f"[WARNING] No pending policy found for worker {worker_id}")
            else:
                print(f"[✓] Policy activated for {worker_name}")

            # Reset worker whatsapp_state
            supabase.table("workers").update(
                {"whatsapp_state": {"step": "enrolled"}}
            ).eq("id", worker_id).execute()

            # Send confirmation WhatsApp message
            message = (
                f"✅ *Coverage Activated!*\n\n"
                f"Your DropSafe income protection is live this week. 🛵\n\n"
                f"📍 *Zone*: {zone_name}\n"
                f"💰 *Coverage cap*: ₹{coverage_cap:.0f}\n"
                f"📝 *Payment ref*: {payment_id[:12]}...\n\n"
                f"Stay safe out there!\n"
                f"Reply *STATUS* anytime to check coverage."
            )

            if worker_phone:
                send_whatsapp_message(worker_phone, message)

            print(f"[✓] Payment confirmed for {worker_name} | Link: {payment_link_id}")

            return {
                "status": "success",
                "message": "Payment confirmed, policy activated",
                "worker_id": worker_id,
            }

        # Payment failed or expired
        else:
            notes = webhook_data.get("notes", {})
            worker_id = notes.get("worker_id")

            if not worker_id:
                return {"status": "error", "message": "Missing worker_id"}

            # Fetch worker
            worker_response = (
                supabase.table("workers")
                .select("id, name, encrypted_phone")
                .eq("id", worker_id)
                .execute()
            )

            if not worker_response.data:
                return {"status": "error", "message": "Worker not found"}

            worker = worker_response.data[0]
            worker_phone = worker.get("encrypted_phone")
            worker_name = worker.get("name", "Worker")

            # Cancel pending policy
            week_start = get_week_start()
            week_start_str = week_start.strftime("%Y-%m-%d")

            supabase.table("policies").update({"status": "cancelled"}).eq(
                "worker_id", worker_id
            ).eq("status", "pending_payment").gte(
                "week_start", week_start_str
            ).execute()

            # Reset state
            supabase.table("workers").update(
                {"whatsapp_state": {"step": "enrolled"}}
            ).eq("id", worker_id).execute()

            # Send failure message
            if status == "expired":
                message = (
                    f"⏰ *Payment Link Expired*\n\n"
                    f"Your payment link has expired. "
                    f"Reply *YES* to get a new one. 🙏"
                )
            else:
                message = (
                    f"❌ *Payment Unsuccessful*\n\n"
                    f"Your coverage was not activated this week.\n"
                    f"Reply *YES* anytime to try again. 🙏"
                )

            if worker_phone:
                send_whatsapp_message(worker_phone, message)

            print(f"[⚠️] Payment {status} for {worker_name} | Link: {payment_link_id}")

            return {
                "status": status,
                "message": f"Payment {status}",
                "worker_id": worker_id,
            }

    except Exception as e:
        print(f"[ERROR] Webhook handler failed: {e}")
        raise HTTPException(status_code=500, detail=f"Webhook error: {str(e)}")
