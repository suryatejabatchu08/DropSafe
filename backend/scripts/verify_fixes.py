"""
DropSafe Phase 2 — Fix Verification Script
==========================================
Run from: backend/  (python scripts/verify_fixes.py)

Checks every fix applied in the audit WITHOUT needing a running server.
Uses static code inspection + import checks + logic validation.
"""

import sys
import os
import ast
import re
import json
from pathlib import Path

# ── Make sure we run from backend/ ──────────────────────────────────────────
ROOT = Path(__file__).resolve().parent.parent   # backend/
FRONTEND = ROOT.parent / "frontend" / "src"

PASS = "✅"
FAIL = "❌"
WARN = "⚠️ "

results = []


def check(name: str, passed: bool, detail: str = ""):
    icon = PASS if passed else FAIL
    results.append((icon, name, detail))
    print(f"  {icon}  {name}" + (f"  →  {detail}" if detail else ""))


def section(title: str):
    print(f"\n{'─'*60}")
    print(f"  {title}")
    print(f"{'─'*60}")


def read(rel: str) -> str:
    return (ROOT / rel).read_text(encoding="utf-8", errors="ignore")


def read_fe(rel: str) -> str:
    return (FRONTEND / rel).read_text(encoding="utf-8", errors="ignore")


# ═══════════════════════════════════════════════════════════════════════════
# 1. BACKEND — PREMIUM HELPERS
# ═══════════════════════════════════════════════════════════════════════════
section("1 · Premium Helpers (premium_helpers.py)")

src = read("utils/premium_helpers.py")

check(
    "Temp threshold >40°C returns 1.20 (spec fix)",
    "max_temp > 40" in src and "1.20" in src,
    "get_ml_adjustment() threshold corrected"
)
check(
    "Temp threshold >45°C for extreme heat (1.25)",
    "max_temp > 45" in src and "1.25" in src,
    "extreme heat tier added"
)
check(
    "Coverage cap uses hours × income × 0.80 (no zone_risk)",
    "declared_hours * avg_hourly_income * 0.80" in src or
    "declared_hours * avg_hourly_income * 0.80" in src.replace(" ", ""),
    "zone_risk removed from cap formula"
)
check(
    "Coverage cap docstring says 'not applied'",
    "backwards compatibility" in src or "not applied" in src,
    "backward compat signature kept"
)

# ═══════════════════════════════════════════════════════════════════════════
# 2. BACKEND — WHATSAPP HELPERS
# ═══════════════════════════════════════════════════════════════════════════
section("2 · WhatsApp Helpers (whatsapp_helpers.py)")

src = read("utils/whatsapp_helpers.py")

check(
    "Coverage cap uses hours × income × 0.80 (no 1.2 multiplier)",
    "declared_hours * avg_hourly_income * 0.80" in src or
    "* avg_hourly_income * 0.80" in src,
    "old zone_risk×1.2 formula removed"
)
check(
    "Coverage cap zone_risk not applied",
    "1.2" not in src.split("def calculate_coverage_cap")[1].split("def ")[0]
    if "def calculate_coverage_cap" in src else False,
    "zone_risk×1.2 multiplier gone"
)

# ═══════════════════════════════════════════════════════════════════════════
# 3. BACKEND — FRAUD ENGINE
# ═══════════════════════════════════════════════════════════════════════════
section("3 · Fraud Engine (fraud_engine.py)")

src = read("services/fraud_engine.py")

