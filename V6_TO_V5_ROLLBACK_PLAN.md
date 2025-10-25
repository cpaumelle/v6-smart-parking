# V6 to V5 Rollback Plan

**Date**: 2025-10-25
**Purpose**: Complete V6 shutdown, GitHub archival, and V5 restoration
**Status**: Ready for Execution
**Decision**: Full V6 decommission - moving entirely back to V5

---

## Executive Summary

This plan outlines the steps to:
1. Archive V6 development work to GitHub (permanent record)
2. Completely shut down and remove all V6 services
3. Restore V5 to full production operation
4. Clean up V6 infrastructure while preserving data snapshots

---

## Current State Assessment

### V6 Services (To Be Stopped)
```
Running V6 Containers:
- parking-api-v6 (Backend API)
- parking-frontend-v6 (Frontend - Build 48)
- parking-postgres-v6 (Database)
- parking-redis-v6 (Cache)
- parking-adminer-v6 (Database admin)
```

### V5 Infrastructure Location
```
Primary: /opt/parking-infrastructure
GitHub: https://github.com/cpaumelle/smart-parking-platform/tree/feature/multi-tenancy-v5.3
```

---

## Phase 1: V6 Documentation & GitHub Archive

### 1.1 Document Current V6 State
**Time**: 10 minutes

Create comprehensive snapshot:
```bash
cd /opt/v6_smart_parking

# Document running containers
docker ps --filter "name=v6" > V6_RUNNING_STATE.txt

# Document V6 database schema (final snapshot)
docker exec parking-postgres-v6 pg_dump -U parking_user -d parking_v6 --schema-only > database/v6_schema_final.sql

# Optional: Export sample data for reference
docker exec parking-postgres-v6 pg_dump -U parking_user -d parking_v6 --data-only --table=alembic_version > database/v6_migrations_state.sql

# List all V6 volumes
docker volume ls | grep v6 > V6_VOLUMES.txt

# Document achievements
cat > V6_FINAL_STATUS.md << 'EOF'
# V6 Development - Final Status

**Date Archived**: 2025-10-25
**Final Build**: Build 48
**Status**: Development frozen, moving back to V5

## Accomplishments

### ✅ Phase 1: Frontend Simplification (95% Complete)
- Removed WebSocket entirely (100% code reduction)
- Consolidated API client (70% code reduction)
- Migrated from Zustand to React Context (67% state management reduction)
- Build 48 deployed and tested successfully
- Simplified component structure

### ⏸️ Phase 2: Backend Simplification (Not Started)
- Planned but not implemented due to rollback decision

### ⏸️ Phase 3: Infrastructure Simplification (Not Started)
- Planned but not implemented due to rollback decision

## Key Learnings
- Frontend simplification proved effective
- Build times improved with reduced dependencies
- React Context sufficient for application state needs
- Decision made to return to stable V5 production environment

## Archive Location
- GitHub: [Repository URL to be added after push]
- Local backup: /opt/archives/v6_smart_parking_[timestamp].tar.gz
EOF
```

### 1.2 Commit All V6 Work to Git
**Time**: 5 minutes

```bash
cd /opt/v6_smart_parking

# Ensure all changes are committed
git add .
git status

# Create final commit
git commit -m "Final V6 state before rollback to V5

- Frontend simplification Phase 1 complete (Build 48)
- WebSocket removal complete
- API client consolidation complete
- State management migrated to React Context
- Archiving V6 development, returning to V5 production

This represents the final state of the V6 simplification effort.
All services will be shut down and V5 will be restored."

# Create archive tag
git tag -a v6-archive-2025-10-25 -m "V6 development archived - returning to V5"
```

### 1.3 Push V6 to GitHub Archive
**Time**: 5 minutes

```bash
cd /opt/v6_smart_parking

# Verify remote repository
git remote -v

# Push all commits
git push origin main

# Push archive tag
git push origin v6-archive-2025-10-25

# Verify push succeeded
git log --oneline -5
```

### 1.4 Create Local Backup Archive
**Time**: 5 minutes

```bash
# Create timestamped archive
cd /opt
tar -czf v6_smart_parking_archive_$(date +%Y%m%d_%H%M%S).tar.gz v6_smart_parking/

# Store in safe location
mkdir -p /opt/archives
mv v6_smart_parking_archive_*.tar.gz /opt/archives/

# Verify archive integrity
ls -lh /opt/archives/v6_smart_parking_*.tar.gz
tar -tzf /opt/archives/v6_smart_parking_*.tar.gz | head -20

echo "✅ V6 archived to GitHub and local backup created"
```

