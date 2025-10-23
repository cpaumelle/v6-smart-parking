"""Authentication Router - JWT-based authentication and tenant registration"""

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from datetime import datetime, timedelta
from typing import Optional
from uuid import UUID
from jose import JWTError

from ..core.database import get_db
from ..core.security import (
    hash_password,
    verify_password,
    create_access_token,
    create_refresh_token,
    decode_token,
    verify_token_type,
    ACCESS_TOKEN_EXPIRE_MINUTES,
    REFRESH_TOKEN_EXPIRE_DAYS
)
from ..schemas.auth import UserLogin, UserRegister, Token, TokenRefresh, UserResponse

router = APIRouter(prefix="/api/auth", tags=["authentication"])

# OAuth2 scheme for JWT
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")


@router.post("/register", response_model=Token, status_code=status.HTTP_201_CREATED)
async def register(
    user_data: UserRegister,
    db = Depends(get_db)
):
    """
    Register a new user and tenant

    Creates:
    1. A new tenant with the provided tenant_name and tenant_slug
    2. A new user associated with that tenant
    3. Returns JWT tokens for immediate login
    """
    try:
        # Check if email already exists
        existing_user = await db.fetchrow("""
            SELECT id FROM users WHERE email = $1
        """, user_data.email)

        if existing_user:
            raise HTTPException(
                status_code=400,
                detail="Email already registered"
            )

        # Check if tenant slug already exists
        existing_tenant = await db.fetchrow("""
            SELECT id FROM tenants WHERE slug = $1
        """, user_data.tenant_slug)

        if existing_tenant:
            raise HTTPException(
                status_code=400,
                detail="Tenant slug already taken"
            )

        # Create tenant
        tenant_id = await db.fetchval("""
            INSERT INTO tenants (
                name, slug, type, is_active,
                subscription_tier, created_at, updated_at
            )
            VALUES ($1, $2, 'customer', true, 'basic', $3, $3)
            RETURNING id
        """, user_data.tenant_name, user_data.tenant_slug, datetime.utcnow())

        # Hash password
        hashed_password = hash_password(user_data.password)

        # Create user
        user_id = await db.fetchval("""
            INSERT INTO users (
                email, name, password_hash,
                is_active, created_at, updated_at
            )
            VALUES ($1, $2, $3, true, $4, $4)
            RETURNING id
        """, user_data.email, user_data.username, hashed_password, datetime.utcnow())

        # Create user membership (link user to tenant with owner role)
        await db.execute("""
            INSERT INTO user_memberships (
                user_id, tenant_id, role, is_active, created_at, updated_at
            )
            VALUES ($1, $2, 'owner', true, $3, $3)
        """, user_id, tenant_id, datetime.utcnow())

        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": str(user_id),
                "tenant_id": str(tenant_id),
                "email": user_data.email,
                "role": "owner"
            }
        )
        refresh_token = create_refresh_token(user_id, tenant_id)

        # Get user details for response
        user = await db.fetchrow("""
            SELECT u.id, u.email, u.name as username, um.role, u.created_at,
                   t.id as tenant_id, t.name as tenant_name, t.slug as tenant_slug
            FROM users u
            JOIN user_memberships um ON um.user_id = u.id
            JOIN tenants t ON t.id = um.tenant_id
            WHERE u.id = $1 AND um.tenant_id = $2
        """, user_id, tenant_id)

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user['id']),
                "email": user['email'],
                "username": user['username'],
                "tenant_id": str(user['tenant_id']),
                "tenant_name": user['tenant_name'],
                "tenant_slug": user['tenant_slug'],
                "role": user['role'],  # This is a string: 'owner', 'admin', 'operator', 'viewer'
                "is_platform_admin": False,  # New users are never platform admins
                "created_at": user['created_at'].isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")


