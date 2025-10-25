"""V6 Reservations Router - Reservation management with idempotency"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional
from uuid import UUID
from datetime import datetime

from ...core.database import get_db
from ...core.tenant_context_v6 import get_tenant_context_v6, TenantContextV6
from ...services.reservation_service import ReservationService
from ...schemas.reservation import (
    ReservationCreate,
    ReservationUpdate,
    ReservationResponse,
    ReservationCancel,
    ReservationListResponse
)

router = APIRouter(prefix="/api/v6/reservations", tags=["reservations-v6"])


@router.post("/", response_model=dict, status_code=201)
async def create_reservation(
    reservation_data: ReservationCreate,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Create a new reservation with idempotency support

    Use the `request_id` field to ensure duplicate requests don't create multiple reservations.
    If a reservation with the same `request_id` already exists, it will be returned instead.
    """
    service = ReservationService(db, tenant)
    try:
        return await service.create_reservation(
            space_id=reservation_data.space_id,
            start_time=reservation_data.start_time,
            end_time=reservation_data.end_time,
            user_email=reservation_data.user_email,
            user_name=reservation_data.user_name,
            notes=reservation_data.notes,
            metadata=reservation_data.metadata,
            request_id=reservation_data.request_id
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("", response_model=ReservationListResponse)
async def list_reservations(
    space_id: Optional[UUID] = Query(None, description="Filter by space ID"),
    status: Optional[str] = Query(None, description="Filter by status (active, completed, cancelled, expired)"),
    start_date: Optional[datetime] = Query(None, description="Filter reservations ending after this date"),
    end_date: Optional[datetime] = Query(None, description="Filter reservations starting before this date"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(50, ge=1, le=200, description="Items per page"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    List reservations with optional filtering and pagination
    """
    service = ReservationService(db, tenant)
    try:
        result = await service.list_reservations(
            space_id=space_id,
            status=status,
            start_date=start_date,
            end_date=end_date,
            page=page,
            page_size=page_size
        )
        return ReservationListResponse(**result)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{reservation_id}", response_model=dict)
async def get_reservation(
    reservation_id: UUID = Path(..., description="Reservation ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get a single reservation by ID
    """
    service = ReservationService(db, tenant)
    try:
        return await service.get_reservation(reservation_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{reservation_id}/cancel")
async def cancel_reservation(
    reservation_id: UUID = Path(..., description="Reservation ID"),
    cancel_data: ReservationCancel = None,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Cancel an active reservation
    """
    service = ReservationService(db, tenant)
    try:
        cancellation_reason = cancel_data.cancellation_reason if cancel_data else None
        return await service.cancel_reservation(
            reservation_id,
            cancellation_reason=cancellation_reason
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/expire-old")
async def expire_old_reservations(
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Expire old reservations (background job endpoint)

    This endpoint should be called periodically (e.g., every minute) to:
    - Mark reservations as 'expired' if their end_time has passed
    - Update space states from 'reserved' to 'free' if no active reservation exists

    Typically called by a scheduler, not by end users.
    """
    # Only allow platform admins to trigger this
    if not tenant.is_platform_admin:
        raise HTTPException(
            status_code=403,
            detail="Only platform admins can trigger expiration job"
        )

    service = ReservationService(db, tenant)
    try:
        return await service.expire_old_reservations()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{space_id}/check-availability")
async def check_availability(
    space_id: UUID = Path(..., description="Space ID"),
    start_time: datetime = Query(..., description="Reservation start time"),
    end_time: datetime = Query(..., description="Reservation end time"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Check if a space is available for a specific time range

    Returns:
    - is_available: boolean
    - conflicting_reservations: list of overlapping reservations
    """
    service = ReservationService(db, tenant)
    try:
        result = await service.check_availability(space_id, start_time, end_time)
        return {
            "space_id": str(space_id),
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
