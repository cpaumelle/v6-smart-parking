#!/bin/bash
set -e

echo "=========================================="
echo "V5 to V6 Database Migration"
echo "Smart Parking Platform"
echo "=========================================="

# Configuration
V5_DB="parking_v5"
V6_DB="parking_v6"
DB_USER="parking_user"
DB_PASS="parking"
DB_HOST="${DB_HOST:-parking-postgres}"

echo ""
echo "Source Database: $V5_DB"
echo "Target Database: $V6_DB"
echo "Database Host: $DB_HOST"
echo ""

# Function to run SQL
run_sql() {
    local database=$1
    local sql=$2
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $database -c "$sql"
}

# Function to run SQL file
run_sql_query() {
    local database=$1
    local query=$2
    PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -d $database << EOF
$query
EOF
}

# ==================================
# Step 1: Verify Databases Exist
# ==================================
echo "[1/8] Verifying databases..."

if ! PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $V5_DB; then
    echo "❌ ERROR: Source database '$V5_DB' does not exist!"
    exit 1
fi
echo "  ✓ Source database $V5_DB found"

if ! PGPASSWORD=$DB_PASS psql -h $DB_HOST -U $DB_USER -lqt | cut -d \| -f 1 | grep -qw $V6_DB; then
    echo "❌ ERROR: Target database '$V6_DB' does not exist!"
    echo "  Please create V6 schema first."
    exit 1
fi
echo "  ✓ Target database $V6_DB found"

# ==================================
# Step 2: Backup V6 Database
# ==================================
echo ""
echo "[2/8] Creating backup of V6 database..."
BACKUP_FILE="/tmp/v6_pre_migration_backup_$(date +%Y%m%d_%H%M%S).sql"
PGPASSWORD=$DB_PASS pg_dump -h $DB_HOST -U $DB_USER $V6_DB > $BACKUP_FILE
echo "  ✓ Backup created: $BACKUP_FILE"

# ==================================
# Step 3: Check V5 Data Counts
# ==================================
echo ""
echo "[3/8] Analyzing V5 data..."

run_sql_query $V5_DB "
SELECT 
    'Tenants: ' || COUNT(*) FROM tenants
UNION ALL
SELECT 'Users: ' || COUNT(*) FROM users
UNION ALL
SELECT 'Sites: ' || COUNT(*) FROM sites
UNION ALL
SELECT 'Spaces: ' || COUNT(*) FROM spaces
UNION ALL
SELECT 'Sensors: ' || COUNT(*) FROM sensor_devices
UNION ALL
SELECT 'Displays: ' || COUNT(*) FROM display_devices;
"

# ==================================
# Step 4: Migrate Tenants
# ==================================
echo ""
echo "[4/8] Migrating tenants..."

run_sql_query $V6_DB "
-- Insert V5 tenants into V6 if they don't already exist
INSERT INTO tenants (id, name, slug, type, subscription_tier, is_active, created_at, updated_at)
SELECT 
    t.id,
    t.name,
    t.slug,
    CASE 
        WHEN t.slug = 'platform' THEN 'platform'
        ELSE 'customer'
    END as type,
    COALESCE(t.subscription_tier, 'basic') as subscription_tier,
    COALESCE(t.is_active, true) as is_active,
    COALESCE(t.created_at, NOW()) as created_at,
    COALESCE(t.updated_at, NOW()) as updated_at
FROM dblink('dbname=$V5_DB user=$DB_USER password=$DB_PASS host=$DB_HOST',
    'SELECT id, name, slug, subscription_tier, is_active, created_at, updated_at FROM tenants'
) AS t(
    id uuid,
    name varchar,
    slug varchar,
    subscription_tier varchar,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp
)
ON CONFLICT (id) DO UPDATE SET
    name = EXCLUDED.name,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
"

TENANT_COUNT=$(run_sql $V6_DB "SELECT COUNT(*) FROM tenants;" | grep -o '[0-9]*' | head -1)
echo "  ✓ Tenants in V6: $TENANT_COUNT"

# ==================================
# Step 5: Migrate Users
# ==================================
echo ""
echo "[5/8] Migrating users..."