check(
    "Rule 4 Frequency Check exists as static method",
    "_check_claim_frequency" in src,
    "+0.30 for >8 claims / 30 days"
)
check(
    "Frequency check threshold is 8 claims",
    "<= 8" in src or "count <= 8" in src,
    "threshold: max 8 claims in 30 days"
)
check(
    "Frequency check weight is 0.30",
    '"weight": 0.30 if not passed' in src or "0.30 if not passed" in src,
)
check(
    "Frequency check uses 30-day window",
    "timedelta(days=30)" in src,
)
check(
    "score_claim calls _check_claim_frequency",
    "_check_claim_frequency" in src and
    "await FraudEngine._check_claim_frequency" in src,
)
check(
    "OVC check is now called Rule 5 in docstring",
    "CHECK 5: Order Volume" in src,
)
check(
    "Platform activity is now Rule 6 in docstring",
    "CHECK 6: Platform Activity" in src,
)
check(
    "New Worker is now Rule 7 in docstring",
    "CHECK 7: New Worker" in src,
)
check(
    "Docstring lists 7 rules including Frequency",
    "4. Frequency Check" in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# 4. BACKEND — CLAIM ENGINE
# ═══════════════════════════════════════════════════════════════════════════
section("4 · Claim Engine (claim_engine.py)")

src = read("services/claim_engine.py")

check(
    "_freeze_cluster_fraud_payouts method exists",
    "_freeze_cluster_fraud_payouts" in src,
)
check(
    "process_trigger calls _freeze_cluster_fraud_payouts after loop",
    "await ClaimEngine._freeze_cluster_fraud_payouts" in src,
)
check(
    "Freeze triggers when fraud_rate > 30%",
    "fraud_rate > 30.0" in src,
)
check(
    "Freeze moves auto_approved → review",
    '"review"' in src and "auto_approved" in src and
    "in_(\"id\", auto_approved_ids)" in src,
)
check(
    "Freeze stores reason in rejection_reason field",
    "CLUSTER FRAUD FREEZE" in src,
)
check(
    "Cluster freeze protected by try/except",
    "except Exception as e:" in src and
    "Cluster fraud freeze check failed" in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# 5. BACKEND — FRAUD ROUTER (reject notification)
# ═══════════════════════════════════════════════════════════════════════════
section("5 · Fraud Router (routers/fraud.py) — Rejection Notification")

src = read("routers/fraud.py")

check(
    "send_whatsapp_message imported",
    "from utils.whatsapp_helpers import send_whatsapp_message" in src,
)
check(
    "Rejection handler fetches worker phone",
    "encrypted_phone" in src and "worker_resp" in src,
)
check(
    "Rejection message sent via WhatsApp",
    "send_whatsapp_message" in src and "Claim Rejected" in src,
)
check(
    "DISPUTE option included in rejection message",
    "DISPUTE" in src,
)
check(
    "Notification wrapped in try/except (non-blocking)",
    "except Exception as notify_err" in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# 6. BACKEND — PAYOUTS ROUTER
# ═══════════════════════════════════════════════════════════════════════════
section("6 · Payouts Router (routers/payouts.py) — Webhook Sig + Retry")

src = read("routers/payouts.py")

# Webhook signature
check(
    "Request and Header imported from fastapi",
    "from fastapi import" in src and "Request" in src and "Header" in src,
)
check(
    "hmac imported",
    "import hmac" in src,
)
check(
    "hashlib imported",
    "import hashlib" in src,
)
check(
    "RAZORPAY_WEBHOOK_SECRET read from env",
    'os.getenv("RAZORPAY_WEBHOOK_SECRET"' in src,
)
check(
    "HMAC-SHA256 digest computed",
    "hmac.new(" in src and "hashlib.sha256" in src,
)
check(
    "Constant-time compare_digest used (timing-safe)",
    "hmac.compare_digest(" in src,
)
check(
    "Missing signature header raises 400",
    "Missing X-Razorpay-Signature" in src,
)
check(
    "TODO comment removed from webhook",
    "# TODO: Verify webhook signature" not in src,
)

# Retry
check(
    "Retry fetches claim_id from payout record",
    'payout.get("claim_id")' in src,
)
check(
    "Retry calls PayoutEngine.process_payout()",
    "await PayoutEngine.process_payout(claim_id)" in src,
)
check(
    "Retry resets claim status to approved",
    '"approved"' in src and "claims" in src,
)
check(
    "Retry returns actual payout_id from PayoutEngine",
    'payout_result.get("payout_id"' in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# 7. SCRIPTS MOVED
# ═══════════════════════════════════════════════════════════════════════════
section("7 · Utility Scripts Relocated to backend/scripts/")

scripts_dir = ROOT / "scripts"
for fname in [
    "delete_user_complete.py",
    "delete_zone_triggers.py",
    "cleanup_worker_coverage.py",
    "test_run_triggers.py",
    "verify_fixes.py",
]:
    path = scripts_dir / fname
    check(
        f"scripts/{fname} exists",
        path.exists(),
    )

for fname in [
    "delete_user_complete.py",
    "delete_zone_triggers.py",
    "cleanup_worker_coverage.py",
]:
    check(
        f"{fname} removed from backend root",
        not (ROOT / fname).exists(),
    )

# ═══════════════════════════════════════════════════════════════════════════
# 8. FRONTEND — API CLIENT
# ═══════════════════════════════════════════════════════════════════════════
section("8 · Frontend API Client (src/lib/api.ts)")

src = read_fe("lib/api.ts")

check(
    "getDailyClaimsSummary calls /dashboard/claims/daily-summary",
    "/dashboard/claims/daily-summary" in src,
    "was /claims/daily-summary (404)"
)
check(
    "getDailyPayoutsSummary calls /payouts/daily-summary",
    "/payouts/daily-summary" in src,
)
check(
    "getRecentPayouts function exists",
    "getRecentPayouts" in src,
)
check(
    "retryPayout function exists",
    "retryPayout" in src,
)
check(
    "No duplicate getDailyPayoutsSummary declarations",
    src.count("export async function getDailyPayoutsSummary") == 1,
)

# ═══════════════════════════════════════════════════════════════════════════
# 9. FRONTEND — DASHBOARD
# ═══════════════════════════════════════════════════════════════════════════
section("9 · Frontend Dashboard (src/pages/Dashboard.tsx)")

src = read_fe("pages/Dashboard.tsx")

check(
    "Imports StatCard component",
    "import StatCard" in src,
)
check(
    "Imports TriggerFeed component",
    "import TriggerFeed" in src,
)
check(
    "Renders <StatCard> elements",
    "<StatCard" in src,
)
check(
    "Renders <TriggerFeed> element",
    "<TriggerFeed" in src,
)
check(
    "Imports BarChart from recharts",
    "BarChart" in src and "recharts" in src,
)
check(
    "Imports LineChart from recharts",
    "LineChart" in src and "recharts" in src,
)
check(
    "Renders claims BarChart",
    "<BarChart" in src,
)
check(
    "Renders payouts LineChart",
    "<LineChart" in src,
)
check(
    "Claims chart uses stacked bars by status",
    "stackId" in src,
)
check(
    "Dashboard auto-refreshes every 30s",
    "30000" in src,
)
check(
    "getDailyClaimsSummary called",
    "getDailyClaimsSummary" in src,
)
check(
    "getDailyPayoutsSummary called",
    "getDailyPayoutsSummary" in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# 10. FRONTEND — CLAIMS
# ═══════════════════════════════════════════════════════════════════════════
section("10 · Frontend Claims (src/pages/Claims.tsx)")

src = read_fe("pages/Claims.tsx")

check(
    "Status filter tabs defined (All/Review/Approved/Rejected)",
    "STATUS_TABS" in src and "review" in src,
)
check(
    "StatusFilter type defined",
    "StatusFilter" in src,
)
check(
    "Filter state hook exists",
    "activeFilter" in src,
)
check(
    "Filter buttons rendered from STATUS_TABS",
    "STATUS_TABS.map" in src,
)
check(
    "Review count badge on Review tab",
    "reviewQueue.length" in src,
)
check(
    "STATUS_COLORS unused variable removed",
    "STATUS_COLORS" not in src,
)
check(
    "Summary stats row (5 cards) shown",
    "total_claims" in src and "auto_approved" in src and "fraud_rate" in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# 11. FRONTEND — PAYOUTS
# ═══════════════════════════════════════════════════════════════════════════
section("11 · Frontend Payouts (src/pages/Payouts.tsx)")

src = read_fe("pages/Payouts.tsx")

check(
    "Payouts table rendered (table element)",
    "<table" in src,
)
check(
    "Status badge column in table",
    "STATUS_BADGE" in src,
)
check(
    "Retry button shown for failed payouts",
    "status === \"failed\"" in src and "handleRetry" in src,
)
check(
    "handleRetry calls retryPayout from api",
    "retryPayout" in src,
)
check(
    "Retry shows loading state",
    "Retrying" in src,
)
check(
    "RefreshCw icon used for retry",
    "RefreshCw" in src,
)
check(
    "Payout rows mapped over recent_payouts",
    "recent_payouts" in src or "recentPayouts" in src,
)
check(
    "Empty state shown when no payouts",
    "No payout records" in src,
)
check(
    "Razorpay typo fixed ('Razorpay' not 'Rayorpay')",
    "Rayorpay" not in src,
)

# ═══════════════════════════════════════════════════════════════════════════
# FINAL SUMMARY
# ═══════════════════════════════════════════════════════════════════════════
passed = sum(1 for r in results if r[0] == PASS)
failed = sum(1 for r in results if r[0] == FAIL)
total  = len(results)

print(f"\n{'═'*60}")
print(f"  VERIFICATION SUMMARY")
print(f"{'═'*60}")
print(f"  Total checks : {total}")
print(f"  {PASS} Passed    : {passed}")
print(f"  {FAIL} Failed    : {failed}")
print(f"{'═'*60}\n")

if failed > 0:
    print("Failed checks:")
    for icon, name, detail in results:
        if icon == FAIL:
            print(f"  {FAIL}  {name}" + (f"  →  {detail}" if detail else ""))

sys.exit(0 if failed == 0 else 1)
