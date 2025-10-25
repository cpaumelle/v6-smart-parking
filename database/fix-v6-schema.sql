-- Fix V6 Database Schema to Match Architecture Specification
-- This adds missing columns identified during migration

\c parking_v6

-- ============================================
-- Fix sensor_devices table
-- ============================================
ALTER TABLE sensor_devices
ADD COLUMN IF NOT EXISTS device_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(100),
ADD COLUMN IF NOT EXISTS model VARCHAR(100);

-- Set defaults for existing rows
UPDATE sensor_devices
SET device_type = 'parking_sensor'
WHERE device_type IS NULL;

-- ============================================
-- Fix display_devices table
-- ============================================
ALTER TABLE display_devices
ADD COLUMN IF NOT EXISTS device_type VARCHAR(50),
ADD COLUMN IF NOT EXISTS manufacturer VARCHAR(100),
ADD COLUMN IF NOT EXISTS model VARCHAR(100);

-- Set defaults for existing rows
UPDATE display_devices
SET device_type = 'e-paper_display'
WHERE device_type IS NULL;

-- ============================================
-- Fix users table
-- ============================================
-- Add first_name, last_name, role if missing
ALTER TABLE users
ADD COLUMN IF NOT EXISTS first_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS last_name VARCHAR(255),
ADD COLUMN IF NOT EXISTS role VARCHAR(50);

-- Rename password_hash to hashed_password for consistency
DO $$
BEGIN
  IF EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'password_hash'
  ) AND NOT EXISTS (
    SELECT 1 FROM information_schema.columns
    WHERE table_name = 'users' AND column_name = 'hashed_password'
  ) THEN
    ALTER TABLE users RENAME COLUMN password_hash TO hashed_password;
  END IF;
END $$;

-- Migrate name field to first_name/last_name if populated
UPDATE users
SET first_name = SPLIT_PART(name, ' ', 1),
    last_name = NULLIF(SPLIT_PART(name, ' ', 2), '')
WHERE first_name IS NULL
  AND name IS NOT NULL
  AND name != '';

-- ============================================
-- Fix sites table
-- ============================================
ALTER TABLE sites
ADD COLUMN IF NOT EXISTS slug VARCHAR(100);

-- Generate slug from name if missing
UPDATE sites
SET slug = LOWER(REGEXP_REPLACE(name, '[^a-zA-Z0-9]+', '-', 'g'))
WHERE slug IS NULL AND name IS NOT NULL;

-- Add unique constraint on slug within tenant
DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname = 'sites_tenant_id_slug_key'
  ) THEN
    ALTER TABLE sites ADD CONSTRAINT sites_tenant_id_slug_key UNIQUE (tenant_id, slug);
  END IF;
END $$;

-- ============================================
-- Verify schema changes
-- ============================================
SELECT
  'sensor_devices' as table_name,
  column_name,
  data_type,
  character_maximum_length
FROM information_schema.columns
WHERE table_name = 'sensor_devices'
  AND column_name IN ('device_type', 'manufacturer', 'model')
ORDER BY column_name;

SELECT
  'display_devices' as table_name,
  column_name,
  data_type,
  character_maximum_length
FROM information_schema.columns
WHERE table_name = 'display_devices'
  AND column_name IN ('device_type', 'manufacturer', 'model')
ORDER BY column_name;

SELECT
  'users' as table_name,
  column_name,
  data_type,
  character_maximum_length
FROM information_schema.columns
WHERE table_name = 'users'
  AND column_name IN ('first_name', 'last_name', 'role', 'hashed_password')
ORDER BY column_name;

SELECT
  'sites' as table_name,
  column_name,
  data_type,
  character_maximum_length
FROM information_schema.columns
WHERE table_name = 'sites'
  AND column_name = 'slug';

ECHO '';
ECHO '✅ V6 Schema fixes applied successfully';
ECHO '   Ready to re-run migration script';
