"""Space Pydantic schemas for V6"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class SpaceBase(BaseModel):
    """Base space schema"""
    code: str = Field(..., min_length=1, max_length=50, description="Space code/number")
    name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    enabled: bool = Field(default=True)
    auto_release_minutes: Optional[int] = Field(None, ge=1, le=1440)
    config: Dict[str, Any] = Field(default_factory=dict)


class SpaceCreate(SpaceBase):
    """Schema for creating a space"""
    site_id: UUID


class SpaceUpdate(BaseModel):
    """Schema for updating a space"""
    code: Optional[str] = Field(None, min_length=1, max_length=50)
    name: Optional[str] = Field(None, max_length=255)
    display_name: Optional[str] = Field(None, max_length=255)
    enabled: Optional[bool] = None
    auto_release_minutes: Optional[int] = Field(None, ge=1, le=1440)
    config: Optional[Dict[str, Any]] = None
    current_state: Optional[str] = None


class SpaceResponse(SpaceBase):
    """Schema for space response"""
    id: UUID
    tenant_id: UUID
    site_id: UUID
    sensor_device_id: Optional[UUID] = None
    display_device_id: Optional[UUID] = None
    current_state: str  # 'free', 'occupied', 'reserved', 'maintenance', 'unknown'
    sensor_state: Optional[str] = None
    display_state: Optional[str] = None
    state_changed_at: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SpaceAvailabilityRequest(BaseModel):
    """Request to check space availability"""
    start_time: datetime
    end_time: datetime


class SpaceAvailabilityResponse(BaseModel):
    """Response for space availability"""
    space_id: UUID
    is_available: bool
    current_state: str
    conflicting_reservations: list = Field(default_factory=list)
