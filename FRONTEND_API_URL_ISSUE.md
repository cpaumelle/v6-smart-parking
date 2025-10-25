# Frontend API URL Issue

**Status:** ⚠️ REQUIRES MANUAL FIX

---

## Issue

The V6 frontend is hardcoded to call `https://api-v6.verdegris.eu` but the actual production API is at `https://api.verdegris.eu`.

This means:
- ❌ Frontend cannot communicate with the backend
- ❌ Login will fail with CORS/network errors
- ❌ All API calls will go to non-existent endpoint

---

## Root Cause

The frontend build process bakes in the `VITE_API_URL` environment variable at **build time**. The value is read from `/frontend/.env` and compiled into the JavaScript bundles.

Current frontend .env:
```
VITE_API_URL=https://api.verdegris.eu  ✅ Correct
```

But the Docker build is caching old values or not picking up the change.

---

## Solutions

### Option 1: Quick Fix - Update API Route (RECOMMENDED)

Instead of changing the frontend, update the API to respond on BOTH URLs:

1. Add `api-v6.verdegris.eu` as an additional route in Traefik
2. Keep `api.verdegris.eu` as primary

```yaml
# In docker-compose.prod.yml
labels:
  - "traefik.http.routers.api.rule=Host(`api.verdegris.eu`) || Host(`api-v6.verdegris.eu`)"
```

### Option 2: Rebuild Frontend Properly

The Dockerfile needs to accept and use build args:

```dockerfile
# In frontend/Dockerfile
ARG VITE_API_URL=https://api.verdegris.eu
ARG VITE_WS_URL=wss://api.verdegris.eu

# Before RUN npm run build
ENV VITE_API_URL=${VITE_API_URL}
ENV VITE_WS_URL=${VITE_WS_URL}
```

Then rebuild:
```bash
docker compose -f docker-compose.prod.yml build --no-cache frontend-v6
docker compose -f docker-compose.prod.yml up -d frontend-v6
```

---

## Recommended Immediate Action

**Use Option 1** - It's faster and doesn't require rebuilding the frontend.

Update `/opt/v6_smart_parking/docker-compose.prod.yml`:

```yaml
api-v6:
  labels:
    - "traefik.http.routers.api.rule=Host(`api.verdegris.eu`) || Host(`api-v6.verdegris.eu`)"
```

Then restart:
```bash
docker compose -f docker-compose.prod.yml up -d api-v6
```

This makes the API respond on both URLs, so the frontend will work immediately.

---

## Verification

After implementing Option 1, test:

```bash
# Should return same response
curl -k https://api.verdegris.eu/health
curl -k https://api-v6.verdegris.eu/health
```

Both should return:
```json
{"status":"healthy","version":"6.0.0"}
```

Then test frontend login at `https://parking.eroundit.eu`

---

## Long-term Fix

For production cleanliness, eventually rebuild the frontend with the correct URL using Option 2.