---

## Phase 2: Complete V6 Services Shutdown & Cleanup

### 2.1 Stop All V6 Services via Docker Compose
**Time**: 3 minutes

```bash
cd /opt/v6_smart_parking

# Stop all V6 services gracefully
docker-compose down

# Verify all containers stopped and removed
docker ps -a | grep v6

# Expected: No v6 containers should be listed
```

### 2.2 Remove V6 Docker Images (Optional - Save Space)
**Time**: 2 minutes

```bash
# List V6 images
docker images | grep -E "(parking.*v6|v6_smart_parking)"

# Remove V6 images to reclaim disk space
# (Can always rebuild from GitHub archive if needed)
docker rmi parking-frontend-v6 || true
docker rmi parking-api-v6 || true
docker rmi v6_smart_parking-frontend || true
docker rmi v6_smart_parking-api || true

# Clean up dangling images
docker image prune -f
```

### 2.3 Handle V6 Data Volumes
**Time**: 5 minutes

**Decision Point**: Choose one approach:

**Option A: Keep V6 volumes (safer, uses disk space)**
```bash
# List V6 volumes for documentation only
docker volume ls | grep v6 > /opt/archives/v6_volumes_preserved.txt

# Volumes preserved:
# - v6_smart_parking_postgres-data
# - v6_smart_parking_redis-data
# - Any other v6-prefixed volumes

echo "✅ V6 volumes preserved - can be removed later if needed"
```

**Option B: Remove V6 volumes (clean slate, saves ~500MB-2GB)**
```bash
# ONLY if certain you don't need V6 data
# Database schema already exported to git in Phase 1.1

# List volumes to remove
docker volume ls | grep v6

# Remove V6 volumes
docker volume rm v6_smart_parking_postgres-data || true
docker volume rm v6_smart_parking_redis-data || true
docker volume prune -f

echo "✅ V6 volumes removed - V6 fully cleaned up"
```

**Recommendation**: Use Option A initially. Remove volumes after 30 days if V5 is stable.

### 2.4 Remove V6 Docker Network
**Time**: 1 minute

```bash
# List V6 networks
docker network ls | grep v6

# Remove V6 network
docker network rm v6_smart_parking_default || true

# Verify removal
docker network ls | grep v6
# Expected: No results
```

### 2.5 Final V6 Cleanup Verification
**Time**: 2 minutes

```bash
# Comprehensive check - all should return empty
echo "=== V6 Containers ==="
docker ps -a | grep v6

echo "=== V6 Images ==="
docker images | grep v6

echo "=== V6 Networks ==="
docker network ls | grep v6

echo "=== V6 Volumes (may still exist if Option A chosen) ==="
docker volume ls | grep v6

echo "✅ V6 infrastructure shutdown complete"
```

---

## Phase 3: V5 Verification & Preparation

### 3.1 Verify V5 Code Exists
**Time**: 5 minutes

```bash
# Check V5 infrastructure directory
ls -la /opt/parking-infrastructure/

# Expected structure:
# - docker-compose.yml (V5 services)
# - backend/ (V5 API code)
# - frontend/ (V5 UI code)
# - database/ (V5 schema)
# - config/ (Traefik, etc.)

# Check git status
cd /opt/parking-infrastructure
git status
git branch
git log --oneline -10
```

### 3.2 Check V5 GitHub Repository
**Time**: 5 minutes

```bash
# Verify remote is accessible
cd /opt/parking-infrastructure
git remote -v

# Fetch latest from feature/multi-tenancy-v5.3
git fetch origin feature/multi-tenancy-v5.3

# Check if local is up to date
git status
```

### 3.3 Review V5 Docker Compose Configuration
**Time**: 5 minutes

```bash
# Check V5 services configuration
cd /opt/parking-infrastructure
cat docker-compose.yml | grep -E "(container_name|image:)" | head -30

# Expected V5 services:
# - parking-postgres (V5 database)
# - parking-redis (V5 cache)
# - parking-api (V5 backend)
# - parking-frontend (V5 UI)
# - parking-traefik (reverse proxy)
# - parking-chirpstack
# - parking-mosquitto
# - parking-gateway-bridge
```

