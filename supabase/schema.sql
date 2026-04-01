-- DropSafe Database Schema
-- Parametric Income Insurance for Q-Commerce Partners

-- Zone intelligence (Dark Store Zone Intelligence)
CREATE TABLE zones (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  pincode VARCHAR(10) NOT NULL,
  dark_store_name VARCHAR(100) NOT NULL,
  platform VARCHAR(20) CHECK (platform IN ('zepto', 'blinkit')),
  risk_multiplier DECIMAL(4,2) DEFAULT 1.00,
  flood_incident_count INT DEFAULT 0,
  aqi_breach_count INT DEFAULT 0,
  road_connectivity_score DECIMAL(3,2) DEFAULT 1.00,
  last_updated TIMESTAMP DEFAULT now()
);

-- Workers
CREATE TABLE workers (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  phone_hash VARCHAR(255) UNIQUE NOT NULL,
  name VARCHAR(100),
  zone_id UUID REFERENCES zones(id),
  platform VARCHAR(20) CHECK (platform IN ('zepto', 'blinkit')),
  declared_weekly_hours INT DEFAULT 40,
  avg_hourly_income DECIMAL(8,2) DEFAULT 80.00,
  ml_risk_score DECIMAL(4,2) DEFAULT 1.00,
  upi_id_encrypted VARCHAR(255),
  whatsapp_state JSONB DEFAULT '{}',
  created_at TIMESTAMP DEFAULT now()
);

-- Policies (weekly)
CREATE TABLE policies (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  worker_id UUID REFERENCES workers(id),
  zone_id UUID REFERENCES zones(id),
  week_start DATE NOT NULL,
  week_end DATE NOT NULL,
  premium_paid DECIMAL(8,2),
  coverage_cap DECIMAL(10,2),
  status VARCHAR(20) DEFAULT 'active' CHECK (status IN ('active', 'expired', 'cancelled')),
  created_at TIMESTAMP DEFAULT now()
);

-- Trigger events (zone-level)
CREATE TABLE trigger_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id UUID REFERENCES zones(id),
  trigger_type VARCHAR(30) CHECK (trigger_type IN ('rain', 'heat', 'aqi', 'curfew', 'order_collapse', 'store_closure')),
  severity DECIMAL(4,2),
  start_time TIMESTAMP,
  end_time TIMESTAMP,
  data_sources JSONB DEFAULT '{}',
  verified BOOLEAN DEFAULT false,
  created_at TIMESTAMP DEFAULT now()
);

-- Claims (auto-generated, never manually filed)
CREATE TABLE claims (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  policy_id UUID REFERENCES policies(id),
  trigger_event_id UUID REFERENCES trigger_events(id),
  disrupted_hours DECIMAL(4,2),
  payout_amount DECIMAL(10,2),
  fraud_score DECIMAL(4,2) DEFAULT 0.00,
  fraud_flags JSONB DEFAULT '{}',
  status VARCHAR(20) DEFAULT 'auto_approved' CHECK (status IN ('auto_approved', 'review', 'rejected', 'paid')),
  created_at TIMESTAMP DEFAULT now()
);

-- Payouts
CREATE TABLE payouts (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  claim_id UUID REFERENCES claims(id),
  worker_id UUID REFERENCES workers(id),
  amount DECIMAL(10,2),
  channel VARCHAR(50) DEFAULT 'upi',
  razorpay_ref VARCHAR(255),
  status VARCHAR(20) DEFAULT 'initiated' CHECK (status IN ('initiated', 'success', 'failed')),
  paid_at TIMESTAMP
);

-- Indexes for better query performance
CREATE INDEX idx_workers_phone_hash ON workers(phone_hash);
CREATE INDEX idx_workers_zone_id ON workers(zone_id);
CREATE INDEX idx_policies_worker_id ON policies(worker_id);
CREATE INDEX idx_policies_week_start ON policies(week_start);
CREATE INDEX idx_trigger_events_zone_id ON trigger_events(zone_id);
CREATE INDEX idx_trigger_events_verified ON trigger_events(verified);
CREATE INDEX idx_claims_policy_id ON claims(policy_id);
CREATE INDEX idx_payouts_worker_id ON payouts(worker_id);
