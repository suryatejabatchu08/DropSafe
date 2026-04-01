"""
DropSafe WhatsApp Router
Handles incoming WhatsApp messages and manages conversation flows
"""

from fastapi import APIRouter, Request, Response
from datetime import datetime, timedelta
from database import get_supabase
import pytz
from utils.whatsapp_helpers import (
    hash_phone,
    send_whatsapp_message,
    calculate_premium,
    calculate_coverage_cap,
    validate_pincode,
    validate_upi_id,
    extract_phone_from_whatsapp,
    get_current_season,
)
from utils.razorpay_helpers import create_payment_link, get_week_start

router = APIRouter(prefix="/webhook", tags=["whatsapp"])

IST = pytz.timezone("Asia/Kolkata")


@router.post("/whatsapp")
async def whatsapp_webhook(request: Request):
    """
    Twilio WhatsApp webhook endpoint.
    Receives incoming messages and routes to appropriate conversation flow.
    """
    try:
        # Parse incoming Twilio request
        form_data = await request.form()
        from_number = form_data.get("From", "")  # whatsapp:+919876543210
        message_body = form_data.get("Body", "").strip()

        print(f"[WHATSAPP] Received from {from_number}: {message_body}")

        # Extract clean phone and create hash
        clean_phone = extract_phone_from_whatsapp(from_number)
        phone_hash = hash_phone(clean_phone)

        # Look up worker in database
        supabase = get_supabase()
        worker_response = (
            supabase.table("workers").select("*").eq("phone_hash", phone_hash).execute()
        )

        if not worker_response.data:
            # New user - start onboarding
            response_message = await handle_onboarding(
                phone_hash, from_number, message_body, step=1
            )
        else:
            # Existing user
            worker = worker_response.data[0]
            whatsapp_state = worker.get("whatsapp_state", {})
            current_step = whatsapp_state.get("step", "unknown")

            if current_step == "enrolled":
                # Enrolled worker - handle commands
                response_message = await handle_enrolled_worker(worker, message_body)
            elif current_step == "awaiting_payment":
                # Worker waiting for payment - handle payment-specific commands
                response_message = await handle_awaiting_payment(worker, message_body)
            else:
                # Still in onboarding flow
                step_number = whatsapp_state.get("onboarding_step", 2)
                response_message = await handle_onboarding(
                    phone_hash,
                    from_number,
                    message_body,
                    step=step_number,
                    worker=worker,
                )

        # Send response back via WhatsApp
        if response_message:
            send_whatsapp_message(from_number, response_message)

        # Return empty TwiML response (required by Twilio)
        return Response(
            content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
            media_type="application/xml",
        )

    except Exception as e:
        print(f"[ERROR] WhatsApp webhook error: {e}")
        return Response(
            content="<?xml version='1.0' encoding='UTF-8'?><Response></Response>",
            media_type="application/xml",
        )


