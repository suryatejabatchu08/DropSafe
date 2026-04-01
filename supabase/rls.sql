-- DropSafe Row Level Security (RLS) Policies
-- Ensures data isolation and privacy for workers

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

-- Zones: Only authenticated backend service can insert/update
CREATE POLICY "Only service role can modify zones" ON zones
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Workers: Users can only read/update their own record
CREATE POLICY "Workers can view their own profile" ON workers
  FOR SELECT USING (auth.uid()::text = id::text);

CREATE POLICY "Workers can update their own profile" ON workers
  FOR UPDATE USING (auth.uid()::text = id::text);

-- Workers: Backend service can create and manage all workers
CREATE POLICY "Service can manage all workers" ON workers
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Policies: Workers can only see their own policies
CREATE POLICY "Workers can view their own policies" ON policies
  FOR SELECT USING (auth.uid()::text = worker_id::text);

-- Policies: Backend service can manage all policies
CREATE POLICY "Service can manage all policies" ON policies
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Trigger Events: Public read access (transparency for all users)
CREATE POLICY "Trigger events are publicly readable" ON trigger_events
  FOR SELECT USING (true);

-- Trigger Events: Only service role can insert/update
CREATE POLICY "Only service can manage trigger events" ON trigger_events
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Claims: Workers can only see their own claims
CREATE POLICY "Workers can view their own claims" ON claims
  FOR SELECT USING (
    EXISTS (
      SELECT 1 FROM policies
      WHERE policies.id = claims.policy_id
      AND policies.worker_id::text = auth.uid()::text
    )
  );

-- Claims: Backend service can manage all claims
CREATE POLICY "Service can manage all claims" ON claims
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');

-- Payouts: Workers can only see their own payouts
CREATE POLICY "Workers can view their own payouts" ON payouts
  FOR SELECT USING (auth.uid()::text = worker_id::text);

-- Payouts: Backend service can manage all payouts
CREATE POLICY "Service can manage all payouts" ON payouts
  FOR ALL USING (auth.jwt() ->> 'role' = 'service_role');
