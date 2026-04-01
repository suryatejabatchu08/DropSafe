-- DropSafe Migration 003: Update Claims Table
-- Add missing columns for auto-claim and fraud detection (Steps 7-8)

-- Add missing columns to existing claims table
ALTER TABLE claims ADD COLUMN IF NOT EXISTS worker_id UUID REFERENCES workers(id) ON DELETE CASCADE;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS zone_id UUID REFERENCES zones(id) ON DELETE CASCADE;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS reviewed_at TIMESTAMP WITHOUT TIME ZONE;
ALTER TABLE claims ADD COLUMN IF NOT EXISTS reviewed_by VARCHAR(100);
ALTER TABLE claims ADD COLUMN IF NOT EXISTS rejection_reason VARCHAR(500);
ALTER TABLE claims ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITHOUT TIME ZONE DEFAULT NOW();

-- Update status enum to include 'approved'
ALTER TABLE claims DROP CONSTRAINT IF EXISTS claims_status_check;
ALTER TABLE claims ADD CONSTRAINT claims_status_check CHECK (status IN ('auto_approved', 'approved', 'review', 'rejected', 'paid'));

-- Create indexes for fraud detection queries if they don't exist
CREATE INDEX IF NOT EXISTS idx_claims_worker_id ON claims(worker_id);
CREATE INDEX IF NOT EXISTS idx_claims_policy_id ON claims(policy_id);
CREATE INDEX IF NOT EXISTS idx_claims_zone_id ON claims(zone_id);
CREATE INDEX IF NOT EXISTS idx_claims_trigger_event_id ON claims(trigger_event_id);
CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status);
CREATE INDEX IF NOT EXISTS idx_claims_fraud_score ON claims(fraud_score);
CREATE INDEX IF NOT EXISTS idx_claims_created_at ON claims(created_at DESC);

-- Grant permissions to service role
GRANT SELECT, INSERT, UPDATE, DELETE ON claims TO service_role;

PRINT 'Updated claims table with fraud detection columns and indexes';