### 3.4 Check V5 Database Volume
**Time**: 2 minutes

```bash
# List existing volumes
docker volume ls | grep parking

# Expected V5 volumes:
# - parking_postgres-data (V5 database - should still exist)
# - parking_redis-data
# - parking_chirpstack-data
# - parking_mosquitto-data
```

---

## Phase 4: V5 Services Startup

### 4.1 Start V5 Database First
**Time**: 3 minutes

```bash
cd /opt/parking-infrastructure

# Start PostgreSQL
docker-compose up -d postgres

# Wait for database to be ready
sleep 10

# Check health
docker-compose ps postgres
docker logs parking-postgres --tail 50
```

### 4.2 Start V5 Supporting Services
**Time**: 5 minutes

```bash
# Start Redis
docker-compose up -d redis

# Start MQTT/ChirpStack
docker-compose up -d mosquitto chirpstack gateway-bridge

# Verify all started
docker-compose ps
```

### 4.3 Start V5 Backend API
**Time**: 3 minutes

```bash
# Start V5 API
docker-compose up -d api

# Check logs for startup
docker logs parking-api --tail 100

# Wait for healthy status
sleep 10
docker-compose ps api
```

### 4.4 Start V5 Frontend
**Time**: 3 minutes

```bash
# Start V5 frontend
docker-compose up -d frontend

# Check logs
docker logs parking-frontend --tail 50

# Verify nginx started
docker-compose ps frontend
```

### 4.5 Start V5 Reverse Proxy (Traefik)
**Time**: 2 minutes

```bash
# Start Traefik
docker-compose up -d traefik

# Check routing
docker logs parking-traefik --tail 50
```

### 4.6 Verify All V5 Services Running
**Time**: 5 minutes

```bash
# Check all services status
docker-compose ps

# Expected output: All services "Up" and "healthy"

# Check Docker networks
docker network ls | grep parking

# Test internal connectivity
docker exec parking-api curl -s http://parking-postgres:5432 || echo "DB not reachable"
```

---

## Phase 5: V5 Functionality Testing

### 5.1 Test V5 API Health
**Time**: 5 minutes

```bash
# Test health endpoint
curl -s https://api.verdegris.eu/health

# Test API docs (should be accessible)
curl -s https://api.verdegris.eu/docs | head -50

# Test authentication
curl -X POST https://api.verdegris.eu/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@example.com","password":"<password>"}' \
  | jq
```

### 5.2 Test V5 Frontend Access
**Time**: 5 minutes

```bash
# Check frontend is serving
curl -s https://app.parking.verdegris.eu | grep -i "title"

# Check version endpoint (if exists)
curl -s https://app.parking.verdegris.eu/version.json || echo "No version file"

# Manual browser test:
# 1. Open https://app.parking.verdegris.eu
# 2. Login with V5 credentials
# 3. Verify dashboard loads
# 4. Check sites/spaces management
# 5. Verify real-time data updates
```

### 5.3 Test ChirpStack Integration
**Time**: 5 minutes

```bash
# Check ChirpStack is accessible
curl -s http://localhost:8080 || echo "ChirpStack not accessible"

# Check webhook endpoint is responding
curl -X POST https://api.verdegris.eu/api/webhooks/chirpstack \
  -H "Content-Type: application/json" \
  -d '{"test": true}' \
  -w "\nHTTP_CODE: %{http_code}\n"

# Check MQTT broker
docker exec parking-mosquitto mosquitto_sub -t '#' -C 1 -W 5 || echo "MQTT not responding"
```

### 5.4 Verify Database Connectivity
**Time**: 3 minutes

```bash
# Test database connection
docker exec parking-postgres psql -U <username> -d <dbname> -c "SELECT COUNT(*) FROM sites;"

# Check recent data
docker exec parking-postgres psql -U <username> -d <dbname> -c "SELECT * FROM spaces ORDER BY updated_at DESC LIMIT 5;"
```

---

## Phase 6: DNS/Routing Verification

### 6.1 Check Traefik Routing
**Time**: 5 minutes

```bash
# Check Traefik configuration
cat /opt/parking-infrastructure/config/traefik/dynamic.yml | grep -A 10 "app.parking"

# Verify routing rules
docker logs parking-traefik | grep -i "router"

# Expected routes:
# - app.parking.verdegris.eu -> parking-frontend (V5)
# - api.verdegris.eu -> parking-api (V5)
```

