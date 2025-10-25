# Complete V5 to V6 Migration Plan

**Date:** 2025-10-24
**Goal:** Migrate entire V5 Smart Parking Platform to V6 with zero downtime and clean architecture

---

## Current V5 Stack Analysis

### Infrastructure Services (Keep & Share)
These are platform infrastructure - V6 will continue using them:

| Service | Container | Purpose | V6 Status |
|---------|-----------|---------|-----------|
| **Traefik** | parking-traefik | Reverse proxy, SSL, routing | ✅ **KEEP - Shared** |
| **PostgreSQL** | parking-postgres | Database server | ✅ **KEEP - Shared** |
| **Redis** | parking-redis | Cache & queue | ✅ **KEEP - Shared** |
| **ChirpStack** | parking-chirpstack | LoRaWAN network server | ✅ **KEEP - Shared** |
| **Mosquitto** | parking-mosquitto | MQTT broker | ✅ **KEEP - Shared** |
| **Gateway Bridge** | parking-gateway-bridge | LoRa packet forwarder | ✅ **KEEP - Shared** |

### Application Services (Replace with V6)

| Service | Container | Purpose | V6 Replacement |
|---------|-----------|---------|----------------|
| **V5 API** | parking-api | FastAPI backend | 🔄 **parking-api-v6** (new code) |
| **Device Manager UI** | parking-device-manager | Device assignment UI | 🔄 **Integrated into V6 frontend** |
| **Adminer** | parking-adminer | DB admin tool | 🔄 **parking-adminer-v6** (separate instance) |
| **Filebrowser** | parking-filebrowser | File management | 🔄 **parking-filebrowser-v6** (separate instance) |

### Legacy/Deprecated Services (Remove)

| Service | Container | Purpose | Action |
|---------|-----------|---------|--------|
| **Website** | parking-website | Old marketing site | ❌ **REMOVE** (unhealthy, unused) |
| **Kuando UI** | parking-kuando-ui | Old status light UI | ❌ **REMOVE** (unhealthy, unused) |
| **Contact API** | parking-contact-api | Contact form API | ❌ **REMOVE** (unhealthy, unused) |

---

## Database Migration Strategy

### Current Databases

```
parking-postgres (shared server)
├── chirpstack       → ChirpStack LoRaWAN (KEEP)
├── parking_v5       → V5 application data (MIGRATE → V6)
├── parking_v6       → V6 application data (TARGET)
└── parking_platform → Unknown/legacy (INVESTIGATE → DROP?)
```

### Data to Migrate

| Table | V5 Count | Action |
|-------|----------|--------|
| tenants | 4 | Merge into V6 (already has 8) |
| users | 3 | Migrate with updated schema |
| sites | 7 | Migrate (V6 has 3, check duplicates) |
| spaces | 5 | Migrate (V6 has 9, check duplicates) |
| **sensor_devices** | **13** | **CRITICAL: V6 has 0!** |
| **display_devices** | ? | Check count and migrate |
| reservations | ? | Check and migrate |
| state_changes | ? | Migrate recent history |

### Migration Challenges

1. **Schema Differences:**
   - V6 adds `tenant_id` to ALL tables (devices, gateways, etc.)
   - V6 has new `lifecycle_state` column
   - V6 has `device_assignments` history table
   - V6 uses `deleted_at` instead of `archived_at`

2. **Device Ownership:**
   - V5: Devices indirectly linked via `spaces → sites → tenants`
   - V6: Devices have direct `tenant_id` foreign key
   - **Solution:** Backfill tenant_id from space assignments, orphans → platform tenant

3. **Gateways:**
   - V5: Gateways only in ChirpStack DB
   - V6: Gateways replicated in `parking_v6.gateways` table with tenant ownership
   - **Solution:** Import from ChirpStack into V6 schema

---

## V6 Docker Compose Architecture

### Proposed Structure

```yaml
version: '3.8'

# V6-only services (NOT duplicating infrastructure)
services:
  api-v6:
    build: ./backend
    container_name: parking-api-v6
    networks:
      - parking-v5_parking-network  # Connect to V5 network for shared infra
    environment:
      DATABASE_URL: postgresql://parking_user:parking@parking-postgres/parking_v6
      REDIS_URL: redis://parking-redis:6379/1  # Different DB than V5
      CHIRPSTACK_HOST: parking-chirpstack:8080
    labels:
      - "traefik.http.routers.api-v6.rule=Host(`api-v6.verdegris.eu`)"
    depends_on:
      - [No postgres/redis here - use V5's shared instances]

  frontend-v6:
    build: ./frontend
    container_name: parking-frontend-v6
    networks:
      - parking-v5_parking-network
    labels:
      - "traefik.http.routers.frontend-v6.rule=Host(`parking.eroundit.eu`)"

  adminer-v6:
    image: adminer:latest
    container_name: parking-adminer-v6
    networks:
      - parking-v5_parking-network
    labels:
      - "traefik.http.routers.adminer-v6.rule=Host(`db-v6.verdegris.eu`)"

networks:
  parking-v5_parking-network:
    external: true  # Use existing V5 network

# NO VOLUMES - use V5's existing Postgres/Redis volumes
```

