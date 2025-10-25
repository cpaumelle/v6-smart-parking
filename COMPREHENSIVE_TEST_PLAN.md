# V6 Smart Parking Platform - Comprehensive Test Plan

**Version**: 6.0.0
**Build**: 20251024.25
**Date**: 2025-10-24

---

## Test Scope

This document outlines all UI functionalities and corresponding API endpoints that need to be tested for both **Tenant Admin** and **Platform Super Admin** roles.

---

## User Roles

### 1. Tenant Admin (Owner Role)
- **Access**: Full access to their own tenant's data
- **Restrictions**: Cannot access other tenants' data, cannot manage platform-level resources
- **Test User**: `test_auth@example.com` / `TestPassword123`

### 2. Platform Super Admin
- **Access**: Full access to all tenants, platform-level management
- **Can**: Manage tenants, view cross-tenant data, platform administration
- **Test User**: To be created

---

## Pages and Functionalities

### 1. **Authentication** (`/login`)

#### UI Functionalities
- [ ] Login form display
- [ ] Email/password validation
- [ ] Login submission
- [ ] Token storage
- [ ] Redirect to dashboard on success
- [ ] Error message display on failure
- [ ] Logout functionality

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| POST | `/api/auth/login` | User login | ✅ | ✅ |
| POST | `/api/auth/register` | User registration | ✅ | ✅ |
| POST | `/api/auth/refresh` | Refresh token | ✅ | ✅ |
| POST | `/api/auth/logout` | User logout | ✅ | ✅ |
| GET | `/api/auth/me` | Get current user | ✅ | ✅ |

---

### 2. **Dashboard** (`/dashboard`)

#### UI Functionalities
- [ ] Display overview statistics
  - Total devices (sensors + displays)
  - Active/inactive sensors
  - Assigned/unassigned sensors
  - Gateway status (online/offline)
  - Space occupancy (free/occupied/reserved/maintenance)
  - Occupancy rate percentage
- [ ] Display recent activity feed
- [ ] Display system health status
- [ ] Real-time updates via WebSocket
- [ ] Quick action buttons
- [ ] Charts and visualizations

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/dashboard/data` | Get dashboard statistics | ✅ Own tenant | ✅ All tenants |

---

### 3. **Operations Grid** (`/operations`)

#### UI Functionalities
- [ ] Display real-time parking grid
- [ ] Show space status (free/occupied/reserved/maintenance)
- [ ] Color-coded space visualization
- [ ] Space filtering by status
- [ ] Space search functionality
- [ ] Click space for details
- [ ] Quick status update
- [ ] Sensor assignment indicator
- [ ] Last update timestamp
- [ ] Auto-refresh/real-time updates

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/spaces/` | List all spaces | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/spaces/{id}` | Get space details | ✅ Own tenant | ✅ All tenants |
| PATCH | `/api/v6/spaces/{id}` | Update space status | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/devices/` | List devices (for sensor info) | ✅ Own tenant | ✅ All tenants |

---

### 4. **Device Pool** (`/devices`)

#### UI Functionalities
- [ ] Display all devices (sensors + displays)
- [ ] Filter by device type (sensor/display)
- [ ] Filter by status (active/inactive/assigned/unassigned)
- [ ] Search by dev_eui, name, or location
- [ ] Pagination controls
- [ ] Device list view with columns:
  - Device name
  - Type (sensor/display)
  - Dev EUI
  - Status (active/inactive)
  - Assignment status
  - Assigned space (if any)
  - Last seen
  - Battery level
  - Signal strength
- [ ] Add new device button
- [ ] Edit device button
- [ ] Delete device button
- [ ] Assign device to space
- [ ] Unassign device from space
- [ ] Send downlink command
- [ ] View device history
- [ ] Export device list

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/devices/` | List all devices | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/devices/{id}` | Get device details | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/devices/` | Create new device | ✅ Own tenant | ✅ All tenants |
| PUT | `/api/v6/devices/{id}` | Update device | ✅ Own tenant | ✅ All tenants |
| DELETE | `/api/v6/devices/{id}` | Delete device | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/devices/sensors/` | List sensors only | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/devices/displays/` | List displays only | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/devices/{id}/assign` | Assign device to space | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/devices/{id}/unassign` | Unassign device | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/devices/{id}/command` | Send downlink command | ✅ Own tenant | ✅ All tenants |

---

### 5. **Space Management** (`/spaces`)

#### UI Functionalities
- [ ] Display all parking spaces
- [ ] Filter by status (free/occupied/reserved/maintenance/unknown)
- [ ] Filter by floor/zone
- [ ] Search by space number or name
- [ ] Pagination controls
- [ ] Space list view with columns:
  - Space number
  - Floor
  - Zone
  - Status
  - Assigned sensor
  - Last updated
  - Reservation status
