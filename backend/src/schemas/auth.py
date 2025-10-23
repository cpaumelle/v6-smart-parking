"""Authentication Pydantic schemas for V6"""

from pydantic import BaseModel, EmailStr, Field
from typing import Optional
from uuid import UUID
from datetime import datetime


class UserLogin(BaseModel):
    """Schema for user login"""
    email: EmailStr
    password: str = Field(..., min_length=8)


class UserRegister(BaseModel):
    """Schema for user registration"""
    email: EmailStr
    password: str = Field(..., min_length=8)
    username: str = Field(..., min_length=3, max_length=50)
    tenant_name: str = Field(..., min_length=3, max_length=255, description="Tenant/organization name")
    tenant_slug: str = Field(..., min_length=3, max_length=100, pattern="^[a-z0-9-]+$", description="Tenant URL slug")


class UserResponse(BaseModel):
    """Schema for user response"""
    id: UUID
    email: str
    username: str
    tenant_id: UUID
    tenant_name: str
    tenant_slug: str
    role: str  # Role: 'owner', 'admin', 'operator', 'viewer'
    is_platform_admin: bool
    created_at: datetime

    class Config:
        from_attributes = True


class Token(BaseModel):
    """Schema for JWT token response"""
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int  # seconds
    user: dict  # Changed from UserResponse to dict to avoid circular import


class TokenRefresh(BaseModel):
    """Schema for refreshing access token"""
    refresh_token: str