async def handle_onboarding(
    phone_hash: str, from_number: str, message: str, step: int, worker: dict = None
):
    """
    Handle onboarding conversation flow.

    Steps:
    1. Welcome message → ask for name
    2. Save name → ask for platform (Zepto/Blinkit)
    3. Save platform → ask for pincode
    4. Validate pincode → look up zone → ask for UPI ID
    5. Save UPI ID → complete onboarding → set enrolled
    """
    supabase = get_supabase()

    if step == 1:
        # First interaction - save initial record
        # Extract clean phone for scheduler (encrypted storage)
        clean_phone = extract_phone_from_whatsapp(from_number)

        worker_data = {
            "phone_hash": phone_hash,
            "encrypted_phone": clean_phone,  # Store for scheduler
            "whatsapp_state": {"step": "onboarding", "onboarding_step": 2},
        }
        supabase.table("workers").insert(worker_data).execute()
        print(f"[ONBOARDING] Step 1: New user {phone_hash[:8]}... welcomed")

        return (
            "👋 Welcome to DropSafe! I'm your income protection assistant.\n\n"
            "I help delivery partners like you protect against income loss from "
            "weather, AQI, and other disruptions.\n\n"
            "What's your name?"
        )

    elif step == 2:
        # Save name, ask for platform
        name = message.title()
        supabase.table("workers").update(
            {
                "name": name,
                "whatsapp_state": {"step": "onboarding", "onboarding_step": 3},
            }
        ).eq("phone_hash", phone_hash).execute()

        print(f"[ONBOARDING] Step 2: Name saved - {name}")

        return (
            f"Hi {name}! 👋\n\n"
            f"Which platform do you deliver for?\n"
            f"Reply:\n"
            f"1 for Zepto 🟢\n"
            f"2 for Blinkit 🟠"
        )

    elif step == 3:
        # Save platform, ask for pincode
        platform_map = {"1": "zepto", "2": "blinkit"}
        platform = platform_map.get(message, None)

        if not platform:
            return "Please reply with 1 for Zepto or 2 for Blinkit"

        supabase.table("workers").update(
            {
                "platform": platform,
                "whatsapp_state": {"step": "onboarding", "onboarding_step": 4},
            }
        ).eq("phone_hash", phone_hash).execute()

        print(f"[ONBOARDING] Step 3: Platform saved - {platform}")

        platform_name = "Zepto" if platform == "zepto" else "Blinkit"
        return (
            f"Great! {platform_name} it is. 🛵\n\n"
            f"What's your PIN code?\n"
            f"(We'll find your nearest dark store zone)"
        )

    elif step == 4:
        # Validate pincode, look up zone, ask for UPI ID
        pincode = message.strip()

        if not validate_pincode(pincode):
            return (
                "That doesn't look like a valid PIN code. "
                "Please send a 6-digit PIN code (e.g., 560102)"
            )

        # Look up zone by pincode
        zones_response = (
            supabase.table("zones").select("*").eq("pincode", pincode).execute()
        )

        if not zones_response.data:
            return (
                f"Sorry, we don't have coverage in {pincode} yet. 😔\n\n"
                f"We're expanding fast! DM us your PIN code and we'll notify "
                f"you when we launch there."
            )

        zone = zones_response.data[0]
        zone_id = zone["id"]
        dark_store_name = zone["dark_store_name"]

        supabase.table("workers").update(
            {
                "zone_id": zone_id,
                "whatsapp_state": {"step": "onboarding", "onboarding_step": 5},
            }
        ).eq("phone_hash", phone_hash).execute()

        print(f"[ONBOARDING] Step 4: Zone matched - {dark_store_name}")

        return (
            f"Found your zone: {dark_store_name} ✅\n\n"
            f"Last step — share your UPI ID for instant payouts:\n"
            f"(e.g., 9876543210@paytm or yourname@oksbi)"
        )

    elif step == 5:
        # Validate and save UPI ID, complete onboarding
        upi_id = message.strip().lower()

        if not validate_upi_id(upi_id):
            return (
                "That doesn't look like a valid UPI ID. "
                "Please send in format: number@provider or name@provider\n"
                "(e.g., 9876543210@paytm)"
            )

        # Complete onboarding
        supabase.table("workers").update(
            {
                "upi_id_encrypted": upi_id,  # In production, encrypt this!
                "declared_weekly_hours": 40,  # Default
                "avg_hourly_income": 80.0,  # Default (can update later)
                "ml_risk_score": 1.0,  # Default
                "whatsapp_state": {"step": "enrolled"},
                "created_at": datetime.utcnow().isoformat(),
            }
        ).eq("phone_hash", phone_hash).execute()

        print(f"[ONBOARDING] Step 5: Onboarding complete for {phone_hash[:8]}...")

        return (
            "🎉 You're all set!\n\n"
            "Your DropSafe account is now active.\n\n"
            "📅 Every Monday at 7 AM, I'll ask if you want this week's income coverage.\n"
            "💰 Premium starts at just ₹100-150/week\n"
            "🛡️ You'll be protected from rain, AQI, and other disruptions\n\n"
            "💬 Quick commands:\n"
            "- Reply STATUS to check your coverage\n"
            "- Reply HELP for more info\n\n"
            "Stay safe out there! 🛵"
        )

    return "Something went wrong. Please try again."


