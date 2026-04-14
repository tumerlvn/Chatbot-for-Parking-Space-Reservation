"""State definitions for orchestrator graph."""

from typing import TypedDict, Literal, Optional, List, Dict, Any, Annotated
from langgraph.graph.message import add_messages


class OrchestratorState(TypedDict, total=False):
    """
    Unified state for orchestration layer with checkpointing.

    Uses two-level checkpointing:
    - Orchestrator level: Stores coordination state (messages, metrics, events)
    - Subgraph level: Maintains agent-specific state (conversation context)
    """
    # Routing
    mode: Literal["user", "admin"]  # Which agent to route to

    # Thread mapping for subgraphs
    user_thread_id: Optional[str]  # Thread ID for user subgraph (e.g., "user_default_thread")
    admin_thread_id: Optional[str]  # Thread ID for admin subgraph (e.g., "admin_default_thread")

    # Conversation state (checkpointed by orchestrator)
    messages: Annotated[List, add_messages]  # Full conversation history

    # Agent-specific states (passed to subgraphs)
    user_state: Optional[Dict[str, Any]]  # User agent state
    admin_state: Optional[Dict[str, Any]]  # Admin agent state

    # Result from subgraph execution
    result: Optional[Dict[str, Any]]

    # Event system
    events: List[Dict[str, Any]]  # Event queue

    # Session management
    session_id: str  # Unique session ID
    thread_id: Optional[str]  # Thread ID for orchestrator checkpoint

    # Metrics and monitoring
    metrics: Dict[str, Any]  # Performance metrics

    # Shared data (cross-agent)
    shared_data: Dict[str, Any]  # Cross-agent communication

    # Error handling
    error: Optional[str]  # Error message if any