- [ ] Add new space button
- [ ] Edit space button
- [ ] Delete space button
- [ ] Bulk import spaces
- [ ] Export spaces list
- [ ] Space details modal
- [ ] Assign sensor to space
- [ ] Manual status override
- [ ] View space history

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/spaces/` | List all spaces | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/spaces/{id}` | Get space details | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/spaces/` | Create new space | ✅ Own tenant | ✅ All tenants |
| PUT | `/api/v6/spaces/{id}` | Update space | ✅ Own tenant | ✅ All tenants |
| PATCH | `/api/v6/spaces/{id}` | Partial update space | ✅ Own tenant | ✅ All tenants |
| DELETE | `/api/v6/spaces/{id}` | Delete space | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/spaces/stats` | Get space statistics | ✅ Own tenant | ✅ All tenants |

---

### 6. **Reservation Management** (`/reservations`)

#### UI Functionalities
- [ ] Display all reservations
- [ ] Filter by status (active/completed/cancelled)
- [ ] Filter by date range
- [ ] Search by user or space
- [ ] Pagination controls
- [ ] Reservation list view with columns:
  - Reservation ID
  - Space number
  - User/Customer
  - Start time
  - End time
  - Status
  - Created at
- [ ] Create new reservation button
- [ ] Edit reservation button
- [ ] Cancel reservation button
- [ ] View reservation details
- [ ] Export reservations

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/reservations/` | List all reservations | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/reservations/{id}` | Get reservation details | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/reservations/` | Create reservation | ✅ Own tenant | ✅ All tenants |
| PUT | `/api/v6/reservations/{id}` | Update reservation | ✅ Own tenant | ✅ All tenants |
| DELETE | `/api/v6/reservations/{id}` | Cancel reservation | ✅ Own tenant | ✅ All tenants |

---

### 7. **Analytics Dashboard** (`/analytics`)

#### UI Functionalities
- [ ] Date range selector
- [ ] Occupancy over time chart
- [ ] Space utilization chart
- [ ] Peak hours heatmap
- [ ] Average occupancy rate
- [ ] Busiest spaces ranking
- [ ] Revenue analytics (if applicable)
- [ ] Export analytics data
- [ ] Custom report generation

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/analytics/occupancy` | Get occupancy analytics | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/analytics/utilization` | Get space utilization | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/analytics/revenue` | Get revenue analytics | ✅ Own tenant | ✅ All tenants |

---

### 8. **Gateway Management** (Part of Devices or separate)

#### UI Functionalities
- [ ] Display all gateways
- [ ] Gateway status (online/offline)
- [ ] Last seen timestamp
- [ ] Signal strength
- [ ] Connected devices count
- [ ] Add gateway button
- [ ] Edit gateway button
- [ ] Delete gateway button
- [ ] Gateway details modal

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/gateways/` | List all gateways | ✅ Own tenant | ✅ All tenants |
| GET | `/api/v6/gateways/{id}` | Get gateway details | ✅ Own tenant | ✅ All tenants |
| POST | `/api/v6/gateways/` | Create gateway | ✅ Own tenant | ✅ All tenants |
| PUT | `/api/v6/gateways/{id}` | Update gateway | ✅ Own tenant | ✅ All tenants |
| DELETE | `/api/v6/gateways/{id}` | Delete gateway | ✅ Own tenant | ✅ All tenants |

---

### 9. **Settings** (`/settings`)

#### UI Functionalities
- [ ] User profile settings
  - Name
  - Email
  - Password change
- [ ] Tenant settings (owner only)
  - Tenant name
  - Contact info
  - Timezone
  - Notification preferences
- [ ] API keys management
- [ ] Integration settings
- [ ] Notification preferences
- [ ] Save settings button

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/auth/me` | Get current user profile | ✅ | ✅ |
| PUT | `/api/auth/me` | Update user profile | ✅ | ✅ |
| POST | `/api/auth/change-password` | Change password | ✅ | ✅ |

---

### 10. **Tenant Management** (`/tenants`) - **Platform Admin Only**

#### UI Functionalities
- [ ] Display all tenants
- [ ] Search tenants
- [ ] Pagination controls
- [ ] Tenant list view with columns:
  - Tenant name
  - Slug
  - Owner email
  - Created at
  - Status (active/suspended)
  - Total spaces
  - Total devices
- [ ] Create new tenant button
- [ ] Edit tenant button
- [ ] Suspend/activate tenant
- [ ] Delete tenant button
- [ ] View tenant details
- [ ] Impersonate tenant (view as tenant)

