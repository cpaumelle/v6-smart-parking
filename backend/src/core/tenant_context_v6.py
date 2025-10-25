# src/core/tenant_context_v6.py

from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status, Request
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from enum import IntEnum
import logging

logging.basicConfig(level=logging.ERROR)
logger = logging.getLogger(__name__)

class TenantType(str):
    PLATFORM = "platform"
    CUSTOMER = "customer"
    TRIAL = "trial"

class Role(IntEnum):
    VIEWER = 1
    OPERATOR = 2
    ADMIN = 3
    OWNER = 4
    PLATFORM_ADMIN = 999

class TenantContextV6(BaseModel):
    """Enhanced tenant context for v6"""

    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    tenant_type: str
    user_id: UUID
    username: str
    role: int
    is_platform_admin: bool
    subscription_tier: str = "basic"
    features: dict = {}
    limits: dict = {}

    class Config:
        arbitrary_types_allowed = True

    @property
    def is_viewing_platform_tenant(self) -> bool:
        """Check if currently viewing the platform tenant"""
        return str(self.tenant_id) == "00000000-0000-0000-0000-000000000000"

    @property
    def can_manage_all_tenants(self) -> bool:
        """Check if user can manage all tenants"""
        return self.is_platform_admin and self.is_viewing_platform_tenant

    def can_access_tenant(self, target_tenant_id: UUID) -> bool:
        """Check if user can access a specific tenant"""
        if self.is_platform_admin:
            return True
        return str(self.tenant_id) == str(target_tenant_id)

    async def apply_to_db(self, db: AsyncSession):
        """Apply tenant context to database session for RLS"""
        await db.execute(
            "SET LOCAL app.current_tenant_id = :tenant_id",
            {"tenant_id": str(self.tenant_id)}
        )
        await db.execute(
            "SET LOCAL app.is_platform_admin = :is_admin",
            {"is_admin": self.is_platform_admin}
        )

async def get_tenant_context_v6(request: Request) -> TenantContextV6:
    """
    Dependency to get enhanced tenant context from JWT token
    Extracts token from Authorization header
    """
    from ..core.security import decode_token
    from ..core.database import db as database

    logger.error(f"====== TENANT CONTEXT CALLED ======")
    logger.error(f"Request URL: {request.url}")
    logger.error(f"Request method: {request.method}")
    
    # Extract token from Authorization header
    auth_header = request.headers.get("Authorization")
    logger.error(f"Auth header present: {auth_header is not None}")
    
    if not auth_header:
        logger.error("ERROR: No Authorization header")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing authorization header"
        )
    
    if not auth_header.startswith("Bearer "):
        logger.error(f"ERROR: Invalid auth header format: {auth_header[:20]}")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization header format"
        )
    
    token = auth_header.split(" ")[1]
    logger.error(f"Token extracted: {token[:30]}...")

    try:
        # Decode JWT token
        payload = decode_token(token)
        logger.error(f"Token decoded - user_id: {payload.get('sub')}, tenant_id: {payload.get('tenant_id')}")

        # Get user and tenant info from database
        user_info = await database.fetchrow("""
            SELECT u.id as user_id, u.name as username, u.email,
                   um.role, um.tenant_id,
                   t.name as tenant_name, t.slug as tenant_slug, t.type as tenant_type,
                   t.subscription_tier
            FROM users u
            JOIN user_memberships um ON um.user_id = u.id
            JOIN tenants t ON t.id = um.tenant_id
            WHERE u.id = $1 AND um.tenant_id = $2 AND um.is_active = true
        """, UUID(payload['sub']), UUID(payload['tenant_id']))

        if not user_info:
            logger.error(f"ERROR: User not found for user_id={payload.get('sub')}, tenant_id={payload.get('tenant_id')}")
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User or tenant not found"
            )

        logger.error(f"User found: {user_info['email']}")

        # Determine if platform admin
        is_platform_admin = (
            user_info['tenant_type'] == 'platform' and
            user_info['role'] in ['owner', 'admin']
        )

        # Map role string to int for compatibility
        role_map = {'viewer': Role.VIEWER, 'operator': Role.OPERATOR,
                   'admin': Role.ADMIN, 'owner': Role.OWNER}
        role_int = role_map.get(user_info['role'], Role.VIEWER)
        if is_platform_admin:
            role_int = Role.PLATFORM_ADMIN

        logger.error(f"SUCCESS: Tenant context created for {user_info['email']}")

        return TenantContextV6(
            tenant_id=user_info['tenant_id'],
            tenant_name=user_info['tenant_name'],
            tenant_slug=user_info['tenant_slug'],
            tenant_type=user_info['tenant_type'],
            user_id=user_info['user_id'],
            username=user_info['username'],
            role=role_int,
            is_platform_admin=is_platform_admin,
            subscription_tier=user_info['subscription_tier'] or 'basic',
            features={"parking": True, "analytics": True, "api_access": True},
            limits={"max_devices": 1000, "max_gateways": 50, "max_spaces": 500}
        )

    except HTTPException:
        raise
    except Exception as e:
        import traceback
        logger.error(f"EXCEPTION in tenant_context:")
        logger.error(traceback.format_exc())
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
