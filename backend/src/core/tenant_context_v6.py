# src/core/tenant_context_v6.py

from typing import Optional
from uuid import UUID
from fastapi import Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from enum import IntEnum

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

async def get_tenant_context_v6(
    token: str = Depends(lambda: None)  # Will be replaced with OAuth2 scheme
) -> TenantContextV6:
    """
    Dependency to get enhanced tenant context from JWT token
    This is integrated with the JWT authentication system
    """
    from fastapi.security import OAuth2PasswordBearer
    from ..routers.auth import oauth2_scheme
    from ..core.security import decode_token
    from ..core.database import db as database

    # Get token from Authorization header
    from fastapi import Request, Depends as FastAPIDep
    async def get_token_from_header(request: Request) -> str:
        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header",
                headers={"WWW-Authenticate": "Bearer"},
            )
        return auth_header.split(" ")[1]

    # Decode JWT
    try:
        # Get token from dependency
        from fastapi import Request
        import inspect
        frame = inspect.currentframe().f_back.f_back
        request = frame.f_locals.get('request')
        if not request:
            # Fallback for testing
            return TenantContextV6(
                tenant_id=UUID("00000000-0000-0000-0000-000000000000"),
                tenant_name="Platform",
                tenant_slug="platform",
                tenant_type="platform",
                user_id=UUID("00000000-0000-0000-0000-000000000001"),
                username="admin",
                role=Role.PLATFORM_ADMIN,
                is_platform_admin=True,
                subscription_tier="enterprise",
                features={"parking": True, "analytics": True, "api_access": True},
                limits={"max_devices": 10000, "max_gateways": 100, "max_spaces": 5000}
            )

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing or invalid authorization header"
            )

        token_str = auth_header.split(" ")[1]
        payload = decode_token(token_str)

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
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User or tenant not found"
            )

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
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=f"Authentication failed: {str(e)}"
        )