run_sql_query $V6_DB "
-- Insert V5 users into V6
-- V5 has: id, email, name, password_hash (no tenant_id, no first/last names)
-- V6 has: id, email, name, hashed_password (also no tenant_id in V6)
INSERT INTO users (id, email, name, hashed_password, is_active, email_verified, created_at, updated_at)
SELECT
    u.id,
    u.email,
    u.name,
    u.password_hash,
    COALESCE(u.is_active, true) as is_active,
    COALESCE(u.email_verified, false) as email_verified,
    COALESCE(u.created_at, NOW()) as created_at,
    COALESCE(u.updated_at, NOW()) as updated_at
FROM dblink('dbname=$V5_DB user=$DB_USER password=$DB_PASS host=$DB_HOST',
    'SELECT id, email, name, password_hash, is_active, email_verified, created_at, updated_at FROM users'
) AS u(
    id uuid,
    email varchar,
    name varchar,
    password_hash varchar,
    is_active boolean,
    email_verified boolean,
    created_at timestamp,
    updated_at timestamp
)
ON CONFLICT (email) DO UPDATE SET
    name = EXCLUDED.name,
    is_active = EXCLUDED.is_active,
    updated_at = NOW();
"

USER_COUNT=$(run_sql $V6_DB "SELECT COUNT(*) FROM users;" | grep -o '[0-9]*' | head -1)
echo "  ✓ Users in V6: $USER_COUNT"

# ==================================
# Step 6: Migrate Sites and Spaces
# ==================================
echo ""
echo "[6/8] Migrating sites and spaces..."

# Sites
run_sql_query $V6_DB "
INSERT INTO sites (id, tenant_id, name, timezone, location, metadata, is_active, created_at, updated_at)
SELECT
    s.id,
    s.tenant_id,
    s.name,
    COALESCE(s.timezone, 'UTC') as timezone,
    s.location,
    COALESCE(s.metadata, '{}'::jsonb) as metadata,
    COALESCE(s.is_active, true) as is_active,
    COALESCE(s.created_at, NOW()) as created_at,
    COALESCE(s.updated_at, NOW()) as updated_at
FROM dblink('dbname=$V5_DB user=$DB_USER password=$DB_PASS host=$DB_HOST',
    'SELECT id, tenant_id, name, timezone, location, metadata, is_active, created_at, updated_at FROM sites'
) AS s(
    id uuid,
    tenant_id uuid,
    name varchar,
    timezone varchar,
    location jsonb,
    metadata jsonb,
    is_active boolean,
    created_at timestamp,
    updated_at timestamp
)
ON CONFLICT (id) DO NOTHING;
"

# Spaces
run_sql_query $V6_DB "
INSERT INTO spaces (
    id, tenant_id, site_id, code, name,
    building, floor, zone,
    gps_latitude, gps_longitude,
    sensor_eui, display_eui,
    sensor_device_id, display_device_id,
    state, metadata,
    created_at, updated_at, deleted_at
)
SELECT
    sp.id,
    sp.tenant_id,
    sp.site_id,
    sp.code,
    sp.name,
    sp.building,
    sp.floor,
    sp.zone,
    sp.gps_latitude,
    sp.gps_longitude,
    sp.sensor_eui,
    sp.display_eui,
    sp.sensor_device_id,
    sp.display_device_id,
    sp.state,
    COALESCE(sp.metadata, '{}'::jsonb) as metadata,
    COALESCE(sp.created_at, NOW()) as created_at,
    COALESCE(sp.updated_at, NOW()) as updated_at,
    sp.deleted_at
