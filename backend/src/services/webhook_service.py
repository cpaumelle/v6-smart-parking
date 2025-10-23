"""Webhook Service for handling ChirpStack uplink messages"""

import hmac
import hashlib
import json
import os
from typing import Dict, Any, Optional
from uuid import UUID
from datetime import datetime
from pathlib import Path


class WebhookService:
    """
    Handle sensor uplink webhooks from ChirpStack with:
    - HMAC-SHA256 signature validation
    - fcnt deduplication
    - Orphan device tracking
    - File spool for back-pressure
    """

    def __init__(self, db, spool_dir: str = "/tmp/parking_webhooks"):
        self.db = db
        self.webhook_secret = os.getenv("CHIRPSTACK_WEBHOOK_SECRET", "")
        self.spool_dir = Path(spool_dir)
        self.spool_dir.mkdir(parents=True, exist_ok=True)

    def validate_signature(self, payload: bytes, signature: str) -> bool:
        """
        Validate HMAC-SHA256 signature from ChirpStack

        Args:
            payload: Raw request body bytes
            signature: Signature from X-Signature header

        Returns:
            bool: True if signature is valid
        """
        if not self.webhook_secret:
            # If no secret configured, skip validation (development only)
            return True

        expected_signature = hmac.new(
            self.webhook_secret.encode(),
            payload,
            hashlib.sha256
        ).hexdigest()

        return hmac.compare_digest(signature, expected_signature)

    async def deduplicate_by_fcnt(
        self,
        dev_eui: str,
        fcnt: int
    ) -> bool:
        """
        Check if we've already processed this frame counter

        Args:
            dev_eui: Device EUI
            fcnt: Frame counter

        Returns:
            bool: True if this is a duplicate (should skip)
        """
        # Check if we have a recent message with same or higher fcnt
        existing = await self.db.fetchrow("""
            SELECT fcnt, received_at
            FROM sensor_readings
            WHERE dev_eui = $1
            ORDER BY received_at DESC
            LIMIT 1
        """, dev_eui.upper())

        if existing and existing['fcnt'] >= fcnt:
            return True  # Duplicate

        return False  # New message

    async def process_uplink(
        self,
        payload: Dict[str, Any],
        signature: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Process an uplink message from ChirpStack

        Args:
            payload: Decoded JSON payload
            signature: Optional HMAC signature for validation

        Returns:
            dict: Processing result
        """
        try:
            # Extract device info
            device_info = payload.get("deviceInfo", {})
            dev_eui = device_info.get("devEui", "").upper()

            if not dev_eui:
                raise ValueError("Missing devEui in payload")

            # Extract uplink data
            uplink_data = payload.get("data", "")
            fcnt = payload.get("fCnt", 0)
            rx_info = payload.get("rxInfo", [{}])[0] if payload.get("rxInfo") else {}
            rssi = rx_info.get("rssi")
            snr = rx_info.get("snr")

            # Deduplicate by frame counter
            if await self.deduplicate_by_fcnt(dev_eui, fcnt):
                return {
                    "status": "duplicate",
                    "dev_eui": dev_eui,
                    "fcnt": fcnt,
                    "message": "Duplicate message (already processed)"
                }

            # Find device
            device = await self.db.fetchrow("""
                SELECT id, tenant_id, assigned_space_id, status
                FROM sensor_devices
                WHERE dev_eui = $1
            """, dev_eui)

            if not device:
                # Orphan device - log it
                await self.track_orphan_device(dev_eui, payload)
                return {
                    "status": "orphan",
                    "dev_eui": dev_eui,
                    "message": "Device not found in database"
                }

            # Decode sensor data (example: simple occupancy byte)
            occupied = self._decode_sensor_data(uplink_data)

            # Store sensor reading
            reading_id = await self._store_sensor_reading(
                device['id'],
                device['tenant_id'],
                dev_eui,
                fcnt,
                occupied,
                rssi,
                snr,
                payload
            )

            # Update space occupancy if device is assigned
            if device['assigned_space_id']:
                await self._update_space_occupancy(
                    device['assigned_space_id'],
                    device['tenant_id'],
                    occupied
                )

                return {
                    "status": "processed",
                    "dev_eui": dev_eui,
                    "fcnt": fcnt,
                    "space_id": str(device['assigned_space_id']),
                    "occupied": occupied,
                    "reading_id": str(reading_id)
                }
            else:
                return {
                    "status": "unassigned",
                    "dev_eui": dev_eui,
                    "fcnt": fcnt,
                    "message": "Device not assigned to any space",
                    "reading_id": str(reading_id)
                }

        except Exception as e:
            # Spool to file on error for retry
            await self.spool_to_file(payload)
            raise Exception(f"Webhook processing failed: {str(e)}")

    def _decode_sensor_data(self, data: str) -> bool:
        """
        Decode uplink data to determine occupancy

        Args:
            data: Base64 or hex encoded sensor data

        Returns:
            bool: True if occupied, False if free

        Note: This is a simplified example. Real implementation would:
        - Support multiple sensor types
        - Handle different encoding formats
        - Parse complex payloads
        """
        try:
            # Example: First byte is occupancy (0x01 = occupied, 0x00 = free)
            if data:
                # Assuming hex string
                first_byte = int(data[:2], 16) if len(data) >= 2 else 0
                return first_byte == 1
        except:
            pass

        return False  # Default to free if can't decode

    async def _store_sensor_reading(
        self,
        device_id: UUID,
        tenant_id: UUID,
        dev_eui: str,
        fcnt: int,
        occupied: bool,
        rssi: Optional[float],
        snr: Optional[float],
        raw_payload: Dict[str, Any]
    ) -> UUID:
        """Store sensor reading in database"""

        reading_id = await self.db.fetchval("""
            INSERT INTO sensor_readings (
                tenant_id, device_id, dev_eui, fcnt,
                occupied, rssi, snr, raw_payload,
                received_at, created_at
            )
            VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $9)
            RETURNING id
        """,
            tenant_id,
            device_id,
            dev_eui,
            fcnt,
            occupied,
            rssi,
            snr,
            json.dumps(raw_payload),
            datetime.utcnow()
        )

        # Update device last_seen_at
        await self.db.execute("""
            UPDATE sensor_devices
            SET last_seen_at = $1, updated_at = $1
            WHERE id = $2
        """, datetime.utcnow(), device_id)

        return reading_id

    async def _update_space_occupancy(
        self,
        space_id: UUID,
        tenant_id: UUID,
        occupied: bool
    ):
        """Update space current_state based on sensor reading"""

        new_state = 'occupied' if occupied else 'free'

        # Get current state
        current = await self.db.fetchrow("""
            SELECT current_state FROM spaces
            WHERE id = $1 AND tenant_id = $2
        """, space_id, tenant_id)

        if current and current['current_state'] != new_state:
            # State changed - update space
            await self.db.execute("""
                UPDATE spaces
                SET current_state = $1,
                    sensor_state = $1,
                    state_changed_at = $2,
                    updated_at = $2
                WHERE id = $3
            """, new_state, datetime.utcnow(), space_id)

    async def track_orphan_device(self, dev_eui: str, payload: Dict[str, Any]):
        """
        Track devices that send uplinks but aren't in our database

        This helps identify:
        - New devices that need to be provisioned
        - Misconfigured devices
        - Devices from wrong application
        """
        await self.db.execute("""
            INSERT INTO orphan_devices (
                dev_eui, first_seen, last_seen, message_count, last_payload
            )
            VALUES ($1, $2, $2, 1, $3)
            ON CONFLICT (dev_eui)
            DO UPDATE SET
                last_seen = $2,
                message_count = orphan_devices.message_count + 1,
                last_payload = $3
        """,
            dev_eui.upper(),
            datetime.utcnow(),
            json.dumps(payload)
        )

    async def spool_to_file(self, payload: Dict[str, Any]):
        """
        Write payload to file spool for later retry

        Used when database is under pressure or processing fails
        """
        timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S_%f")
        dev_eui = payload.get("deviceInfo", {}).get("devEui", "unknown")
        filename = f"{timestamp}_{dev_eui}.json"
        filepath = self.spool_dir / filename

        with open(filepath, 'w') as f:
            json.dump(payload, f, indent=2)

    async def process_spool(self) -> Dict[str, Any]:
        """
        Process spooled webhook files (background job)

        Returns:
            dict: Processing statistics
        """
        processed = 0
        failed = 0
        files = list(self.spool_dir.glob("*.json"))

        for filepath in files:
            try:
                with open(filepath, 'r') as f:
                    payload = json.load(f)

                await self.process_uplink(payload)

                # Delete file on success
                filepath.unlink()
                processed += 1

            except Exception as e:
                failed += 1
                # Keep file for manual review if failed multiple times
                # Could add retry count logic here

        return {
            "processed": processed,
            "failed": failed,
            "remaining": len(list(self.spool_dir.glob("*.json")))
        }