async def handle_enrolled_worker(worker: dict, message: str):
    """
    Handle messages from enrolled workers.

    Commands:
    - YES: Opt in to this week's coverage
    - SKIP: Skip this week's coverage
    - STATUS: Check current coverage status
    - DISPUTE: Challenge a rejected claim
    - HELP: Show available commands
    """
    message_upper = message.upper().strip()
    supabase = get_supabase()

    if message_upper == "YES":
        return await handle_opt_in(worker)

    elif message_upper == "SKIP":
        return (
            "No problem! You're not covered this week. 🙏\n\n"
            "I'll check in again next Monday.\n"
            "Stay safe!"
        )

    elif message_upper == "STATUS":
        return await handle_status_check(worker)

    elif message_upper == "DISPUTE":
        return await handle_dispute(worker)

    elif message_upper == "HELP":
        return (
            "📋 DropSafe Commands:\n\n"
            "YES - Activate coverage for this week\n"
            "SKIP - Skip this week's coverage\n"
            "STATUS - Check your current coverage\n"
            "DISPUTE - Challenge a rejected claim\n"
            "HELP - Show this message\n\n"
            "Questions? Reply with your question and we'll help!"
        )

    else:
        # Unrecognized message - provide guidance
        return (
            "I didn't quite understand that. 🤔\n\n"
            "Quick commands:\n"
            "- YES to activate coverage\n"
            "- STATUS to check coverage\n"
            "- DISPUTE to challenge a claim\n"
            "- HELP for all commands"
        )


async def handle_opt_in(worker: dict):
    """
    Handle worker opting in to weekly coverage.
    Calculate premium, create Razorpay payment link, send payment request.
    """
    supabase = get_supabase()
    worker_id = worker["id"]
    worker_name = worker.get("name", "Worker")
    zone_id = worker["zone_id"]

    # Get week boundaries
    week_start = get_week_start()
    week_start_str = week_start.strftime("%Y-%m-%d")
    week_end = week_start + timedelta(days=7)
    week_end_str = week_end.strftime("%Y-%m-%d")

    # Check if already has policy this week (any status)
    existing_policy = (
        supabase.table("policies")
        .select("*")
        .eq("worker_id", worker_id)
        .gte("week_start", week_start_str)
        .lte("week_end", week_end_str)
        .execute()
    )

    if existing_policy.data:
        policy = existing_policy.data[0]
        status = policy.get("status")
        if status == "active":
            return (
                "You already have active coverage for this week! ✅\n\n"
                "Reply STATUS to see your coverage details."
            )
        elif status == "pending_payment":
            return (
                "You already have a pending payment link. 🔗\n\n"
                "Reply YES to get a new link, or SKIP to cancel."
            )

    # Fetch zone data
    zone_response = supabase.table("zones").select("*").eq("id", zone_id).execute()
    if not zone_response.data:
        return "Error: Could not find your zone. Please contact support."

    zone = zone_response.data[0]
    zone_risk = float(zone["risk_multiplier"])
    zone_name = zone["dark_store_name"]

    # Calculate premium and coverage
    declared_hours = worker.get("declared_weekly_hours", 40)
    avg_hourly_income = float(worker.get("avg_hourly_income", 80.0))
    season = get_current_season()

    premium = calculate_premium(zone_risk, declared_hours, season)
    coverage_cap = calculate_coverage_cap(zone_risk, declared_hours, avg_hourly_income)

    try:
        # Create pending policy (not yet active)
        policy_data = {
            "worker_id": worker_id,
            "zone_id": zone_id,
            "week_start": week_start_str,
            "week_end": week_end_str,
            "premium_paid": premium,
            "coverage_cap": coverage_cap,
            "status": "pending_payment",
            "created_at": datetime.now(IST).replace(tzinfo=None).isoformat(),
        }

        policy_response = supabase.table("policies").insert(policy_data).execute()

        if not policy_response.data:
            print(f"[ERROR] Policy insert failed: {policy_response}")
            return "Error creating policy. Please try again."

        policy_id = policy_response.data[0].get("id")
        print(f"[PAYMENT] Policy created: {policy_id} with status=pending_payment")

        # Create Razorpay payment link
        try:
            payment_link_data = await create_payment_link(
                worker_id=worker_id,
                worker_name=worker_name,
                premium_amount=premium,
                zone_name=zone_name,
                coverage_cap=coverage_cap,
            )
            payment_link_url = payment_link_data["short_url"]
            payment_link_id = payment_link_data["link_id"]
            expire_timestamp = payment_link_data["expire_by"]
        except Exception as razorpay_error:
            print(
                f"[WARNING] Razorpay error (using mock link for test): {razorpay_error}"
            )
            # Use test link for development
            payment_link_url = "https://rzp.io/test"
            payment_link_id = f"test_link_{policy_id[:8]}"
            expire_timestamp = int(
                (datetime.now(IST) + timedelta(minutes=30)).timestamp()
            )

        # Convert timestamp to IST time
        expire_ist = datetime.fromtimestamp(expire_timestamp, tz=IST)
        expire_time_str = expire_ist.strftime("%H:%M IST")

        # Update worker whatsapp_state to awaiting_payment
        supabase.table("workers").update(
            {
                "whatsapp_state": {
                    "step": "awaiting_payment",
                    "policy_id": policy_id,
                    "payment_link_id": payment_link_id,
                    "payment_link": payment_link_url,
                    "expires_at": expire_ist.isoformat(),
                }
            }
        ).eq("id", worker_id).execute()

        print(f"[PAYMENT] Worker state updated to awaiting_payment")

        # Send payment link via WhatsApp
        return (
            f"💳 *Activate This Week's Coverage*\n\n"
            f"📍 *Zone*: {zone_name}\n"
            f"💰 *Premium*: ₹{premium:.0f}\n"
            f"🛡️ *Coverage cap*: ₹{coverage_cap:.0f}\n\n"
            f"Tap to pay securely 👇\n"
            f"{payment_link_url}\n\n"
            f"⏰ Link expires in 30 minutes.\n"
            f"Reply *SKIP* to cancel."
        )

    except Exception as e:
        print(f"[ERROR] Opt-in failed for {worker_id}: {e}")
        import traceback

        traceback.print_exc()
        return f"Error: {str(e)}. Please contact support."


