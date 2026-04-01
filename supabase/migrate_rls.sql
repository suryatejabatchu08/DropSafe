-- Migration: Update RLS Policies to Allow Backend Access
-- Run this in Supabase SQL Editor to fix the RLS access issues

-- Step 1: Drop all existing policies
DROP POLICY IF EXISTS "Zones are publicly readable" ON zones;
DROP POLICY IF EXISTS "Only service role can modify zones" ON zones;
DROP POLICY IF EXISTS "Workers can view their own profile" ON workers;
DROP POLICY IF EXISTS "Workers can update their own profile" ON workers;
DROP POLICY IF EXISTS "Service can manage all workers" ON workers;
DROP POLICY IF EXISTS "Workers can view their own policies" ON policies;
DROP POLICY IF EXISTS "Service can manage all policies" ON policies;
DROP POLICY IF EXISTS "Trigger events are publicly readable" ON trigger_events;
DROP POLICY IF EXISTS "Only service can manage trigger events" ON trigger_events;
DROP POLICY IF EXISTS "Workers can view their own claims" ON claims;
DROP POLICY IF EXISTS "Service can manage all claims" ON claims;
DROP POLICY IF EXISTS "Workers can view their own payouts" ON payouts;
DROP POLICY IF EXISTS "Service can manage all payouts" ON payouts;

-- Step 2: Create new policies with backend read access

-- Zones: Public read access
CREATE POLICY "Zones are publicly readable" ON zones
  FOR SELECT USING (true);

CREATE POLICY "Only service role can modify zones" ON zones
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Workers: Backend can read all workers (for aggregation/reporting)
CREATE POLICY "Backend can read all workers" ON workers
  FOR SELECT USING (true);

CREATE POLICY "Workers can update their own profile" ON workers
  FOR UPDATE USING (auth.uid()::text = id::text);

CREATE POLICY "Service role can manage workers" ON workers
  FOR INSERT USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role can delete workers" ON workers
  FOR DELETE USING (auth.jwt() ->> 'role' = 'service_role');

-- Policies: Backend can read all policies
CREATE POLICY "Backend can read all policies" ON policies
  FOR SELECT USING (true);

CREATE POLICY "Service role can manage policies" ON policies
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Trigger Events: Public read access
CREATE POLICY "Trigger events are publicly readable" ON trigger_events
  FOR SELECT USING (true);

CREATE POLICY "Only service can manage trigger events" ON trigger_events
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Claims: Backend can read all claims
CREATE POLICY "Backend can read all claims" ON claims
  FOR SELECT USING (true);

CREATE POLICY "Service role can manage claims" ON claims
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Payouts: Backend can read all payouts
CREATE POLICY "Backend can read all payouts" ON payouts
  FOR SELECT USING (true);

CREATE POLICY "Service role can manage payouts" ON payouts
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Verification: Check that policies are applied
SELECT schemaname, tablename, policyname
FROM pg_policies
WHERE schemaname = 'public'
ORDER BY tablename, policyname;
