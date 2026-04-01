-- DropSafe: Create Test Policy for Claim Testing
-- Creates an active policy for today's week to enable trigger → claim flow

-- Step 1: Get Dwarka zone ID
WITH dwarka_zone AS (
  SELECT id as zone_id, dark_store_name
  FROM zones
  WHERE dark_store_name LIKE '%Dwarka%'
  LIMIT 1
),

-- Step 2: Get a worker from that zone
worker_in_zone AS (
  SELECT w.id as worker_id, w.name, w.declared_weekly_hours, w.avg_hourly_income
  FROM workers w
  WHERE w.zone_id = (SELECT zone_id FROM dwarka_zone)
  LIMIT 1
)

-- Step 3: Insert active policy for current week
INSERT INTO policies (
  worker_id,
  zone_id,
  week_start,
  week_end,
  premium_paid,
  coverage_cap,
  status,
  created_at
)
SELECT
  (SELECT worker_id FROM worker_in_zone),
  (SELECT zone_id FROM dwarka_zone),
  DATE_TRUNC('week', NOW() AT TIME ZONE 'UTC')::DATE,
  (DATE_TRUNC('week', NOW() AT TIME ZONE 'UTC') + INTERVAL '7 days')::DATE,
  (38.0 * 1.4 * ((SELECT COALESCE(declared_weekly_hours, 40) FROM worker_in_zone)::NUMERIC / 40.0) * 1.0 * 1.35)::NUMERIC(10,2) as premium_paid,
  ((SELECT COALESCE(declared_weekly_hours, 40) FROM worker_in_zone)::NUMERIC * (SELECT COALESCE(avg_hourly_income, 80.0) FROM worker_in_zone) * 1.4 * 0.80)::NUMERIC(10,2) as coverage_cap,
  'active',
  NOW()
RETURNING
  id,
  worker_id,
  zone_id,
  week_start,
  week_end,
  premium_paid,
  coverage_cap,
  status;