### 6.2 Test Public Access
**Time**: 5 minutes

```bash
# Test from external perspective
curl -s https://app.parking.verdegris.eu -I | grep HTTP

# Test API from external
curl -s https://api.verdegris.eu/health

# DNS check
nslookup app.parking.verdegris.eu
nslookup api.verdegris.eu
```

---

## Phase 7: Monitoring & Validation

### 7.1 Check Logs for Errors
**Time**: 10 minutes

```bash
# Check all V5 service logs
docker-compose logs --tail=100 | grep -i error

# Check specific services
docker logs parking-api --tail 100 | grep -i error
docker logs parking-frontend --tail 100 | grep -i error
docker logs parking-postgres --tail 100 | grep -i error
```

### 7.2 Monitor Resource Usage
**Time**: 5 minutes

```bash
# Check container resource usage
docker stats --no-stream

# Check disk usage
df -h

# Check volume usage
docker system df -v | grep parking
```

### 7.3 Verify No V6 Interference
**Time**: 3 minutes

```bash
# Ensure NO v6 containers running
docker ps | grep v6

# Ensure V5 is using correct ports
docker ps --format "table {{.Names}}\t{{.Ports}}" | grep parking

# Check network conflicts
docker network inspect parking-network | grep -i container
```

---

## Phase 8: Documentation & Handoff

### 8.1 Update Status Documentation
**File**: `/opt/V5_RESTORATION_STATUS.md`

Document:
- Date/time of V5 restoration
- All V5 services confirmed running
- V6 services confirmed stopped
- Test results summary
- Any issues encountered

### 8.2 Create Operational Checklist
**File**: `/opt/V5_DAILY_OPERATIONS.md`

Include:
- How to check V5 service health
- How to restart services if needed
- Log locations
- Backup procedures
- Emergency contacts

### 8.3 Archive V6 Work Summary
**File**: `/opt/v6_smart_parking/V6_LESSONS_LEARNED.md`

Document:
- What was accomplished in V6
- Why rollback was needed
- Technical insights gained
- Recommendations for future

---

## Rollback Decision Tree

### If V5 Fails to Start:

**Problem**: Database won't start
```bash
# Check volume exists
docker volume ls | grep postgres-data

# Check permissions
docker exec parking-postgres ls -la /var/lib/postgresql/data

# Review logs
docker logs parking-postgres

# Last resort: Restore from backup
```

**Problem**: API won't connect to database
```bash
# Check network
docker network inspect parking-network

# Check environment variables
docker exec parking-api env | grep DATABASE

# Restart services in order
docker-compose restart postgres
sleep 10
docker-compose restart api
```

**Problem**: Frontend shows 404/500 errors
```bash
# Check API is accessible
curl http://parking-api:8000/health

# Check Traefik routing
docker logs parking-traefik | grep frontend

# Restart frontend
docker-compose restart frontend
```

### If Cannot Restore V5:

**Emergency Plan**:
1. Restore V6 temporarily:
   ```bash
   cd /opt/v6_smart_parking
   docker-compose up -d
   ```

2. Contact support with:
   - Error messages from logs
   - Output of `docker-compose ps`
   - Output of `docker volume ls`

3. Restore from latest backup if available

---

## Timeline Estimate

| Phase | Duration | Cumulative |
|-------|----------|------------|
| 1. V6 Documentation & GitHub Archive | 25 min | 25 min |
| 2. V6 Complete Shutdown & Cleanup | 13 min | 38 min |
| 3. V5 Verification | 17 min | 55 min |
| 4. V5 Services Startup | 21 min | 76 min |
| 5. V5 Functionality Testing | 18 min | 94 min |
| 6. DNS/Routing Verification | 10 min | 104 min |
| 7. Monitoring & Validation | 18 min | 122 min |
| 8. Documentation | 10 min | 132 min |

**Total Estimated Time**: ~2.2 hours
**With contingency**: 3 hours
**Actual downtime**: 10-15 minutes (V6 stop → V5 start)

---

## Risk Assessment

### Low Risk
- ✅ V5 code exists in /opt/parking-infrastructure
- ✅ V5 database volume should be preserved
- ✅ V5 and V6 use different container names (no conflicts)
- ✅ Docker networks are isolated

