"""
DropSafe APScheduler
Handles scheduled tasks like weekly opt-in messages and trigger monitoring
"""

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
from datetime import datetime, timedelta
import pytz
from database import get_supabase
from utils.whatsapp_helpers import (
    send_whatsapp_message,
    calculate_premium,
    format_phone_for_whatsapp,
    get_current_season,
)
from services.trigger_monitor import TriggerMonitor

# Initialize scheduler
scheduler = AsyncIOScheduler()

# Indian Standard Time timezone
IST = pytz.timezone("Asia/Kolkata")


async def send_weekly_opt_in_messages():
    """
    Send weekly opt-in messages to all enrolled workers.
    Runs every Monday at 7:00 AM IST.
    """
    print(f"[SCHEDULER] Running weekly opt-in job at {datetime.now(IST)}")

    try:
        supabase = get_supabase()

        # Fetch all enrolled workers
        workers_response = (
            supabase.table("workers")
            .select(
                "id, name, phone_hash, encrypted_phone, zone_id, declared_weekly_hours, "
                "zones(risk_multiplier, dark_store_name)"
            )
            .eq("whatsapp_state->>step", "enrolled")
            .execute()
        )

        if not workers_response.data:
            print("[SCHEDULER] No enrolled workers found")
            return

        workers = workers_response.data
        print(f"[SCHEDULER] Sending opt-in to {len(workers)} workers")

        current_season = get_current_season()
        successful_sends = 0
        failed_sends = 0

        for worker in workers:
            try:
                name = worker.get("name", "there")
                phone_hash = worker["phone_hash"]
                zone_data = worker.get("zones", {})
                zone_risk = float(zone_data.get("risk_multiplier", 1.0))
                dark_store_name = zone_data.get("dark_store_name", "your zone")
                declared_hours = worker.get("declared_weekly_hours", 40)

                # Calculate personalized premium
                premium = calculate_premium(zone_risk, declared_hours, current_season)

                # Get encrypted phone (stored during onboarding)
                encrypted_phone = worker.get("encrypted_phone")

                if not encrypted_phone:
                    print(
                        f"[SCHEDULER] Warning: No encrypted_phone for {name}. Skipping."
                    )
                    failed_sends += 1
                    continue

                # Format WhatsApp number
                whatsapp_number = format_phone_for_whatsapp(encrypted_phone)

                # Message template
                message = (
                    f"Good morning {name}! 🌅\n\n"
                    f"Ready to protect your income this week?\n\n"
                    f"💰 Your premium: ₹{premium:.2f}\n"
                    f"📍 Zone: {dark_store_name}\n"
                    f"🛡️ Protection: Rain, AQI, disruptions\n\n"
                    f"Reply:\n"
                    f"YES to activate coverage\n"
                    f"SKIP to pass this week\n\n"
                    f"Have a great week! 🛵"
                )

                # Send message via Twilio
                success = send_whatsapp_message(whatsapp_number, message)

                if success:
                    print(f"[SCHEDULER] Sent to {name}: ₹{premium:.2f}")
                    successful_sends += 1
                else:
                    print(f"[SCHEDULER] Failed to send to {name}")
                    failed_sends += 1

            except Exception as e:
                print(f"[SCHEDULER] Error processing worker {worker.get('id')}: {e}")
                failed_sends += 1

        print(
            f"[SCHEDULER] Opt-in job complete: {successful_sends} sent, {failed_sends} failed"
        )

    except Exception as e:
        print(f"[SCHEDULER] Error in weekly opt-in job: {e}")


async def check_and_process_triggers():
    """
    Placeholder for future trigger processing job.
    Check for new trigger events and auto-generate claims.
    Can run hourly or every 6 hours.
    """
    print(f"[SCHEDULER] Checking triggers at {datetime.now(IST)}")
    # TODO: Implement trigger event processing
    # 1. Fetch unprocessed verified trigger events
    # 2. Find policies in affected zones during trigger time
    # 3. Auto-generate claims
    # 4. Send WhatsApp notifications to affected workers


