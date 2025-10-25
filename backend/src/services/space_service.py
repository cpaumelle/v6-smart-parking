"""Space Service V6 with occupancy tracking and tenant scoping"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime


class SpaceService:
    """Space service with tenant scoping and occupancy tracking"""

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def list_spaces(
        self,
        site_id: Optional[UUID] = None,
        current_state: Optional[str] = None,
        include_devices: bool = False,
        page: int = 1,
        page_size: int = 100
    ) -> dict:
        """
        List spaces with optional filtering

        Args:
            site_id: Filter by site
            current_state: Filter by state (free, occupied, reserved, maintenance, unknown)
            include_devices: Include device information
            page: Page number
            page_size: Items per page

        Returns:
            dict with spaces list and pagination info
        """

        # Build base query
        query = """
            SELECT
                s.id, s.tenant_id, s.site_id, s.code, s.name, s.display_name,
                s.current_state, s.sensor_state, s.display_state,
                s.state_changed_at, s.enabled, s.auto_release_minutes,
                s.sensor_device_id, s.display_device_id,
                s.config, s.created_at, s.updated_at
        """

        if include_devices:
            query += """,
                sd.dev_eui as sensor_dev_eui,
                sd.name as sensor_name,
                dd.dev_eui as display_dev_eui,
                dd.name as display_name
            """

        query += " FROM spaces s"

        if include_devices:
            query += """
                LEFT JOIN sensor_devices sd ON sd.id = s.sensor_device_id
                LEFT JOIN display_devices dd ON dd.id = s.display_device_id
            """

        query += " WHERE s.tenant_id = $1"
        params = [self.tenant.tenant_id]
        param_count = 1

        if site_id:
            param_count += 1
            query += f" AND s.site_id = ${param_count}"
            params.append(site_id)

        if current_state:
            param_count += 1
            query += f" AND s.current_state = ${param_count}"
            params.append(current_state)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
        total = await self.db.fetchval(count_query, *params)

        # Add ordering and pagination
        query += f" ORDER BY s.code LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([page_size, (page - 1) * page_size])

        # Execute query
        spaces = await self.db.fetch(query, *params)

        return {
            "spaces": [self._space_to_dict(s, include_devices) for s in spaces],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size,
            "tenant_id": str(self.tenant.tenant_id)
        }

    async def get_space(self, space_id: UUID) -> dict:
        """Get a single space by ID with all details"""

        space = await self.db.fetchrow("""
            SELECT
                s.id, s.tenant_id, s.site_id, s.code, s.name, s.display_name,
                s.current_state, s.sensor_state, s.display_state,
                s.state_changed_at, s.enabled, s.auto_release_minutes,
                s.sensor_device_id, s.display_device_id,
                s.config, s.created_at, s.updated_at,
                sd.dev_eui as sensor_dev_eui,
                sd.name as sensor_name,
                sd.status as sensor_status,
                dd.dev_eui as display_dev_eui,
                dd.name as display_name,
                dd.status as display_status
            FROM spaces s
            LEFT JOIN sensor_devices sd ON sd.id = s.sensor_device_id
            LEFT JOIN display_devices dd ON dd.id = s.display_device_id
            WHERE s.id = $1 AND s.tenant_id = $2
        """, space_id, self.tenant.tenant_id)

        if not space:
            raise ValueError(f"Space {space_id} not found")

        return self._space_to_dict(space, include_devices=True)

    async def get_space_by_sensor(self, dev_eui: str) -> Optional[dict]:
        """Get space assigned to a sensor device by DevEUI"""

        space = await self.db.fetchrow("""
            SELECT
                s.id, s.tenant_id, s.site_id, s.code, s.name, s.display_name,
                s.current_state, s.sensor_state, s.display_state,
                s.state_changed_at, s.enabled, s.auto_release_minutes,
                s.sensor_device_id, s.display_device_id,
                s.config, s.created_at, s.updated_at
            FROM spaces s
            JOIN sensor_devices sd ON sd.id = s.sensor_device_id
            WHERE sd.dev_eui = $1 AND s.tenant_id = $2
        """, dev_eui.upper(), self.tenant.tenant_id)

        if not space:
            return None

        return self._space_to_dict(space)

    async def create_space(
        self,
        site_id: UUID,
        code: str,
        name: Optional[str] = None,
        display_name: Optional[str] = None,
        enabled: bool = True,
        auto_release_minutes: Optional[int] = None,
        config: dict = None
    ) -> dict:
        """Create a new space"""

        # Verify site exists and check tenant access
        if self.tenant.is_platform_admin and self.tenant.is_viewing_platform_tenant:
            # Platform admin on Platform tenant can access any site
            site = await self.db.fetchrow("""
                SELECT id, tenant_id FROM sites WHERE id = $1
            """, site_id)
        else:
            # Regular users or platform admin on customer tenant: check tenant ownership
            site = await self.db.fetchrow("""
                SELECT id, tenant_id FROM sites WHERE id = $1 AND tenant_id = $2
            """, site_id, self.tenant.tenant_id)

        if not site:
            raise ValueError(f"Site {site_id} not found or does not belong to your tenant")

        # Check for duplicate code within site
        existing = await self.db.fetchrow("""
            SELECT id FROM spaces WHERE site_id = $1 AND code = $2
        """, site_id, code)

        if existing:
            raise ValueError(f"Space with code '{code}' already exists in this site")

        # Create space (use site's tenant_id, not user's tenant_id)
        import json
        config_json = json.dumps(config or {})
        space_id = await self.db.fetchval("""
            INSERT INTO spaces (
                tenant_id, site_id, code, name, display_name,
                enabled, auto_release_minutes, config,
                current_state, created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8::jsonb, 'unknown', $9, $9)
            RETURNING id
        """,
            site['tenant_id'],  # Use site's tenant_id
            site_id,
            code,
            name or code,
            display_name or name or code,
            enabled,
            auto_release_minutes,
            config_json,
            datetime.utcnow()
        )

        return await self.get_space(space_id)

    async def update_space(
        self,
        space_id: UUID,
        **updates
    ) -> dict:
        """Update a space"""

        # Verify space exists and belongs to tenant
        space = await self.db.fetchrow("""
            SELECT id FROM spaces WHERE id = $1 AND tenant_id = $2
        """, space_id, self.tenant.tenant_id)

        if not space:
            raise ValueError(f"Space {space_id} not found")

        # Build update query
        allowed_fields = [
            'code', 'name', 'display_name', 'enabled',
            'auto_release_minutes', 'config', 'current_state'
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

        # Add space_id for WHERE clause
        param_count += 1
        params.append(space_id)

        query = f"""
            UPDATE spaces
            SET {', '.join(update_fields)}
            WHERE id = ${param_count}
        """

        await self.db.execute(query, *params)

        return await self.get_space(space_id)

    async def delete_space(self, space_id: UUID) -> dict:
        """Delete a space (soft delete by setting deleted_at)"""

        # Verify space exists and belongs to tenant
        space = await self.db.fetchrow("""
            SELECT id, code FROM spaces WHERE id = $1 AND tenant_id = $2
        """, space_id, self.tenant.tenant_id)

        if not space:
            raise ValueError(f"Space {space_id} not found")

        # Check for active reservations
        active_reservations = await self.db.fetchval("""
            SELECT COUNT(*) FROM reservations
            WHERE space_id = $1 AND status = 'active'
        """, space_id)

        if active_reservations > 0:
            raise ValueError(
                f"Cannot delete space with {active_reservations} active reservations"
            )

        # Soft delete
        await self.db.execute("""
            UPDATE spaces
            SET deleted_at = $1, updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), space_id)

        return {
            "success": True,
            "space_id": str(space_id),
            "space_code": space['code'],
            "message": "Space deleted successfully"
        }

    async def update_space_state(
        self,
        space_id: UUID,
        new_state: str,
        sensor_state: Optional[str] = None,
        display_state: Optional[str] = None,
        source: str = "manual"
    ) -> dict:
        """
        Update space state from sensor readings or manual input

        Args:
            space_id: Space UUID
            new_state: New current state (free, occupied, reserved, maintenance, unknown)
            sensor_state: Optional sensor-specific state
            display_state: Optional display-specific state
            source: Source of update (manual, sensor, reservation, system)

        Returns:
            dict with updated space info
        """

        valid_states = ['free', 'occupied', 'reserved', 'maintenance', 'unknown']
        if new_state not in valid_states:
            raise ValueError(f"Invalid state: {new_state}. Must be one of {valid_states}")

        # Get current space state
        space = await self.db.fetchrow("""
            SELECT id, current_state, sensor_state, display_state
            FROM spaces
            WHERE id = $1 AND tenant_id = $2
        """, space_id, self.tenant.tenant_id)

        if not space:
            raise ValueError(f"Space {space_id} not found")

        # Only update if state changed
        if space['current_state'] == new_state:
            return {
                "space_id": str(space_id),
                "current_state": new_state,
                "changed": False,
                "message": "State unchanged"
            }

        # Update space state
        await self.db.execute("""
            UPDATE spaces
            SET current_state = $1,
                sensor_state = COALESCE($2, sensor_state),
                display_state = COALESCE($3, display_state),
                state_changed_at = $4,
                updated_at = $4
            WHERE id = $5
        """, new_state, sensor_state, display_state, datetime.utcnow(), space_id)

        # Log state change (for audit/analytics)
        # Could be stored in a separate state_history table

        return {
            "space_id": str(space_id),
            "previous_state": space['current_state'],
            "current_state": new_state,
            "changed": True,
            "source": source,
            "message": f"State updated from {space['current_state']} to {new_state}"
        }

    async def get_occupancy_stats(self, site_id: Optional[UUID] = None) -> dict:
        """
        Get occupancy statistics for spaces

        Args:
            site_id: Optional site filter

        Returns:
            dict with occupancy statistics
        """

        query = """
            SELECT
                current_state,
                COUNT(*) as count
            FROM spaces
            WHERE tenant_id = $1
              AND deleted_at IS NULL
        """
        params = [self.tenant.tenant_id]

        if site_id:
            query += " AND site_id = $2"
            params.append(site_id)

        query += " GROUP BY current_state"

        stats = await self.db.fetch(query, *params)

        # Get total count
        total = sum(s['count'] for s in stats)

        # Build response
        state_counts = {s['current_state']: s['count'] for s in stats}

        return {
            "total_spaces": total,
            "free": state_counts.get('free', 0),
            "occupied": state_counts.get('occupied', 0),
            "reserved": state_counts.get('reserved', 0),
            "maintenance": state_counts.get('maintenance', 0),
            "unknown": state_counts.get('unknown', 0),
            "available": state_counts.get('free', 0),  # free spaces are available
            "occupancy_rate": round(
                (state_counts.get('occupied', 0) / total * 100) if total > 0 else 0,
                2
            ),
            "site_id": str(site_id) if site_id else None,
            "tenant_id": str(self.tenant.tenant_id)
        }

    def _space_to_dict(self, space, include_devices: bool = False) -> dict:
        """Convert space row to dictionary"""
        import json
        # Handle config field - asyncpg returns JSONB as dict by default
        config_value = space.get('config', {})
        if isinstance(config_value, str):
            config_value = json.loads(config_value) if config_value else {}

        result = {
            "id": str(space['id']),
            "tenant_id": str(space['tenant_id']),
            "site_id": str(space['site_id']),
            "code": space['code'],
            "name": space['name'],
            "display_name": space['display_name'],
            "current_state": space['current_state'],
            "sensor_state": space.get('sensor_state'),
            "display_state": space.get('display_state'),
            "state_changed_at": space['state_changed_at'].isoformat() if space.get('state_changed_at') else None,
            "enabled": space['enabled'],
            "auto_release_minutes": space.get('auto_release_minutes'),
            "sensor_device_id": str(space['sensor_device_id']) if space.get('sensor_device_id') else None,
            "display_device_id": str(space['display_device_id']) if space.get('display_device_id') else None,
            "config": config_value,
            "created_at": space['created_at'].isoformat() if space.get('created_at') else None,
            "updated_at": space['updated_at'].isoformat() if space.get('updated_at') else None
        }

        if include_devices:
            result['sensor_device'] = {
                "dev_eui": space.get('sensor_dev_eui'),
                "name": space.get('sensor_name'),
                "status": space.get('sensor_status')
            } if space.get('sensor_dev_eui') else None

            result['display_device'] = {
                "dev_eui": space.get('display_dev_eui'),
                "name": space.get('display_name'),
                "status": space.get('display_status')
            } if space.get('display_dev_eui') else None

        return result