**Key Design Decision:** V6 docker-compose ONLY creates application containers, not infrastructure.

---

## Migration Phases

### Phase 1: Database Migration (THIS FIRST)

**Goal:** Populate `parking_v6` database with production data

**Steps:**
1. ✅ Verify V6 schema exists (DONE)
2. Create migration script:
   ```sql
   -- Add tenant_id to V5 devices based on space assignments
   -- Copy V5 data to V6 with schema transformations
   -- Backfill new V6 columns
   -- Import gateways from ChirpStack
   ```
3. Test migration on backup
4. Run migration to populate V6
5. Verify data integrity

**Deliverable:** `parking_v6` database fully populated with production data

### Phase 2: Deploy V6 Application Stack

**Goal:** Get V6 API and Frontend running alongside V5

**Steps:**
1. Update V6 docker-compose.yml (use external V5 network)
2. Deploy V6 containers:
   ```bash
   cd /opt/v6_smart_parking
   docker compose up -d api-v6 frontend-v6 adminer-v6
   ```
3. Configure Traefik routes for V6
4. Test V6 API endpoints
5. Test V6 Frontend login

**Deliverable:** V6 running in parallel with V5

### Phase 3: Cutover & Testing

**Goal:** Switch production traffic to V6

**Steps:**
1. Configure Traefik to route to V6 (change priority/rules)
2. Monitor V6 performance and errors
3. Keep V5 running but idle for rollback
4. Test all V6 functionality:
   - Login/Authentication
   - Device management
   - Space management
   - Reservations
   - Real-time updates via WebSocket
   - ChirpStack webhook delivery

**Deliverable:** V6 serving production traffic

### Phase 4: Cleanup & Decommission V5

**Goal:** Remove V5 once V6 is stable

**Steps:**
1. Stop V5 containers:
   ```bash
   docker compose stop api device-manager-ui website kuando-ui contact-api
   ```
2. Drop V5 database:
   ```sql
   DROP DATABASE parking_v5;
   DROP DATABASE parking_platform;  -- if unused
   ```
3. Remove V5 containers:
   ```bash
   docker compose rm -f api device-manager-ui website kuando-ui contact-api
   ```
4. Clean up V5 code directory (optional backup first)

**Deliverable:** Clean V6-only environment

---

## Rollback Plan

At any phase, we can rollback:

### If Phase 1 Fails (Database Migration)
- V6 database migration is non-destructive
- V5 database untouched
- Simply fix migration script and retry

### If Phase 2 Fails (V6 Deployment)
- Stop V6 containers
- V5 continues running normally
- No impact to production

### If Phase 3 Fails (Cutover)
- Change Traefik rules back to V5
- Stop V6 containers if needed
- V5 resumes serving traffic

### If Phase 4 Fails (Cleanup)
- V5 containers can be restarted
- V5 database still exists (not dropped yet)
- Full rollback possible

---

## Success Metrics

### Database Migration Success
- ✅ All V5 tenants present in V6
- ✅ All V5 users migrated
- ✅ All devices have tenant_id assigned
- ✅ 0 devices in platform tenant (unless legitimately unassigned)
- ✅ All spaces migrated with correct device links
- ✅ RLS policies functional

### V6 Application Success
- ✅ API responds on all endpoints
- ✅ Frontend loads and authenticates
- ✅ Dashboard displays real data
- ✅ ChirpStack webhooks being received
- ✅ Real-time updates via WebSocket work
- ✅ Device assignments function correctly

### Infrastructure Health
- ✅ Traefik routing working
- ✅ SSL certificates valid
- ✅ Database connections stable
- ✅ Redis caching functional
- ✅ ChirpStack sync operational

---

## Timeline Estimate

| Phase | Duration | Effort |
|-------|----------|--------|
| Phase 1: Database Migration | 2-3 hours | Create script, test, execute |
| Phase 2: Deploy V6 Stack | 1 hour | docker compose up, verify |
| Phase 3: Cutover & Testing | 2-4 hours | Route switch, thorough testing |
| Phase 4: Cleanup | 30 min | Stop old services, cleanup |
| **TOTAL** | **6-9 hours** | Can be done in one day |

---

## Next Steps

**Immediate Action Items:**

1. ✅ **Confirm Migration Approach** (You're reading this!)
2. 🔄 **Create Database Migration Script**
3. 🔄 **Test Migration on Backup**
4. 🔄 **Execute Migration to Populate V6**
5. 🔄 **Deploy V6 Stack**
6. 🔄 **Test V6 Thoroughly**
7. 🔄 **Cutover to V6**
8. 🔄 **Decommission V5**

---

## Questions to Answer

Before proceeding, confirm:

1. **Is `parking_platform` database needed?**
   - Purpose unclear
   - Can we investigate and drop it?

2. **Are website/kuando-ui/contact-api still needed?**
   - All show as "unhealthy"
   - Appear unused
   - OK to remove?

3. **What data retention policy for V5?**
   - Keep V5 database backup?
   - For how long?
   - Or confident to drop immediately after V6 stable?

4. **Device Manager UI functionality:**
   - V5 has standalone device manager
   - V6 has integrated device management
   - Confirm V6 frontend has all needed features?

---

**Ready to proceed with Phase 1 (Database Migration)?**
