-- DropSafe Seed Data
-- Realistic test data for Indian Q-Commerce zones

-- Insert Zones (5 major Indian cities with varying risk profiles)
INSERT INTO zones (id, pincode, dark_store_name, platform, risk_multiplier, flood_incident_count, aqi_breach_count, road_connectivity_score, last_updated) VALUES
  ('550e8400-e29b-41d4-a716-446655440001', '560102', 'Zepto Dark Store - HSR Layout', 'zepto', 1.15, 2, 8, 0.95, now()),
  ('550e8400-e29b-41d4-a716-446655440002', '110075', 'Blinkit Hub - Dwarka', 'blinkit', 1.35, 1, 15, 0.85, now()),
  ('550e8400-e29b-41d4-a716-446655440003', '400053', 'Zepto Dark Store - Andheri West', 'zepto', 1.55, 5, 12, 0.78, now()),
  ('550e8400-e29b-41d4-a716-446655440004', '500032', 'Blinkit Hub - Gachibowli', 'blinkit', 0.95, 0, 4, 1.00, now()),
  ('550e8400-e29b-41d4-a716-446655440005', '411038', 'Zepto Dark Store - Kothrud', 'zepto', 0.85, 1, 6, 0.98, now());

-- Insert Workers (3 delivery partners across different zones)
INSERT INTO workers (id, phone_hash, name, zone_id, platform, declared_weekly_hours, avg_hourly_income, ml_risk_score, upi_id_encrypted, whatsapp_state, created_at) VALUES
  ('660e8400-e29b-41d4-a716-446655440001',
   'a665a45920422f9d417e4867efdc4fb8a04a1f3fff1fa07e998e86f7f7a27ae3',
   'Rajesh Kumar',
   '550e8400-e29b-41d4-a716-446655440001',
   'zepto',
   42,
   85.50,
   1.05,
   'rajesh.kumar@paytm',
   '{"last_interaction": "2026-03-28T10:30:00Z", "language": "hi"}',
   now() - interval '45 days'),

  ('660e8400-e29b-41d4-a716-446655440002',
   'b3a8e0e1f9ab1bfe3a36f231f676f78bb30a519d1b1cd80c6c3c123456789abc',
   'Mohammed Saleem',
   '550e8400-e29b-41d4-a716-446655440002',
   'blinkit',
   48,
   92.00,
   0.88,
   'saleem9876@paytm',
   '{"last_interaction": "2026-03-27T15:45:00Z", "language": "en"}',
   now() - interval '30 days'),

  ('660e8400-e29b-41d4-a716-446655440003',
   'c74d97b01eae257e44aa9d5bade97baf3b8c7c3d9e1f2a3b4c5d6e7f8a9b0c1d',
   'Priya Sharma',
   '550e8400-e29b-41d4-a716-446655440003',
   'zepto',
   40,
   78.75,
   1.20,
   'priyasharma@gpay',
   '{"last_interaction": "2026-03-29T09:00:00Z", "language": "hi"}',
   now() - interval '20 days');

-- Insert Policies (2 active policies for current week)
INSERT INTO policies (id, worker_id, zone_id, week_start, week_end, premium_paid, coverage_cap, status, created_at) VALUES
  ('770e8400-e29b-41d4-a716-446655440001',
   '660e8400-e29b-41d4-a716-446655440001',
   '550e8400-e29b-41d4-a716-446655440001',
   '2026-03-24',
   '2026-03-30',
   125.00,
   3500.00,
   'active',
   '2026-03-24T08:00:00Z'),

  ('770e8400-e29b-41d4-a716-446655440002',
   '660e8400-e29b-41d4-a716-446655440002',
   '550e8400-e29b-41d4-a716-446655440002',
   '2026-03-24',
   '2026-03-30',
   145.00,
   4200.00,
   'active',
   '2026-03-24T09:30:00Z');

-- Insert Trigger Events (2 events: one verified rain, one pending AQI breach)
INSERT INTO trigger_events (id, zone_id, trigger_type, severity, start_time, end_time, data_sources, verified, created_at) VALUES
  ('880e8400-e29b-41d4-a716-446655440001',
   '550e8400-e29b-41d4-a716-446655440001',
   'rain',
   2.35,
   '2026-03-27T14:00:00Z',
   '2026-03-27T19:30:00Z',
   '{"imd": "heavy_rain_alert", "rainfall_mm": 85, "orders_dropped": 127}',
   true,
   '2026-03-27T14:15:00Z'),

  ('880e8400-e29b-41d4-a716-446655440002',
   '550e8400-e29b-41d4-a716-446655440002',
   'aqi',
   1.85,
   '2026-03-28T06:00:00Z',
   '2026-03-28T12:00:00Z',
   '{"cpcb": "severe_aqi", "aqi_value": 425, "graded_response": "stage_3"}',
   false,
   '2026-03-28T07:00:00Z');

-- Insert Claim (1 auto-approved claim for the verified rain trigger)
INSERT INTO claims (id, policy_id, trigger_event_id, disrupted_hours, payout_amount, fraud_score, fraud_flags, status, created_at) VALUES
  ('990e8400-e29b-41d4-a716-446655440001',
   '770e8400-e29b-41d4-a716-446655440001',
   '880e8400-e29b-41d4-a716-446655440001',
   5.50,
   470.25,
   0.12,
   '{"anomaly_flags": [], "verification_passed": true}',
   'auto_approved',
   '2026-03-27T20:00:00Z');

-- Insert Payout (1 successful payout)
INSERT INTO payouts (id, claim_id, worker_id, amount, channel, razorpay_ref, status, paid_at) VALUES
  ('aa0e8400-e29b-41d4-a716-446655440001',
   '990e8400-e29b-41d4-a716-446655440001',
   '660e8400-e29b-41d4-a716-446655440001',
   470.25,
   'upi',
   'rzp_test_1234567890abcdef',
   'success',
   '2026-03-27T20:15:00Z');
