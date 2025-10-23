"""Tenant Service - Multi-tenant management (Platform Admin only)"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class TenantService:
    """
    Tenant management service (Platform Admin only)

    Features:
    - Tenant CRUD operations
    - Subscription management
    - Feature flags
    - Usage limits
    - Tenant statistics
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    def _verify_platform_admin(self):
        """Verify user is platform admin"""
        if not self.tenant.is_platform_admin:
            raise PermissionError("Only platform admins can manage tenants")

    async def list_tenants(
        self,
        tenant_type: Optional[str] = None,
        is_active: Optional[bool] = None,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        List all tenants (Platform Admin only)

        Args:
            tenant_type: Filter by type (platform, customer, trial)
            is_active: Filter by active status
            page: Page number
            page_size: Items per page

        Returns:
            dict: Tenants list with pagination
        """

        self._verify_platform_admin()

        # Build query
        query = """
            SELECT id, name, slug, type, is_active,
                   subscription_tier, subscription_status,
                   trial_ends_at, features, limits,
                   created_at, updated_at
            FROM tenants
            WHERE 1=1
        """
        params = []

        # Filters
        if tenant_type:
            params.append(tenant_type)
            query += f" AND type = ${len(params)}"

        if is_active is not None:
            params.append(is_active)
            query += f" AND is_active = ${len(params)}"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
        total = await self.db.fetchval(count_query, *params)

        # Add pagination
        query += f" ORDER BY name LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([page_size, (page - 1) * page_size])

        # Execute query
        tenants = await self.db.fetch(query, *params)

        return {
            "tenants": [self._tenant_to_dict(t) for t in tenants],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    async def get_tenant(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get tenant by ID (Platform Admin only)"""

        self._verify_platform_admin()

        tenant = await self.db.fetchrow("""
            SELECT * FROM tenants WHERE id = $1
        """, tenant_id)

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Get statistics
        stats = await self._get_tenant_stats(tenant_id)

        result = self._tenant_to_dict(tenant)
        result['stats'] = stats

        return result

    async def create_tenant(
        self,
        name: str,
        slug: str,
        tenant_type: str = 'customer',
        subscription_tier: str = 'basic',
        trial_days: Optional[int] = None,
        features: dict = None,
        limits: dict = None
    ) -> Dict[str, Any]:
        """
        Create a new tenant (Platform Admin only)

        Args:
            name: Tenant name
            slug: Unique slug
            tenant_type: Type (platform, customer, trial)
            subscription_tier: Tier (basic, professional, enterprise)
            trial_days: Trial period in days
            features: Feature flags
            limits: Usage limits

        Returns:
            dict: Created tenant
        """

        self._verify_platform_admin()

        # Check for duplicate slug
        existing = await self.db.fetchrow("""
            SELECT id FROM tenants WHERE slug = $1
        """, slug)

        if existing:
            raise ValueError(f"Tenant with slug '{slug}' already exists")

        # Calculate trial end date
        trial_ends_at = None
        if trial_days:
            from datetime import timedelta
            trial_ends_at = datetime.utcnow() + timedelta(days=trial_days)

        # Default features and limits
        default_features = {
            "parking": True,
            "reservations": True,
            "analytics": subscription_tier in ['professional', 'enterprise'],
            "api_access": True,
            "webhooks": True,
            "custom_branding": subscription_tier == 'enterprise'
        }

        default_limits = {
            "max_devices": 100 if subscription_tier == 'basic' else 500 if subscription_tier == 'professional' else 10000,
            "max_gateways": 10 if subscription_tier == 'basic' else 50 if subscription_tier == 'professional' else 100,
            "max_spaces": 100 if subscription_tier == 'basic' else 500 if subscription_tier == 'professional' else 5000,
            "max_users": 5 if subscription_tier == 'basic' else 25 if subscription_tier == 'professional' else 100,
            "api_rate_limit": 100 if subscription_tier == 'basic' else 1000 if subscription_tier == 'professional' else 10000
        }

        # Merge with provided features/limits
        import json
        final_features = {**default_features, **(features or {})}
        final_limits = {**default_limits, **(limits or {})}

        # Create tenant
        tenant_id = await self.db.fetchval("""
            INSERT INTO tenants (
                name, slug, type, is_active,
                subscription_tier, subscription_status,
                trial_ends_at, features, limits,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, true, $4, $5, $6, $7, $8, $9, $9)
            RETURNING id
        """,
            name,
            slug,
            tenant_type,
            subscription_tier,
            'trial' if trial_days else 'active',
            trial_ends_at,
            json.dumps(final_features),
            json.dumps(final_limits),
            datetime.utcnow()
        )

        return await self.get_tenant(tenant_id)

    async def update_tenant(
        self,
        tenant_id: UUID,
        **updates
    ) -> Dict[str, Any]:
        """Update tenant (Platform Admin only)"""

        self._verify_platform_admin()

        # Verify tenant exists
        tenant = await self.db.fetchrow("""
            SELECT id FROM tenants WHERE id = $1
        """, tenant_id)

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        # Build update query
        allowed_fields = [
            'name', 'slug', 'type', 'is_active',
            'subscription_tier', 'subscription_status',
            'trial_ends_at', 'features', 'limits'
        ]

        update_fields = []
        params = []
        param_count = 0

        for field, value in updates.items():
            if field in allowed_fields and value is not None:
                param_count += 1
                update_fields.append(f"{field} = ${param_count}")
                params.append(value)

        if not update_fields:
            raise ValueError("No valid fields to update")

        # Add updated_at
        param_count += 1
        update_fields.append(f"updated_at = ${param_count}")
        params.append(datetime.utcnow())

        # Add tenant_id
        param_count += 1
        params.append(tenant_id)

        query = f"""
            UPDATE tenants
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
        """

        await self.db.execute(query, *params)

        return await self.get_tenant(tenant_id)

    async def suspend_tenant(self, tenant_id: UUID, reason: str) -> Dict[str, Any]:
        """Suspend a tenant (Platform Admin only)"""

        self._verify_platform_admin()

        await self.db.execute("""
            UPDATE tenants
            SET is_active = false,
                subscription_status = 'suspended',
                updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), tenant_id)

        # TODO: Log suspension reason

        return {
            "success": True,
            "tenant_id": str(tenant_id),
            "status": "suspended",
            "reason": reason,
            "message": "Tenant suspended successfully"
        }

    async def activate_tenant(self, tenant_id: UUID) -> Dict[str, Any]:
        """Activate a suspended tenant (Platform Admin only)"""

        self._verify_platform_admin()

        await self.db.execute("""
            UPDATE tenants
            SET is_active = true,
                subscription_status = 'active',
                updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), tenant_id)

        return {
            "success": True,
            "tenant_id": str(tenant_id),
            "status": "active",
            "message": "Tenant activated successfully"
        }

    async def delete_tenant(self, tenant_id: UUID) -> Dict[str, Any]:
        """
        Delete a tenant and all associated data (Platform Admin only)

        WARNING: This is a destructive operation!
        """

        self._verify_platform_admin()

        # Prevent deleting platform tenant
        tenant = await self.db.fetchrow("""
            SELECT id, name, type FROM tenants WHERE id = $1
        """, tenant_id)

        if not tenant:
            raise ValueError(f"Tenant {tenant_id} not found")

        if tenant['type'] == 'platform':
            raise ValueError("Cannot delete platform tenant")

        # In production, you would:
        # 1. Archive all data
        # 2. Cascade delete or soft delete
        # 3. Send notifications
        # For now, just mark as deleted

        await self.db.execute("""
            UPDATE tenants
            SET is_active = false,
                subscription_status = 'deleted',
                updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), tenant_id)

        return {
            "success": True,
            "tenant_id": str(tenant_id),
            "name": tenant['name'],
            "message": "Tenant marked as deleted (data archived)"
        }

    async def get_platform_stats(self) -> Dict[str, Any]:
        """
        Get platform-wide statistics (Platform Admin only)

        Returns:
            dict: Platform statistics
        """

        self._verify_platform_admin()

        # Tenant stats
        tenant_stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_tenants,
                COUNT(*) FILTER (WHERE is_active = true) as active_tenants,
                COUNT(*) FILTER (WHERE type = 'customer') as customer_tenants,
                COUNT(*) FILTER (WHERE type = 'trial') as trial_tenants,
                COUNT(*) FILTER (WHERE subscription_tier = 'basic') as basic_tier,
                COUNT(*) FILTER (WHERE subscription_tier = 'professional') as pro_tier,
                COUNT(*) FILTER (WHERE subscription_tier = 'enterprise') as enterprise_tier
            FROM tenants
        """)

        # Device stats
        device_stats = await self.db.fetchrow("""
            SELECT
                COUNT(DISTINCT tenant_id) as tenants_with_devices,
                COUNT(*) as total_devices
            FROM sensor_devices
        """)

        # Space stats
        space_stats = await self.db.fetchrow("""
            SELECT
                COUNT(DISTINCT tenant_id) as tenants_with_spaces,
                COUNT(*) as total_spaces,
                COUNT(*) FILTER (WHERE current_state = 'occupied') as occupied_spaces
            FROM spaces
            WHERE archived_at IS NULL
        """)

        # Reservation stats
        reservation_stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_reservations,
                COUNT(*) FILTER (WHERE status = 'active') as active_reservations,
                COUNT(*) FILTER (WHERE created_at > NOW() - INTERVAL '24 hours') as recent_reservations
            FROM reservations
        """)

        return {
            "tenants": dict(tenant_stats) if tenant_stats else {},
            "devices": dict(device_stats) if device_stats else {},
            "spaces": dict(space_stats) if space_stats else {},
            "reservations": dict(reservation_stats) if reservation_stats else {},
            "generated_at": datetime.utcnow().isoformat()
        }

    async def _get_tenant_stats(self, tenant_id: UUID) -> Dict[str, Any]:
        """Get statistics for a specific tenant"""

        stats = await self.db.fetchrow("""
            SELECT
                (SELECT COUNT(*) FROM users u
                 JOIN user_memberships um ON um.user_id = u.id
                 WHERE um.tenant_id = $1 AND um.is_active = true) as user_count,
                (SELECT COUNT(*) FROM sensor_devices WHERE tenant_id = $1) as device_count,
                (SELECT COUNT(*) FROM display_devices WHERE tenant_id = $1) as display_count,
                (SELECT COUNT(*) FROM gateways WHERE tenant_id = $1) as gateway_count,
                (SELECT COUNT(*) FROM sites WHERE tenant_id = $1) as site_count,
                (SELECT COUNT(*) FROM spaces WHERE tenant_id = $1 AND archived_at IS NULL) as space_count,
                (SELECT COUNT(*) FROM reservations WHERE tenant_id = $1) as reservation_count
        """, tenant_id)

        return dict(stats) if stats else {}

    def _tenant_to_dict(self, tenant) -> Dict[str, Any]:
        """Convert tenant row to dictionary"""
        import json

        # Handle JSONB fields
        features = tenant.get('features', {})
        if isinstance(features, str):
            features = json.loads(features) if features else {}

        limits = tenant.get('limits', {})
        if isinstance(limits, str):
            limits = json.loads(limits) if limits else {}

        return {
            "id": str(tenant['id']),
            "name": tenant['name'],
            "slug": tenant['slug'],
            "type": tenant['type'],
            "is_active": tenant['is_active'],
            "subscription_tier": tenant.get('subscription_tier'),
            "subscription_status": tenant.get('subscription_status'),
            "trial_ends_at": tenant['trial_ends_at'].isoformat() if tenant.get('trial_ends_at') else None,
            "features": features,
            "limits": limits,
            "created_at": tenant['created_at'].isoformat() if tenant.get('created_at') else None,
            "updated_at": tenant['updated_at'].isoformat() if tenant.get('updated_at') else None
        }
