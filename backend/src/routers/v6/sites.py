"""V6 Sites Router - Site/location management"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from ...core.database import get_db
from ...core.tenant_context_v6 import get_tenant_context_v6, TenantContextV6
from ...services.site_service import SiteService

router = APIRouter(prefix="/api/v6/sites", tags=["sites-v6"])


class SiteCreate(BaseModel):
    name: str
    slug: str
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    metadata: Optional[dict] = None


class SiteUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    address: Optional[str] = None
    city: Optional[str] = None
    state: Optional[str] = None
    postal_code: Optional[str] = None
    country: Optional[str] = None
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    timezone: Optional[str] = None
    metadata: Optional[dict] = None


@router.get("")
async def list_sites(
    include_stats: bool = Query(False, description="Include space and device counts"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    List sites with optional statistics

    Returns paginated list of sites for the current tenant.
    Platform admins see sites for the tenant they're currently viewing.
    """
    service = SiteService(db, tenant)
    try:
        return await service.list_sites(
            include_stats=include_stats,
            page=page,
            page_size=page_size
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/occupancy/all")
async def get_all_sites_occupancy(
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get occupancy statistics for all sites in the current tenant

    Returns real-time occupancy data for each site.
    """
    service = SiteService(db, tenant)
    try:
        return await service.get_all_sites_occupancy()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{site_id}")
async def get_site(
    site_id: UUID = Path(..., description="Site ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get a single site by ID with statistics
    """
    service = SiteService(db, tenant)
    try:
        return await service.get_site(site_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{site_id}/occupancy")
async def get_site_occupancy(
    site_id: UUID = Path(..., description="Site ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get real-time occupancy statistics for a specific site

    Returns detailed occupancy breakdown by space state.
    """
    service = SiteService(db, tenant)
    try:
        return await service.get_site_occupancy(site_id)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
async def create_site(
    site_data: SiteCreate,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Create a new site

    Requires owner or admin role.
    """
    service = SiteService(db, tenant)
    try:
        return await service.create_site(
            name=site_data.name,
            slug=site_data.slug,
            address=site_data.address,
            city=site_data.city,
            state=site_data.state,
            postal_code=site_data.postal_code,
            country=site_data.country,
            latitude=site_data.latitude,
            longitude=site_data.longitude,
            timezone=site_data.timezone,
            metadata=site_data.metadata
        )
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{site_id}")
async def update_site(
    site_id: UUID = Path(..., description="Site ID"),
    site_data: SiteUpdate = None,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Update a site

    Requires owner or admin role.
    """
    service = SiteService(db, tenant)
    try:
        updates = site_data.model_dump(exclude_unset=True)
        return await service.update_site(site_id, **updates)
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{site_id}")
async def delete_site(
    site_id: UUID = Path(..., description="Site ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Delete a site

    Prevents deletion if site has active spaces or gateways.
    Requires owner or admin role.
    """
    service = SiteService(db, tenant)
    try:
        return await service.delete_site(site_id)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
