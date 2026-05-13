"""State definitions for orchestrator graph."""

from typing import Literal, Optional, List, Dict, Any
from pydantic import BaseModel, Field


class OrchestratorState(BaseModel):
    """
    Unified state for orchestration layer with checkpointing.

    Uses two-level checkpointing:
    - Orchestrator level: Stores coordination state (messages, metrics, events)
    - Subgraph level: Maintains agent-specific state (conversation context)
    """
    # Routing
    mode: Optional[Literal["user", "admin"]] = None  # Which agent to route to (backward compat - use intent instead)
    intent: Optional[str] = None  # Classified intent (user/admin)
    next_action: Optional[str] = None  # Next action to take (e.g., "admin_approval_needed")

    # Thread mapping for subgraphs
    user_thread_id: Optional[str] = None  # Thread ID for user subgraph (e.g., "user_default_thread")
    admin_thread_id: Optional[str] = None  # Thread ID for admin subgraph (e.g., "admin_default_thread")

    # Conversation state (checkpointed by orchestrator)
    messages: List[Any] = Field(default_factory=list)  # Full conversation history

    # Agent-specific states (passed to subgraphs)
    user_state: Optional[Dict[str, Any]] = None  # User agent state
    admin_state: Optional[Dict[str, Any]] = None  # Admin agent state

    # Data from subgraph execution
    result: Optional[Dict[str, Any]] = None
    reservation_data: Dict[str, Any] = Field(default_factory=dict)  # Reservation data from user agent
    action_data: Dict[str, Any] = Field(default_factory=dict)  # Action data from admin agent

    # Event system
    events: List[Dict[str, Any]] = Field(default_factory=list)  # Event queue

    # Session management
    session_id: str = ""  # Unique session ID
    thread_id: Optional[str] = None  # Thread ID for orchestrator checkpoint

    # Metrics and monitoring
    metrics: Dict[str, Any] = Field(default_factory=dict)  # Performance metrics

    # Shared data (cross-agent)
    shared_data: Dict[str, Any] = Field(default_factory=dict)  # Cross-agent communication

    # Error handling
    error: Optional[str] = None  # Error message if any

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
