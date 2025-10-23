"""V6 Spaces Router - CRUD operations for parking spaces"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional
from uuid import UUID

from ...core.database import get_db
from ...core.tenant_context_v6 import get_tenant_context_v6, TenantContextV6
from ...services.space_service import SpaceService
from ...schemas.space import (
    SpaceCreate,
    SpaceUpdate,
    SpaceResponse,
    SpaceAvailabilityRequest,
    SpaceAvailabilityResponse
)

router = APIRouter(prefix="/api/v6/spaces", tags=["spaces-v6"])


@router.get("/", response_model=dict)
async def list_spaces(
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    current_state: Optional[str] = Query(None, description="Filter by state (free, occupied, reserved, etc.)"),
    include_devices: bool = Query(False, description="Include device information"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    List parking spaces with optional filtering

    Returns paginated list of spaces with occupancy information.
    """
    service = SpaceService(db, tenant)
    try:
        return await service.list_spaces(
            site_id=site_id,
            current_state=current_state,
            include_devices=include_devices,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{space_id}", response_model=SpaceResponse)
async def get_space(
    space_id: UUID = Path(..., description="Space ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get a single space by ID with all details
    """
    service = SpaceService(db, tenant)
    try:
        return await service.get_space(space_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=SpaceResponse, status_code=201)
async def create_space(
    space_data: SpaceCreate,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Create a new parking space
    """
    service = SpaceService(db, tenant)
    try:
        return await service.create_space(
            site_id=space_data.site_id,
            code=space_data.code,
            name=space_data.name,
            display_name=space_data.display_name,
            enabled=space_data.enabled,
            auto_release_minutes=space_data.auto_release_minutes,
            config=space_data.config
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{space_id}", response_model=SpaceResponse)
async def update_space(
    space_id: UUID = Path(..., description="Space ID"),
    space_data: SpaceUpdate = None,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Update a parking space
    """
    service = SpaceService(db, tenant)
    try:
        updates = space_data.model_dump(exclude_unset=True)
        return await service.update_space(space_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{space_id}")
async def delete_space(
    space_id: UUID = Path(..., description="Space ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Delete a parking space (soft delete)
    """
    service = SpaceService(db, tenant)
    try:
        return await service.delete_space(space_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{space_id}/availability", response_model=SpaceAvailabilityResponse)
async def check_space_availability(
    space_id: UUID = Path(..., description="Space ID"),
    availability_request: SpaceAvailabilityRequest = None,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Check if a space is available for a given time range
    """
    from ...services.reservation_service import ReservationService

    service = ReservationService(db, tenant)
    try:
        result = await service.check_availability(
            space_id,
            availability_request.start_time,
            availability_request.end_time
        )
        return {
            "space_id": space_id,
            **result
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{space_id}/state")
async def update_space_state(
    space_id: UUID = Path(..., description="Space ID"),
    new_state: str = Query(..., description="New state (free, occupied, reserved, maintenance, unknown)"),
    sensor_state: Optional[str] = Query(None, description="Sensor-specific state"),
    display_state: Optional[str] = Query(None, description="Display-specific state"),
    source: str = Query("manual", description="Source of update"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Update space state (typically called by sensor webhook or manual override)
    """
    service = SpaceService(db, tenant)
    try:
        return await service.update_space_state(
            space_id,
            new_state,
            sensor_state=sensor_state,
            display_state=display_state,
            source=source
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/occupancy")
async def get_occupancy_stats(
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get occupancy statistics for spaces
    """
    service = SpaceService(db, tenant)
    try:
        return await service.get_occupancy_stats(site_id=site_id)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