#### API Endpoints
| Method | Endpoint | Description | Tenant Admin | Platform Admin |
|--------|----------|-------------|--------------|----------------|
| GET | `/api/v6/tenants/` | List all tenants | ❌ | ✅ |
| GET | `/api/v6/tenants/{id}` | Get tenant details | ❌ | ✅ |
| POST | `/api/v6/tenants/` | Create tenant | ❌ | ✅ |
| PUT | `/api/v6/tenants/{id}` | Update tenant | ❌ | ✅ |
| DELETE | `/api/v6/tenants/{id}` | Delete tenant | ❌ | ✅ |

---

## Additional API Endpoints

### Webhooks (No Authentication)
| Method | Endpoint | Description | Notes |
|--------|----------|-------------|-------|
| POST | `/api/chirpstack/uplink` | ChirpStack uplink webhook | External |
| POST | `/api/chirpstack/join` | ChirpStack join webhook | External |

### Health Check
| Method | Endpoint | Description | Public |
|--------|----------|-------------|--------|
| GET | `/health` | Health check | ✅ |

---

## Test Scenarios

### Tenant Isolation Tests
1. **Tenant A cannot access Tenant B's data**
   - Attempt to GET spaces from another tenant
   - Attempt to UPDATE device from another tenant
   - Attempt to DELETE reservation from another tenant

2. **Row-Level Security enforcement**
   - Verify all queries filter by tenant_id
   - Verify no cross-tenant data leakage

### Permission Tests
1. **Tenant admin permissions**
   - Can CRUD their own resources
   - Cannot access /tenants routes
   - Cannot access other tenants' data

2. **Platform admin permissions**
   - Can access all tenant data
   - Can manage tenants
   - Can impersonate tenants (if implemented)

### Data Integrity Tests
1. **Soft deletes**
   - Verify deleted_at is set, not actual deletion
   - Verify deleted items don't appear in listings
   - Verify deleted items can be restored (if implemented)

2. **Timestamps**
   - created_at set on creation
   - updated_at updated on modification

3. **Required fields validation**
   - API returns 422 for missing required fields
   - UI shows validation errors

### Real-time Tests
1. **WebSocket connections**
   - Dashboard receives real-time updates
   - Operations grid updates on space status change
   - Device status updates reflect immediately

2. **Webhook processing**
   - ChirpStack uplink creates/updates sensor readings
   - Space status updates based on sensor data

---

## Test Execution Plan

### Phase 1: Authentication & Setup
1. Create test users (tenant admin, platform admin)
2. Test login/logout
3. Test token refresh
4. Verify role-based access

### Phase 2: Tenant Admin Tests
1. Test all CRUD operations on spaces
2. Test all CRUD operations on devices
3. Test all CRUD operations on reservations
4. Test dashboard data retrieval
5. Test analytics endpoints
6. Verify cannot access other tenants' data
7. Verify cannot access /tenants routes

### Phase 3: Platform Admin Tests
1. Test tenant management CRUD
2. Test cross-tenant data access
3. Test all endpoints with platform admin token
4. Verify can access all tenants' resources

### Phase 4: Edge Cases & Error Handling
1. Invalid authentication tokens
2. Malformed request bodies
3. Non-existent resource IDs
4. Duplicate entries
5. Constraint violations

### Phase 5: Performance & Load
1. Pagination with large datasets
2. Concurrent updates
3. Real-time update performance
4. Database query performance

---

## Test Data Requirements

### Tenants
- Minimum 2 tenants for isolation testing
- 1 with sample data, 1 empty

### Users
- 1 owner per tenant
- 1 platform_admin
- 1 regular user per tenant (if applicable)

### Spaces
- Minimum 20 spaces per tenant
- Mix of statuses (free/occupied/reserved/maintenance)
- Assigned and unassigned spaces

### Devices
- Minimum 10 sensors per tenant
- Minimum 5 displays per tenant
- Mix of assigned and unassigned devices
- Various battery levels and signal strengths

### Reservations
- Minimum 10 reservations per tenant
- Mix of active/completed/cancelled

### Gateways
- Minimum 2 gateways per tenant
- 1 online, 1 offline

---

## Success Criteria

- ✅ All API endpoints return expected status codes
- ✅ All API responses match schema definitions
- ✅ Row-level security prevents cross-tenant access
- ✅ UI displays data correctly for all pages
- ✅ CRUD operations work for all resources
- ✅ Real-time updates work via WebSocket
- ✅ Authentication and authorization work correctly
- ✅ Error messages are clear and helpful
- ✅ No SQL errors or unhandled exceptions
- ✅ Performance is acceptable (<500ms for most queries)
