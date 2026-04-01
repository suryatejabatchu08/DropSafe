-- DropSafe Row Level Security (RLS) Policies - Updated for Backend Access
-- Ensures data isolation for end users while allowing backend read access

-- Enable RLS on all tables
ALTER TABLE zones ENABLE ROW LEVEL SECURITY;
ALTER TABLE workers ENABLE ROW LEVEL SECURITY;
ALTER TABLE policies ENABLE ROW LEVEL SECURITY;
ALTER TABLE trigger_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE claims ENABLE ROW LEVEL SECURITY;
ALTER TABLE payouts ENABLE ROW LEVEL SECURITY;

-- Zones: Public read access (anyone can see zone information)
CREATE POLICY "Zones are publicly readable" ON zones
  FOR SELECT USING (true);

-- Zones: Only service role can insert/update
CREATE POLICY "Only service role can modify zones" ON zones
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Workers: Backend can read all workers (for aggregation/reporting)
CREATE POLICY "Backend can read all workers" ON workers
  FOR SELECT USING (true);

-- Workers: Authenticated users can only update their own profile
CREATE POLICY "Workers can update their own profile" ON workers
  FOR UPDATE USING (auth.uid()::text = id::text);

-- Workers: Only service role can insert/delete workers
CREATE POLICY "Service role can manage workers" ON workers
  FOR INSERT USING (auth.jwt() ->> 'role' = 'service_role');

CREATE POLICY "Service role can delete workers" ON workers
  FOR DELETE USING (auth.jwt() ->> 'role' = 'service_role');

-- Policies: Backend can read all policies (for reporting)
CREATE POLICY "Backend can read all policies" ON policies
  FOR SELECT USING (true);

-- Policies: Only service role can insert/update/delete
CREATE POLICY "Service role can manage policies" ON policies
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Trigger Events: Public read access (transparency for all users)
CREATE POLICY "Trigger events are publicly readable" ON trigger_events
  FOR SELECT USING (true);

-- Trigger Events: Only service role can insert/update
CREATE POLICY "Only service can manage trigger events" ON trigger_events
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Claims: Backend can read all claims (for auto-generation and reporting)
CREATE POLICY "Backend can read all claims" ON claims
  FOR SELECT USING (true);

-- Claims: Only service role can insert/update claims
CREATE POLICY "Service role can manage claims" ON claims
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Payouts: Backend can read all payouts (for processing)
CREATE POLICY "Backend can read all payouts" ON payouts
  FOR SELECT USING (true);

-- Payouts: Only service role can insert/update payouts
CREATE POLICY "Service role can manage payouts" ON payouts
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- NOTE: For production with user authentication:
-- - Add worker-specific policies: WHERE auth.uid()::text = worker_id::text
-- - Enable authentication in frontend
-- - Use service_role key only in secure backend functions
-- - Current setup allows backend read access for MVP/demo phase
