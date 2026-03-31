"""LangGraph graph configuration and routing logic."""

import os
import sqlite3
from langgraph.graph import StateGraph, END
from langgraph.checkpoint.sqlite import SqliteSaver

from .state import GraphState
from .nodes import (
    router_node,
    rag_node,
    reservation_collector_node,
    create_reservation_node,
    await_approval_node,
    finalize_reservation_node,
    status_checker_node
)


def route_after_classification(state: GraphState) -> str:
    """Route based on classified intent."""
    intent = state.get("intent", "question")

    if intent == "reservation":
        return "reservation_node"
    elif intent == "status_check":
        return "status_checker"
    else:
        return "rag_node"


def check_reservation_complete(state: GraphState) -> str:
    """Check if all reservation fields have been collected."""
    res_data = state.get("reservation_data", {})
    required_fields = ["name", "car_number", "start_time", "end_time", "preferred_spot_type"]

    if all(res_data.get(field) for field in required_fields):
        if res_data.get("availability_checked") and res_data.get("available_spots"):
            return "complete"

    return "incomplete"


def should_continue(state: GraphState) -> str:
    """Determine if conversation should continue or end."""
    next_action = state.get("next_action", "wait_for_user")
    return END if next_action == "wait_for_user" else "router"


def create_chatbot_graph():
    """Create and compile LangGraph with interrupt for admin approval."""
    workflow = StateGraph(GraphState)

    workflow.add_node("router", router_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("reservation_node", reservation_collector_node)
    workflow.add_node("create_reservation", create_reservation_node)
    workflow.add_node("await_approval", await_approval_node)
    workflow.add_node("finalize_reservation", finalize_reservation_node)
    workflow.add_node("status_checker", status_checker_node)

    workflow.set_entry_point("router")

    workflow.add_conditional_edges(
        "router",
        route_after_classification,
        {
            "rag_node": "rag_node",
            "reservation_node": "reservation_node",
            "status_checker": "status_checker"
        }
    )

    workflow.add_edge("rag_node", END)

    workflow.add_edge("status_checker", END)

    workflow.add_conditional_edges(
        "reservation_node",
        check_reservation_complete,
        {
            "complete": "create_reservation",   # All data collected → create in DB
            "incomplete": END                   # Still collecting → wait for next turn
        }
    )

    workflow.add_edge("create_reservation", "await_approval")
    workflow.add_edge("await_approval", "finalize_reservation")
    workflow.add_edge("finalize_reservation", END)

    checkpoint_db = os.path.join(os.path.dirname(__file__), "../../data/checkpoints.sqlite")

    conn = sqlite3.connect(checkpoint_db, check_same_thread=False)
    checkpointer = SqliteSaver(conn)

    app = workflow.compile(
        checkpointer=checkpointer,
        interrupt_before=["await_approval"]  # Pause here for admin approval
    )

    return app



def save_graph_visualization(graph, output_path: str = "chatbot_graph.png"):
    """
    Saves a visual representation of the graph structure.

    Args:
        graph: The compiled LangGraph
        output_path: Where to save the visualization
    """
    try:
        from IPython.display import Image, display
        display(Image(graph.get_graph().draw_mermaid_png()))
    except Exception as e:
        print(f"Could not generate graph visualization: {e}")
        print("Install required packages: pip install pygraphviz")
