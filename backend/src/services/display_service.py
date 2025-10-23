"""Display Service - State machine and policy management for display devices"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from enum import Enum

from .downlink_service import DownlinkService


class DisplayColor(str, Enum):
    """Display LED colors"""
    GREEN = "green"
    RED = "red"
    BLUE = "blue"
    YELLOW = "yellow"
    ORANGE = "orange"
    WHITE = "white"
    OFF = "off"


class DisplayState(str, Enum):
    """Display device states"""
    FREE = "free"
    OCCUPIED = "occupied"
    RESERVED = "reserved"
    MAINTENANCE = "maintenance"
    ERROR = "error"
    UNKNOWN = "unknown"


# Display policies map space states to display colors/patterns
DEFAULT_DISPLAY_POLICY = {
    "free": {"color": DisplayColor.GREEN, "pattern": "solid"},
    "occupied": {"color": DisplayColor.RED, "pattern": "solid"},
    "reserved": {"color": DisplayColor.BLUE, "pattern": "blink"},
    "maintenance": {"color": DisplayColor.ORANGE, "pattern": "solid"},
    "unknown": {"color": DisplayColor.YELLOW, "pattern": "slow_blink"},
    "error": {"color": DisplayColor.RED, "pattern": "fast_blink"}
}


class DisplayService:
    """
    Display device state machine and policy management

    Features:
    - Policy-driven display states
    - State transitions
    - Command queuing via DownlinkService
    - Display configuration per tenant/site
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context
        self.downlink_service = DownlinkService(db, tenant_context)

    async def update_display_for_space(
        self,
        space_id: UUID,
        new_state: str,
        reason: str = "space_state_change"
    ) -> Dict[str, Any]:
        """
        Update display device based on space state

        Args:
            space_id: Space UUID
            new_state: New space state (free, occupied, reserved, etc.)
            reason: Reason for update

        Returns:
            dict: Update result
        """

        # Get space with display device
        space = await self.db.fetchrow("""
            SELECT s.id, s.code, s.current_state, s.display_device_id,
                   s.config, s.tenant_id,
                   dd.dev_eui as display_dev_eui,
                   dd.status as display_status
            FROM spaces s
            LEFT JOIN display_devices dd ON dd.id = s.display_device_id
            WHERE s.id = $1 AND s.tenant_id = $2
        """, space_id, self.tenant.tenant_id)

        if not space:
            raise ValueError(f"Space {space_id} not found")

        if not space['display_device_id']:
            return {
                "success": False,
                "space_id": str(space_id),
                "message": "Space has no display device assigned"
            }

        # Get display policy (from space config, site config, or default)
        policy = await self._get_display_policy(space)

        # Get display command from policy
        display_config = policy.get(new_state, policy.get("unknown"))

        # Queue downlink command
        command_id = await self.downlink_service.queue_command(
            device_id=space['display_device_id'],
            command="set_display",
            payload={
                "color": display_config["color"],
                "pattern": display_config["pattern"],
                "space_code": space['code'],
                "state": new_state,
                "reason": reason
            },
            priority=3,  # Normal priority
            confirmed=False
        )

        # Update display state in database
        await self.db.execute("""
            UPDATE spaces
            SET display_state = $1,
                updated_at = $2
            WHERE id = $3
        """, display_config["color"], datetime.utcnow(), space_id)

        return {
            "success": True,
            "space_id": str(space_id),
            "space_code": space['code'],
            "display_device_id": str(space['display_device_id']),
            "new_state": new_state,
            "display_color": display_config["color"],
            "display_pattern": display_config["pattern"],
            "command_id": str(command_id),
            "message": f"Display command queued for {space['code']}"
        }

    async def update_bulk_displays(
        self,
        site_id: UUID,
        state_filter: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Update multiple displays at once (e.g., all spaces in a site)

        Args:
            site_id: Site UUID
            state_filter: Optional state filter (only update spaces in this state)

        Returns:
            dict: Bulk update result
        """

        query = """
            SELECT s.id, s.code, s.current_state, s.display_device_id
            FROM spaces s
            WHERE s.site_id = $1
              AND s.tenant_id = $2
              AND s.display_device_id IS NOT NULL
        """
        params = [site_id, self.tenant.tenant_id]

        if state_filter:
            query += " AND s.current_state = $3"
            params.append(state_filter)

        spaces = await self.db.fetch(query, *params)

        queued_count = 0
        failed_count = 0

        for space in spaces:
            try:
                await self.update_display_for_space(
                    space['id'],
                    space['current_state'],
                    reason="bulk_update"
                )
                queued_count += 1
            except Exception as e:
                failed_count += 1

        return {
            "success": True,
            "site_id": str(site_id),
            "total_spaces": len(spaces),
            "queued": queued_count,
            "failed": failed_count
        }

    async def set_display_color(
        self,
        device_id: UUID,
        color: str,
        pattern: str = "solid",
        priority: int = 5
    ) -> Dict[str, Any]:
        """
        Directly set display color (manual override)

        Args:
            device_id: Display device UUID
            color: Color to display
            pattern: Display pattern (solid, blink, etc.)
            priority: Command priority

        Returns:
            dict: Command result
        """

        command_id = await self.downlink_service.queue_command(
            device_id=device_id,
            command="set_display",
            payload={
                "color": color,
                "pattern": pattern,
                "manual_override": True
            },
            priority=priority,
            confirmed=False
        )

        return {
            "success": True,
            "device_id": str(device_id),
            "command_id": str(command_id),
            "color": color,
            "pattern": pattern,
            "message": "Manual display command queued"
        }

    async def reboot_display(self, device_id: UUID) -> Dict[str, Any]:
        """
        Send reboot command to display device

        Args:
            device_id: Display device UUID

        Returns:
            dict: Command result
        """

        command_id = await self.downlink_service.queue_command(
            device_id=device_id,
            command="reboot",
            payload={},
            priority=1,  # High priority
            confirmed=True  # Request confirmation
        )

        return {
            "success": True,
            "device_id": str(device_id),
            "command_id": str(command_id),
            "message": "Reboot command queued"
        }

    async def _get_display_policy(self, space: dict) -> Dict[str, Dict[str, str]]:
        """
        Get display policy for a space

        Priority:
        1. Space-specific config
        2. Site-specific config
        3. Tenant-specific config
        4. Default policy

        Args:
            space: Space database row

        Returns:
            dict: Display policy mapping
        """

        # Check space config
        import json
        config = space.get('config', {})
        if isinstance(config, str):
            config = json.loads(config) if config else {}

        if config.get('display_policy'):
            return config['display_policy']

        # Check site config
        # TODO: Implement site-level policies

        # Check tenant config
        # TODO: Implement tenant-level policies

        # Return default
        return DEFAULT_DISPLAY_POLICY

    async def get_display_stats(self) -> Dict[str, Any]:
        """
        Get display device statistics

        Returns:
            dict: Display statistics
        """

        stats = await self.db.fetchrow("""
            SELECT
                COUNT(*) as total_displays,
                COUNT(*) FILTER (WHERE status = 'active') as active,
                COUNT(*) FILTER (WHERE status = 'inactive') as inactive,
                COUNT(*) FILTER (WHERE assigned_space_id IS NOT NULL) as assigned,
                COUNT(*) FILTER (WHERE assigned_space_id IS NULL) as unassigned
            FROM display_devices
            WHERE tenant_id = $1
        """, self.tenant.tenant_id)

        # Get pending commands
        pending_commands = await self.db.fetchval("""
            SELECT COUNT(*)
            FROM downlink_queue
            WHERE tenant_id = $1
              AND status IN ('queued', 'pending')
        """, self.tenant.tenant_id)

        return {
            "total_displays": stats['total_displays'] or 0,
            "active": stats['active'] or 0,
            "inactive": stats['inactive'] or 0,
            "assigned": stats['assigned'] or 0,
            "unassigned": stats['unassigned'] or 0,
            "pending_commands": pending_commands or 0,
            "tenant_id": str(self.tenant.tenant_id)
        }
