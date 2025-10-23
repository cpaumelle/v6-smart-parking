"""Reservation Pydantic schemas for V6"""

from pydantic import BaseModel, Field, field_validator
from typing import Optional, Dict, Any
from uuid import UUID
from datetime import datetime


class ReservationBase(BaseModel):
    """Base reservation schema"""
    space_id: UUID
    start_time: datetime
    end_time: datetime
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, info):
        if 'start_time' in info.data and v <= info.data['start_time']:
            raise ValueError('end_time must be after start_time')
        return v


class ReservationCreate(ReservationBase):
    """Schema for creating a reservation"""
    request_id: Optional[str] = Field(None, description="Idempotency key for duplicate prevention")


class ReservationUpdate(BaseModel):
    """Schema for updating a reservation"""
    start_time: Optional[datetime] = None
    end_time: Optional[datetime] = None
    notes: Optional[str] = None
    metadata: Optional[Dict[str, Any]] = None

    @field_validator('end_time')
    @classmethod
    def validate_end_time(cls, v, info):
        if v is not None and 'start_time' in info.data and info.data['start_time'] is not None:
            if v <= info.data['start_time']:
                raise ValueError('end_time must be after start_time')
        return v


class ReservationResponse(BaseModel):
    """Schema for reservation response"""
    id: UUID
    tenant_id: UUID
    space_id: UUID
    user_id: UUID
    user_email: Optional[str] = None
    user_name: Optional[str] = None
    start_time: datetime
    end_time: datetime
    status: str  # 'active', 'completed', 'cancelled', 'expired', 'no_show'
    checked_in: bool
    checked_in_at: Optional[datetime] = None
    checked_out_at: Optional[datetime] = None
    rate: Optional[float] = None
    total_cost: Optional[float] = None
    payment_status: str  # 'pending', 'paid', 'refunded'
    cancelled_at: Optional[datetime] = None
    cancelled_by: Optional[UUID] = None
    cancellation_reason: Optional[str] = None
    notes: Optional[str] = None
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class ReservationCancel(BaseModel):
    """Schema for cancelling a reservation"""
    cancellation_reason: Optional[str] = Field(None, max_length=500)


class ReservationListResponse(BaseModel):
    """Schema for listing reservations"""
    reservations: list[ReservationResponse]
    total: int
    page: int = 1
    page_size: int = 50
