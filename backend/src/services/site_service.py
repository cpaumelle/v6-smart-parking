"""Site Service - Location/facility management with tenant scoping"""

from typing import Optional, List, Dict, Any
from uuid import UUID
from datetime import datetime


class SiteService:
    """
    Site (location/facility) management service

    Features:
    - Site CRUD operations
    - Hierarchical organization support
    - Space and device assignment to sites
    - Site-level statistics
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def list_sites(
        self,
        include_stats: bool = False,
        page: int = 1,
        page_size: int = 100
    ) -> Dict[str, Any]:
        """
        List sites with optional statistics

        Args:
            include_stats: Include space and device counts
            page: Page number
            page_size: Items per page

        Returns:
            dict: Sites list with pagination
        """

        # Build base query
        if include_stats:
            query = """
                SELECT s.*,
                    (SELECT COUNT(*) FROM spaces sp WHERE sp.site_id = s.id AND sp.archived_at IS NULL) as space_count,
                    (SELECT COUNT(*) FROM sensor_devices sd WHERE sd.assigned_space_id IN
                        (SELECT id FROM spaces WHERE site_id = s.id)) as device_count
                FROM sites s
                WHERE s.tenant_id = $1
            """
        else:
            query = """
                SELECT * FROM sites
                WHERE tenant_id = $1
            """

        params = [self.tenant.tenant_id]

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
        total = await self.db.fetchval(count_query, *params)

        # Add pagination
        query += f" ORDER BY name LIMIT ${len(params) + 1} OFFSET ${len(params) + 2}"
        params.extend([page_size, (page - 1) * page_size])

        # Execute query
        sites = await self.db.fetch(query, *params)

        return {
            "sites": [self._site_to_dict(s, include_stats) for s in sites],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "tenant_id": str(self.tenant.tenant_id)
        }

    async def get_site(self, site_id: UUID) -> Dict[str, Any]:
        """Get site by ID with statistics"""

        site = await self.db.fetchrow("""
            SELECT s.*,
                (SELECT COUNT(*) FROM spaces WHERE site_id = s.id AND archived_at IS NULL) as space_count,
                (SELECT COUNT(*) FROM spaces WHERE site_id = s.id AND archived_at IS NULL AND current_state = 'free') as free_spaces,
                (SELECT COUNT(*) FROM spaces WHERE site_id = s.id AND archived_at IS NULL AND current_state = 'occupied') as occupied_spaces,
                (SELECT COUNT(*) FROM gateways WHERE site_id = s.id) as gateway_count
            FROM sites s
            WHERE s.id = $1 AND s.tenant_id = $2
        """, site_id, self.tenant.tenant_id)

        if not site:
            raise ValueError(f"Site {site_id} not found")

        return self._site_to_dict(site, include_stats=True)

    async def create_site(
        self,
        name: str,
        code: str,
        address: Optional[str] = None,
        city: Optional[str] = None,
        state: Optional[str] = None,
        postal_code: Optional[str] = None,
        country: Optional[str] = None,
        latitude: Optional[float] = None,
        longitude: Optional[float] = None,
        timezone: Optional[str] = None,
        metadata: dict = None
    ) -> Dict[str, Any]:
        """
        Create a new site

        Args:
            name: Site name
            code: Unique site code
            address: Street address
            city: City
            state: State/province
            postal_code: Postal/ZIP code
            country: Country
            latitude: GPS latitude
            longitude: GPS longitude
            timezone: Timezone (e.g., "America/New_York")
            metadata: Additional metadata

        Returns:
            dict: Created site
        """

        # Check for duplicate code
        existing = await self.db.fetchrow("""
            SELECT id FROM sites WHERE code = $1 AND tenant_id = $2
        """, code, self.tenant.tenant_id)

        if existing:
            raise ValueError(f"Site with code '{code}' already exists")

        # Create site
        import json
        site_id = await self.db.fetchval("""
            INSERT INTO sites (
                tenant_id, name, code, address, city, state,
                postal_code, country, latitude, longitude,
                timezone, metadata, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $13)
            RETURNING id
        """,
            self.tenant.tenant_id,
            name,
            code,
            address,
            city,
            state,
            postal_code,
            country,
            latitude,
            longitude,
            timezone or 'UTC',
            json.dumps(metadata or {}),
            datetime.utcnow()
        )

        return await self.get_site(site_id)

    async def update_site(
        self,
        site_id: UUID,
        **updates
    ) -> Dict[str, Any]:
        """Update site"""

        # Verify site exists
        site = await self.db.fetchrow("""
            SELECT id FROM sites WHERE id = $1 AND tenant_id = $2
        """, site_id, self.tenant.tenant_id)

        if not site:
            raise ValueError(f"Site {site_id} not found")

        # Build update query
        allowed_fields = [
            'name', 'code', 'address', 'city', 'state',
            'postal_code', 'country', 'latitude', 'longitude',
            'timezone', 'metadata'
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

        # Add site_id
        param_count += 1
        params.append(site_id)

        query = f"""
            UPDATE sites
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
        """

        await self.db.execute(query, *params)

        return await self.get_site(site_id)

    async def delete_site(self, site_id: UUID) -> Dict[str, Any]:
        """
        Delete a site (soft delete)

        Prevents deletion if site has spaces or gateways
        """

        site = await self.db.fetchrow("""
            SELECT id, name FROM sites
            WHERE id = $1 AND tenant_id = $2
        """, site_id, self.tenant.tenant_id)

        if not site:
            raise ValueError(f"Site {site_id} not found")

        # Check for spaces
        space_count = await self.db.fetchval("""
            SELECT COUNT(*) FROM spaces
            WHERE site_id = $1 AND archived_at IS NULL
        """, site_id)

        if space_count > 0:
            raise ValueError(f"Cannot delete site with {space_count} active spaces")

        # Check for gateways
        gateway_count = await self.db.fetchval("""
            SELECT COUNT(*) FROM gateways WHERE site_id = $1
        """, site_id)

        if gateway_count > 0:
            raise ValueError(f"Cannot delete site with {gateway_count} gateways")

        # Soft delete (if sites table has archived_at)
        # Otherwise hard delete
        try:
            await self.db.execute("""
                UPDATE sites
                SET archived_at = $1, updated_at = $1
                WHERE id = $2
            """, datetime.utcnow(), site_id)
        except:
            # If archived_at column doesn't exist, hard delete
            await self.db.execute("DELETE FROM sites WHERE id = $1", site_id)

        return {
            "success": True,
            "site_id": str(site_id),
            "name": site['name'],
            "message": "Site deleted successfully"
        }

    async def get_site_occupancy(self, site_id: UUID) -> Dict[str, Any]:
        """
        Get real-time occupancy statistics for a site

        Args:
            site_id: Site UUID

        Returns:
            dict: Occupancy statistics
        """

        # Verify site exists
        site = await self.db.fetchrow("""
            SELECT id, name, code FROM sites
            WHERE id = $1 AND tenant_id = $2
        """, site_id, self.tenant.tenant_id)

        if not site:
            raise ValueError(f"Site {site_id} not found")

        # Get space statistics
        stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_spaces,
                COUNT(*) FILTER (WHERE current_state = 'free') as free,
                COUNT(*) FILTER (WHERE current_state = 'occupied') as occupied,
                COUNT(*) FILTER (WHERE current_state = 'reserved') as reserved,
                COUNT(*) FILTER (WHERE current_state = 'maintenance') as maintenance,
                COUNT(*) FILTER (WHERE current_state = 'unknown') as unknown
            FROM spaces
            WHERE site_id = $1 AND archived_at IS NULL
        """, site_id)

        total = stats['total_spaces'] or 0
        occupied = stats['occupied'] or 0

        return {
            "site_id": str(site_id),
            "site_name": site['name'],
            "site_code": site['code'],
            "total_spaces": total,
            "free": stats['free'] or 0,
            "occupied": occupied,
            "reserved": stats['reserved'] or 0,
            "maintenance": stats['maintenance'] or 0,
            "unknown": stats['unknown'] or 0,
            "available": stats['free'] or 0,
            "occupancy_rate": round((occupied / total * 100) if total > 0 else 0, 2),
            "tenant_id": str(self.tenant.tenant_id)
        }

    async def get_all_sites_occupancy(self) -> List[Dict[str, Any]]:
        """
        Get occupancy for all sites in tenant

        Returns:
            list: Occupancy statistics for each site
        """

        sites = await self.db.fetch("""
            SELECT id FROM sites
            WHERE tenant_id = $1
            ORDER BY name
        """, self.tenant.tenant_id)

        results = []
        for site in sites:
            try:
                occupancy = await self.get_site_occupancy(site['id'])
                results.append(occupancy)
            except Exception as e:
                # Skip sites with errors
                pass

        return results

    def _site_to_dict(self, site, include_stats: bool = False) -> Dict[str, Any]:
        """Convert site row to dictionary"""
        import json

        # Handle metadata field
        metadata_value = site.get('metadata', {})
        if isinstance(metadata_value, str):
            metadata_value = json.loads(metadata_value) if metadata_value else {}

        result = {
            "id": str(site['id']),
            "tenant_id": str(site['tenant_id']),
            "name": site['name'],
            "code": site['code'],
            "address": site.get('address'),
            "city": site.get('city'),
            "state": site.get('state'),
            "postal_code": site.get('postal_code'),
            "country": site.get('country'),
            "latitude": site.get('latitude'),
            "longitude": site.get('longitude'),
            "timezone": site.get('timezone'),
            "metadata": metadata_value,
            "created_at": site['created_at'].isoformat() if site.get('created_at') else None,
            "updated_at": site['updated_at'].isoformat() if site.get('updated_at') else None
        }

        if include_stats:
            result['space_count'] = site.get('space_count', 0) or 0
            result['device_count'] = site.get('device_count', 0) or 0
            result['gateway_count'] = site.get('gateway_count', 0) or 0
            result['free_spaces'] = site.get('free_spaces', 0) or 0
            result['occupied_spaces'] = site.get('occupied_spaces', 0) or 0

        return result