### Medium Risk
- ⚠️ V5 database might need migrations if schema changed
- ⚠️ Environment variables might need updating
- ⚠️ ChirpStack webhooks might need reconfiguration

### High Risk Items
- 🔴 If V5 database volume was deleted (check first!)
- 🔴 If V5 code has uncommitted changes
- 🔴 If credentials/secrets were lost

---

## Pre-Execution Checklist

Before starting rollback:

- [ ] Verify V5 code exists: `ls -la /opt/parking-infrastructure`
- [ ] Verify V5 database volume exists: `docker volume ls | grep parking_postgres-data`
- [ ] Verify V5 GitHub accessible: `git ls-remote https://github.com/cpaumelle/smart-parking-platform`
- [ ] Have V5 credentials/secrets available
- [ ] Verify V6 GitHub repository is accessible (for final push)
- [ ] Check V6 git status - all work committed: `cd /opt/v6_smart_parking && git status`
- [ ] Notify users of maintenance window (if applicable)
- [ ] Decide on volume cleanup strategy (Option A: keep, Option B: remove)
- [ ] Emergency plan: V6 can be restored from GitHub archive if needed

---

## Success Criteria

V5 restoration is successful when:

1. ✅ All V5 containers showing "Up" and "healthy"
2. ✅ https://app.parking.verdegris.eu loads V5 frontend
3. ✅ https://api.verdegris.eu/health returns 200 OK
4. ✅ User can login to V5 interface
5. ✅ Dashboard shows live parking data
6. ✅ ChirpStack webhook delivers sensor data
7. ✅ No errors in service logs
8. ✅ All V6 containers confirmed stopped
9. ✅ V6 work archived safely

---

## Post-Restoration Tasks

After successful V5 restoration:

1. **Day 1-7**: Monitor V5 stability daily
   - Check logs: `cd /opt/parking-infrastructure && docker-compose logs --tail=100`
   - Verify sensor data flowing: ChirpStack webhooks working
   - Confirm no performance issues

2. **Day 7-30**: Verify all features working as expected
   - Multi-tenancy working correctly
   - All sites/spaces visible and functional
   - Mobile responsiveness maintained
   - User access controls functioning

3. **Day 30**: Decide on V6 volume cleanup
   - If V5 stable and no issues: `docker volume rm v6_smart_parking_postgres-data v6_smart_parking_redis-data`
   - This saves ~1-2GB disk space
   - V6 code remains in GitHub archive

4. **Optional**: Archive /opt/v6_smart_parking directory
   - After GitHub push verified: `rm -rf /opt/v6_smart_parking`
   - Code preserved in GitHub at v6-archive-2025-10-25 tag
   - Local tar.gz backup in /opt/archives/

---

## Contact Information

**For Issues During Rollback**:
- Check logs first: `docker-compose logs`
- Review this document's troubleshooting section
- Document exact error messages
- Check Docker and system resources

---

**Plan Created**: 2025-10-25
**Plan Version**: 2.0 (Updated for complete V6 decommission)
**Status**: Ready for Execution
**Estimated Downtime**: 10-15 minutes (during service restart)

---

## Quick Start Execution

For experienced operators, execute phases in order:

```bash
# Phase 1: Archive V6
cd /opt/v6_smart_parking
docker ps --filter "name=v6" > V6_RUNNING_STATE.txt
docker exec parking-postgres-v6 pg_dump -U parking_user -d parking_v6 --schema-only > database/v6_schema_final.sql
git add . && git commit -m "Final V6 state before rollback to V5" && git tag v6-archive-2025-10-25
git push origin main && git push origin v6-archive-2025-10-25
cd /opt && tar -czf archives/v6_smart_parking_$(date +%Y%m%d_%H%M%S).tar.gz v6_smart_parking/

# Phase 2: Shutdown V6
cd /opt/v6_smart_parking
docker-compose down
docker volume ls | grep v6  # Decide: keep or remove volumes

# Phase 3-4: Start V5
cd /opt/parking-infrastructure
docker-compose up -d postgres && sleep 10
docker-compose up -d redis mosquitto chirpstack gateway-bridge
docker-compose up -d api && sleep 10
docker-compose up -d frontend traefik

# Phase 5-7: Verify
docker-compose ps  # All should be "Up"
curl -s https://api.verdegris.eu/health
curl -s https://app.parking.verdegris.eu | grep title

# Success!
```
