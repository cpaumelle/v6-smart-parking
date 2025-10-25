# V6 Simplification Implementation Plan

**Goal**: Transform the over-engineered V6 system into a simple, maintainable multi-tenant parking management system

**Timeline**: 3 weeks (1 developer)
**Start Date**: 2025-10-25
**Completion Target**: 2025-11-15

---

## Overview

This plan transforms the current complex V6 implementation into a simple system appropriate for:
- 5-10 tenants (customers)
- 10-20 total users (platform admins + tenant admins)
- Clear hierarchy: Tenant → Sites → Spaces → Sensors
- Simple HTTP polling instead of WebSocket
- 5 Docker containers instead of 15
- Easy to maintain and debug

---

## Phase 1: Frontend Simplification (Week 1)

### Day 1-2: Remove WebSocket, Add Simple Polling

**Goal**: Replace complex WebSocket implementation with simple HTTP polling

#### Tasks

**1.1 Create Simple Polling Hook** (2 hours)
```javascript
// frontend/src/hooks/usePolling.js
import { useState, useEffect, useCallback } from 'react';

export function usePolling(fetchFn, interval = 30000, enabled = true) {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  const fetch = useCallback(async () => {
    if (!enabled) return;

    try {
      setLoading(true);
      const result = await fetchFn();
      setData(result);
      setError(null);
    } catch (err) {
      setError(err);
      console.error('Polling error:', err);
    } finally {
      setLoading(false);
    }
  }, [fetchFn, enabled]);

  useEffect(() => {
    // Initial fetch
    fetch();

    // Set up polling
    if (enabled) {
      const intervalId = setInterval(fetch, interval);
      return () => clearInterval(intervalId);
    }
  }, [fetch, interval, enabled]);

  return { data, loading, error, refetch: fetch };
}
```

**1.2 Update Dashboard to Use Polling** (3 hours)
```javascript
// frontend/src/modules/operations/Dashboard.jsx
import { usePolling } from '../../hooks/usePolling';
import { dashboardApi } from '../../services/api/dashboardApi';

export function Dashboard() {
  const { data: dashboardData, loading, refetch } = usePolling(
    () => dashboardApi.getData(),
    30000 // Poll every 30 seconds
  );

  return (
    <div>
      <Button onClick={refetch}>Refresh Now</Button>
      {loading && <Spin />}
      {dashboardData && (
        <>
          <OccupancyStats data={dashboardData.occupancy} />
          <SitesList sites={dashboardData.sites} />
        </>
      )}
    </div>
  );
}
```

**1.3 Remove WebSocket Code** (1 hour)
- [ ] Delete `frontend/src/utils/hooks/useWebSocket.ts`
- [ ] Remove WebSocket imports from all components
- [ ] Remove `VITE_WS_URL` from environment variables
- [ ] Update all real-time components to use polling hook

**1.4 Test Polling** (2 hours)
- [ ] Verify dashboard updates every 30 seconds
- [ ] Test manual refresh button
- [ ] Verify no WebSocket connections in browser DevTools
- [ ] Check network tab shows regular polling requests

**Deliverable**: Working dashboard with simple polling, no WebSocket

---

### Day 3-4: Simplify Component Structure

**Goal**: Reduce component complexity, remove unnecessary abstractions

#### Tasks

**2.1 Consolidate API Clients** (3 hours)

Create a single, simple API client:

```javascript
// frontend/src/services/api.js
const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

class ApiClient {
  async request(endpoint, options = {}) {
    const token = localStorage.getItem('auth_token');

    const response = await fetch(`${API_URL}${endpoint}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    });

    if (!response.ok) {
      const error = await response.json().catch(() => ({}));
      throw new Error(error.detail || 'Request failed');
    }

    return response.json();
  }

  get(endpoint) {
    return this.request(endpoint);
  }

  post(endpoint, data) {
    return this.request(endpoint, {
      method: 'POST',
      body: JSON.stringify(data),
    });
  }

  put(endpoint, data) {
    return this.request(endpoint, {
      method: 'PUT',
      body: JSON.stringify(data),
    });
  }

  delete(endpoint) {
    return this.request(endpoint, { method: 'DELETE' });
  }
}

export const api = new ApiClient();

// Simple API methods
export const tenantsApi = {
  list: () => api.get('/api/tenants'),
  get: (id) => api.get(`/api/tenants/${id}`),
  create: (data) => api.post('/api/tenants', data),
  update: (id, data) => api.put(`/api/tenants/${id}`, data),
  delete: (id) => api.delete(`/api/tenants/${id}`),
};

