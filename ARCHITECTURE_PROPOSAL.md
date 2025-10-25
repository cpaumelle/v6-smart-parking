# Smart Parking Platform - Architecture Options

## The Question
You correctly identified that website, kuando-ui, and contact-api are NOT dead - they're infrastructure/platform services. So how should we organize everything?

---

## Option 1: Separate Infrastructure Stack (CLEANEST)

### Filesystem Structure
```
/opt/
├── infrastructure/              # NEW - Shared platform
│   ├── docker-compose.yml
│   ├── config/
│   │   ├── traefik/
│   │   ├── chirpstack/
│   │   └── mosquitto/
│   └── .env
│
├── v5-smart-parking/           # V5 Applications only
│   ├── docker-compose.yml      # Just V5 API + device manager
│   ├── backend/
│   └── frontend/
│
└── v6_smart_parking/           # V6 Applications only
    ├── docker-compose.yml      # Just V6 API + frontend
    ├── backend/
    └── frontend/
```

### Infrastructure Stack Services:
- Traefik (reverse proxy)
- Postgres (database server hosting parking_v5, parking_v6, chirpstack DBs)
- Redis (cache - DB 0 for V5, DB 1 for V6)
- ChirpStack + Mosquitto + Gateway Bridge (LoRaWAN)
- Website (marketing site)
- Kuando UI (status lights)
- Contact API (contact forms)
- Adminer (database admin)
- Filebrowser (file manager)

### V5 Application Stack:
- parking-api-v5 (FastAPI backend for V5)
- parking-device-manager-v5 (device management UI)

### V6 Application Stack:
- parking-api-v6 (FastAPI backend for V6)
- parking-frontend-v6 (React admin UI)

**Pros:**
- ✅ Very clean separation
- ✅ Infrastructure independent of applications
- ✅ Easy to add V7, V8, etc. in future
- ✅ Can restart/update apps without touching infrastructure

**Cons:**
- ❌ Requires significant reorganization
- ❌ More complex migration
- ❌ 3 separate docker-compose stacks to manage

---

## Option 2: Infrastructure Stays in V5 (SIMPLER)

### Filesystem Structure
```
/opt/
├── v5-smart-parking/           # Infrastructure + V5 apps
│   ├── docker-compose.yml      # ALL infrastructure + V5 services
│   ├── backend/
│   ├── frontend/
│   └── config/
│
└── v6_smart_parking/           # V6 apps only
    ├── docker-compose.yml      # Just V6 API + frontend
    ├── backend/
    └── frontend/
```

### V5 Stack Contains:
**Infrastructure:**
- Traefik, Postgres, Redis, ChirpStack, Mosquitto, Gateway Bridge
- Website, Kuando UI, Contact API, Adminer, Filebrowser

**V5 Applications:**
- parking-api-v5
- parking-device-manager-v5

### V6 Stack Contains:
**V6 Applications Only:**
- parking-api-v6
- parking-frontend-v6
- Connects to V5's infrastructure via external network

**Pros:**
- ✅ Minimal reorganization
- ✅ Infrastructure already running and stable
- ✅ Simple V6 deployment
- ✅ Can migrate immediately

**Cons:**
- ❌ Infrastructure tied to "V5" name (misleading)
- ❌ Can't fully sunset V5 stack (infrastructure still needed)
- ❌ Less clean separation

---

## Option 3: Hybrid - Rename V5 to Platform (COMPROMISE)

### Filesystem Structure
```
/opt/
├── parking-platform/           # RENAMED from v5-smart-parking
│   ├── docker-compose.yml      # Infrastructure + legacy apps
│   ├── infrastructure/         # Traefik, Postgres, etc.
│   ├── v5-api/                 # V5 API (legacy, will deprecate)
│   ├── website/
│   ├── kuando/
│   └── config/
│
└── v6_smart_parking/           # V6 apps
    ├── docker-compose.yml      # V6 API + frontend
    ├── backend/
    └── frontend/
```

**Pros:**
- ✅ Better naming (not calling infrastructure "V5")
- ✅ Acknowledges these are platform services
- ✅ Still relatively simple migration
- ✅ Clear that infrastructure is separate from V5 app

**Cons:**
- ❌ Still mixing infrastructure with application code
- ❌ Requires renaming/moving V5 directory

---

## My Recommendation

Given your goals:
1. Want to turn off V5 completely
2. Don't want a mess
3. Need infrastructure services (website, kuando, contact-api)

**I recommend Option 3 (Hybrid):**

1. Rename `/opt/v5-smart-parking` → `/opt/parking-platform`
2. This stack contains:
   - ✅ All infrastructure (Traefik, Postgres, ChirpStack, etc.)
   - ✅ Platform services (website, kuando, contact-api)
   - ⚠️ V5 API (legacy, will deprecate after V6 stable)

3. V6 stack at `/opt/v6_smart_parking` contains only V6 application

4. Migration path:
   - Deploy V6 apps
   - Test V6 thoroughly
   - Remove V5 API from platform stack
   - Keep all infrastructure running

This gives you:
- Clean V6 application deployment
- Can "turn off V5" (just the V5 API)
- Infrastructure stays running for V6 and platform services
- Not misleadingly called "V5" anymore

**What do you think?**
