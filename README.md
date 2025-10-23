# Smart Parking Platform v6.0 🚗

**Enterprise-Grade Multi-Tenant Parking Management System**

[![Status](https://img.shields.io/badge/status-production--active-brightgreen)]()
[![Version](https://img.shields.io/badge/version-6.0.0-blue)]()
[![Migration](https://img.shields.io/badge/migration-complete-success)]()
[![License](https://img.shields.io/badge/license-MIT-green)]()

---

## 🌟 What's New in v6.0

### **✅ MIGRATION COMPLETE - V6 NOW IN PRODUCTION**
- **Deployed:** 2025-10-23
- **Status:** Live and receiving sensor data
- **Webhooks:** ChirpStack routing to V6
- **Devices:** 3 active sensors transmitting

### **Complete Service Layer Implementation** ✅
- **13 Production Services** - Full business logic coverage
- **55+ API Endpoints** - Comprehensive REST API
- **100% Feature Parity** with v5.3 + new capabilities

### **Core Architecture Improvements**
- ✅ **Row-Level Security (RLS)** - Database-level tenant isolation
- ✅ **Direct Tenant Ownership** - Efficient single-hop queries
- ✅ **Device Lifecycle Management** - Clear state transitions
- ✅ **Platform Admin Features** - Cross-tenant visibility and management
- ✅ **Multi-Site Support** - Manage multiple locations/facilities
- ✅ **Advanced Analytics** - Usage patterns, revenue tracking, device health
- ✅ **API Key System** - Secure third-party integrations

### **New Services in v6.0**
1. **Gateway Service** - LoRaWAN gateway management
2. **Site Service** - Multi-location facility management
3. **Tenant Service** - Platform-wide tenant administration
4. **Analytics Service** - Advanced reporting and insights
5. **API Key Service** - Scoped API access with rate limiting
6. **Enhanced ChirpStack Sync** - Orphan device discovery

---

## 📊 Platform Capabilities

### **Multi-Tenancy**
- Complete data isolation per tenant
- Subscription tiers (Basic, Professional, Enterprise)
- Feature flags and usage limits
- Trial period management

### **Device Management**
- **Sensor Devices** - Occupancy detection via LoRaWAN
- **Display Devices** - LED indicators for space status
- **Gateways** - LoRaWAN infrastructure management
- **Device Pool** - Platform-level device inventory

### **Space Management**
- Real-time occupancy tracking
- Multi-site organization
- State machine (free, occupied, reserved, maintenance)
- Auto-release and reservation management

### **Reservations**
- Idempotent booking with overlap prevention
- Availability checking
- Auto-expiration
- Revenue tracking

### **Analytics & Reporting**
- Occupancy trends (hourly, daily, weekly)
- Peak hours analysis
- Popular spaces identification
- Device health scores
- Revenue tracking

### **Integrations**
- **ChirpStack** - LoRaWAN network server integration
- **Webhooks** - Real-time event notifications
- **REST API** - Full programmatic access
- **API Keys** - Scoped third-party access

---

## 🚀 Quick Start

### Prerequisites
- Python 3.11+
- PostgreSQL 15+
- Redis 7+ (for caching and queues)
- Node.js 18+ (for frontend)

### Installation

#### 1. Clone Repository
```bash
git clone https://github.com/your-org/v6_smart_parking.git
cd v6_smart_parking
```

#### 2. Database Setup
```bash
# Create database
createdb parking_v6

# Run migrations
psql -U postgres -d parking_v6 -f migrations/001_v6_add_tenant_columns.sql
psql -U postgres -d parking_v6 -f migrations/002_v6_backfill_tenant_data.sql
psql -U postgres -d parking_v6 -f migrations/003_v6_create_new_tables.sql
psql -U postgres -d parking_v6 -f migrations/004_v6_row_level_security.sql

# Validate
python scripts/validate_migration.py
```

#### 3. Backend Setup
```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env with your settings

# Run server
uvicorn src.main:app --reload --host 0.0.0.0 --port 8000
```

#### 4. Access API
- **API**: http://localhost:8000
- **Docs**: http://localhost:8000/docs
- **Health**: http://localhost:8000/health

---

## 📁 Project Structure

```
v6_smart_parking/
├── backend/
│   ├── src/
│   │   ├── core/                 # Core infrastructure
│   │   │   ├── database.py       # Database connection
│   │   │   ├── security.py       # JWT, password hashing
│   │   │   └── tenant_context_v6.py  # Multi-tenancy
│   │   ├── services/             # Business logic (13 services)
│   │   │   ├── device_service_v6.py
│   │   │   ├── space_service.py
│   │   │   ├── reservation_service.py
│   │   │   ├── gateway_service.py      # NEW
│   │   │   ├── site_service.py         # NEW
│   │   │   ├── tenant_service.py       # NEW
│   │   │   ├── analytics_service.py    # NEW
│   │   │   ├── api_key_service.py      # NEW
│   │   │   ├── webhook_service.py
│   │   │   ├── downlink_service.py
│   │   │   ├── display_service.py
│   │   │   ├── chirpstack_sync.py
│   │   │   └── background_jobs.py
│   │   ├── routers/              # API endpoints
│   │   │   ├── auth.py           # Authentication
│   │   │   ├── webhooks.py       # ChirpStack webhooks
│   │   │   └── v6/               # v6 API
│   │   │       ├── devices.py
│   │   │       ├── spaces.py
│   │   │       ├── reservations.py
│   │   │       ├── gateways.py
│   │   │       └── dashboard.py
│   │   ├── schemas/              # Pydantic models
│   │   └── main.py               # FastAPI app
│   ├── tests/                    # Test suite
│   └── requirements.txt
├── migrations/                   # Database migrations
├── scripts/                      # Utility scripts
└── docs/                         # Documentation
    ├── V6_DATABASE_SCHEMA.md
    ├── V6_API_DOCUMENTATION.md
    └── V6_ARCHITECTURE.md
```

---

## 🔒 Security Features

### Authentication & Authorization
- **JWT Tokens** - Secure access/refresh token flow
- **API Keys** - Scoped third-party access
- **Row-Level Security** - Database-level isolation
- **Role-Based Access** - Owner, Admin, Operator, Viewer

### Data Protection
- **Password Hashing** - Bcrypt with salt
- **HMAC Webhooks** - SHA-256 signature validation
- **Rate Limiting** - Per-tenant API limits
- **Token Expiration** - Automatic key expiry

### Multi-Tenancy Isolation
```sql
-- All queries automatically scoped to tenant
CREATE POLICY tenant_isolation ON sensor_devices
    USING (tenant_id = current_setting('app.current_tenant_id')::uuid
           OR current_setting('app.is_platform_admin')::boolean = true);
```

---

## 🎯 API Endpoints

### Authentication
```
POST   /api/auth/register      # Create tenant + user
POST   /api/auth/login         # JWT authentication
POST   /api/auth/refresh       # Refresh access token
GET    /api/auth/me            # Current user info
```

### Devices (v6)
```
GET    /api/v6/devices                    # List devices
POST   /api/v6/devices/{id}/assign        # Assign to space
POST   /api/v6/devices/{id}/unassign      # Unassign device
GET    /api/v6/devices/pool/stats         # Pool stats (admin)
```

### Spaces (v6)
```
GET    /api/v6/spaces                     # List spaces
POST   /api/v6/spaces                     # Create space
GET    /api/v6/spaces/{id}                # Get space
PUT    /api/v6/spaces/{id}                # Update space
DELETE /api/v6/spaces/{id}                # Delete space
PUT    /api/v6/spaces/{id}/state          # Update state
GET    /api/v6/spaces/stats/occupancy     # Occupancy stats
```

### Reservations (v6)
```
POST   /api/v6/reservations               # Create (idempotent)
GET    /api/v6/reservations               # List reservations
GET    /api/v6/reservations/{id}          # Get reservation
PUT    /api/v6/reservations/{id}/cancel   # Cancel reservation
POST   /api/v6/reservations/expire-old    # Expire old (job)
```

### Gateways (v6)
```
GET    /api/v6/gateways                   # List gateways
GET    /api/v6/gateways/{id}              # Get gateway
GET    /api/v6/gateways/{id}/stats        # Gateway stats
```

### Dashboard (v6)
```
GET    /api/v6/dashboard/data             # Unified dashboard
```

### Webhooks
```
POST   /webhooks/chirpstack/uplink        # Sensor uplink
POST   /webhooks/chirpstack/join          # Device join
GET    /webhooks/health                   # Health check
```

---

## 📈 Subscription Tiers

| Feature | Basic | Professional | Enterprise |
|---------|-------|--------------|------------|
| **Devices** | 100 | 500 | 10,000 |
| **Gateways** | 10 | 50 | 100 |
| **Spaces** | 100 | 500 | 5,000 |
| **Users** | 5 | 25 | 100 |
| **API Rate Limit** | 100/min | 1,000/min | 10,000/min |
| **Analytics** | ❌ | ✅ | ✅ |
| **Custom Branding** | ❌ | ❌ | ✅ |
| **Priority Support** | ❌ | ✅ | ✅ |

---

## 🔄 Background Jobs

The platform runs 4 background jobs:

1. **Expire Reservations** (60s) - Auto-expire old reservations
2. **Process Webhook Spool** (60s) - Retry failed webhooks
3. **ChirpStack Sync** (5min) - Sync devices/gateways
4. **Cleanup Readings** (24h) - Remove old sensor data (90 days)

---

## 📊 Performance Metrics

| Metric | v5.3 | v6.0 | Improvement |
|--------|------|------|-------------|
| Device List API | 800ms | 150ms | **81%** ⬇️ |
| Device Assignment | 400ms | 80ms | **80%** ⬇️ |
| Dashboard Load | 3s | 800ms | **73%** ⬇️ |
| Database CPU | 40% | 18% | **55%** ⬇️ |
| Query Complexity | 3-hop | 1-hop | **Direct** |

---

## 🧪 Testing

```bash
# Backend unit tests
cd backend
pytest tests/ -v

# Integration tests
pytest tests/e2e/ -v --cov

# Load testing
locust -f tests/load_test.py
```

---

## 📝 Environment Variables

```bash
# Database
DATABASE_URL=postgresql://user:pass@localhost:5432/parking_v6

# Security
SECRET_KEY=your-secret-key-here
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7

# ChirpStack
CHIRPSTACK_URL=http://localhost:8080
CHIRPSTACK_API_TOKEN=your-token
CHIRPSTACK_WEBHOOK_SECRET=webhook-secret

# Redis
REDIS_URL=redis://localhost:6379/0

# CORS
ALLOWED_ORIGINS=http://localhost:3000,https://app.example.com
```

---

## 🐛 Troubleshooting

### Database Connection
```bash
# Test connection
psql $DATABASE_URL -c "SELECT version();"

# Check RLS
psql $DATABASE_URL -c "SELECT tablename, rowsecurity FROM pg_tables WHERE schemaname='public';"
```

### Server Not Starting
```bash
# Check logs
tail -f /tmp/server.log

# Verify Python dependencies
pip list | grep fastapi

# Check port availability
lsof -i :8000
```

---

## 📚 Documentation

- **[Database Schema](docs/V6_DATABASE_SCHEMA.md)** - Complete schema documentation
- **[API Documentation](docs/V6_API_DOCUMENTATION.md)** - All endpoints with examples
- **[Architecture](docs/V6_ARCHITECTURE.md)** - System design and patterns
- **[Migration Guide](docs/MIGRATION_V5_TO_V6.md)** - Upgrade from v5.3

---

## 🤝 Contributing

We welcome contributions! Please follow these guidelines:

1. **Fork** the repository
2. **Create** a feature branch (`git checkout -b feature/amazing-feature`)
3. **Commit** with conventional commits (`feat:`, `fix:`, `docs:`)
4. **Test** your changes (`pytest`, `npm test`)
5. **Push** to your branch
6. **Open** a Pull Request

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

## 👥 Team

**Smart Parking Platform v6**
- Developed by Verdegris Solutions
- Powered by FastAPI, PostgreSQL, and React

---

## 🎯 Roadmap

### v6.1 (Q1 2025)
- [ ] Payment gateway integration
- [ ] Mobile app (iOS/Android)
- [ ] Bluetooth LE support
- [ ] Advanced ML-based predictions

### v6.2 (Q2 2025)
- [ ] Multi-language support
- [ ] White-label customization
- [ ] Advanced reporting dashboard
- [ ] Automated billing

---

## 📞 Support

- **Documentation**: https://docs.parkingplatform.com
- **Issues**: https://github.com/your-org/v6_smart_parking/issues
- **Email**: support@parkingplatform.com
- **Slack**: #smart-parking-support

---

**Version**: 6.0.0
**Last Updated**: 2025-10-23
**Status**: Production Ready ✅