export const sitesApi = {
  list: (tenantId) => api.get(`/api/tenants/${tenantId}/sites`),
  get: (id) => api.get(`/api/sites/${id}`),
  create: (tenantId, data) => api.post(`/api/tenants/${tenantId}/sites`, data),
  update: (id, data) => api.put(`/api/sites/${id}`, data),
  delete: (id) => api.delete(`/api/sites/${id}`),
  getOccupancy: (id) => api.get(`/api/sites/${id}/occupancy`),
};

export const spacesApi = {
  list: (siteId) => api.get(`/api/sites/${siteId}/spaces`),
  get: (id) => api.get(`/api/spaces/${id}`),
  create: (siteId, data) => api.post(`/api/sites/${siteId}/spaces`, data),
  update: (id, data) => api.put(`/api/spaces/${id}`, data),
  delete: (id) => api.delete(`/api/spaces/${id}`),
};
```

**2.2 Simplify State Management** (2 hours)

Replace Zustand with simple React Context:

```javascript
// frontend/src/contexts/AuthContext.jsx
import { createContext, useContext, useState, useEffect } from 'react';
import { api } from '../services/api';

const AuthContext = createContext(null);

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Check if user is logged in
    const token = localStorage.getItem('auth_token');
    if (token) {
      api.get('/api/auth/me')
        .then(setUser)
        .catch(() => {
          localStorage.removeItem('auth_token');
        })
        .finally(() => setLoading(false));
    } else {
      setLoading(false);
    }
  }, []);

  const login = async (email, password) => {
    const response = await api.post('/api/auth/login', { email, password });
    localStorage.setItem('auth_token', response.token);
    setUser(response.user);
    return response.user;
  };

  const logout = () => {
    localStorage.removeItem('auth_token');
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, login, logout, loading }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
```

**2.3 Create Simple Page Components** (4 hours)

Consolidate into 6 main pages:

```
frontend/src/pages/
├── Login.jsx              # Login page
├── Dashboard.jsx          # Main dashboard with occupancy
├── Tenants.jsx           # Tenant management (platform admin)
├── Sites.jsx             # Site management
├── Spaces.jsx            # Space management
└── Settings.jsx          # User settings
```

**Deliverable**: Simplified frontend with clear structure, no complex state management

---

### Day 5: UI Cleanup and Testing

**3.1 Remove Unused Dependencies** (2 hours)
```bash
cd frontend
npm remove zustand i18next react-i18next @ant-design/icons
npm remove @types/node @types/react @types/react-dom
# Keep only essential: react, react-dom, react-router-dom, antd, axios
```

**3.2 Simplify Build Configuration** (1 hour)
```javascript
// vite.config.js - simplified
import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 3000,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
});
```

**3.3 Test All Pages** (3 hours)
- [ ] Login/logout flow
- [ ] Dashboard polling and display
- [ ] Tenant CRUD (platform admin)
- [ ] Site CRUD
- [ ] Space CRUD
- [ ] Verify no console errors

**Deliverable**: Clean, simple frontend ready for Phase 2

---

## Phase 2: Database Simplification (Week 2)

### Day 6-7: New Simplified Schema

**Goal**: Create clean 5-table schema with clear hierarchy

#### Tasks

**4.1 Design New Schema** (1 hour)

```sql
-- database/schema_v6_simplified.sql

-- 1. Tenants (customers)
CREATE TABLE tenants (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    name VARCHAR(255) NOT NULL UNIQUE,
    subdomain VARCHAR(100) UNIQUE,
    contact_email VARCHAR(255),
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 2. Users (platform admins and tenant admins)
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    email VARCHAR(255) NOT NULL UNIQUE,
    password_hash VARCHAR(255) NOT NULL,
    name VARCHAR(255),
    tenant_id UUID REFERENCES tenants(id) ON DELETE CASCADE,
    is_platform_admin BOOLEAN DEFAULT false,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- 3. Sites (parking locations) - belongs to tenant
CREATE TABLE sites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    tenant_id UUID NOT NULL REFERENCES tenants(id) ON DELETE CASCADE,
    name VARCHAR(255) NOT NULL,
    address TEXT,
    city VARCHAR(100),
    country VARCHAR(100),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    timezone VARCHAR(50) DEFAULT 'UTC',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_tenant_site UNIQUE (tenant_id, name)
);

