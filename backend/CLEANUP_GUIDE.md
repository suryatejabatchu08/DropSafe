# Clean Worker Coverage - Testing Guide

## Option 1: Python Script (Recommended - Safer)

### Usage:
```bash
cd backend
python cleanup_worker_coverage.py +919876543210
```

### What it does:
✅ Finds worker by phone number
✅ Deletes this week's policy
✅ Deletes all related claims
✅ Deletes all related payouts
✅ Resets WhatsApp state to "enrolled"

### Example Output:
```
============================================================
DropSafe Coverage Cleanup Tool
============================================================

📱 Phone: +919876543210

[1/5] Finding worker...
✅ Found worker: Mohammed Saleem (ID: 8f3c2a1...)

[2/5] Finding weekly policy...
✅ Found policy: d4e5f6a... (Status: active, Premium: ₹52.40)

[3/5] Checking for related claims...
   Found 2 claim(s)

[4/5] Deleting related payouts...
   ✓ Deleted payout: a1b2c3d...
   ✓ Deleted payout: e5f6g7h...

[5/5] Deleting claims...
   ✓ Deleted claim: c1d2e3f...
   ✓ Deleted claim: g7h8i9j...

[Final] Deleting policy...
✅ Deleted policy: d4e5f6a...

[Bonus] Resetting WhatsApp state...
✅ Reset WhatsApp state to 'enrolled'

============================================================
✅ CLEANUP SUCCESSFUL
============================================================

Worker Mohammed Saleem can now test the flow from scratch.
Send 'YES' on WhatsApp to activate next week's coverage.
```

---

## Option 2: Direct SQL in Supabase (Manual)

### Step 1: Get worker ID
```sql
SELECT id, phone_hash, name
FROM workers
WHERE phone_hash = (
  SELECT encode(digest('+919876543210', 'sha256'), 'hex')
);
```
Copy the resulting `id`.

### Step 2: Get current week dates
```sql
-- Current week (Monday to Sunday, IST)
SELECT
  DATE(NOW() AT TIME ZONE 'Asia/Kolkata' - INTERVAL '1 day' * EXTRACT(DOW FROM NOW() AT TIME ZONE 'Asia/Kolkata')::int) as week_start,
  DATE(NOW() AT TIME ZONE 'Asia/Kolkata' - INTERVAL '1 day' * EXTRACT(DOW FROM NOW() AT TIME ZONE 'Asia/Kolkata')::int + INTERVAL '7 days') as week_end;
```

### Step 3: Find policy ID
```sql
SELECT id, status, premium_paid
FROM policies
WHERE worker_id = '<WORKER_ID_FROM_STEP_1>'
  AND week_start >= '<WEEK_START_DATE>'
  AND week_end <= '<WEEK_END_DATE>';
```
Copy the `id`.

### Step 4: Delete payouts
```sql
DELETE FROM payouts
WHERE claim_id IN (
  SELECT id FROM claims
  WHERE policy_id = '<POLICY_ID_FROM_STEP_3>'
);
```

### Step 5: Delete claims
```sql
DELETE FROM claims
WHERE policy_id = '<POLICY_ID_FROM_STEP_3>';
```

### Step 6: Delete policy
```sql
DELETE FROM policies
WHERE id = '<POLICY_ID_FROM_STEP_3>';
```

### Step 7: Reset WhatsApp state
```sql
UPDATE workers
SET whatsapp_state = '{"step": "enrolled"}'::jsonb
WHERE id = '<WORKER_ID_FROM_STEP_1>';
```

---

## End-to-End Testing Workflow

After cleanup, test the full flow:

### 1️⃣ Worker sends "YES"
```
WhatsApp → +14155238886
Message: YES
```

### 2️⃣ Bot responds with premium and payment link
```
Expected:
✅ Activate This Week's Coverage
Premium: ₹XX
Tap to pay: https://rzp.io/l/...
```

### 3️⃣ Complete payment on Razorpay
```
Card: 4111 1111 1111 1111
CVV: Any 3 digits
OTP: 1234
```

### 4️⃣ Webhook confirms payment

### 5️⃣ Bot sends activation confirmation
```
✅ Coverage Activated!
Zone: XXX
Coverage Cap: ₹XXXX
```

### 6️⃣ Trigger fires (simulate)
```bash
curl -X POST http://localhost:8000/admin/trigger/simulate \
  -H "Content-Type: application/json" \
  -d '{
    "zone_id": "<ZONE_ID>",
    "trigger_type": "rain",
    "severity": 0.85
  }'
```

### 7️⃣ Claim created automatically

### 8️⃣ Bot notifies worker of claim
```
✅ Claim Approved!
Payout: ₹XX
Amount credited within 24 hours
```

### 9️⃣ Worker checks status
```
WhatsApp Message: STATUS
Expected: Policy details + claim count
```

### 🔟 Worker challenges rejected claim (optional)
```
WhatsApp Message: DISPUTE
Bot moves claim to review
```

---

## Common Issues

### Issue: "Worker not found"
- Check phone number format (must be +919876543210)
- Verify worker exists: `SELECT * FROM workers LIMIT 5;`

### Issue: "No policy found for this week"
- Worker may not have activated coverage yet
- Check week_start/week_end dates are correct for IST timezone

### Issue: Foreign key constraint error
- Delete payouts before claims
- Delete claims before policy
- Script handles this automatically

---

## Quick Commands

**See all workers:**
```sql
SELECT id, name, zone_id FROM workers LIMIT 10;
```

**See all this week's policies:**
```sql
SELECT p.*, w.name
FROM policies p
JOIN workers w ON p.worker_id = w.id
WHERE week_start >= CURRENT_DATE;
```

**See all claims for a worker:**
```sql
SELECT * FROM claims
WHERE worker_id = '<WORKER_ID>'
ORDER BY created_at DESC;
```

