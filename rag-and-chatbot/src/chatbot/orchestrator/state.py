"""State definitions for orchestrator graph."""

from typing import TypedDict, Literal, Optional, List, Dict, Any


class OrchestratorState(TypedDict, total=False):
    """
    Unified state for orchestration layer.

    The orchestrator routes between user and admin agents while collecting
    metrics, emitting events, and managing shared resources.
    """
    # Routing
    mode: Literal["user", "admin"]  # Which agent to route to

    # Agent-specific states (passed to subgraphs)
    user_state: Optional[Dict[str, Any]]  # User agent state
    admin_state: Optional[Dict[str, Any]]  # Admin agent state

    # Result from subgraph execution
    result: Optional[Dict[str, Any]]

    # Event system
    events: List[Dict[str, Any]]  # Event queue

    # Session management
    session_id: str  # Unique session ID
    thread_id: Optional[str]  # Thread ID for checkpointer

    # Metrics and monitoring
    metrics: Dict[str, Any]  # Performance metrics

    # Shared data (cross-agent)
    shared_data: Dict[str, Any]  # Cross-agent communication

    # Error handling
    error: Optional[str]  # Error message if any
