"""
LangGraph StateGraph Definition
This creates the graph structure that routes between nodes
"""

from langgraph.graph import StateGraph, END
from langgraph.checkpoint.memory import MemorySaver

from .state import GraphState
from .nodes import (
    router_node,
    rag_node,
    reservation_collector_node
)


def route_after_classification(state: GraphState) -> str:
    """
    Conditional edge function that routes based on classified intent.

    Returns:
        - "rag_node" if intent is "question"
        - "reservation_node" if intent is "reservation"
    """
    intent = state.get("intent", "question")

    if intent == "reservation":
        return "reservation_node"
    else:
        return "rag_node"


def should_continue(state: GraphState) -> str:
    """
    Determines if the conversation should continue or end.

    Returns:
        - END if next_action is "wait_for_user"
        - Otherwise continues processing
    """
    next_action = state.get("next_action", "wait_for_user")

    if next_action == "wait_for_user":
        return END
    else:
        return "router"


def create_chatbot_graph():
    """
    Creates and compiles the LangGraph StateGraph.

    Graph Structure:
        START → router → [rag_node | reservation_node] → END

    Returns:
        Compiled StateGraph ready to use
    """
    # Initialize the graph
    workflow = StateGraph(GraphState)

    # Add nodes
    workflow.add_node("router", router_node)
    workflow.add_node("rag_node", rag_node)
    workflow.add_node("reservation_node", reservation_collector_node)

    # Set entry point
    workflow.set_entry_point("router")

    # Add conditional edges from router
    workflow.add_conditional_edges(
        "router",
        route_after_classification,
        {
            "rag_node": "rag_node",
            "reservation_node": "reservation_node"
        }
    )

    # Add edges from handler nodes back to END
    workflow.add_edge("rag_node", END)
    workflow.add_edge("reservation_node", END)

    # Compile the graph with memory checkpointing
    memory = MemorySaver()
    app = workflow.compile(checkpointer=memory)

    return app


# ============================================================================
# Helper function to visualize the graph (optional)
# ============================================================================

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
