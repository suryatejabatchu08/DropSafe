-- DropSafe Migration: Add pending_payment status to policies table
-- Enables payment link workflow for premium collection

-- Step 1: Drop existing constraint
ALTER TABLE policies DROP CONSTRAINT IF EXISTS policies_status_check;

-- Step 2: Add new constraint with pending_payment status
ALTER TABLE policies ADD CONSTRAINT policies_status_check
  CHECK (status IN (
    'active',
    'expired',
    'cancelled',
    'pending_payment'
  ));

-- Verification query (run after migration):
-- SELECT status, COUNT(*) FROM policies GROUP BY status;
-- Should show new 'pending_payment' status option available
