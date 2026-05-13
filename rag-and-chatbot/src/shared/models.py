"""Pydantic models for database entities and API responses."""

from typing import Optional, Literal
from datetime import datetime
from pydantic import BaseModel, Field


class ParkingSpot(BaseModel):
    """Parking spot model."""
    id: int
    spot_number: str
    spot_type: str
    floor: str
    status: Literal["available", "occupied", "reserved"] = "available"
    price_per_hour: float = Field(default=5.0, description="Hourly rate for this spot")

    class Config:
        from_attributes = True


class Reservation(BaseModel):
    """Reservation model."""
    id: int
    user_name: str
    car_number: str
    start_time: str
    end_time: str
    reservation_time: str
    status: Literal["pending", "approved", "rejected", "cancelled"] = "pending"
    thread_id: Optional[str] = None
    spot_id: int
    # Additional spot details (from JOIN queries)
    spot_number: Optional[str] = None
    spot_type: Optional[str] = None
    floor: Optional[str] = None

    class Config:
        from_attributes = True


class AdminAction(BaseModel):
    """Admin action data model."""
    action_type: Literal["approve", "reject"]
    reservation_id: int
    admin_notes: str = ""
    completed: bool = False

    class Config:
        from_attributes = True
