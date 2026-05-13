"""State definitions for Admin Agent."""

from typing import List, Optional, Any
from pydantic import BaseModel, Field


class AdminActionData(BaseModel):
    """Admin action details."""
    action_type: Optional[str] = None  # "approve" or "reject"
    reservation_id: Optional[int] = None  # Which reservation
    admin_notes: Optional[str] = None  # Optional notes
    completed: Optional[bool] = None  # Action completed via API

    class Config:
        arbitrary_types_allowed = True

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __iter__(self):
        return iter(self.model_fields.keys())

    def keys(self):
        return self.model_fields.keys()

    def items(self):
        return ((k, getattr(self, k)) for k in self.model_fields.keys())

    def values(self):
        return (getattr(self, k) for k in self.model_fields.keys())


class ReservationDetails(BaseModel):
    """Reservation details for confirmation writing."""
    reservation_id: Optional[int] = None
    name: Optional[str] = None
    car_number: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __iter__(self):
        return iter(self.model_fields.keys())

    def keys(self):
        return self.model_fields.keys()

    def items(self):
        return ((k, getattr(self, k)) for k in self.model_fields.keys())

    def values(self):
        return (getattr(self, k) for k in self.model_fields.keys())


class AdminGraphState(BaseModel):
    """State for admin agent conversations."""
    messages: List[Any] = Field(default_factory=list)
    intent: Optional[str] = None  # "list_pending", "approve", "reject", "query"
    action_data: AdminActionData = Field(default_factory=AdminActionData)
    admin_id: Optional[str] = None  # Admin identifier
    thread_id: Optional[str] = None  # Thread ID for API resumption
    should_write_confirmation: Optional[bool] = None  # Flag to write confirmation
    reservation_details: ReservationDetails = Field(default_factory=ReservationDetails)  # Details for confirmation

    class Config:
        arbitrary_types_allowed = True

    def __getitem__(self, key: str) -> Any:
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        return getattr(self, key, default)

    def __iter__(self):
        return iter(self.model_fields.keys())

    def keys(self):
        return self.model_fields.keys()

    def items(self):
        return ((k, getattr(self, k)) for k in self.model_fields.keys())

    def values(self):
        return (getattr(self, k) for k in self.model_fields.keys())