-- 4. Spaces (parking spots) - belongs to site
CREATE TABLE spaces (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    site_id UUID NOT NULL REFERENCES sites(id) ON DELETE CASCADE,
    code VARCHAR(50) NOT NULL,
    name VARCHAR(255),
    current_state VARCHAR(20) DEFAULT 'unknown',
    sensor_dev_eui VARCHAR(16),
    last_update TIMESTAMP,
    is_active BOOLEAN DEFAULT true,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT unique_site_space UNIQUE (site_id, code)
);

-- 5. Sensor readings (history)
CREATE TABLE sensor_readings (
    id BIGSERIAL PRIMARY KEY,
    space_id UUID NOT NULL REFERENCES spaces(id) ON DELETE CASCADE,
    state VARCHAR(20) NOT NULL,
    battery_level INTEGER,
    recorded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Indexes for performance
CREATE INDEX idx_sites_tenant ON sites(tenant_id);
CREATE INDEX idx_spaces_site ON spaces(site_id);
CREATE INDEX idx_spaces_state ON spaces(current_state);
CREATE INDEX idx_spaces_dev_eui ON spaces(sensor_dev_eui);
CREATE INDEX idx_readings_space_time ON sensor_readings(space_id, recorded_at DESC);
CREATE INDEX idx_users_tenant ON users(tenant_id);
CREATE INDEX idx_users_email ON users(email);

-- Update timestamp trigger
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_tenants_updated_at BEFORE UPDATE ON tenants
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_sites_updated_at BEFORE UPDATE ON sites
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_spaces_updated_at BEFORE UPDATE ON spaces
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_users_updated_at BEFORE UPDATE ON users
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();
```

**4.2 Create Migration Script** (3 hours)

```bash
#!/bin/bash
# database/migrate_to_simplified.sh

set -e

echo "🔄 Migrating to simplified schema..."

# Backup current database
echo "📦 Creating backup..."
docker exec parking-postgres pg_dump -U parking_user parking > backup_before_simplification_$(date +%Y%m%d_%H%M%S).sql

# Create new database for simplified schema
echo "🗄️  Creating new database..."
docker exec parking-postgres psql -U parking_user -c "CREATE DATABASE parking_v6_simple;"

# Apply new schema
echo "📋 Applying simplified schema..."
docker exec -i parking-postgres psql -U parking_user parking_v6_simple < database/schema_v6_simplified.sql

# Migrate data
echo "📊 Migrating data..."
docker exec -i parking-postgres psql -U parking_user << 'EOF'

-- Connect to old database
\c parking

-- Export tenants
\copy (SELECT id, name, slug as subdomain, created_at FROM tenants WHERE id != '00000000-0000-0000-0000-000000000000') TO '/tmp/tenants.csv' CSV HEADER;

-- Export sites
\copy (SELECT id, tenant_id, name, created_at FROM sites) TO '/tmp/sites.csv' CSV HEADER;

-- Export spaces
\copy (SELECT s.id, s.site_id, s.code, s.name, s.current_state, s.created_at FROM spaces s) TO '/tmp/spaces.csv' CSV HEADER;

-- Connect to new database
\c parking_v6_simple

-- Import tenants
\copy tenants(id, name, subdomain, created_at) FROM '/tmp/tenants.csv' CSV HEADER;

-- Import sites
\copy sites(id, tenant_id, name, created_at) FROM '/tmp/sites.csv' CSV HEADER;

-- Import spaces
\copy spaces(id, site_id, code, name, current_state, created_at) FROM '/tmp/spaces.csv' CSV HEADER;

EOF

echo "✅ Migration complete!"
echo "⚠️  Update docker-compose.yml to use 'parking_v6_simple' database"
```

**4.3 Test New Schema** (2 hours)
- [ ] Run migration script on test database
- [ ] Verify all data migrated correctly
- [ ] Test foreign key constraints
- [ ] Verify indexes created

**Deliverable**: New simplified schema ready to use

---

### Day 8-9: Backend API Simplification

**Goal**: Create simple RESTful API with clear hierarchy

#### Tasks

**5.1 Create Simple Service Layer** (4 hours)

```python
# backend/src/services/simple_service.py
from typing import List, Optional
from uuid import UUID

class SimpleService:
    """Base service with common functionality"""

    def __init__(self, db):
        self.db = db

    async def execute_query(self, query: str, *args):
        """Execute query and return results"""
        return await self.db.fetch(query, *args)

    async def execute_one(self, query: str, *args):
        """Execute query and return single row"""
        return await self.db.fetchrow(query, *args)

class TenantService(SimpleService):
    """Tenant management"""

    async def list_tenants(self) -> List[dict]:
        query = "SELECT * FROM tenants WHERE is_active = true ORDER BY name"
        rows = await self.execute_query(query)
        return [dict(row) for row in rows]

    async def get_tenant(self, tenant_id: UUID) -> dict:
        query = "SELECT * FROM tenants WHERE id = $1"
        row = await self.execute_one(query, tenant_id)
        if not row:
            raise ValueError(f"Tenant {tenant_id} not found")
        return dict(row)

    async def create_tenant(self, name: str, subdomain: str, contact_email: str) -> dict:
        query = """
            INSERT INTO tenants (name, subdomain, contact_email)
            VALUES ($1, $2, $3)
            RETURNING *
        """
        row = await self.execute_one(query, name, subdomain, contact_email)
        return dict(row)

class SiteService(SimpleService):
    """Site management"""

    async def list_sites(self, tenant_id: UUID) -> List[dict]:
        query = """
            SELECT s.*,
                   (SELECT COUNT(*) FROM spaces WHERE site_id = s.id) as space_count,
                   (SELECT COUNT(*) FROM spaces WHERE site_id = s.id AND current_state = 'free') as free_spaces,
                   (SELECT COUNT(*) FROM spaces WHERE site_id = s.id AND current_state = 'occupied') as occupied_spaces
            FROM sites s
            WHERE s.tenant_id = $1
            ORDER BY s.name
        """
        rows = await self.execute_query(query, tenant_id)
        return [dict(row) for row in rows]

    async def get_site(self, site_id: UUID) -> dict:
        query = """
            SELECT s.*,
                   (SELECT COUNT(*) FROM spaces WHERE site_id = s.id) as space_count
            FROM sites s
            WHERE s.id = $1
        """
        row = await self.execute_one(query, site_id)
        if not row:
            raise ValueError(f"Site {site_id} not found")
        return dict(row)

class SpaceService(SimpleService):
    """Space management"""

    async def list_spaces(self, site_id: UUID) -> List[dict]:
        query = """
            SELECT * FROM spaces
            WHERE site_id = $1 AND is_active = true
            ORDER BY code
        """
        rows = await self.execute_query(query, site_id)
        return [dict(row) for row in rows]

    async def update_space_state(self, space_id: UUID, state: str) -> dict:
        query = """
            UPDATE spaces
            SET current_state = $1, last_update = CURRENT_TIMESTAMP
            WHERE id = $2
            RETURNING *
        """
        row = await self.execute_one(query, state, space_id)
        return dict(row)
```

**5.2 Create Simple API Routes** (4 hours)

```python
# backend/src/routers/simple_api.py
from fastapi import APIRouter, Depends, HTTPException
from typing import List
from uuid import UUID
from pydantic import BaseModel

from ..database import get_db
from ..auth import get_current_user, User
from ..services.simple_service import TenantService, SiteService, SpaceService

router = APIRouter(prefix="/api")

def require_platform_admin(user: User = Depends(get_current_user)):
    """Dependency to require platform admin"""
    if not user.is_platform_admin:
        raise HTTPException(403, "Platform admin access required")
    return user

def require_tenant_access(tenant_id: UUID):
    """Dependency to check tenant access"""
    async def check_access(user: User = Depends(get_current_user)):
        if not user.is_platform_admin and user.tenant_id != tenant_id:
            raise HTTPException(403, "Access denied")
        return user
    return check_access

# === TENANTS ===
@router.get("/tenants", dependencies=[Depends(require_platform_admin)])
async def list_tenants(db = Depends(get_db)):
    service = TenantService(db)
    return await service.list_tenants()

@router.post("/tenants", dependencies=[Depends(require_platform_admin)])
async def create_tenant(
    name: str,
    subdomain: str,
    contact_email: str,
    db = Depends(get_db)
):
    service = TenantService(db)
    return await service.create_tenant(name, subdomain, contact_email)

# === SITES ===
@router.get("/tenants/{tenant_id}/sites")
async def list_sites(
    tenant_id: UUID,
    user: User = Depends(require_tenant_access(tenant_id)),
    db = Depends(get_db)
):
    service = SiteService(db)
    return await service.list_sites(tenant_id)

@router.get("/sites/{site_id}")
async def get_site(
    site_id: UUID,
    user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    service = SiteService(db)
    site = await service.get_site(site_id)

    # Check access
    if not user.is_platform_admin and user.tenant_id != site['tenant_id']:
        raise HTTPException(403, "Access denied")

    return site

@router.get("/sites/{site_id}/occupancy")
async def get_site_occupancy(
    site_id: UUID,
    user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    service = SpaceService(db)
    spaces = await service.list_spaces(site_id)

    # Calculate occupancy
    total = len(spaces)
    free = sum(1 for s in spaces if s['current_state'] == 'free')
    occupied = sum(1 for s in spaces if s['current_state'] == 'occupied')

    return {
        'site_id': str(site_id),
        'total_spaces': total,
        'free_spaces': free,
        'occupied_spaces': occupied,
        'occupancy_rate': (occupied / total * 100) if total > 0 else 0,
        'spaces': spaces
    }

# === SPACES ===
@router.get("/sites/{site_id}/spaces")
async def list_spaces(
    site_id: UUID,
    user: User = Depends(get_current_user),
    db = Depends(get_db)
):
    service = SpaceService(db)
    return await service.list_spaces(site_id)

# === WEBHOOK (ChirpStack) ===
@router.post("/webhooks/chirpstack")
async def chirpstack_webhook(
    payload: dict,
    db = Depends(get_db)
):
    """Handle sensor updates from ChirpStack"""
    try:
        # Extract device EUI
        dev_eui = payload.get('devEUI')
        if not dev_eui:
            raise HTTPException(400, "Missing devEUI")

        # Get sensor state from payload
        data = payload.get('data', {})
        state = 'occupied' if data.get('occupied', 0) == 1 else 'free'
        battery = data.get('battery')

        # Find space by sensor dev_eui
        space = await db.fetchrow(
            "SELECT id FROM spaces WHERE sensor_dev_eui = $1",
            dev_eui
        )

        if not space:
            return {"status": "device_not_assigned"}

        # Update space state
        service = SpaceService(db)
        await service.update_space_state(space['id'], state)

        # Record reading
        await db.execute(
            """
            INSERT INTO sensor_readings (space_id, state, battery_level)
            VALUES ($1, $2, $3)
            """,
            space['id'], state, battery
        )

        return {"status": "success", "space_id": str(space['id'])}

    except Exception as e:
        raise HTTPException(500, f"Webhook processing failed: {str(e)}")
```

**5.3 Simplify Authentication** (2 hours)

```python
# backend/src/auth/simple_auth.py
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from jose import JWTError, jwt
from datetime import datetime, timedelta
from passlib.context import CryptContext
from pydantic import BaseModel
from typing import Optional
from uuid import UUID

SECRET_KEY = "your-secret-key-here"  # Move to environment
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_HOURS = 24

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

class User(BaseModel):
    id: UUID
    email: str
    name: Optional[str]
    tenant_id: Optional[UUID]
    is_platform_admin: bool

def create_access_token(user: User) -> str:
    """Create JWT token"""
    expire = datetime.utcnow() + timedelta(hours=ACCESS_TOKEN_EXPIRE_HOURS)
    to_encode = {
        "sub": str(user.id),
        "email": user.email,
        "tenant_id": str(user.tenant_id) if user.tenant_id else None,
        "is_platform_admin": user.is_platform_admin,
        "exp": expire
    }
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

async def get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db = Depends(get_db)
) -> User:
    """Validate token and return current user"""
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = payload.get("sub")

        if user_id is None:
            raise HTTPException(401, "Invalid token")

        # Get user from database
        user_data = await db.fetchrow(
            "SELECT * FROM users WHERE id = $1 AND is_active = true",
            UUID(user_id)
        )

        if not user_data:
            raise HTTPException(401, "User not found")

        return User(
            id=user_data['id'],
            email=user_data['email'],
            name=user_data['name'],
            tenant_id=user_data['tenant_id'],
            is_platform_admin=user_data['is_platform_admin']
        )

    except JWTError:
        raise HTTPException(401, "Invalid token")
```

**Deliverable**: Simplified backend API with clear endpoints

---

### Day 10: Remove Backend Complexity

**6.1 Remove Unused Code** (3 hours)
- [ ] Delete `tenant_context_v6.py` (replaced with simple auth)
- [ ] Delete unused service files
- [ ] Remove RLS-related code
- [ ] Remove WebSocket endpoint
- [ ] Clean up imports

**6.2 Update Main App** (2 hours)

```python
# backend/src/main.py - simplified
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .routers.simple_api import router as api_router
from .routers.auth import router as auth_router
from .database import init_db, close_db

app = FastAPI(title="Smart Parking V6 Simplified")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "https://verdegris.eu"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(api_router, tags=["api"])

@app.on_event("startup")
async def startup():
    await init_db()

@app.on_event("shutdown")
async def shutdown():
    await close_db()

@app.get("/")
async def root():
    return {
        "name": "Smart Parking V6 Simplified",
        "version": "6.1.0",
        "status": "operational"
    }

@app.get("/health")
async def health():
    return {"status": "healthy"}
```

**6.3 Test Backend** (2 hours)
- [ ] Test all API endpoints
- [ ] Verify authentication works
- [ ] Test tenant access control
- [ ] Test ChirpStack webhook

**Deliverable**: Clean, simple backend ready for deployment

---

## Phase 3: Infrastructure Simplification (Week 3)

### Day 11-12: Docker Cleanup

**Goal**: Reduce from 15 containers to 5 essential containers

#### Tasks

**7.1 Create Simplified Docker Compose** (2 hours)

```yaml
# docker-compose.simple.yml
version: '3.8'

services:
  # 1. PostgreSQL Database
  postgres:
    image: postgres:16-alpine
    container_name: parking-postgres-simple
    restart: unless-stopped
    environment:
      POSTGRES_DB: parking_v6_simple
      POSTGRES_USER: parking_user
      POSTGRES_PASSWORD: ${DB_PASSWORD}
    volumes:
      - ./data/postgres:/var/lib/postgresql/data
      - ./database/schema_v6_simplified.sql:/docker-entrypoint-initdb.d/01-schema.sql
    ports:
      - "5432:5432"
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U parking_user"]
      interval: 10s
      timeout: 5s
      retries: 5

  # 2. Backend API
  api:
    build:
      context: ./backend
      dockerfile: Dockerfile
    container_name: parking-api-simple
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://parking_user:${DB_PASSWORD}@postgres:5432/parking_v6_simple
      SECRET_KEY: ${SECRET_KEY}
      CORS_ORIGINS: ${CORS_ORIGINS}
    ports:
      - "8000:8000"
    volumes:
      - ./backend:/app
    command: uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 3. Frontend
  frontend:
    build:
      context: ./frontend
      dockerfile: Dockerfile
      args:
        VITE_API_URL: ${VITE_API_URL}
    container_name: parking-frontend-simple
    restart: unless-stopped
    ports:
      - "3000:80"
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost/"]
      interval: 30s
      timeout: 10s
      retries: 3

  # 4. ChirpStack (LoRaWAN)
  chirpstack:
    image: chirpstack/chirpstack:4
    container_name: parking-chirpstack
    restart: unless-stopped
    depends_on:
      postgres:
        condition: service_healthy
    environment:
      DATABASE_URL: postgresql://parking_user:${DB_PASSWORD}@postgres:5432/chirpstack?sslmode=disable
    ports:
      - "8080:8080"
    volumes:
      - ./config/chirpstack:/etc/chirpstack
      - ./data/chirpstack:/var/lib/chirpstack

  # 5. Reverse Proxy (Caddy - simpler than Traefik)
  caddy:
    image: caddy:2-alpine
    container_name: parking-caddy
    restart: unless-stopped
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./Caddyfile:/etc/caddy/Caddyfile
      - ./data/caddy:/data
      - ./config/caddy:/config
```

**7.2 Create Caddyfile** (1 hour)

```
# Caddyfile
{
    email admin@verdegris.eu
}

verdegris.eu {
    reverse_proxy frontend:80
}

api.verdegris.eu {
    reverse_proxy api:8000
}
```

**7.3 Environment Variables** (1 hour)

```.env
# .env.example
DB_PASSWORD=secure_password_here
SECRET_KEY=your-secret-key-32-chars-min
CORS_ORIGINS=http://localhost:3000,https://verdegris.eu
VITE_API_URL=https://api.verdegris.eu
```

**7.4 Deploy Simplified Stack** (2 hours)
- [ ] Stop old containers
- [ ] Start new simplified stack
- [ ] Verify all 5 containers running
- [ ] Test health checks
- [ ] Test frontend access
- [ ] Test API access

**Deliverable**: Running system with 5 containers instead of 15

---

### Day 13: Testing and Validation

**Goal**: Comprehensive testing of simplified system

#### Tasks

**8.1 Functional Testing** (3 hours)
- [ ] Login as platform admin
- [ ] Create a test tenant
- [ ] Create sites for tenant
- [ ] Create spaces for sites
- [ ] Verify occupancy display
- [ ] Test ChirpStack webhook
- [ ] Verify sensor state updates

**8.2 Performance Testing** (2 hours)
- [ ] Test dashboard polling (30s interval)
- [ ] Verify database queries are fast (<50ms)
- [ ] Check memory usage (<500MB total)
- [ ] Verify CPU usage (<10% idle)

**8.3 User Acceptance Testing** (2 hours)
- [ ] Platform admin can manage all tenants
- [ ] Tenant admin can only see their data
- [ ] Occupancy updates correctly
- [ ] UI is responsive and simple
- [ ] No console errors

**Deliverable**: Validated, working simplified system

---

### Day 14-15: Documentation and Cleanup

**Goal**: Update documentation, clean up old code

#### Tasks

**9.1 Update Documentation** (3 hours)

Create new simple docs:
- System architecture diagram
- API endpoint list
- Deployment guide
- User manual (5 pages max)

**9.2 Code Cleanup** (3 hours)
- [ ] Remove all unused files
- [ ] Update README.md
- [ ] Create simple deployment script
- [ ] Archive old complex code

**9.3 Create Backup and Restore Scripts** (2 hours)

```bash
#!/bin/bash
# scripts/backup.sh
DATE=$(date +%Y%m%d_%H%M%S)
docker exec parking-postgres-simple pg_dump -U parking_user parking_v6_simple > backups/parking_${DATE}.sql
echo "Backup created: backups/parking_${DATE}.sql"
```

**9.4 Training Materials** (2 hours)
- [ ] Platform admin quick start guide
- [ ] Tenant admin guide
- [ ] Troubleshooting guide

**Deliverable**: Complete, documented simplified system

---

## Success Metrics

### Before (Complex V6)
- 15 Docker containers
- ~10,000 lines of code
- WebSocket complexity
- RLS overhead
- Difficult to debug
- 6-8 weeks remaining work

### After (Simplified V6)
- 5 Docker containers
- ~3,500 lines of code
- Simple HTTP polling
- Clear SQL queries
- Easy to debug
- Production ready in 3 weeks

### Key Improvements
- ✅ 67% fewer containers
- ✅ 65% less code
- ✅ No WebSocket complexity
- ✅ Simple mental model (Tenant → Site → Space → Sensor)
- ✅ Any developer can maintain
- ✅ Deploy in < 30 minutes
- ✅ 75% lower infrastructure costs

---

## Risk Mitigation

### Risks

1. **Data Migration Fails**
   - Mitigation: Test migration on copy first, keep backups
   - Rollback: Restore from backup

2. **Breaking Changes for Users**
   - Mitigation: Parallel deployment, gradual cutover
   - Rollback: Keep old system running during transition

3. **ChirpStack Integration Issues**
   - Mitigation: Test webhook extensively
   - Rollback: Keep ChirpStack config backed up

4. **Performance Degradation**
   - Mitigation: Test with realistic data volumes
   - Rollback: Optimize queries if needed

---

## Timeline Summary

| Week | Focus | Deliverables |
|------|-------|--------------|
| Week 1 | Frontend Simplification | Polling instead of WebSocket, simplified components |
| Week 2 | Backend & Database | New 5-table schema, simple API, clean services |
| Week 3 | Infrastructure & Deploy | 5 containers, testing, documentation |

---

## Next Steps

1. **Review this plan** - Ensure it aligns with your goals
2. **Create backups** - Backup everything before starting
3. **Start Phase 1** - Begin with frontend simplification
4. **Test incrementally** - Test each phase before moving to next
5. **Deploy gradually** - Run old and new systems in parallel initially

---

## Questions to Answer Before Starting

1. Do you have complete backups of current system?
2. Can we run old and new systems in parallel during migration?
3. Are there any critical features I've missed?
4. What's the acceptable downtime window for migration?
5. Do you want to keep any specific complex features?

---

**Ready to Start**: This plan can begin immediately and will result in a simple, maintainable system appropriate for your actual scale and needs.