async def cleanup_expired_payment_links():
    """
    Clean up expired pending payment policies and notify workers.
    Runs every 15 minutes IST.

    - Find policies with status = 'pending_payment' created > 30 minutes ago
    - Mark as 'cancelled'
    - Reset worker whatsapp_state to 'enrolled'
    - Send WhatsApp notification to worker
    """
    print(f"[SCHEDULER] Checking expired payment links at {datetime.now(IST)}")

    try:
        supabase = get_supabase()
        now_ist = datetime.now(IST)
        cutoff_time = (now_ist - timedelta(minutes=30)).replace(tzinfo=None)

        # Find all pending_payment policies created > 30 minutes ago
        expired_policies = (
            supabase.table("policies")
            .select("id, worker_id, zone_id, created_at, premium_paid")
            .eq("status", "pending_payment")
            .lt("created_at", cutoff_time.isoformat())
            .execute()
        )

        if not expired_policies.data:
            print("[SCHEDULER] No expired payment links found")
            return

        expired_count = len(expired_policies.data)
        print(f"[SCHEDULER] Found {expired_count} expired payment links")

        successful = 0
        failed = 0

        for policy in expired_policies.data:
            try:
                policy_id = policy.get("id")
                worker_id = policy.get("worker_id")

                # Update policy to cancelled
                supabase.table("policies").update({"status": "cancelled"}).eq(
                    "id", policy_id
                ).execute()

                # Fetch worker for notification
                worker_response = (
                    supabase.table("workers")
                    .select("id, name, encrypted_phone")
                    .eq("id", worker_id)
                    .execute()
                )

                if not worker_response.data:
                    failed += 1
                    continue

                worker = worker_response.data[0]
                worker_name = worker.get("name", "Worker")
                worker_phone = worker.get("encrypted_phone")

                # Reset whatsapp_state to enrolled
                supabase.table("workers").update(
                    {"whatsapp_state": {"step": "enrolled"}}
                ).eq("id", worker_id).execute()

                # Send notification
                message = (
                    f"⏰ *Payment Link Expired*\n\n"
                    f"Your payment link has expired. "
                    f"Reply *YES* to get a new one any time. 🙏"
                )

                if worker_phone:
                    send_whatsapp_message(worker_phone, message)
                    print(f"[SCHEDULER] Expired link cleaned up for {worker_name}")
                    successful += 1
                else:
                    print(f"[SCHEDULER] No phone for {worker_name}")
                    failed += 1

            except Exception as e:
                print(f"[SCHEDULER] Error cleaning policy {policy.get('id')}: {e}")
                failed += 1

        print(f"[SCHEDULER] Cleanup complete: {successful} cleaned, {failed} failed")

    except Exception as e:
        print(f"[SCHEDULER] Error in cleanup_expired_payment_links: {e}")


def start_scheduler():
    """
    Start the APScheduler with all jobs.
    Call this when FastAPI app starts.
    """
    print("[SCHEDULER] Initializing APScheduler...")

    # Job 1: Weekly opt-in messages every Monday at 7:00 AM IST
    scheduler.add_job(
        send_weekly_opt_in_messages,
        trigger=CronTrigger(
            day_of_week="mon", hour=7, minute=0, timezone=IST  # Monday
        ),
        id="weekly_opt_in",
        name="Send weekly opt-in messages",
        replace_existing=True,
    )

    # Job 2: Check triggers every 15 minutes
    scheduler.add_job(
        TriggerMonitor.run_all_zones,
        trigger=IntervalTrigger(minutes=15),
        id="trigger_monitor",
        name="Check parametric triggers across all zones",
        replace_existing=True,
    )

    # Job 3: Clean up expired payment links every 15 minutes
    scheduler.add_job(
        cleanup_expired_payment_links,
        trigger=IntervalTrigger(minutes=15),
        id="cleanup_expired_payments",
        name="Clean up expired payment links",
        replace_existing=True,
    )

    scheduler.start()
    print("[SCHEDULER] APScheduler started successfully")
    opt_in_job = scheduler.get_job("weekly_opt_in")
    trigger_job = scheduler.get_job("trigger_monitor")
    cleanup_job = scheduler.get_job("cleanup_expired_payments")
    print(
        f"[SCHEDULER] Next opt-in job: {opt_in_job.next_run_time if opt_in_job else 'N/A'}"
    )
    print(
        f"[SCHEDULER] Next trigger check: {trigger_job.next_run_time if trigger_job else 'N/A'}"
    )
    print(
        f"[SCHEDULER] Next cleanup job: {cleanup_job.next_run_time if cleanup_job else 'N/A'}"
    )


def stop_scheduler():
    """
    Gracefully stop the scheduler.
    Call this when FastAPI app shuts down.
    """
    print("[SCHEDULER] Stopping APScheduler...")
    scheduler.shutdown()
    print("[SCHEDULER] APScheduler stopped")


# For testing: run opt-in job immediately
async def test_send_opt_in():
    """
    Test function to send opt-in messages immediately.
    Useful for development and testing.
    """
    print("[TEST] Running weekly opt-in test...")
    await send_weekly_opt_in_messages()


# For testing: run trigger monitor immediately
async def test_trigger_monitor():
    """
    Test function to run trigger monitoring immediately.
    Useful for development and testing.
    """
    print("[TEST] Running trigger monitor test...")
    await TriggerMonitor.run_all_zones()
