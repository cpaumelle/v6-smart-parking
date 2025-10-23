"""Pydantic schemas for V6 API"""

from .space import SpaceBase, SpaceCreate, SpaceUpdate, SpaceResponse
from .reservation import ReservationBase, ReservationCreate, ReservationUpdate, ReservationResponse, ReservationCancel
from .device import DeviceBase, DeviceResponse, DeviceAssignRequest, DeviceUnassignRequest
from .auth import UserLogin, UserRegister, Token, TokenRefresh

__all__ = [
    # Space schemas
    "SpaceBase",
    "SpaceCreate",
    "SpaceUpdate",
    "SpaceResponse",
    # Reservation schemas
    "ReservationBase",
    "ReservationCreate",
    "ReservationUpdate",
    "ReservationResponse",
    "ReservationCancel",
    # Device schemas
    "DeviceBase",
    "DeviceResponse",
    "DeviceAssignRequest",
    "DeviceUnassignRequest",
    # Auth schemas
    "UserLogin",
    "UserRegister",
    "Token",
    "TokenRefresh",
]
