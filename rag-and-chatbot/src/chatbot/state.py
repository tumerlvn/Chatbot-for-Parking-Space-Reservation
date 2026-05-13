"""State definitions for LangGraph chatbot."""

from typing import Annotated, List, Optional, Any
from pydantic import BaseModel, Field
from langgraph.graph.message import add_messages


class ReservationData(BaseModel):
    """Reservation information collected from user."""
    name: Optional[str] = None
    car_number: Optional[str] = None
    start_time: Optional[str] = None
    end_time: Optional[str] = None
    availability_checked: Optional[bool] = None
    available_spots: Optional[List[dict]] = None
    count_by_type: Optional[dict] = None
    preferred_spot_type: Optional[str] = None
    reservation_id: Optional[int] = None
    assigned_spot_id: Optional[int] = None
    status: Optional[str] = None
    admin_decision_time: Optional[str] = None

    class Config:
        arbitrary_types_allowed = True


class GraphState(BaseModel):
    """State that flows through the LangGraph."""
    messages: List[Any] = Field(default_factory=list)
    intent: Optional[str] = None
    reservation_data: ReservationData = Field(default_factory=ReservationData)
    next_action: Optional[str] = None
    thread_id: Optional[str] = None
    retrieved_docs: List[Any] = Field(default_factory=list)  # Store retrieved documents for evaluation

    class Config:
        arbitrary_types_allowed = True

    def __getitem__(self, key: str) -> Any:
        """Enable dictionary-style access for backward compatibility."""
        return getattr(self, key)

    def __setitem__(self, key: str, value: Any) -> None:
        """Enable dictionary-style assignment for backward compatibility."""
        setattr(self, key, value)

    def get(self, key: str, default: Any = None) -> Any:
        """Enable dict.get() style access for backward compatibility."""
        return getattr(self, key, default)

    def __iter__(self):
        """Enable iteration over state keys for dict unpacking."""
        return iter(self.model_fields.keys())

    def keys(self):
        """Return state keys."""
        return self.model_fields.keys()

    def items(self):
        """Return state items."""
        return ((k, getattr(self, k)) for k in self.model_fields.keys())

    def values(self):
        """Return state values."""
        return (getattr(self, k) for k in self.model_fields.keys())

    def dict(self, **kwargs) -> dict:
        """Override dict method to ensure proper serialization."""
        return {k: getattr(self, k) for k in self.model_fields.keys()}
