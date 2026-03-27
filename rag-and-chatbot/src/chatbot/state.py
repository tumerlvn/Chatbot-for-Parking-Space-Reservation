"""
GraphState: The state object passed between nodes in the LangGraph.
This tracks the conversation history, user intent, and reservation data.
"""

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages


class ReservationData(TypedDict, total=False):
    """Tracks reservation information being collected"""
    name: Optional[str]
    car_number: Optional[str]
    start_time: Optional[str]
    end_time: Optional[str]
    availability_checked: Optional[bool]  # Flag to track if availability was verified
    available_spots: Optional[list]       # List of available spots from database
    count_by_type: Optional[dict]         # Count of available spots by type


class GraphState(TypedDict):
    """
    The state that flows through the graph.

    Attributes:
        messages: Conversation history (using LangGraph's add_messages reducer)
        intent: Current user intent ('question', 'reservation', or None)
        reservation_data: Dictionary storing collected reservation info
        next_action: What the graph should do next
    """
    messages: Annotated[List, add_messages]
    intent: Optional[str]
    reservation_data: ReservationData
    next_action: Optional[str]