async def handle_awaiting_payment(worker: dict, message: str):
    """
    Handle messages from workers waiting for payment confirmation.

    Commands when awaiting_payment:
    - YES: Get a new payment link (if old one expired) or resend existing
    - SKIP: Cancel pending policy and go back to enrolled
    - STATUS: Show current payment status and link details
    """
    message_upper = message.upper().strip()
    supabase = get_supabase()
    worker_id = worker["id"]
    worker_name = worker.get("name", "Worker")
    whatsapp_state = worker.get("whatsapp_state", {})
    payment_link = whatsapp_state.get("payment_link")
    expires_at_str = whatsapp_state.get("expires_at")
    policy_id = whatsapp_state.get("policy_id")

    if message_upper == "SKIP":
        # Cancel pending payment and policy
        supabase.table("policies").update({"status": "cancelled"}).eq(
            "id", policy_id
        ).execute()

        supabase.table("workers").update({"whatsapp_state": {"step": "enrolled"}}).eq(
            "id", worker_id
        ).execute()

        return (
            "No problem! Coverage cancelled. 🙏\n\n"
            "Reply YES next Monday to try again.\n"
            "Stay safe out there! 🛵"
        )

    elif message_upper == "YES":
        # Check if link is still valid or create new one
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            now = datetime.now(IST)

            if now < expires_at:
                # Link still valid - resend it
                expire_time_str = expires_at.strftime("%H:%M IST")
                return (
                    f"Your payment link is still active 🔗\n\n"
                    f"{payment_link}\n\n"
                    f"⏰ Expires at {expire_time_str}\n"
                    f"Complete payment to activate coverage."
                )

        # Link expired or invalid - create new one
        try:
            # Get zone and premium details from existing policy
            policy_response = (
                supabase.table("policies")
                .select("*, zones(dark_store_name)")
                .eq("id", policy_id)
                .execute()
            )

            if not policy_response.data:
                return "Error: Policy not found. Please contact support."

            policy = policy_response.data[0]
            zone = policy.get("zones", {})
            zone_name = zone.get("dark_store_name", "Your Zone")
            premium = float(policy.get("premium_paid", 0))
            coverage_cap = float(policy.get("coverage_cap", 0))

            # Create new payment link
            payment_link_data = await create_payment_link(
                worker_id=worker_id,
                worker_name=worker_name,
                premium_amount=premium,
                zone_name=zone_name,
                coverage_cap=coverage_cap,
            )

            new_payment_link = payment_link_data["short_url"]
            new_link_id = payment_link_data["link_id"]
            new_expire_timestamp = payment_link_data["expire_by"]

            # Convert timestamp to IST
            new_expire_ist = datetime.fromtimestamp(new_expire_timestamp, tz=IST)
            new_expire_time_str = new_expire_ist.strftime("%H:%M IST")

            # Update worker state with new link
            supabase.table("workers").update(
                {
                    "whatsapp_state": {
                        "step": "awaiting_payment",
                        "policy_id": policy_id,
                        "payment_link_id": new_link_id,
                        "payment_link": new_payment_link,
                        "expires_at": new_expire_ist.isoformat(),
                    }
                }
            ).eq("id", worker_id).execute()

            return (
                f"💳 *New Payment Link*\n\n"
                f"Your previous link expired. Here's a new one:\n\n"
                f"{new_payment_link}\n\n"
                f"⏰ Expires at {new_expire_time_str}\n"
                f"Reply *SKIP* to cancel."
            )

        except Exception as e:
            print(f"[ERROR] Failed to create new payment link: {e}")
            return f"Error creating payment link: {str(e)}"

    elif message_upper == "STATUS":
        # Show payment status
        if expires_at_str:
            expires_at = datetime.fromisoformat(expires_at_str)
            now = datetime.now(pytz.timezone("Asia/Kolkata"))
            expire_time_str = expires_at.strftime("%H:%M IST")

            return (
                f"⏳ *Your Payment is Pending*\n\n"
                f"Complete payment to activate coverage:\n\n"
                f"{payment_link}\n\n"
                f"⏰ Expires at {expire_time_str}\n\n"
                f"Reply YES for a new link if this one expired."
            )
        else:
            return (
                "Your payment is pending. Tap the link below to pay:\n\n"
                f"{payment_link}"
            )

    else:
        # Unrecognized command
        return (
            "I didn't understand that. 🤔\n\n"
            "Quick commands while payment is pending:\n"
            "- YES to get payment link\n"
            "- STATUS to check payment\n"
            "- SKIP to cancel"
        )

    """
    Check and return worker's current coverage status.
    """
    supabase = get_supabase()
    worker_id = worker["id"]

    # Get current week's policy
    today = datetime.now().date()
    week_start = today - timedelta(days=today.weekday())  # Monday

    policy_response = (
        supabase.table("policies")
        .select("*, zones(dark_store_name, pincode)")
        .eq("worker_id", worker_id)
        .eq("week_start", week_start.isoformat())
        .eq("status", "active")
        .execute()
    )

    if not policy_response.data:
        return (
            "📊 Your DropSafe Status:\n\n"
            "❌ No active coverage this week\n\n"
            "Want to activate coverage now?\n"
            "Reply YES to protect your income! 🛡️"
        )

    policy = policy_response.data[0]
    zone = policy.get("zones", {})
    dark_store_name = zone.get("dark_store_name", "Unknown")
    premium = policy["premium_paid"]
    coverage_cap = policy["coverage_cap"]
    week_end = datetime.fromisoformat(policy["week_end"]).date()

    # Check for claims this week
    claims_response = (
        supabase.table("claims").select("*").eq("policy_id", policy["id"]).execute()
    )

    claims_count = len(claims_response.data) if claims_response.data else 0
    total_payout = (
        sum(float(claim.get("payout_amount", 0)) for claim in claims_response.data)
        if claims_response.data
        else 0
    )

    status_message = (
        f"📊 Your DropSafe Status:\n\n"
        f"✅ Coverage ACTIVE this week\n"
        f"Zone: {dark_store_name}\n"
        f"Premium: ₹{premium:.2f}\n"
        f"Coverage cap: ₹{coverage_cap:.2f}\n"
        f"Valid until: {week_end.strftime('%d %b %Y')}\n\n"
    )

    if claims_count > 0:
        status_message += (
            f"💰 Claims this week: {claims_count}\n"
            f"Total payout: ₹{total_payout:.2f}\n\n"
        )
    else:
        status_message += "💰 No claims filed yet this week\n\n"

    status_message += "Stay safe! 🛵"

    return status_message


