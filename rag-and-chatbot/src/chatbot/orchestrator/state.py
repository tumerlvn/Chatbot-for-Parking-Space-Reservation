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
    mode: Literal["user", "admin"] = "user"  # Which agent to route to

    # Thread mapping for subgraphs
    user_thread_id: Optional[str] = None  # Thread ID for user subgraph (e.g., "user_default_thread")
    admin_thread_id: Optional[str] = None  # Thread ID for admin subgraph (e.g., "admin_default_thread")

    # Conversation state (checkpointed by orchestrator)
    messages: List[Any] = Field(default_factory=list)  # Full conversation history

    # Agent-specific states (passed to subgraphs)
    user_state: Optional[Dict[str, Any]] = None  # User agent state
    admin_state: Optional[Dict[str, Any]] = None  # Admin agent state

    # Result from subgraph execution
    result: Optional[Dict[str, Any]] = None

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
