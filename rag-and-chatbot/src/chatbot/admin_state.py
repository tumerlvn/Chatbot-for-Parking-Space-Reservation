"""State definitions for Admin Agent."""

from typing import TypedDict, Annotated, List, Optional
from langgraph.graph.message import add_messages


class AdminActionData(TypedDict, total=False):
    """Admin action details."""
    action_type: Optional[str]  # "approve" or "reject"
    reservation_id: Optional[int]  # Which reservation
    admin_notes: Optional[str]  # Optional notes
    completed: Optional[bool]  # Action completed via API


class AdminGraphState(TypedDict):
    """State for admin agent conversations."""
    messages: Annotated[List, add_messages]
    intent: Optional[str]  # "list_pending", "approve", "reject", "query"
    action_data: AdminActionData
    admin_id: Optional[str]  # Admin identifier
    thread_id: Optional[str]  # Thread ID for API resumption
