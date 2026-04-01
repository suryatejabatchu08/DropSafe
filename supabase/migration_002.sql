-- DropSafe Migration 002
-- Add curfew events, store closures, and lat/lon to zones for trigger monitoring

-- Add latitude and longitude to zones table
ALTER TABLE zones ADD COLUMN IF NOT EXISTS lat DECIMAL(9,6);
ALTER TABLE zones ADD COLUMN IF NOT EXISTS lon DECIMAL(9,6);

-- Create curfew_events table
CREATE TABLE IF NOT EXISTS curfew_events (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  declared_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  duration_hours INT DEFAULT 4,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_curfew_events_zone_id ON curfew_events(zone_id);
CREATE INDEX IF NOT EXISTS idx_curfew_events_active ON curfew_events(is_active);

-- Create store_closures table
CREATE TABLE IF NOT EXISTS store_closures (
  id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
  zone_id UUID NOT NULL REFERENCES zones(id) ON DELETE CASCADE,
  closed_at TIMESTAMP WITH TIME ZONE DEFAULT now(),
  duration_hours INT DEFAULT 3,
  is_active BOOLEAN DEFAULT true,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_store_closures_zone_id ON store_closures(zone_id);
CREATE INDEX IF NOT EXISTS idx_store_closures_active ON store_closures(is_active);

-- Update zones with latitude and longitude for Indian metro zones
UPDATE zones SET lat = 12.9116, lon = 77.6741
  WHERE pincode = '560102' AND dark_store_name LIKE '%HSR%';

UPDATE zones SET lat = 28.5921, lon = 77.0460
  WHERE pincode = '110075' AND dark_store_name LIKE '%Dwarka%';

UPDATE zones SET lat = 19.1136, lon = 72.8697
  WHERE pincode = '400053' AND dark_store_name LIKE '%Andheri%';

UPDATE zones SET lat = 17.4401, lon = 78.3489
  WHERE pincode = '500032' AND dark_store_name LIKE '%Gachibowli%';

UPDATE zones SET lat = 18.5074, lon = 73.8077
  WHERE pincode = '411038' AND dark_store_name LIKE '%Kothrud%';

-- Verify zones have coordinates
SELECT pincode, dark_store_name, lat, lon FROM zones WHERE lat IS NOT NULL;