FROM dblink('dbname=$V5_DB user=$DB_USER password=$DB_PASS host=$DB_HOST',
    'SELECT id, tenant_id, site_id, code, name, building, floor, zone, gps_latitude, gps_longitude, sensor_eui, display_eui, sensor_device_id, display_device_id, state, metadata, created_at, updated_at, deleted_at FROM spaces WHERE deleted_at IS NULL'
) AS sp(
    id uuid,
    tenant_id uuid,
    site_id uuid,
    code varchar,
    name varchar,
    building varchar,
    floor varchar,
    zone varchar,
    gps_latitude numeric,
    gps_longitude numeric,
    sensor_eui varchar,
    display_eui varchar,
    sensor_device_id uuid,
    display_device_id uuid,
    state varchar,
    metadata jsonb,
    created_at timestamp,
    updated_at timestamp,
    deleted_at timestamp
)
ON CONFLICT (id) DO NOTHING;
"

SITE_COUNT=$(run_sql $V6_DB "SELECT COUNT(*) FROM sites;" | grep -o '[0-9]*' | head -1)
SPACE_COUNT=$(run_sql $V6_DB "SELECT COUNT(*) FROM spaces;" | grep -o '[0-9]*' | head -1)
echo "  ✓ Sites in V6: $SITE_COUNT"
echo "  ✓ Spaces in V6: $SPACE_COUNT"

# ==================================
# Step 7: Migrate Devices (CRITICAL)
# ==================================
echo ""
echo "[7/8] Migrating devices..."

# Sensor Devices
run_sql_query $V6_DB "
-- First, get tenant_id for each device based on their space assignment
-- If no space, assign to platform tenant
INSERT INTO sensor_devices (
    id, tenant_id, dev_eui, device_type, manufacturer, model,
    status, lifecycle_state, assigned_space_id, assigned_at,
    enabled, config, created_at, updated_at
)
SELECT
    sd.id,
    -- Derive tenant_id from space assignment, or use platform tenant
    COALESCE(
        (SELECT sp.tenant_id FROM spaces sp WHERE sp.sensor_device_id = sd.id LIMIT 1),
        '00000000-0000-0000-0000-000000000000'::uuid
    ) as tenant_id,
    sd.dev_eui,
    sd.device_type,
    sd.manufacturer,
    sd.device_model as model,
    CASE
        WHEN sd.status = 'orphan' THEN 'unassigned'
        WHEN sd.status = 'active' THEN 'assigned'
        WHEN sd.status = 'inactive' THEN 'unassigned'
        WHEN sd.status = 'decommissioned' THEN 'unassigned'
        ELSE 'unassigned'
    END as status,
    'operational' as lifecycle_state,  -- Default lifecycle state
    (SELECT sp.id FROM spaces sp WHERE sp.sensor_device_id = sd.id LIMIT 1) as assigned_space_id,
    sd.created_at as assigned_at,
    COALESCE(sd.enabled, true) as enabled,
    COALESCE(sd.capabilities, '{}'::jsonb) as config,
    COALESCE(sd.created_at, NOW()) as created_at,
    COALESCE(sd.updated_at, NOW()) as updated_at
FROM dblink('dbname=$V5_DB user=$DB_USER password=$DB_PASS host=$DB_HOST',
    'SELECT id, dev_eui, device_type, manufacturer, device_model, status, enabled, capabilities, created_at, updated_at FROM sensor_devices'
) AS sd(
    id uuid,
    dev_eui varchar,
    device_type varchar,
    manufacturer varchar,
    device_model varchar,
    status varchar,
    enabled boolean,
    capabilities jsonb,
    created_at timestamp,
    updated_at timestamp
)
ON CONFLICT (dev_eui) DO UPDATE SET
    device_type = EXCLUDED.device_type,
    manufacturer = EXCLUDED.manufacturer,
    model = EXCLUDED.model,
    status = EXCLUDED.status,
    tenant_id = EXCLUDED.tenant_id,
    assigned_space_id = EXCLUDED.assigned_space_id,
    updated_at = NOW();
"