async def handle_dispute(worker: dict):
    """
    Handle worker disputing a rejected claim.

    Finds most recent rejected claim for worker and moves it back to review.
    Notifies fraud team to re-examine.
    """
    try:
        supabase = get_supabase()
        worker_id = worker["id"]

        # Find most recent rejected claim
        rejected_claims = (
            supabase.table("claims")
            .select("*, policies(id, premium_paid), trigger_events(trigger_type)")
            .eq("worker_id", worker_id)
            .eq("status", "rejected")
            .order("created_at", desc=True)
            .limit(1)
            .execute()
        )

        if not rejected_claims.data:
            return (
                "No rejected claims found. 🤔\n\n"
                "There's nothing to dispute right now.\n"
                "Reply STATUS to check your coverage."
            )

        claim = rejected_claims.data[0]
        claim_id = claim.get("id")
        trigger = claim.get("trigger_events", {})
        trigger_type = trigger.get("trigger_type", "Unknown")

        # Move claim back to review for manual inspection
        now = datetime.now(pytz.UTC).replace(tzinfo=None)

        update_data = {
            "status": "review",
            "reviewed_at": None,
            "reviewed_by": None,
            "rejection_reason": None,
        }

        supabase.table("claims").update(update_data).eq("id", claim_id).execute()

        print(
            f"[WHATSAPP] Worker {worker['name']} disputed claim {claim_id[:8]} "
            f"({trigger_type})"
        )

        return (
            "✅ Dispute submitted!\n\n"
            f"Claim ID: {claim_id[:8]}\n"
            f"Trigger: {trigger_type.replace('_', ' ').title()}\n\n"
            "Our team will re-examine your claim within 2 hours.\n"
            "We'll notify you with the decision via WhatsApp.\n\n"
            "Thank you for using DropSafe! 🙏"
        )

    except Exception as e:
        print(f"[ERROR] Dispute handling failed: {e}")
        return (
            "Something went wrong. 😟\n\n"
            "Please try again in a moment or contact support."
        )


