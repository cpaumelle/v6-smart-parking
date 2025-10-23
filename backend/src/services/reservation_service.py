"""Reservation Service V6 with idempotency and tenant scoping"""

from typing import List, Optional
from uuid import UUID
from datetime import datetime, timedelta
from asyncpg import UniqueViolationError


class ReservationService:
    """Reservation service with tenant scoping and idempotency"""

    def __init__(self, db, tenant_context):
        self.db = db
        self.tenant = tenant_context

    async def create_reservation(
        self,
        space_id: UUID,
        start_time: datetime,
        end_time: datetime,
        user_email: Optional[str] = None,
        user_name: Optional[str] = None,
        notes: Optional[str] = None,
        metadata: dict = None,
        request_id: Optional[str] = None
    ) -> dict:
        """
        Create a reservation with idempotency support

        Args:
            space_id: UUID of the space to reserve
            start_time: Reservation start time
            end_time: Reservation end time
            user_email: Optional user email
            user_name: Optional user name
            notes: Optional notes
            metadata: Optional metadata dictionary
            request_id: Idempotency key to prevent duplicates

        Returns:
            dict with reservation details
        """

        # Validate times
        if end_time <= start_time:
            raise ValueError("end_time must be after start_time")

        if start_time < datetime.utcnow():
            raise ValueError("Cannot create reservation in the past")

        # Check for duplicate request_id (idempotency)
        if request_id:
            existing = await self.db.fetchrow("""
                SELECT id, space_id, start_time, end_time, status
                FROM reservations
                WHERE tenant_id = $1 AND metadata->>'request_id' = $2
            """, self.tenant.tenant_id, request_id)

            if existing:
                # Return existing reservation
                return {
                    "id": str(existing['id']),
                    "space_id": str(existing['space_id']),
                    "start_time": existing['start_time'].isoformat(),
                    "end_time": existing['end_time'].isoformat(),
                    "status": existing['status'],
                    "is_duplicate": True,
                    "message": "Reservation already exists (idempotent request)"
                }

        # Verify space exists and belongs to tenant
        space = await self.db.fetchrow("""
            SELECT id, code, current_state, enabled
            FROM spaces
            WHERE id = $1 AND tenant_id = $2
        """, space_id, self.tenant.tenant_id)

        if not space:
            raise ValueError(f"Space {space_id} not found or does not belong to your tenant")

        if not space['enabled']:
            raise ValueError(f"Space {space['code']} is not enabled for reservations")

        # Check for overlapping reservations
        overlapping = await self.check_availability(space_id, start_time, end_time)
        if not overlapping['is_available']:
            raise ValueError(
                f"Space is not available during the requested time. "
                f"Conflicts: {len(overlapping['conflicting_reservations'])}"
            )

        # Prepare metadata
        reservation_metadata = metadata or {}
        if request_id:
            reservation_metadata['request_id'] = request_id

        # Create reservation
        try:
            reservation_id = await self.db.fetchval("""
                INSERT INTO reservations (
                    tenant_id, space_id, user_id, user_email, user_name,
                    start_time, end_time, status, notes, metadata,
                    checked_in, payment_status, created_at, updated_at
                )
                VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, $13, $13)
                RETURNING id
            """,
                self.tenant.tenant_id,
                space_id,
                self.tenant.user_id,
                user_email,
                user_name,
                start_time,
                end_time,
                'active',
                notes,
                reservation_metadata,
                False,
                'pending',
                datetime.utcnow()
            )
        except UniqueViolationError as e:
            raise ValueError(f"Reservation conflict detected: {str(e)}")

        # Update space state if reservation starts soon (within 15 minutes)
        if start_time <= datetime.utcnow() + timedelta(minutes=15):
            await self.db.execute("""
                UPDATE spaces
                SET current_state = 'reserved',
                    state_changed_at = $1,
                    updated_at = $1
                WHERE id = $2 AND current_state NOT IN ('occupied', 'maintenance')
            """, datetime.utcnow(), space_id)

        return {
            "id": str(reservation_id),
            "space_id": str(space_id),
            "space_code": space['code'],
            "start_time": start_time.isoformat(),
            "end_time": end_time.isoformat(),
            "status": "active",
            "is_duplicate": False,
            "message": "Reservation created successfully"
        }

    async def check_availability(
        self,
        space_id: UUID,
        start_time: datetime,
        end_time: datetime
    ) -> dict:
        """
        Check if a space is available for the given time range

        Returns:
            dict with is_available and conflicting_reservations
        """

        # Find overlapping reservations
        # Two time ranges overlap if: start1 < end2 AND start2 < end1
        conflicts = await self.db.fetch("""
            SELECT id, start_time, end_time, status, user_name
            FROM reservations
            WHERE space_id = $1
              AND tenant_id = $2
              AND status = 'active'
              AND start_time < $4
              AND end_time > $3
        """, space_id, self.tenant.tenant_id, start_time, end_time)

        return {
            "is_available": len(conflicts) == 0,
            "conflicting_reservations": [
                {
                    "id": str(c['id']),
                    "start_time": c['start_time'].isoformat(),
                    "end_time": c['end_time'].isoformat(),
                    "user_name": c['user_name']
                }
                for c in conflicts
            ]
        }

    async def list_reservations(
        self,
        space_id: Optional[UUID] = None,
        status: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 50
    ) -> dict:
        """List reservations with filtering and pagination"""

        # Build query
        query = """
            SELECT
                r.id, r.tenant_id, r.space_id, r.user_id, r.user_email, r.user_name,
                r.start_time, r.end_time, r.status, r.checked_in,
                r.checked_in_at, r.checked_out_at, r.rate, r.total_cost,
                r.payment_status, r.cancelled_at, r.notes, r.metadata,
                r.created_at, r.updated_at,
                s.code as space_code
            FROM reservations r
            JOIN spaces s ON s.id = r.space_id
            WHERE r.tenant_id = $1
        """
        params = [self.tenant.tenant_id]
        param_count = 1

        if space_id:
            param_count += 1
            query += f" AND r.space_id = ${param_count}"
            params.append(space_id)

        if status:
            param_count += 1
            query += f" AND r.status = ${param_count}"
            params.append(status)

        if start_date:
            param_count += 1
            query += f" AND r.end_time >= ${param_count}"
            params.append(start_date)

        if end_date:
            param_count += 1
            query += f" AND r.start_time <= ${param_count}"
            params.append(end_date)

        # Get total count
        count_query = f"SELECT COUNT(*) FROM ({query}) AS count_query"
        total = await self.db.fetchval(count_query, *params)

        # Add pagination
        query += f" ORDER BY r.start_time DESC LIMIT ${param_count + 1} OFFSET ${param_count + 2}"
        params.extend([page_size, (page - 1) * page_size])

        # Execute query
        reservations = await self.db.fetch(query, *params)

        return {
            "reservations": [self._reservation_to_dict(r) for r in reservations],
            "total": total,
            "page": page,
            "page_size": page_size,
            "total_pages": (total + page_size - 1) // page_size
        }

    async def get_reservation(self, reservation_id: UUID) -> dict:
        """Get a single reservation by ID"""

        reservation = await self.db.fetchrow("""
            SELECT
                r.id, r.tenant_id, r.space_id, r.user_id, r.user_email, r.user_name,
                r.start_time, r.end_time, r.status, r.checked_in,
                r.checked_in_at, r.checked_out_at, r.rate, r.total_cost,
                r.payment_status, r.cancelled_at, r.cancelled_by,
                r.cancellation_reason, r.notes, r.metadata,
                r.created_at, r.updated_at,
                s.code as space_code
            FROM reservations r
            JOIN spaces s ON s.id = r.space_id
            WHERE r.id = $1 AND r.tenant_id = $2
        """, reservation_id, self.tenant.tenant_id)

        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found")

        return self._reservation_to_dict(reservation)

    async def cancel_reservation(
        self,
        reservation_id: UUID,
        cancellation_reason: Optional[str] = None
    ) -> dict:
        """Cancel a reservation"""

        # Get reservation
        reservation = await self.db.fetchrow("""
            SELECT id, space_id, status, start_time, end_time
            FROM reservations
            WHERE id = $1 AND tenant_id = $2
        """, reservation_id, self.tenant.tenant_id)

        if not reservation:
            raise ValueError(f"Reservation {reservation_id} not found")

        if reservation['status'] != 'active':
            raise ValueError(f"Cannot cancel reservation with status: {reservation['status']}")

        # Update reservation
        await self.db.execute("""
            UPDATE reservations
            SET status = 'cancelled',
                cancelled_at = $1,
                cancelled_by = $2,
                cancellation_reason = $3,
                updated_at = $1
            WHERE id = $4
        """, datetime.utcnow(), self.tenant.user_id, cancellation_reason, reservation_id)

        # Update space state if it was reserved
        await self.db.execute("""
            UPDATE spaces
            SET current_state = 'free',
                state_changed_at = $1,
                updated_at = $1
            WHERE id = $2 AND current_state = 'reserved'
        """, datetime.utcnow(), reservation['space_id'])

        return {
            "success": True,
            "reservation_id": str(reservation_id),
            "message": "Reservation cancelled successfully"
        }

    async def expire_old_reservations(self) -> dict:
        """
        Background job to expire old reservations
        Should be run periodically (e.g., every minute)
        """

        now = datetime.utcnow()

        # Expire reservations that have ended
        # RETURNING can't use aggregate functions, so we fetch all IDs and count them
        expired_ids = await self.db.fetch("""
            UPDATE reservations
            SET status = 'expired',
                updated_at = $1
            WHERE status = 'active'
              AND end_time < $1
              AND checked_in = false
            RETURNING id
        """, now)

        expired_count = len(expired_ids)

        # Update spaces from reserved to free if reservation expired
        await self.db.execute("""
            UPDATE spaces s
            SET current_state = 'free',
                state_changed_at = $1,
                updated_at = $1
            WHERE current_state = 'reserved'
              AND NOT EXISTS (
                  SELECT 1 FROM reservations r
                  WHERE r.space_id = s.id
                    AND r.status = 'active'
                    AND r.start_time <= $1
                    AND r.end_time >= $1
              )
        """, now)

        return {
            "expired_count": expired_count or 0,
            "timestamp": now.isoformat()
        }

    def _reservation_to_dict(self, reservation) -> dict:
        """Convert reservation row to dictionary"""
        return {
            "id": str(reservation['id']),
            "tenant_id": str(reservation['tenant_id']),
            "space_id": str(reservation['space_id']),
            "space_code": reservation.get('space_code'),
            "user_id": str(reservation['user_id']),
            "user_email": reservation['user_email'],
            "user_name": reservation['user_name'],
            "start_time": reservation['start_time'].isoformat() if reservation['start_time'] else None,
            "end_time": reservation['end_time'].isoformat() if reservation['end_time'] else None,
            "status": reservation['status'],
            "checked_in": reservation['checked_in'],
            "checked_in_at": reservation['checked_in_at'].isoformat() if reservation.get('checked_in_at') else None,
            "checked_out_at": reservation['checked_out_at'].isoformat() if reservation.get('checked_out_at') else None,
            "rate": reservation.get('rate'),
            "total_cost": reservation.get('total_cost'),
            "payment_status": reservation['payment_status'],
            "cancelled_at": reservation['cancelled_at'].isoformat() if reservation.get('cancelled_at') else None,
            "cancelled_by": str(reservation['cancelled_by']) if reservation.get('cancelled_by') else None,
            "cancellation_reason": reservation.get('cancellation_reason'),
            "notes": reservation.get('notes'),
            "metadata": reservation.get('metadata', {}),
            "created_at": reservation['created_at'].isoformat() if reservation['created_at'] else None,
            "updated_at": reservation['updated_at'].isoformat() if reservation.get('updated_at') else None
        }
