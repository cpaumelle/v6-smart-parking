"""V6 Tenants Router - Tenant management (Platform Admin only)"""

from fastapi import APIRouter, Depends, Query, HTTPException, Path
from typing import Optional
from uuid import UUID
from pydantic import BaseModel

from ...core.database import get_db
from ...core.tenant_context_v6 import get_tenant_context_v6, TenantContextV6
from ...services.tenant_service import TenantService

router = APIRouter(prefix="/api/v6/tenants", tags=["tenants-v6"])


class TenantCreate(BaseModel):
    name: str
    slug: str
    tenant_type: str = 'customer'
    subscription_tier: str = 'basic'
    trial_days: Optional[int] = None
    features: Optional[dict] = None
    limits: Optional[dict] = None


class TenantUpdate(BaseModel):
    name: Optional[str] = None
    slug: Optional[str] = None
    type: Optional[str] = None
    is_active: Optional[bool] = None
    subscription_tier: Optional[str] = None
    subscription_status: Optional[str] = None
    trial_ends_at: Optional[str] = None
    features: Optional[dict] = None
    limits: Optional[dict] = None


class TenantSuspendRequest(BaseModel):
    reason: str


@router.get("")
async def list_tenants(
    tenant_type: Optional[str] = Query(None, description="Filter by type (platform, customer, trial)"),
    is_active: Optional[bool] = Query(None, description="Filter by active status"),
    page: int = Query(1, ge=1, description="Page number"),
    page_size: int = Query(100, ge=1, le=500, description="Items per page"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    List all tenants (Platform Admin only)

    Returns paginated list of tenants with subscription info.
    """
    service = TenantService(db, tenant)
    try:
        return await service.list_tenants(
            tenant_type=tenant_type,
            is_active=is_active,
            page=page,
            page_size=page_size
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_platform_stats(
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get platform-wide statistics (Platform Admin only)

    Returns statistics across all tenants.
    """
    service = TenantService(db, tenant)
    try:
        return await service.get_platform_stats()
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{tenant_id}")
async def get_tenant(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get a single tenant by ID with statistics (Platform Admin only)
    """
    service = TenantService(db, tenant)
    try:
        return await service.get_tenant(tenant_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("", status_code=201)
async def create_tenant(
    tenant_data: TenantCreate,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Create a new tenant (Platform Admin only)
    """
    service = TenantService(db, tenant)
    try:
        return await service.create_tenant(
            name=tenant_data.name,
            slug=tenant_data.slug,
            tenant_type=tenant_data.tenant_type,
            subscription_tier=tenant_data.subscription_tier,
            trial_days=tenant_data.trial_days,
            features=tenant_data.features,
            limits=tenant_data.limits
        )
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.put("/{tenant_id}")
async def update_tenant(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    tenant_data: TenantUpdate = None,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Update a tenant (Platform Admin only)
    """
    service = TenantService(db, tenant)
    try:
        updates = tenant_data.model_dump(exclude_unset=True)
        return await service.update_tenant(tenant_id, **updates)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tenant_id}/suspend")
async def suspend_tenant(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    request: TenantSuspendRequest = None,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Suspend a tenant (Platform Admin only)
    """
    service = TenantService(db, tenant)
    try:
        return await service.suspend_tenant(tenant_id, request.reason)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{tenant_id}/activate")
async def activate_tenant(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Activate a suspended tenant (Platform Admin only)
    """
    service = TenantService(db, tenant)
    try:
        return await service.activate_tenant(tenant_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID = Path(..., description="Tenant ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Delete a tenant (Platform Admin only)

    WARNING: This will mark the tenant as deleted. Data archiving recommended.
    """
    service = TenantService(db, tenant)
    try:
        return await service.delete_tenant(tenant_id)
    except PermissionError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
