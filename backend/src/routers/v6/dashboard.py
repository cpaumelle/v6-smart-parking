# src/routers/v6/dashboard.py

from fastapi import APIRouter, Depends
from datetime import datetime
from typing import Dict, Any
import asyncio

from ...core.database import get_db
from ...core.tenant_context_v6 import get_tenant_context_v6, TenantContextV6

router = APIRouter(prefix="/api/v6/dashboard", tags=["dashboard-v6"])

@router.get("/data")
async def get_dashboard_data(
    tenant: TenantContextV6 = Depends(get_tenant_context_v6),
    db = Depends(get_db)
):
    """
    Get all dashboard data in a single optimized request
    Reduces frontend API calls from 5+ to 1
    """
    # Use asyncio.gather for parallel queries
    results = await asyncio.gather(
        _get_device_summary(db, tenant),
        _get_gateway_summary(db, tenant),
        _get_space_summary(db, tenant),
        _get_recent_activity(db, tenant),
        _get_system_health(db, tenant)
    )

    devices, gateways, spaces, recent_activity, system_health = results

    return {
        "devices": devices,
        "gateways": gateways,
        "spaces": spaces,
        "recent_activity": recent_activity,
        "system_health": system_health,
        "generated_at": datetime.utcnow().isoformat()
    }

async def _get_device_summary(db, tenant) -> Dict[str, Any]:
    """Get device summary statistics"""
    sensor_stats = await db.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
            COUNT(*) FILTER (WHERE status = 'unassigned') as unassigned,
            COUNT(*) FILTER (WHERE lifecycle_state = 'operational') as active,
            COUNT(*) FILTER (WHERE lifecycle_state != 'operational') as inactive
        FROM sensor_devices
        WHERE tenant_id = $1
    """, tenant.tenant_id)

    display_stats = await db.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE status = 'assigned') as assigned,
            COUNT(*) FILTER (WHERE status = 'unassigned') as unassigned
        FROM display_devices
        WHERE tenant_id = $1
    """, tenant.tenant_id)

    return {
        "sensors": {
            "total": sensor_stats['total'] or 0,
            "assigned": sensor_stats['assigned'] or 0,
            "unassigned": sensor_stats['unassigned'] or 0,
            "active": sensor_stats['active'] or 0,
            "inactive": sensor_stats['inactive'] or 0
        },
        "displays": {
            "total": display_stats['total'] or 0,
            "assigned": display_stats['assigned'] or 0,
            "unassigned": display_stats['unassigned'] or 0
        },
        "total_devices": (sensor_stats['total'] or 0) + (display_stats['total'] or 0)
    }

async def _get_gateway_summary(db, tenant) -> Dict[str, Any]:
    """Get gateway summary statistics"""
    stats = await db.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE last_seen_at > NOW() - INTERVAL '5 minutes') as online,
            COUNT(*) FILTER (WHERE last_seen_at <= NOW() - INTERVAL '5 minutes' OR last_seen_at IS NULL) as offline
        FROM gateways
        WHERE tenant_id = $1
    """, tenant.tenant_id)

    return {
        "total": stats['total'] or 0,
        "online": stats['online'] or 0,
        "offline": stats['offline'] or 0
    }

async def _get_space_summary(db, tenant) -> Dict[str, Any]:
    """Get space summary statistics"""
    stats = await db.fetchrow("""
        SELECT
            COUNT(*) as total,
            COUNT(*) FILTER (WHERE current_state = 'free') as free,
            COUNT(*) FILTER (WHERE current_state = 'occupied') as occupied,
            COUNT(*) FILTER (WHERE current_state = 'reserved') as reserved,
            COUNT(*) FILTER (WHERE current_state = 'maintenance') as maintenance,
            COUNT(*) FILTER (WHERE current_state = 'unknown') as unknown
        FROM spaces
        WHERE tenant_id = $1 AND archived_at IS NULL
    """, tenant.tenant_id)

    total = stats['total'] or 0
    occupied = stats['occupied'] or 0

    return {
        "total": total,
        "free": stats['free'] or 0,
        "occupied": occupied,
        "reserved": stats['reserved'] or 0,
        "maintenance": stats['maintenance'] or 0,
        "unknown": stats['unknown'] or 0,
        "available": stats['free'] or 0,
        "occupancy_rate": round((occupied / total * 100) if total > 0 else 0, 2)
    }

async def _get_recent_activity(db, tenant) -> list:
    """Get recent activity logs"""
    # Get recent reservations and state changes
    recent_reservations = await db.fetch("""
        SELECT
            'reservation' as activity_type,
            r.created_at as timestamp,
            r.user_name as user_name,
            s.code as space_code,
            r.status as status
        FROM reservations r
        JOIN spaces s ON s.id = r.space_id
        WHERE r.tenant_id = $1
        ORDER BY r.created_at DESC
        LIMIT 10
    """, tenant.tenant_id)

    return [
        {
            "type": r['activity_type'],
            "timestamp": r['timestamp'].isoformat(),
            "user": r['user_name'],
            "space": r['space_code'],
            "status": r['status']
        }
        for r in recent_reservations
    ]

async def _get_system_health(db, tenant) -> Dict[str, Any]:
    """Get system health metrics"""
    # Check database connectivity
    db_ok = True
    try:
        await db.fetchval("SELECT 1")
    except:
        db_ok = False

    # Get pending downlink commands
    pending_commands = await db.fetchval("""
        SELECT COUNT(*)
        FROM downlink_queue
        WHERE tenant_id = $1 AND status IN ('queued', 'pending')
    """, tenant.tenant_id)

    return {
        "status": "healthy" if db_ok else "degraded",
        "database": "ok" if db_ok else "error",
        "pending_commands": pending_commands or 0
    }
