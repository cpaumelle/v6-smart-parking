"""Device Pydantic schemas for V6"""

from pydantic import BaseModel, Field
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class DeviceBase(BaseModel):
    """Base device schema"""
    dev_eui: str = Field(..., min_length=16, max_length=16, pattern="^[0-9A-F]{16}$")
    name: Optional[str] = Field(None, max_length=255)
    device_type: Optional[str] = Field(None, max_length=50)
    manufacturer: Optional[str] = Field(None, max_length=100)
    model: Optional[str] = Field(None, max_length=100)
    enabled: bool = Field(default=True)
    config: Dict[str, Any] = Field(default_factory=dict)


class DeviceResponse(DeviceBase):
    """Schema for device response"""
    id: UUID
    tenant_id: UUID
    status: str  # 'unassigned', 'assigned', 'active', 'inactive', 'maintenance', 'retired'
    lifecycle_state: str  # 'provisioned', 'commissioned', 'operational', 'decommissioned'
    assigned_space_id: Optional[UUID] = None
    assigned_at: Optional[datetime] = None
    last_seen_at: Optional[datetime] = None
    chirpstack_device_id: Optional[UUID] = None
    chirpstack_sync_status: Optional[str] = None
    chirpstack_last_sync: Optional[datetime] = None
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class DeviceAssignRequest(BaseModel):
    """Schema for assigning a device to a space"""
    space_id: UUID
    reason: str = Field(default="Manual assignment via API", max_length=500)


class DeviceUnassignRequest(BaseModel):
    """Schema for unassigning a device"""
    reason: str = Field(default="Manual unassignment via API", max_length=500)


class DeviceImportRequest(BaseModel):
    """Schema for bulk importing devices from ChirpStack"""
    application_id: str = Field(..., description="ChirpStack application ID")
    tenant_id: UUID
    auto_commission: bool = Field(default=False, description="Auto-commission devices after import")


class DevicePoolStatsResponse(BaseModel):
    """Schema for device pool statistics"""
    total_devices: int
    total_assigned: int
    total_unassigned: int
    tenants: list[Dict[str, Any]]