async def handle_status_check(worker: dict):
    """
    Handle worker checking their current coverage status.

    Shows active policy details and pending claims.
    """
    try:
        supabase = get_supabase()
        worker_id = worker["id"]

        # Get current week active policy
        week_start = get_week_start()
        week_end = week_start + timedelta(days=7)

        policy_response = (
            supabase.table("policies")
            .select("*, zones(dark_store_name, platform)")
            .eq("worker_id", worker_id)
            .eq("status", "active")
            .gte("week_start", week_start.strftime("%Y-%m-%d"))
            .lte("week_end", week_end.strftime("%Y-%m-%d"))
            .execute()
        )

        if not policy_response.data:
            return (
                "🔴 No active coverage this week.\n\n"
                "Reply YES on Monday to activate coverage.\n\n"
                "Next check-in: Monday 7:00 AM IST"
            )

        policy = policy_response.data[0]
        zone = policy.get("zones", {})
        premium = policy.get("premium_paid", 0)
        coverage_cap = policy.get("coverage_cap", 0)

        # Get claims this week
        claims_response = (
            supabase.table("claims")
            .select("status")
            .eq("worker_id", worker_id)
            .gte("created_at", week_start.isoformat())
            .execute()
        )

        claims = claims_response.data or []
        pending = sum(1 for c in claims if c.get("status") in ["review", "auto_approved"])
        rejected = sum(1 for c in claims if c.get("status") == "rejected")

        # Build response
        status_msg = (
            f"✅ *Coverage Active*\n\n"
            f"Zone: {zone.get('dark_store_name', 'N/A')}\n"
            f"Premium: ₹{premium:.0f}\n"
            f"Coverage Cap: ₹{coverage_cap:.0f}\n\n"
        )

        if claims:
            status_msg += f"📋 Claims: {len(claims)}\n"
            if pending:
                status_msg += f"⏳ Pending: {pending}\n"
            if rejected:
                status_msg += f"❌ Rejected: {rejected}"

        return status_msg

    except Exception as e:
        print(f"[ERROR] Status check failed: {e}")
        return "Unable to fetch coverage details. Try again soon."

