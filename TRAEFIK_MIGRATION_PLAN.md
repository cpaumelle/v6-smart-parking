# Traefik Migration from V5 to V6 - Migration Plan

**Date:** 2025-10-23
**Status:** 🔄 **PLANNING PHASE**

---

## 🎯 Current Situation

### V5 Setup (Current - Running)
- **Location:** `/opt/v5-smart-parking/`
- **Network:** `parking-v5_parking-network`
- **Traefik Container:** `parking-traefik`
- **Configuration:**
  - Watching Docker events
  - Network filter: `parking-v2_parking-network` (incorrect legacy config)
  - Actually defaulting to `parking-v5_parking-network`
  - Managing SSL certificates via Let's Encrypt
  - Routing for: devices.verdegris.eu, chirpstack.verdegris.eu, adminer.verdegris.eu, etc.

### V6 Setup (New - Partially Deployed)
- **Location:** `/opt/v6_smart_parking/`
- **Frontend:** Built and containerized ✅
- **Backend API:** Running on `api-v6.verdegris.eu` ✅
- **Frontend URL:** Needs `app.parking.verdegris.eu` ❌
- **Issue:** Traefik not detecting frontend container

---

## 🔍 Root Cause Analysis

### Why Traefik Isn't Detecting Frontend

1. **Network Mismatch**
   - Traefik configured to watch: `parking-v2_parking-network`
   - Frontend is on: `parking-v5_parking-network`
   - Traefik defaults to first available network but doesn't pick up new containers reliably

2. **Compose Project Isolation**
   - V6 frontend deployed via separate docker-compose in `/opt/v6_smart_parking/frontend/`
   - Traefik running from V5 compose in `/opt/v5-smart-parking/`
   - Docker Compose creates project-specific labels

3. **Label Discovery**
   - Traefik watches Docker events but may not see containers from different Compose projects
   - Need explicit network specification in labels

---

## 🚀 Migration Strategy

### Option 1: Quick Fix (Immediate - Recommended)
**Add V6 services to V5 docker-compose temporarily**

**Pros:**
- Fastest solution
- Traefik will immediately detect services
- Zero downtime
- Can migrate properly later

**Cons:**
- Mixed V5/V6 in same compose file
- Not clean separation

**Steps:**
1. Add `parking-frontend-v6` service to `/opt/v5-smart-parking/docker-compose.yml`
2. Ensure it uses existing `parking-frontend-v6:latest` image
3. Run `docker compose up -d parking-frontend-v6`
4. Test `https://app.parking.verdegris.eu`

### Option 2: Standalone V6 Traefik (Clean - Medium Term)
**Deploy separate Traefik for V6 with different ports**

**Pros:**
- Clean separation
- Independent management
- Can test without affecting V5

**Cons:**
- Requires different ports or subdomains
- More complex certificate management
- Two Traefik instances running

**Steps:**
1. Create `/opt/v6_smart_parking/deployment/docker-compose.traefik.yml`
2. Configure Traefik on ports 8081/8443 or use SNI routing
3. Deploy V6 services with V6 Traefik
4. Update DNS if needed

### Option 3: Full Migration (Long Term - Best Practice)
**Migrate everything to V6 structure**

**Pros:**
- Clean, modern setup
- Single source of truth
- Easier to maintain

**Cons:**
- Requires careful planning
- Potential downtime
- Need to migrate all services

**Steps:**
1. Create `/opt/v6_smart_parking/deployment/docker-compose.full.yml`
2. Include Traefik, all V6 services, and kept V5 services
3. Migrate network to `parking-v6_parking-network`
4. Test thoroughly
5. Cutover during maintenance window

---

## 📋 Recommended Approach

### Phase 1: Immediate Fix (Today)
**Get frontend working ASAP**

```bash
# Option A: Add to V5 compose (fastest)
cd /opt/v5-smart-parking
# Edit docker-compose.yml to add parking-frontend-v6 service
docker compose up -d parking-frontend-v6

# Option B: Fix network detection
# Update Traefik command to watch both projects
docker compose down traefik
# Edit Traefik config
docker compose up -d traefik
```

### Phase 2: V6 Deployment Structure (This Week)
**Create proper V6 deployment setup**

1. **Create V6 deployment directory structure:**
```
/opt/v6_smart_parking/deployment/
├── docker-compose.yml              # Main V6 services
├── docker-compose.traefik.yml      # Traefik (shared or separate)
├── docker-compose.override.yml     # Local overrides
├── .env                            # Environment variables
├── config/
│   ├── traefik/
│   │   ├── traefik.yml            # Static config
│   │   └── dynamic/               # Dynamic config
│   └── nginx/                      # Any nginx configs
└── certs/                          # SSL certificates
```

2. **Services to include:**
   - ✅ V6 Backend API (already running)
   - ✅ V6 Frontend (built, needs routing)
   - Shared Traefik (or new V6 Traefik)
   - Shared PostgreSQL (keep V5 setup)
   - Shared Redis (keep V5 setup)
   - Shared ChirpStack (keep V5 setup)

### Phase 3: Full Migration (Next Month)
**Complete V5 → V6 migration**

1. Migrate remaining V5 services
2. Consolidate into single deployment
3. Update all DNS records
4. Decommission V5
5. Clean up old containers/networks

---

## 🔧 Implementation Plan

### Step 1: Get Frontend Working (Now)

