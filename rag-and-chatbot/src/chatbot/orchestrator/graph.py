"""Orchestrator graph - master coordination layer."""

import os
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import OrchestratorState
from .nodes import (
    supervisor_node,
    notification_hub_node,
    health_monitor_node,
    user_subgraph_node,
    admin_subgraph_node
)


def route_from_supervisor(state: OrchestratorState) -> str:
    """
    Route from supervisor based on intent classification.

    Args:
        state: Current orchestrator state

    Returns:
        Next node name: "user_subgraph", "admin_subgraph", or "health_monitor"
    """
    intent = state.get("intent")

    if intent == "user":
        return "user_subgraph"
    elif intent == "admin":
        return "admin_subgraph"
    else:
        # No intent classified, skip to health monitor
        return "health_monitor"


def route_from_notification_hub(state: OrchestratorState) -> str:
    """
    Route from notification hub based on next action.

    If a reservation was created, automatically trigger admin approval flow.

    Args:
        state: Current orchestrator state

    Returns:
        Next node name: "admin_subgraph" or "health_monitor"
    """
    next_action = state.get("next_action")

    if next_action == "admin_approval_needed":
        return "admin_subgraph"
    else:
        return "health_monitor"


def create_orchestrator_graph():
    """
    Create the orchestrator graph using Supervisor Pattern with conditional routing.

    The orchestrator coordinates user and admin agents:
    1. Supervisor classifies intent
    2. Conditional routing to user or admin subgraph
    3. User flow can automatically trigger admin flow
    4. Notification hub broadcasts events
    5. Health monitor collects metrics

    Returns:
        Compiled orchestrator graph with checkpointer
    """
    workflow = StateGraph(OrchestratorState)

    # Add nodes
    workflow.add_node("supervisor", supervisor_node)
    workflow.add_node("user_subgraph", user_subgraph_node)
    workflow.add_node("admin_subgraph", admin_subgraph_node)
    workflow.add_node("notification_hub", notification_hub_node)
    workflow.add_node("health_monitor", health_monitor_node)

    # Entry point: supervisor classifies intent
    workflow.set_entry_point("supervisor")

    # Conditional routing from supervisor based on intent
    workflow.add_conditional_edges(
        "supervisor",
        route_from_supervisor,
        {
            "user_subgraph": "user_subgraph",
            "admin_subgraph": "admin_subgraph",
            "health_monitor": "health_monitor"
        }
    )

    # After user subgraph, go to notification hub
    workflow.add_edge("user_subgraph", "notification_hub")

    # Conditional routing from notification hub
    # If reservation created, automatically trigger admin flow
    workflow.add_conditional_edges(
        "notification_hub",
        route_from_notification_hub,
        {
            "admin_subgraph": "admin_subgraph",
            "health_monitor": "health_monitor"
        }
    )

    # After admin subgraph, go to health monitor
    workflow.add_edge("admin_subgraph", "health_monitor")

    # After health check, end
    workflow.add_edge("health_monitor", END)

    # Add checkpointer for orchestrator (two-level checkpointing)
    checkpoint_db = os.path.join(os.path.dirname(__file__), "../../../data/orchestrator_checkpoints.sqlite")
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # Compile with checkpointer (orchestrator maintains conversation state)
    app = workflow.compile(checkpointer=checkpointer)

    return app