# Display Devices
run_sql_query $V6_DB "
INSERT INTO display_devices (
    id, tenant_id, dev_eui, device_type, manufacturer, model,
    status, lifecycle_state, assigned_space_id, assigned_at,
    enabled, config, created_at, updated_at
)
SELECT
    dd.id,
    COALESCE(
        (SELECT sp.tenant_id FROM spaces sp WHERE sp.display_device_id = dd.id LIMIT 1),
        '00000000-0000-0000-0000-000000000000'::uuid
    ) as tenant_id,
    dd.dev_eui,
    dd.device_type,
    dd.manufacturer,
    dd.device_model as model,
    CASE
        WHEN dd.status = 'orphan' THEN 'unassigned'
        WHEN dd.status = 'active' THEN 'assigned'
        WHEN dd.status = 'inactive' THEN 'unassigned'
        WHEN dd.status = 'decommissioned' THEN 'unassigned'
        ELSE 'unassigned'
    END as status,
    'operational' as lifecycle_state,
    (SELECT sp.id FROM spaces sp WHERE sp.display_device_id = dd.id LIMIT 1) as assigned_space_id,
    dd.created_at as assigned_at,
    COALESCE(dd.enabled, true) as enabled,
    jsonb_build_object('display_codes', dd.display_codes, 'fport', dd.fport, 'confirmed_downlinks', dd.confirmed_downlinks) as config,
    COALESCE(dd.created_at, NOW()) as created_at,
    COALESCE(dd.updated_at, NOW()) as updated_at
FROM dblink('dbname=$V5_DB user=$DB_USER password=$DB_PASS host=$DB_HOST',
    'SELECT id, dev_eui, device_type, manufacturer, device_model, status, enabled, display_codes, fport, confirmed_downlinks, created_at, updated_at FROM display_devices WHERE dev_eui IS NOT NULL'
) AS dd(
    id uuid,
    dev_eui varchar,
    device_type varchar,
    manufacturer varchar,
    device_model varchar,
    status varchar,
    enabled boolean,
    display_codes jsonb,
    fport integer,
    confirmed_downlinks boolean,
    created_at timestamp,
    updated_at timestamp
)
ON CONFLICT (dev_eui) DO UPDATE SET
    device_type = EXCLUDED.device_type,
    manufacturer = EXCLUDED.manufacturer,
    model = EXCLUDED.model,
    status = EXCLUDED.status,
    tenant_id = EXCLUDED.tenant_id,
    assigned_space_id = EXCLUDED.assigned_space_id,
    updated_at = NOW();
"

SENSOR_COUNT=$(run_sql $V6_DB "SELECT COUNT(*) FROM sensor_devices;" | grep -o '[0-9]*' | head -1)
DISPLAY_COUNT=$(run_sql $V6_DB "SELECT COUNT(*) FROM display_devices;" | grep -o '[0-9]*' | head -1)
echo "  ✓ Sensor devices in V6: $SENSOR_COUNT"
echo "  ✓ Display devices in V6: $DISPLAY_COUNT"

# ==================================
# Step 8: Verify Migration
# ==================================
echo ""
echo "[8/8] Verifying migration..."

echo ""
echo "V6 Database Final Counts:"
run_sql_query $V6_DB "
SELECT 
    'Tenants: ' || COUNT(*) FROM tenants
UNION ALL
SELECT 'Users: ' || COUNT(*) FROM users
UNION ALL
SELECT 'Sites: ' || COUNT(*) FROM sites
UNION ALL
SELECT 'Spaces: ' || COUNT(*) FROM spaces
UNION ALL
SELECT 'Sensors: ' || COUNT(*) FROM sensor_devices
UNION ALL
SELECT 'Displays: ' || COUNT(*) FROM display_devices;
"

echo ""
echo "Device Ownership Verification:"
run_sql $V6_DB "
SELECT 
    t.name as tenant,
    COUNT(*) as device_count,
    COUNT(*) FILTER (WHERE sd.status = 'assigned') as assigned,
    COUNT(*) FILTER (WHERE sd.status = 'unassigned') as unassigned
FROM sensor_devices sd
JOIN tenants t ON t.id = sd.tenant_id
GROUP BY t.name
ORDER BY device_count DESC;
"

echo ""
echo "=========================================="
echo "Migration Complete!"
echo "=========================================="
echo ""
echo "Backup saved to: $BACKUP_FILE"
echo ""
echo "Next steps:"
echo "1. Verify data in V6 database"
echo "2. Test V6 API with migrated data"
echo "3. Deploy V6 application stack"
echo ""

