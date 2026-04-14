"""Orchestrator graph - master coordination layer."""

from langgraph.graph import StateGraph, END

from .state import OrchestratorState
from .nodes import (
    supervisor_node,
    notification_hub_node,
    health_monitor_node
)


def create_orchestrator_graph():
    """
    Create the orchestrator graph using Supervisor Pattern.

    The orchestrator coordinates user and admin agents:
    1. Supervisor routes to appropriate subgraph
    2. Notification hub broadcasts events
    3. Health monitor collects metrics
    4. Returns result to caller

    Returns:
        Compiled orchestrator graph (no checkpointer - subgraphs have their own)
    """
    workflow = StateGraph(OrchestratorState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("notification_hub", notification_hub_node)
    workflow.add_node("health_monitor", health_monitor_node)

    # Entry point: supervisor routes to subgraphs
    workflow.set_entry_point("supervisor")

    # After supervisor, always broadcast events
    workflow.add_edge("supervisor", "notification_hub")

    # After notifications, collect metrics
    workflow.add_edge("notification_hub", "health_monitor")

    # After health check, end
    workflow.add_edge("health_monitor", END)

    # Compile without checkpointer (subgraphs maintain their own state)
    app = workflow.compile()

    return app
