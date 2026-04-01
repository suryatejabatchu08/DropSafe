-- Migration: Add encrypted_phone column for scheduler
-- This allows the scheduler to send WhatsApp messages to enrolled workers

-- Add encrypted phone storage
ALTER TABLE workers ADD COLUMN IF NOT EXISTS encrypted_phone VARCHAR(500);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_workers_encrypted_phone ON workers(encrypted_phone);

-- Add comment explaining the field
COMMENT ON COLUMN workers.encrypted_phone IS 'Encrypted phone number for outbound messaging (scheduler). NOT the phone hash.';

-- Verification query
SELECT id, name, phone_hash, encrypted_phone, whatsapp_state
FROM workers
LIMIT 5;
