"""Gateway Service - LoRaWAN gateway management with tenant scoping"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime, timedelta


class GatewayService:
    """
    Gateway management service with tenant scoping

    Features:
    - Gateway CRUD operations
    - Online/offline status tracking
    - Device connection tracking
    - Site assignment
    - Performance metrics
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def list_gateways(
        self,
        site_id: Optional[UUID] = None,
        include_offline: bool = True,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        List gateways with optional filtering

        Args:
            site_id: Filter by site
            include_offline: Include offline gateways
            page: Page number
            page_size: Items per page

        Returns:
            dict: Gateways list with pagination
        """

        # Build query
        query = """
            SELECT id, tenant_id, gateway_id, name, description,
                   location, latitude, longitude, altitude,
                   last_seen_at, metadata, created_at, updated_at
            FROM gateways
            WHERE 1=1
        """
        params = []

        # Tenant scoping
        if not (self.tenant.is_platform_admin and self.tenant.is_viewing_platform_tenant):
            query += " AND tenant_id = $1"
            params.append(self.tenant.tenant_id)

        # Site filter
        if site_id:
            param_num = len(params) + 1
            query += f" AND site_id = ${param_num}"
            params.append(site_id)

        # Online/offline filter
        if not include_offline:
            # Consider gateway online if seen in last 5 minutes
            query += " AND last_seen_at > NOW() - INTERVAL '5 minutes'"

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
        total = await self.db.fetchval(count_query, *params)

        # Add pagination
        query += f" ORDER BY name LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([page_size, (page - 1) * page_size])

        # Execute query
        gateways = await self.db.fetch(query, *params)

        return {
            "gateways": [self._gateway_to_dict(g) for g in gateways],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "tenant_id": str(self.tenant.tenant_id)
        }

    async def get_gateway(self, gateway_id: UUID) -> Dict[str, Any]:
        """Get gateway by ID"""

        gateway = await self.db.fetchrow("""
            SELECT id, tenant_id, gateway_id, name, description,
                   location, latitude, longitude, altitude,
                   last_seen_at, metadata, created_at, updated_at
            FROM gateways
            WHERE id = $1 AND tenant_id = $2
        """, gateway_id, self.tenant.tenant_id)

        if not gateway:
            raise ValueError(f"Gateway {gateway_id} not found")

        return self._gateway_to_dict(gateway)

    async def create_gateway(
        self,
        gateway_id: str,
        name: str,
        description: Optional[str] = None,
        location: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        altitude: Optional[float] = None,
        site_id: Optional[UUID] = None,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """
        Create a new gateway

        Args:
            gateway_id: ChirpStack gateway ID
            name: Gateway name
            description: Optional description
            location: Location description
            latitude: GPS latitude
            longitude: GPS longitude
            altitude: Altitude in meters
            site_id: Optional site assignment
            metadata: Additional metadata

        Returns:
            dict: Created gateway
        """

        # Check for duplicate gateway_id
        existing = await self.db.fetchrow("""
            SELECT id FROM gateways WHERE gateway_id = $1 AND tenant_id = $2
        """, gateway_id, self.tenant.tenant_id)

        if existing:
            raise ValueError(f"Gateway {gateway_id} already exists")

        # Verify site if provided
        if site_id:
            site = await self.db.fetchrow("""
                SELECT id FROM sites WHERE id = $1 AND tenant_id = $2
            """, site_id, self.tenant.tenant_id)
            if not site:
                raise ValueError(f"Site {site_id} not found")

        # Create gateway
        import json
        new_gateway_id = await self.db.fetchval("""
            INSERT INTO gateways (
                tenant_id, gateway_id, name, description,
                location, latitude, longitude, altitude,
                site_id, metadata, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $11)
            RETURNING id
        """,
            self.tenant.tenant_id,
            gateway_id,
            name,
            description,
            location,
            latitude,
            longitude,
            altitude,
            site_id,
            json.dumps(metadata or {}),
            datetime.utcnow()
        )

        return await self.get_gateway(new_gateway_id)

    async def update_gateway(
        self,
        gateway_id: UUID,
        **updates
    ) -> Dict[str, Any]:
        """Update gateway"""

        # Verify gateway exists
        gateway = await self.db.fetchrow("""
            SELECT id FROM gateways WHERE id = $1 AND tenant_id = $2
        """, gateway_id, self.tenant.tenant_id)

        if not gateway:
            raise ValueError(f"Gateway {gateway_id} not found")

        # Build update query
        allowed_fields = [
            'name', 'description', 'location', 'latitude',
            'longitude', 'altitude', 'site_id', 'metadata'
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

        # Add gateway_id
        param_count += 1
        params.append(gateway_id)

        query = f"""
            UPDATE gateways
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
        """

        await self.db.execute(query, *params)

        return await self.get_gateway(gateway_id)

    async def update_last_seen(
        self,
        gateway_id_str: str,
        timestamp: Optional[datetime] = None
    ):
        """
        Update gateway last_seen_at timestamp

        Called by ChirpStack webhook or sync service

        Args:
            gateway_id_str: ChirpStack gateway ID
            timestamp: Optional timestamp (defaults to now)
        """

        if timestamp is None:
            timestamp = datetime.utcnow()

        await self.db.execute("""
            UPDATE gateways
            SET last_seen_at = $1,
                updated_at = $1
            WHERE gateway_id = $2
        """, timestamp, gateway_id_str)

    async def delete_gateway(self, gateway_id: UUID) -> Dict[str, Any]:
        """Delete a gateway"""

        gateway = await self.db.fetchrow("""
            SELECT id, name FROM gateways
            WHERE id = $1 AND tenant_id = $2
        """, gateway_id, self.tenant.tenant_id)

        if not gateway:
            raise ValueError(f"Gateway {gateway_id} not found")

        # Check if gateway has active devices
        # (This would require a gateway_id column in sensor_devices table)

        # Delete gateway
        await self.db.execute("""
            DELETE FROM gateways WHERE id = $1
        """, gateway_id)

        return {
            "success": True,
            "gateway_id": str(gateway_id),
            "name": gateway['name'],
            "message": "Gateway deleted successfully"
        }

    async def get_gateway_stats(self, gateway_id: UUID) -> Dict[str, Any]:
        """
        Get gateway statistics

        Args:
            gateway_id: Gateway UUID

        Returns:
            dict: Gateway statistics
        """

        # Verify gateway exists
        gateway = await self.db.fetchrow("""
            SELECT id, gateway_id, name, last_seen_at, created_at
            FROM gateways
            WHERE id = $1 AND tenant_id = $2
        """, gateway_id, self.tenant.tenant_id)

        if not gateway:
            raise ValueError(f"Gateway {gateway_id} not found")

        # Calculate uptime
        now = datetime.utcnow()
        if gateway['last_seen_at']:
            is_online = (now - gateway['last_seen_at']) < timedelta(minutes=5)
            last_seen_minutes = int((now - gateway['last_seen_at']).total_seconds() / 60)
        else:
            is_online = False
            last_seen_minutes = None

        # Calculate uptime percentage (would need historical data)
        # For now, return basic stats
        total_days = (now - gateway['created_at']).days
        uptime_percentage = 95.0 if is_online else 0.0  # Placeholder

        return {
            "gateway_id": str(gateway_id),
            "gateway_id_str": gateway['gateway_id'],
            "name": gateway['name'],
            "is_online": is_online,
            "last_seen_at": gateway['last_seen_at'].isoformat() if gateway['last_seen_at'] else None,
            "last_seen_minutes_ago": last_seen_minutes,
            "uptime_percentage": uptime_percentage,
            "total_days": total_days,
            "connected_devices": 0,  # TODO: Track device-gateway relationships
            "message": "Full statistics require device-gateway relationship tracking"
        }

    async def get_online_count(self) -> Dict[str, Any]:
        """Get count of online vs offline gateways"""

        stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total,
                COUNT(*) FILTER (WHERE last_seen_at > NOW() - INTERVAL '5 minutes') as online,
                COUNT(*) FILTER (WHERE last_seen_at <= NOW() - INTERVAL '5 minutes' OR last_seen_at IS NULL) as offline
            FROM gateways
            WHERE tenant_id = $1
        """, self.tenant.tenant_id)

        return {
            "total": stats['total'] or 0,
            "online": stats['online'] or 0,
            "offline": stats['offline'] or 0,
            "tenant_id": str(self.tenant.tenant_id)
        }

    def _gateway_to_dict(self, gateway) -> Dict[str, Any]:
        """Convert gateway row to dictionary"""
        import json

        # Check if online (seen in last 5 minutes)
        is_online = False
        if gateway.get('last_seen_at'):
            time_diff = datetime.utcnow() - gateway['last_seen_at']
            is_online = time_diff < timedelta(minutes=5)

        # Handle metadata field
        metadata_value = gateway.get('metadata', {})
        if isinstance(metadata_value, str):
            metadata_value = json.loads(metadata_value) if metadata_value else {}

        return {
            "id": str(gateway['id']),
            "tenant_id": str(gateway['tenant_id']),
            "gateway_id": gateway['gateway_id'],
            "name": gateway['name'],
            "description": gateway.get('description'),
            "location": gateway.get('location'),
            "latitude": gateway.get('latitude'),
            "longitude": gateway.get('longitude'),
            "altitude": gateway.get('altitude'),
            "is_online": is_online,
            "last_seen_at": gateway['last_seen_at'].isoformat() if gateway.get('last_seen_at') else None,
            "metadata": metadata_value,
            "created_at": gateway['created_at'].isoformat() if gateway.get('created_at') else None,
            "updated_at": gateway['updated_at'].isoformat() if gateway.get('updated_at') else None
        }