@router.post("/login", response_model=Token)
async def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db = Depends(get_db)
):
    """
    Login with email and password

    Returns JWT access token and refresh token.
    """
    try:
        # Find user by email (username field in OAuth2 form)
        # Get the first active membership (user could belong to multiple tenants)
        user = await db.fetchrow("""
            SELECT u.id, u.email, u.name as username, u.password_hash, u.is_active, u.created_at,
                   um.tenant_id, um.role, um.is_active as membership_active,
                   t.name as tenant_name, t.slug as tenant_slug, t.type as tenant_type
            FROM users u
            JOIN user_memberships um ON um.user_id = u.id
            JOIN tenants t ON t.id = um.tenant_id
            WHERE u.email = $1 AND um.is_active = true AND u.is_active = true
            ORDER BY um.created_at DESC
            LIMIT 1
        """, form_data.username)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Verify password
        if not verify_password(form_data.password, user['password_hash']):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Incorrect email or password",
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Check if user is active
        if not user['is_active'] or not user['membership_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        # Generate tokens
        access_token = create_access_token(
            data={
                "sub": str(user['id']),
                "tenant_id": str(user['tenant_id']),
                "email": user['email'],
                "role": user['role']
            }
        )
        refresh_token = create_refresh_token(user['id'], user['tenant_id'])

        # Determine if platform admin (platform tenant with owner/admin role)
        is_platform_admin = user['tenant_type'] == 'platform' and user['role'] in ['owner', 'admin']

        return {
            "access_token": access_token,
            "refresh_token": refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user['id']),
                "email": user['email'],
                "username": user['username'],
                "tenant_id": str(user['tenant_id']),
                "tenant_name": user['tenant_name'],
                "tenant_slug": user['tenant_slug'],
                "role": user['role'],
                "is_platform_admin": is_platform_admin,
                "created_at": user['created_at'].isoformat()
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Login failed: {str(e)}")


@router.post("/refresh")
async def refresh_token(
    token_data: TokenRefresh,
    db = Depends(get_db)
):
    """
    Refresh access token using refresh token

    Validates the refresh token and returns a new access token.
    """
    try:
        # Decode refresh token
        payload = decode_token(token_data.refresh_token)

        # Verify it's a refresh token
        if not verify_token_type(payload, "refresh"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type"
            )

        user_id = UUID(payload.get("sub"))
        tenant_id = UUID(payload.get("tenant_id"))

        # Get user from database to verify they still exist and are active
        user = await db.fetchrow("""
            SELECT u.id, u.email, u.username, u.tenant_id, u.role,
                   u.is_active, u.created_at,
                   t.name as tenant_name, t.slug as tenant_slug, t.type as tenant_type
            FROM users u
            JOIN tenants t ON t.id = u.tenant_id
            WHERE u.id = $1 AND u.tenant_id = $2
        """, user_id, tenant_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )

        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        # Generate new access token
        new_access_token = create_access_token(
            data={
                "sub": str(user['id']),
                "tenant_id": str(user['tenant_id']),
                "email": user['email'],
                "role": user['role']
            }
        )

        # Generate new refresh token
        new_refresh_token = create_refresh_token(user['id'], user['tenant_id'])

        # Determine if platform admin
        is_platform_admin = user['tenant_type'] == 'platform' and user['role'] >= 999

        return {
            "access_token": new_access_token,
            "refresh_token": new_refresh_token,
            "token_type": "bearer",
            "expires_in": ACCESS_TOKEN_EXPIRE_MINUTES * 60,
            "user": {
                "id": str(user['id']),
                "email": user['email'],
                "username": user['username'],
                "tenant_id": str(user['tenant_id']),
                "tenant_name": user['tenant_name'],
                "tenant_slug": user['tenant_slug'],
                "role": user['role'],
                "is_platform_admin": is_platform_admin,
                "created_at": user['created_at'].isoformat()
            }
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired refresh token"
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Token refresh failed: {str(e)}")


@router.post("/logout")
async def logout(
    token: str = Depends(oauth2_scheme),
    db = Depends(get_db)
):
    """
    Logout user and invalidate tokens

    TODO: Implement token blacklist
    """
    # TODO: Add token to blacklist
    return {
        "success": True,
        "message": "Logged out successfully"
    }


@router.get("/me")
async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db = Depends(get_db)
):
    """
    Get current authenticated user information

    Validates the JWT token and returns user details.
    """
    try:
        # Decode access token
        payload = decode_token(token)

        # Verify it's an access token
        if not verify_token_type(payload, "access"):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid token type",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id = UUID(payload.get("sub"))
        tenant_id = UUID(payload.get("tenant_id"))

        # Get user from database with user_memberships
        user = await db.fetchrow("""
            SELECT u.id, u.email, u.name as username, u.is_active, u.created_at,
                   um.role, um.tenant_id,
                   t.name as tenant_name, t.slug as tenant_slug, t.type as tenant_type
            FROM users u
            JOIN user_memberships um ON um.user_id = u.id
            JOIN tenants t ON t.id = um.tenant_id
            WHERE u.id = $1 AND um.tenant_id = $2 AND um.is_active = true
        """, user_id, tenant_id)

        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found",
                headers={"WWW-Authenticate": "Bearer"},
            )

        if not user['is_active']:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="User account is disabled"
            )

        # Determine if platform admin
        is_platform_admin = user['tenant_type'] == 'platform' and user['role'] >= 999

        return {
            "id": str(user['id']),
            "email": user['email'],
            "username": user['username'],
            "tenant_id": str(user['tenant_id']),
            "tenant_name": user['tenant_name'],
            "tenant_slug": user['tenant_slug'],
            "role": user['role'],
            "is_platform_admin": is_platform_admin,
            "created_at": user['created_at'].isoformat()
        }

    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"},
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get user info: {str(e)}")
