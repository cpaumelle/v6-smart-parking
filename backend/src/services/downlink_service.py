"""Downlink Service - Queue and send commands to display devices"""

from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime
import json


class DownlinkService:
    """
    Manage downlink commands to display devices

    Features:
    - Redis-backed FIFO queue
    - Command prioritization
    - Retry logic
    - Command history
    """

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def queue_command(
        self,
        device_id: UUID,
        command: str,
        payload: Dict[str, Any],
        priority: int = 5,
        confirmed: bool = False
    ) -> UUID:
        """
        Queue a downlink command for a display device

        Args:
            device_id: Display device UUID
            command: Command type (e.g., "set_color", "set_text", "reboot")
            payload: Command payload
            priority: Priority 1-10 (1=highest)
            confirmed: Whether to request confirmation from device

        Returns:
            UUID: Command ID
        """

        # Verify device exists and belongs to tenant
        device = await self.db.fetchrow("""
            SELECT id, dev_eui, status, tenant_id
            FROM display_devices
            WHERE id = $1
        """, device_id)

        if not device:
            raise ValueError(f"Display device {device_id} not found")

        if not self.tenant.can_access_tenant(device['tenant_id']):
            raise PermissionError("Cannot access device from another tenant")

        # Create downlink command
        command_id = await self.db.fetchval("""
            INSERT INTO downlink_queue (
                tenant_id, device_id, dev_eui, command_type,
                payload, priority, confirmed, status,
                created_at, updated_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, 'queued', $8, $8)
            RETURNING id
        """,
            device['tenant_id'],
            device_id,
            device['dev_eui'],
            command,
            json.dumps(payload),
            priority,
            confirmed,
            datetime.utcnow()
        )

        return command_id

    async def get_next_command(self, dev_eui: str) -> Optional[Dict[str, Any]]:
        """
        Get the next queued command for a device

        Args:
            dev_eui: Device EUI

        Returns:
            dict: Command details or None if queue is empty
        """

        # Get highest priority pending command
        command = await self.db.fetchrow("""
            SELECT id, device_id, dev_eui, command_type, payload,
                   priority, confirmed, created_at
            FROM downlink_queue
            WHERE dev_eui = $1
              AND status = 'queued'
            ORDER BY priority ASC, created_at ASC
            LIMIT 1
        """, dev_eui.upper())

        if not command:
            return None

        # Mark as pending
        await self.db.execute("""
            UPDATE downlink_queue
            SET status = 'pending',
                sent_at = $1,
                updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), command['id'])

        return {
            "id": str(command['id']),
            "command_type": command['command_type'],
            "payload": json.loads(command['payload']) if isinstance(command['payload'], str) else command['payload'],
            "confirmed": command['confirmed'],
            "created_at": command['created_at'].isoformat()
        }

    async def mark_command_sent(self, command_id: UUID, fcnt: Optional[int] = None):
        """
        Mark a command as successfully sent

        Args:
            command_id: Command UUID
            fcnt: Frame counter (if applicable)
        """

        await self.db.execute("""
            UPDATE downlink_queue
            SET status = 'sent',
                fcnt = $1,
                updated_at = $2
            WHERE id = $3
        """, fcnt, datetime.utcnow(), command_id)

    async def mark_command_confirmed(self, command_id: UUID):
        """
        Mark a command as confirmed by device

        Args:
            command_id: Command UUID
        """

        await self.db.execute("""
            UPDATE downlink_queue
            SET status = 'confirmed',
                confirmed_at = $1,
                updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), command_id)

    async def mark_command_failed(
        self,
        command_id: UUID,
        error: str,
        retry: bool = True
    ):
        """
        Mark a command as failed

        Args:
            command_id: Command UUID
            error: Error message
            retry: Whether to retry the command
        """

        # Get current retry count
        command = await self.db.fetchrow("""
            SELECT retry_count FROM downlink_queue WHERE id = $1
        """, command_id)

        if not command:
            return

        retry_count = (command['retry_count'] or 0) + 1
        max_retries = 3

        if retry and retry_count < max_retries:
            # Requeue for retry
            await self.db.execute("""
                UPDATE downlink_queue
                SET status = 'queued',
                    retry_count = $1,
                    last_error = $2,
                    updated_at = $3
                WHERE id = $4
            """, retry_count, error, datetime.utcnow(), command_id)
        else:
            # Mark as permanently failed
            await self.db.execute("""
                UPDATE downlink_queue
                SET status = 'failed',
                    retry_count = $1,
                    last_error = $2,
                    updated_at = $3
                WHERE id = $4
            """, retry_count, error, datetime.utcnow(), command_id)

    async def get_command_history(
        self,
        device_id: Optional[UUID] = None,
        limit: int = 50
    ) -> list:
        """
        Get command history

        Args:
            device_id: Optional device filter
            limit: Maximum number of commands to return

        Returns:
            list: Command history
        """

        query = """
            SELECT id, device_id, dev_eui, command_type, payload,
                   status, priority, confirmed, created_at, sent_at,
                   confirmed_at, last_error
            FROM downlink_queue
            WHERE tenant_id = $1
        """
        params = [self.tenant.tenant_id]

        if device_id:
            query += " AND device_id = $2"
            params.append(device_id)

        query += " ORDER BY created_at DESC LIMIT $" + str(len(params) + 1)
        params.append(limit)

        commands = await self.db.fetch(query, *params)

        return [
            {
                "id": str(c['id']),
                "device_id": str(c['device_id']),
                "dev_eui": c['dev_eui'],
                "command_type": c['command_type'],
                "payload": json.loads(c['payload']) if isinstance(c['payload'], str) else c['payload'],
                "status": c['status'],
                "priority": c['priority'],
                "confirmed": c['confirmed'],
                "created_at": c['created_at'].isoformat() if c['created_at'] else None,
                "sent_at": c['sent_at'].isoformat() if c.get('sent_at') else None,
                "confirmed_at": c['confirmed_at'].isoformat() if c.get('confirmed_at') else None,
                "last_error": c.get('last_error')
            }
            for c in commands
        ]

    async def clear_queue(self, device_id: UUID):
        """
        Clear all queued commands for a device

        Args:
            device_id: Device UUID
        """

        await self.db.execute("""
            DELETE FROM downlink_queue
            WHERE device_id = $1
              AND tenant_id = $2
              AND status IN ('queued', 'pending')
        """, device_id, self.tenant.tenant_id)
