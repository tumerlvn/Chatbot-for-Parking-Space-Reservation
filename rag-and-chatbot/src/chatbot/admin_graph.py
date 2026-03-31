"""Admin agent graph configuration."""

import os
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .admin_state import AdminGraphState
from .admin_nodes import (
    admin_router_node,
    list_pending_node,
    initiate_action_node,
    execute_action_node
)


def route_admin_intent(state: AdminGraphState) -> str:
    """Route based on admin intent."""
    intent = state.get("intent", "list_pending")

    if intent == "approve" or intent == "reject":
        return "initiate_action"
    elif intent == "list_pending":
        return "list_pending"
    else:
        return "list_pending"  # Default


def create_admin_graph():
    """Create admin agent graph with interrupt at initiate_action."""
    workflow = StateGraph(AdminGraphState)

    # Add nodes
    workflow.add_node("router", admin_router_node)
    workflow.add_node("list_pending", list_pending_node)
    workflow.add_node("initiate_action", initiate_action_node)
    workflow.add_node("execute_action", execute_action_node)

    # Entry point
    workflow.set_entry_point("router")

    # Router edges
    workflow.add_conditional_edges(
        "router",
        route_admin_intent,
        {
            "list_pending": "list_pending",
            "initiate_action": "initiate_action"
        }
    )

    # list_pending ends
    workflow.add_edge("list_pending", END)

    # initiate_action -> execute_action (after interrupt)
    workflow.add_edge("initiate_action", "execute_action")
    workflow.add_edge("execute_action", END)

    # Checkpointer for admin conversations
    checkpoint_db = os.path.join(os.path.dirname(__file__), "../../data/admin_checkpoints.sqlite")
    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    # INTERRUPT at execute_action (admin confirms via API)
    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["execute_action"]  # Pause before executing
    )

    return app
