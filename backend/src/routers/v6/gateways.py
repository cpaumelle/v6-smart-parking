# src/routers/v6/gateways.py

from fastapi import APIRouter, Depends, Query, HTTPException
from typing import Optional
from uuid import UUID

from ...core.database import get_db
from ...core.tenant_context_v6 import get_tenant_context_v6, TenantContextV6

router = APIRouter(prefix="/api/v6/gateways", tags=["gateways-v6"])

@router.get("")
async def list_gateways(
    include_offline: bool = Query(True, description="Include offline gateways"),
    site_id: Optional[UUID] = Query(None, description="Filter by site ID"),
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    List gateways with proper tenant scoping

    Key difference from v5: Gateways are now tenant-scoped
    """
    query = """
        SELECT id, tenant_id, gateway_id, name, location,
               last_seen_at, created_at, updated_at
        FROM gateways
        WHERE 1=1
    """
    params = []

    # Tenant scoping
    if not (tenant.is_viewing_platform_tenant and tenant.is_platform_admin):
        # Regular view: only tenant's gateways
        query += " AND tenant_id = $1"
        params.append(tenant.tenant_id)

    # Status filter
    if not include_offline:
        param_num = len(params) + 1
        query += f" AND last_seen_at > NOW() - INTERVAL '5 minutes'"

    # Site filter
    if site_id:
        param_num = len(params) + 1
        query += f" AND site_id = ${param_num}"
        params.append(site_id)

    query += " ORDER BY name"

    gateways = await db.fetch(query, *params)

    return {
        "gateways": [
            {
                "id": str(g['id']),
                "tenant_id": str(g['tenant_id']),
                "gateway_id": g['gateway_id'],
                "name": g['name'],
                "location": g.get('location'),
                "last_seen_at": g['last_seen_at'].isoformat() if g.get('last_seen_at') else None,
                "created_at": g['created_at'].isoformat() if g.get('created_at') else None
            }
            for g in gateways
        ],
        "count": len(gateways),
        "tenant_scope": str(tenant.tenant_id)
    }

@router.get("/{gateway_id}")
async def get_gateway(
    gateway_id: UUID,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """Get gateway details"""
    gateway = await db.fetchrow("""
        SELECT id, tenant_id, gateway_id, name, location,
               last_seen_at, created_at, updated_at
        FROM gateways
        WHERE id = $1 AND tenant_id = $2
    """, gateway_id, tenant.tenant_id)

    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")

    return {
        "id": str(gateway['id']),
        "tenant_id": str(gateway['tenant_id']),
        "gateway_id": gateway['gateway_id'],
        "name": gateway['name'],
        "location": gateway.get('location'),
        "last_seen_at": gateway['last_seen_at'].isoformat() if gateway.get('last_seen_at') else None,
        "created_at": gateway['created_at'].isoformat() if gateway.get('created_at') else None,
        "updated_at": gateway['updated_at'].isoformat() if gateway.get('updated_at') else None
    }

@router.get("/{gateway_id}/stats")
async def get_gateway_stats(
    gateway_id: UUID,
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """Get gateway statistics and device connections"""
    # Verify gateway exists and belongs to tenant
    gateway = await db.fetchrow("""
        SELECT id FROM gateways
        WHERE id = $1 AND tenant_id = $2
    """, gateway_id, tenant.tenant_id)

    if not gateway:
        raise HTTPException(status_code=404, detail="Gateway not found")

    # Count connected devices (devices that reported through this gateway recently)
    # This would require gateway_id tracking in sensor_readings table
    # For now, return placeholder
    return {
        "gateway_id": str(gateway_id),
        "connected_devices": 0,
        "uptime_percentage": 0,
        "message": "Statistics tracking not yet fully implemented"
    }
