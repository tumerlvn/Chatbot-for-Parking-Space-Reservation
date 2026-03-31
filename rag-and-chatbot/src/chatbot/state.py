"""State definitions for LangGraph chatbot."""

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages


class ReservationData(TypedDict, total=False):
    """Reservation information collected from user."""
    name: Optional[str]
    car_number: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    availability_checked: Optional[bool]
    available_spots: Optional[list]
    count_by_type: Optional[dict]
    preferred_spot_type: Optional[str]
    reservation_id: Optional[int]
    assigned_spot_id: Optional[int]
    status: Optional[str]
    admin_decision_time: Optional[str]


class GraphState(TypedDict):
    """State that flows through the LangGraph."""
    messages: Annotated[List, add_messages]
    intent: Optional[str]
    reservation_data: ReservationData
    next_action: Optional[str]
    thread_id: Optional[str]