#### Solution A: Add to V5 Compose (Recommended for Speed)
```yaml
# Add to /opt/v5-smart-parking/docker-compose.yml
  parking-frontend-v6:
    image: parking-frontend-v6:latest
    container_name: parking-frontend-v6
    restart: unless-stopped
    networks:
      - parking-network
    labels:
      - "traefik.enable=true"
      - "traefik.http.routers.parking-frontend-v6.rule=Host(`app.parking.verdegris.eu`)"
      - "traefik.http.routers.parking-frontend-v6.entrypoints=websecure"
      - "traefik.http.routers.parking-frontend-v6.tls=true"
      - "traefik.http.routers.parking-frontend-v6.tls.certresolver=letsencrypt"
      - "traefik.http.services.parking-frontend-v6.loadbalancer.server.port=80"
```

#### Solution B: Fix Traefik Network Detection
```yaml
# Update Traefik command in /opt/v5-smart-parking/docker-compose.yml
command:
  - --providers.docker=true
  - --providers.docker.exposedbydefault=false
  # Remove network filter OR fix it
  # - --providers.docker.network=parking-v5_parking-network
```

### Step 2: Create V6 Deployment
```bash
mkdir -p /opt/v6_smart_parking/deployment/{config/traefik/dynamic,certs}

# Create comprehensive docker-compose.yml
cat > /opt/v6_smart_parking/deployment/docker-compose.yml <<'EOF'
version: '3.8'

services:
  # V6 Backend API (already configured)
  api-v6:
    # ... existing config ...

  # V6 Frontend
  frontend-v6:
    image: parking-frontend-v6:latest
    # ... config ...

  # Option: V6 Traefik (if going separate)
  traefik-v6:
    image: traefik:v3.1
    # ... config ...

networks:
  parking-network:
    external: true
    name: parking-v5_parking-network  # Use existing network for now
EOF
```

### Step 3: Test and Validate
```bash
# Test frontend
curl -k https://app.parking.verdegris.eu

# Test backend
curl -k https://api-v6.verdegris.eu/health

# Check Traefik dashboard
curl http://localhost:8090/api/http/routers | jq

# Verify certificates
echo | openssl s_client -connect app.parking.verdegris.eu:443 -servername app.parking.verdegris.eu 2>/dev/null | grep -A 2 "Certificate chain"
```

---

## 🎯 Success Criteria

### Immediate (Today)
- [ ] Frontend accessible at https://app.parking.verdegris.eu
- [ ] SSL certificate valid
- [ ] Login page loads
- [ ] No Traefik errors in logs

### Short Term (This Week)
- [ ] V6 deployment structure created
- [ ] All V6 services in one docker-compose
- [ ] Documentation updated
- [ ] Monitoring in place

### Long Term (This Month)
- [ ] V5 services migrated or documented
- [ ] Single Traefik instance
- [ ] Clean network structure
- [ ] Automated deployment scripts

---

## 📝 Configuration Files Needed

### 1. Traefik Static Configuration
```yaml
# /opt/v6_smart_parking/deployment/config/traefik/traefik.yml
api:
  dashboard: true

entryPoints:
  web:
    address: ":80"
    http:
      redirections:
        entryPoint:
          to: websecure
          scheme: https
  websecure:
    address: ":443"

providers:
  docker:
    endpoint: "unix:///var/run/docker.sock"
    exposedByDefault: false
    network: parking-v6_parking-network
    watch: true
  file:
    directory: /etc/traefik/dynamic
    watch: true

certificatesResolvers:
  letsencrypt:
    acme:
      email: admin@verdegris.eu
      storage: /letsencrypt/acme.json
      tlsChallenge: {}

log:
  level: INFO
```

### 2. Dynamic Configuration (Optional)
```yaml
# /opt/v6_smart_parking/deployment/config/traefik/dynamic/middlewares.yml
http:
  middlewares:
    admin-auth:
      basicAuth:
        users:
          - "admin:$apr1$..."  # htpasswd generated

    security-headers:
      headers:
        frameDeny: true
        contentTypeNosniff: true
        browserXssFilter: true

    rate-limit:
      rateLimit:
        average: 100
        burst: 50
```

---

## 🚨 Risks & Mitigation

### Risk 1: Certificate Issues
**Problem:** Let's Encrypt rate limits, certificate conflicts
**Mitigation:**
- Use staging environment first
- Keep existing certificates
- Monitor certificate expiry

### Risk 2: Network Conflicts
**Problem:** Services can't communicate across networks
**Mitigation:**
- Use external network (existing parking-v5_parking-network)
- Test connectivity before switching
- Keep rollback plan ready

### Risk 3: Downtime During Migration
**Problem:** Services unavailable during cutover
**Mitigation:**
- Blue-green deployment
- Keep V5 running during V6 setup
- Test thoroughly before switching DNS

### Risk 4: Port Conflicts
**Problem:** Multiple Traefik instances competing for ports
**Mitigation:**
- Use different ports for V6 Traefik if running separate
- Or ensure only one Traefik runs on 80/443
- Use Docker network isolation

---

## 📊 Decision Matrix

| Criteria | Option 1: Add to V5 | Option 2: Separate V6 | Option 3: Full Migration |
|----------|---------------------|----------------------|-------------------------|
| **Speed** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |
| **Cleanliness** | ⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Risk** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐ |
| **Maintenance** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Effort** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐ |

**Recommendation:** Start with Option 1, then migrate to Option 3 over time.

---

## 🎬 Next Actions

### Immediate (Next 30 minutes)
1. ✅ Stop standalone frontend container
2. Add frontend service to V5 docker-compose.yml
3. Deploy frontend from V5 compose
4. Test https://app.parking.verdegris.eu
5. Document what was done

### Today
1. Create V6 deployment directory structure
2. Document all V6 services
3. Plan network migration
4. Update architecture documentation

### This Week
1. Create comprehensive V6 docker-compose
2. Test V6 deployment independently
3. Plan V5 service migration
4. Create deployment scripts

---

**Status:** Ready to proceed with Option 1 (Quick Fix)
**Blocker:** None
**Next Step:** Add frontend to V5 compose and test

